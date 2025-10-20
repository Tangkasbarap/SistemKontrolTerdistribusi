
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

plot "sensor_data.dat" using 1:2 smooth csplines ls 1 title "Temperature (°C)",      "sensor_data.dat" using 1:3 smooth csplines ls 2 title "Humidity (%)",      "sensor_data.dat" using 1:4 smooth csplines ls 3 title "Hot Side Outlet (°C)",      "sensor_data.dat" using 1:5 smooth csplines ls 4 title "Cold Side Outlet (°C)",      "sensor_data.dat" using 1:6 smooth csplines ls 5 title "Heat Duty (W)"
