import serial
import time
import re
import json
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WriteOptions
import xml.etree.ElementTree as ET
from pathlib import Path

# ============================================================
# 🔧 KONFIGURASI SISTEM
# ============================================================

# Serial Port ESP32
ESP32_PORT = "COM8"
ESP32_BAUD = 115200

# InfluxDB Config
INFLUX_URL = "http://localhost:8086"
INFLUX_ORG = "my-org"
INFLUX_BUCKET = "my-bucket"
INFLUX_TOKEN = "b75UTtBsP_GubiwMJ3K-9EFTKIvpgqiSAGppp8IG4fIk9uf1ZKimaiKBVa1D6wzKpLsrmfw7U6do4U-BXxBQAQ=="

# ThingsBoard MQTT BASIC (tanpa Access Token)
THINGSBOARD_HOST = "demo.thingsboard.io"
THINGSBOARD_PORT = 1883
MQTT_CLIENT_ID = "Kelompok18"
MQTT_USERNAME = "204223"       # isi dari credential di ThingsBoard
MQTT_PASSWORD = "gateway1"    # isi dari credential di ThingsBoard

# DWSIM Simulation Result File
DWSIM_FILE = r"C:\hello-rust\dwsim\141416f0-1f72-4d21-84c8-481c08dc0cc6.xml"

# ============================================================
# 📂 FUNGSI: BACA FILE DWSIM
# ============================================================

def read_dwsim_results(path: str):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        tree = ET.parse(str(p))
        root = tree.getroot()
        for ex in root.findall(".//SimulationObject"):
            t = (ex.findtext("Type") or "").lower()
            if "exchanger" in t:
                hot_t = ex.findtext("HotSideOutletTemperature")
                cold_t = ex.findtext("ColdSideOutletTemperature")
                duty = ex.findtext("HeatDuty") or ex.findtext("Q")
                return {
                    "hot_side_outlet_temp": float(hot_t) - 273.15 if hot_t else None,
                    "cold_side_outlet_temp": float(cold_t) - 273.15 if cold_t else None,
                    "heat_duty": float(duty) if duty else None
                }
        return {}
    except Exception as e:
        print("❌ Error baca DWSIM:", e)
        return {}

# ============================================================
# 🚀 MAIN PROGRAM
# ============================================================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Terhubung ke ThingsBoard via MQTT Basic.")
    else:
        print(f"❌ Gagal konek ke ThingsBoard (rc={rc})")

def on_publish(client, userdata, mid):
    print("📤 Data berhasil dikirim ke ThingsBoard.")

try:
    # InfluxDB
    influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx.write_api(write_options=WriteOptions(batch_size=1))
    print("✅ Koneksi ke InfluxDB berhasil.")

    # MQTT ThingsBoard
    tb_client = mqtt.Client(client_id=MQTT_CLIENT_ID)
    tb_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    tb_client.on_connect = on_connect
    tb_client.on_publish = on_publish
    tb_client.connect(THINGSBOARD_HOST, THINGSBOARD_PORT, 60)
    tb_client.loop_start()

    # Serial
    ser = serial.Serial(ESP32_PORT, ESP32_BAUD, timeout=2)
    print(f"✅ Terhubung ke ESP32 di {ESP32_PORT} @ {ESP32_BAUD} baud.")

    temp = None
    rh = None

    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if not line:
            continue

        print(f"📨 Serial: {line}")

        # Baca data dari output ESP32
        m_t = re.search(r"T\s*=\s*([0-9]+\.[0-9]+)", line)
        m_rh = re.search(r"RH\s*=\s*([0-9]+\.[0-9]+)", line)

        if m_t:
            temp = float(m_t.group(1))
        if m_rh:
            rh = float(m_rh.group(1))

        if temp is not None and rh is not None:
            # Baca simulasi dari DWSIM
            sim_vals = read_dwsim_results(DWSIM_FILE)
            print(f"📊 Sensor: Temp={temp}°C, RH={rh}% | Sim={sim_vals}")

            # Kirim ke InfluxDB
            point = Point("data_gateway").field("temperature", temp).field("humidity", rh)
            for k, v in sim_vals.items():
                if v is not None:
                    point.field(k, v)
            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
            print("✅ Data dikirim ke InfluxDB.")

            # Kirim ke ThingsBoard
            payload = {"temperature": temp, "humidity": rh}
            payload.update(sim_vals)
            tb_client.publish("v1/devices/me/telemetry", json.dumps(payload), qos=1)
            print("✅ Data dikirim ke ThingsBoard.")

            # Reset variabel supaya tidak kirim dobel
            temp, rh = None, None

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\n🛑 Dihentikan oleh user.")
finally:
    if 'ser' in locals() and ser.is_open:
        ser.close()
        print("🔌 Serial ditutup.")
    if 'tb_client' in locals():
        tb_client.loop_stop()
        tb_client.disconnect()
        print("🔌 MQTT ditutup.")
    if 'influx' in locals():
        influx.close()
        print("🔌 InfluxDB ditutup.")
