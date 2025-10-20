#![no_std]
#![no_main]

use panic_halt as _;
use esp_hal::{
    Config,
    uart::{Uart, Config as UartConfig},
    gpio::{Output, Level},
    time::{Instant, Duration},
};
use esp_println::println;

esp_bootloader_esp_idf::esp_app_desc!();

const BAUD: u32 = 9_600;
const SID:  u8  = 1;
const TURNAROUND_SPINS: u32 = 50_000;
const TIMEOUT_SPINS:    u32 = 200_000;

#[esp_hal::main]
fn main() -> ! {
    let p = esp_hal::init(Config::default());

    // UART1 untuk RS485 (sensor SHT20)
    let mut uart = Uart::new(p.UART1, UartConfig::default().with_baudrate(BAUD))
        .expect("UART1 init failed")
        .with_tx(p.GPIO17)
        .with_rx(p.GPIO18);

    // === PIN AKTUATOR ===
    let mut fan_relay = Output::new(p.GPIO15, Level::High, Default::default()); // default: mati
    let mut in1 = Output::new(p.GPIO4, Level::Low, Default::default());
    let mut in2 = Output::new(p.GPIO5, Level::Low, Default::default());
    let mut in3 = Output::new(p.GPIO12, Level::Low, Default::default());
    let mut in4 = Output::new(p.GPIO13, Level::Low, Default::default());

    println!("\n=== SHT20 + Aktuator Loop Start ===");

    loop {
        // ---------- BACA RH ----------
        let mut req = [0u8; 8];
        req[0] = SID;
        req[1] = 0x04;
        req[2..4].copy_from_slice(&0x0002u16.to_be_bytes());
        req[4..6].copy_from_slice(&1u16.to_be_bytes());
        let crc = crc16(&req[..6]);
        req[6] = (crc & 0xFF) as u8;
        req[7] = (crc >> 8) as u8;

        let _ = uart.write(&req);
        let _ = uart.flush();
        short_spin(TURNAROUND_SPINS);

        let mut rx = [0u8; 32];
        let mut n = 0usize;
        let mut spins = 0u32;
        while spins < TIMEOUT_SPINS && n < rx.len() {
            let mut b = [0u8; 1];
            match uart.read(&mut b) {
                Ok(1) => { rx[n] = b[0]; n += 1; if n >= 7 { break; } }
                _ => { short_spin(1_000); spins += 1; }
            }
        }
        if n >= 7 && (rx[1] & 0x80) == 0 && rx[2] == 2 && check_crc(&rx[..n]) {
            let raw_rh = u16::from_be_bytes([rx[3], rx[4]]);
            println!("RH = {:.1} %", raw_rh as f32 / 10.0);
        }

        // ---------- BACA T ----------
        req[2..4].copy_from_slice(&0x0001u16.to_be_bytes());
        let crc2 = crc16(&req[..6]);
        req[6] = (crc2 & 0xFF) as u8;
        req[7] = (crc2 >> 8) as u8;

        let _ = uart.write(&req);
        let _ = uart.flush();
        short_spin(TURNAROUND_SPINS);

        n = 0;
        spins = 0;
        while spins < TIMEOUT_SPINS && n < rx.len() {
            let mut b = [0u8; 1];
            match uart.read(&mut b) {
                Ok(1) => { rx[n] = b[0]; n += 1; if n >= 7 { break; } }
                _ => { short_spin(1_000); spins += 1; }
            }
        }

        if n >= 7 && (rx[1] & 0x80) == 0 && rx[2] == 2 && check_crc(&rx[..n]) {
            let raw_t = u16::from_be_bytes([rx[3], rx[4]]);
            let suhu = raw_t as f32 / 10.0;
            println!("T = {:.1} °C", suhu);

            // === AKTUATOR LOGIC ===
            if suhu > 30.0 {
                println!("🔥 Suhu > 30°C → Fan ON, Stepper Jalan");
                fan_relay.set_low();  // aktif LOW → relay nyala
                stepper_forward(&mut in1, &mut in2, &mut in3, &mut in4, 64);
            } else {
                println!("✅ Suhu <= 30°C → Fan OFF");
                fan_relay.set_high(); // relay mati
            }

        } else {
            println!("⚠️ Gagal baca suhu, relay dimatikan sebagai default");
            fan_relay.set_high(); // safety: matikan fan kalau gagal
        }

        sleep(Duration::from_millis(1000));
    }
}

// === Stepper motor helper ===
fn stepper_forward(
    in1: &mut Output,
    in2: &mut Output,
    in3: &mut Output,
    in4: &mut Output,
    steps: usize,
) {
    // Urutan 4-step half drive (lebih banyak motor yang cocok dengan ini)
    let seq: [[u8; 4]; 4] = [
        [1, 0, 1, 0],
        [0, 1, 1, 0],
        [0, 1, 0, 1],
        [1, 0, 0, 1],
    ];

    for step in 0..steps {
        for phase in &seq {
            in1.set_level(if phase[0] == 1 { Level::High } else { Level::Low });
            in2.set_level(if phase[1] == 1 { Level::High } else { Level::Low });
            in3.set_level(if phase[2] == 1 { Level::High } else { Level::Low });
            in4.set_level(if phase[3] == 1 { Level::High } else { Level::Low });

            // Delay lebih lambat agar sinyal cukup kuat
            sleep(Duration::from_millis(5)); // kamu bisa naikkan ke 10ms kalau motor masih ga gerak
        }
    }

    // Matikan semua coil setelah selesai
    in1.set_low();
    in2.set_low();
    in3.set_low();
    in4.set_low();

    println!("Stepper selesai jalan {} langkah", steps);
}

// === Utils ===
fn short_spin(iter: u32) { for _ in 0..iter { core::hint::spin_loop(); } }

fn sleep(dur: Duration) {
    let start = Instant::now();
    while start.elapsed() < dur {
        core::hint::spin_loop();
    }
}

fn crc16(data: &[u8]) -> u16 {
    let mut crc = 0xFFFFu16;
    for &b in data {
        crc ^= b as u16;
        for _ in 0..8 {
            crc = if (crc & 1) != 0 { (crc >> 1) ^ 0xA001 } else { crc >> 1 };
        }
    }
    crc
}

fn check_crc(frame: &[u8]) -> bool {
    if frame.len() < 3 { return false; }
    let calc = crc16(&frame[..frame.len() - 2]);
    frame[frame.len() - 2] == (calc & 0xFF) as u8 && frame[frame.len() - 1] == (calc >> 8) as u8
}
