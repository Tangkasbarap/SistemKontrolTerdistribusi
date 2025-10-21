# 🌡️ Project SKT Kelompok 18

<p align="justify">
Proyek ini merupakan sistem end-to-end IoT yang mendemonstrasikan bagaimana data dari sensor suhu dan kelembapan dapat dikumpulkan menggunakan modul ESP32-S3, dikirim melalui protokol MQTT ke ThingsBoard untuk pemantauan berbasis cloud, serta disimpan secara lokal ke dalam InfluxDB untuk analisis dan visualisasi real-time menggunakan Gnuplot.  
Sistem ini menggabungkan komunikasi RS485, MQTT, dan database time-series untuk membentuk solusi monitoring yang terintegrasi, efisien, dan mudah dikembangkan.
</p>

---

## 🏗️ Arsitektur Sistem

### 🔹 1. Lapisan Sensor & Perangkat Keras (Edge Layer)
- Menggunakan **ESP32-S3** sebagai mikrokontroler utama.
- Sensor **SHT20** dihubungkan melalui **konverter RS485 to TTL**, memastikan komunikasi jarak jauh yang stabil dan tahan noise.
- ESP32 membaca data suhu dan kelembapan secara periodik.
- Data dikirim ke dua tujuan:
  1. **ThingsBoard** (via MQTT) untuk visualisasi cloud.
  2. **Gateway lokal** (via TCP atau HTTP) untuk penyimpanan ke InfluxDB.

### 🔹 2. Lapisan Komunikasi (MQTT Broker)
- Menggunakan **MQTT protocol** untuk komunikasi ringan antar perangkat IoT.
- ESP32 berperan sebagai **MQTT Publisher**, mengirimkan data ke **ThingsBoard** (yang juga berfungsi sebagai broker MQTT).
- Data dapat dipantau langsung di dashboard ThingsBoard (grafik, indikator, dan kontrol real-time).

### 🔹 3. Lapisan Backend & Penyimpanan (Local Server)
- Sebuah **gateway server** (ditulis dalam Rust atau Python) menerima data dari ESP32 dan menyimpannya ke **InfluxDB**.
- InfluxDB digunakan karena kemampuannya menangani **time-series data** secara efisien.
- Data diatur berdasarkan waktu (`timestamp`), dengan field seperti:
  - `temperature`
  - `humidity`
  - (opsional) `heat_duty`, `hot_side_outlet_temp`, `cold_side_outlet_temp`

### 🔹 4. Lapisan Visualisasi (Local Dashboard)
- Visualisasi dilakukan secara **real-time** menggunakan **Python + Gnuplot**.
- Script `gnuplot.py`:
  - Melakukan query ke InfluxDB menggunakan **Flux query**.
  - Memproses data dengan **Pandas**.
  - Menghasilkan file `.dat` yang divisualisasikan oleh **Gnuplot**.
- Tampilan grafik menampilkan kurva **suhu dan kelembapan terhadap waktu**, serta parameter tambahan jika tersedia.

---

## ⚙️ Komponen Utama

| Komponen | Teknologi | Deskripsi |
|-----------|------------|-----------|
| Sensor | SHT20 via RS485 → TTL | Membaca suhu & kelembapan |
| Mikrokontroler | ESP32-S3 | Mengirim data melalui MQTT |
| Cloud Platform | ThingsBoard | Visualisasi dan manajemen perangkat IoT |
| Gateway Server | Python / Rust | Menyimpan data ke InfluxDB lokal |
| Database | InfluxDB | Penyimpanan time-series data sensor |
| Dashboard Lokal | Gnuplot + Python | Visualisasi real-time data lokal |

---

## 📊 Contoh Visualisasi (Gnuplot)

Contoh tampilan plot suhu & kelembapan secara real-time:

```gnuplot

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

plot "sensor_data.dat" using 1:2 smooth csplines ls 1 title "Temperature (C)",      "sensor_data.dat" using 1:3 smooth csplines ls 2 title "Humidity (%)",      "sensor_data.dat" using 1:4 smooth csplines ls 3 title "Hot Side Outlet (C)",      "sensor_data.dat" using 1:5 smooth csplines ls 4 title "Cold Side Outlet (C)",      "sensor_data.dat" using 1:6 smooth csplines ls 5 title "Heat Duty (W)"
