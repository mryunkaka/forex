# Checklist keselamatan demo

## Sebelum shadow mode

- Pastikan EA dan service menunjukkan status `SHADOW`; tidak ada fungsi order yang aktif dari jalur model.
- Verifikasi sumber data, timestamp, zona waktu server, symbol, timeframe, spread, serta freshness.
- Pastikan respons model cocok dengan schema versi yang diizinkan; selain itu hasilnya `WAIT`.
- Pastikan request harian dan biaya berada di bawah plafon rancangan. Jika plafon tidak dapat ditegakkan, API tetap nonaktif.
- Simpan event ID, model/prompt/schema version, keputusan, penolakan, latensi, dan data PnL tanpa rahasia.

## Sebelum mengirim order demo

- Konfirmasi secara manual nomor akun dan server Finex adalah akun demo; jangan simpan password akun di proyek.
- Periksa komit EA31337 yang dipin, lisensi/dependensi, simbol, contract size, tick value/size, lot min/step, komisi, spread, swap, dan margin.
- Hitung risiko uang dari stop dan lot minimum. Lewati trade jika lot minimum melanggar batas risiko.
- Pastikan hard stop, batas rugi harian, drawdown stop, satu posisi maksimum, dan kill switch bekerja tanpa bergantung pada AI.
- Pastikan keputusan kedaluwarsa, duplicate ID ditolak, dan koneksi/data usang menolak entry baru.
- Pastikan MT5 HP login ke akun demo/server yang sama dan push status/error dapat diterima.
- Tinjau shadow report dan dapatkan persetujuan pengguna sebelum mengubah mode agar order demo dapat dikirim.

## Saat gangguan

- API/model/news feed gagal: jangan buka trade baru; catat satu error dan gunakan cooldown/backoff.
- VPS/terminal/bridge putus atau state akun tidak segar: jangan kirim order baru; kirim health alert bila kanal tersedia.
- Hard stop/daily stop/drawdown stop terlewati: blokir entry baru dan pertahankan batas stop yang telah terpasang.
- Jangan meminta atau mengirim kredensial melalui chat. Jika pernah terpapar, rotasi sebelum penggunaan.
