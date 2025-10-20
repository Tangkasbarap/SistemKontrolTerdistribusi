import time
import pandas as pd
from influxdb_client import InfluxDBClient
import subprocess

# === KONFIGURASI INFLUXDB ===
url = "http://localhost:8086"
token = "b75UTtBsP_GubiwMJ3K-9EFTKIvpgqiSAGppp8IG4fIk9uf1ZKimaiKBVa1D6wzKpLsrmfw7U6do4U-BXxBQAQ=="
org = "my-org"
bucket = "my-bucket"

# === KONEKSI KE INFLUXDB ===
client = InfluxDBClient(url=url, token=token, org=org)
query_api = client.query_api()

# === FUNGSI BACA DATA DARI INFLUXDB ===
def read_influx():
    query = f'''
    from(bucket: "{bucket}")
      |> range(start: -1h)
      |> filter(fn: (r) => r["_measurement"] == "data_gateway")
      |> filter(fn: (r) => r["_field"] == "temperature" or r["_field"] == "humidity" or 
                          r["_field"] == "hot_side_outlet_temp" or 
                          r["_field"] == "cold_side_outlet_temp" or 
                          r["_field"] == "heat_duty")
      |> aggregateWindow(every: 5s, fn: mean, createEmpty: false)
      |> yield(name: "mean")
    '''
    tables = query_api.query(org=org, query=query)
    records = []
    for table in tables:
        for record in table.records:
            records.append({
                "time": record.get_time(),
                "field": record.get_field(),
                "value": record.get_value()
            })
    if not records:
        print("⚠️ Tidak ada data.")
        return None

    df = pd.DataFrame(records)
    df_pivot = df.pivot(index="time", columns="field", values="value").reset_index()
    df_pivot = df_pivot.ffill()
    df_pivot.to_csv("sensor_data.dat", sep=" ", index=False,
                    columns=["time", "temperature", "humidity",
                             "hot_side_outlet_temp", "cold_side_outlet_temp", "heat_duty"])
    print(f"✅ Data diperbarui: {len(df_pivot)} baris")
    return df_pivot

# === FUNGSI MENJALANKAN GNUPLOT ===
def run_gnuplot():
    """Plot multi-line data sensor & simulasi DWSIM dengan tampilan rapi"""
    script = """
set datafile separator whitespace
set xdata time
set timefmt '"%Y-%m-%d %H:%M:%S+00:00"'
set format x "%H:%M:%S"
set xlabel "Waktu (HH:MM:SS)" font ",10"
set ylabel "Nilai Sensor" font ",10"
set title "Realtime Monitoring: Sensor + DWSIM Simulation" font ",12"
set grid lw 1 lc rgb "#cccccc"
set border lw 1 lc rgb "black"
set key outside top center box
set term qt persist size 1000,600
set xtics rotate by -30 font ",8"
set ytics font ",9"
set autoscale xfix
set autoscale yfix

# Warna & gaya garis
set style line 1 lc rgb "#e41a1c" lw 2
set style line 2 lc rgb "#377eb8" lw 2
set style line 3 lc rgb "#4daf4a" lw 2
set style line 4 lc rgb "#ff7f00" lw 2
set style line 5 lc rgb "#984ea3" lw 2

plot "sensor_data.dat" using 1:2 smooth csplines ls 1 title "Temperature (°C)", \
     "sensor_data.dat" using 1:3 smooth csplines ls 2 title "Humidity (%)", \
     "sensor_data.dat" using 1:4 smooth csplines ls 3 title "Hot Side Outlet (°C)", \
     "sensor_data.dat" using 1:5 smooth csplines ls 4 title "Cold Side Outlet (°C)", \
     "sensor_data.dat" using 1:6 smooth csplines ls 5 title "Heat Duty (W)"
"""
    with open("plot_script.gp", "w") as f:
        f.write(script)
    subprocess.Popen(["gnuplot", "plot_script.gp"])


# === MAIN LOOP ===
def main():
    print("📊 Menjalankan live Gnuplot monitoring...")
    run_gnuplot()
    while True:
        df = read_influx()
        if df is None:
            print("⚠️ Tidak ada data.")
        time.sleep(5)  # update setiap 5 detik

if __name__ == "__main__":
    main()
