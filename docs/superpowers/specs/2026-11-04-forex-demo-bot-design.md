# Rancangan Superpower: EA31337 + GPT melalui 9Router untuk Demo Finex MT5 di Ubuntu

Tanggal: 2026-11-04
Status: Draf revisi untuk ditinjau; belum disetujui untuk implementasi.

## Tujuan

Membuat superpower/skill Codex berbahasa Indonesia untuk audit EA31337 dan sistem trading demo aktif di VPS Ubuntu. Service Python memantau berita; model GPT-6 Luna melalui 9Router juga dipanggil ketika ada berita relevan, setup M5 yang lolos saringan EA, atau posisi melewati pemicu evaluasi rugi yang telah ditetapkan. Model menerima headline bersumber dan bertimestamp, konteks harga M5, waktu/tanggal/hari, sesi pasar, kalender, dan status posisi. Model mengusulkan `BUY`, `SELL`, `HOLD`, `CLOSE`, atau `WAIT`, serta memilih profil strategi dari daftar yang telah diuji. Model menjadi pengambil keputusan utama untuk sinyal dan rekomendasi posisi. EA menerapkan order demo dan batas risiko independen yang tidak dapat diubah AI. Sistem berjalan selama minggu perdagangan Forex (24/5); tidak ada jaminan profit.

## Pengguna dan konteks
Pengguna memakai Windows untuk mengelola proyek, broker Finex, MT5 di ponsel, VPS Ubuntu yang spesifikasinya belum diperiksa, endpoint 9Router OpenAI-compatible, dan model `cx/gpt-6-luna`. Akun demo yang sama akan login di MT5 desktop VPS dan MT5 mobile; posisi dan balance akun tersinkron melalui server broker. Proyek lokal saat ini hanya berisi dokumen desain ini. Pengguna ingin mulai dengan dry-run/demo dan mengevaluasi kemungkinan akun real setelah lima gerbang. Forex berjalan hampir 24 jam per hari selama hari kerja pasar (umumnya 5 hari per minggu); saat pasar tutup, sistem tetap hidup dan memantau tetapi tidak dapat membuka transaksi.

## Pendekatan yang dipertimbangkan

1. **EA31337 sebagai eksekusi; GPT sebagai pengambil keputusan sinyal dan rekomendasi posisi, dengan pagar risiko tetap.** Panggil GPT untuk berita relevan, setup M5 hasil prefilter, atau trigger evaluasi posisi. Model dapat mengusulkan BUY/SELL/HOLD/CLOSE/WAIT dan memilih profil strategi beku. EA menerapkan stop-loss, sizing, batas rugi harian, serta kill switch yang tidak dapat diubah AI. Batasi biaya dengan satu panggilan per simbol per candle, deduplikasi/cooldown, dan plafon harian.
2. **EA31337 saja; GPT hanya memantau.** Integrasinya lebih sederhana dan Strategy Tester dapat menguji strategi bawaan secara langsung, tetapi arah transaksi tidak ditentukan GPT seperti yang diinginkan pengguna.
3. **GPT langsung mengendalikan order melalui teks/API.** Tampak sederhana, namun mencampur prediksi dan otorisasi transaksi, rentan timeout/keluaran tak terstruktur, dan sulit direproduksi. Tidak dipilih.

Pilihan rancangan: pendekatan 1. Langkah pertama implementasi adalah audit versi/tag yang dipin, lisensi GPL-3.0, dependensi/submodule, antarmuka strategi EA31337, alur entry/exit, ukuran lot, SL/TP, dan penanganan error. AI boleh memilih hanya di antara profil strategi yang parameternya sudah dipatok; AI tidak boleh menciptakan, mengubah, atau mengoptimalkan parameter risiko saat berjalan. Jika tidak ada antarmuka eksternal yang aman dan sederhana, gunakan hanya modul yang layak atau buat adapter EA tipis, bukan memaksa integrasi ke jalur strategi internal. M5 dan satu simbol awal menjadi lingkup pengujian pertama.

## Temuan riset repo EA31337

- Saat diperiksa 2026-11-04, GitHub menunjukkan sekitar 1,3 ribu stars, 465 forks, dan 1.988 commits. Ini indikator pemakaian/aktivitas repo, bukan bukti profitabilitas strategi.
- README mendeskripsikan proyek sebagai framework robot forex MT4/MT5 untuk mengembangkan, menguji, dan mengotomasi strategi.
- README menyatakan parameter default dioptimalkan untuk EURUSD dan menyarankan demo/backtest menyeluruh saat mengganti simbol atau broker. Performa dapat berbeda antar simbol dan broker.
- Repo menyertakan konfigurasi SET hasil optimasi pra-rilis; parameter historis tidak otomatis sesuai dengan spread, kontrak, leverage, komisi, atau spesifikasi simbol Finex saat ini.
- Lisensi repo adalah GPL-3.0. Sebelum menyalin atau mendistribusikan modifikasi, periksa kewajiban lisensi yang berlaku; jangan mengasumsikan kode GPL dapat diperlakukan seperti komponen proprietary.
- Banyak stars dan riwayat commit membuatnya kandidat audit yang menarik, bukan bukti robot ini menghasilkan profit pada Finex.
- Pemeriksaan source pada checkout `9b9bd38c4e49dd6916f4fe3936e50e97fca7a692` menemukan EA utama memproses entry strategi melalui `EA::TradeRequest` yang virtual. Base route membentuk market request dan volume dengan floor lot minimum; request tersebut tidak memasang hard SL/TP langsung pada fungsi pembentukan request yang diperiksa, sementara `Strategy::OnOrderOpen` mengatur close conditions. Karena itu custom EA adapter harus mengaudit jalur lain, menerapkan broker-side SL dan menghitung risiko uang sebelum order. Detail audit awal: `docs/audits/ea31337-audit.md`.
- Default Lite mencakup beberapa timeframe; M5 bukan satu-satunya timeframe aktif. Stock defaults dan file `.set` dilarang untuk dipasang langsung sebagai strategi Finex order-capable.
- Pada checkout ini terdapat 130 submodule recursive. Banyak submodule tidak memuat berkas LICENSE/COPYING/NOTICE di root, walau beberapa memakai badge/header GPL. Status lisensi per komponen belum lengkap; tidak boleh mendistribusikan hasil bundel sebelum seluruh dependency yang masuk build diverifikasi.
- Kalender ekonomi bawaan MQL5 menyediakan jadwal dan nilai aktual/perkiraan indikator makro, bukan arus semua berita/headline. Data kalender memakai zona waktu server trading, yang perlu dicatat dan dinormalisasi. Dokumentasi MQL5 juga menyatakan kalender tidak dapat dibaca langsung dari Strategy Tester; evaluasi historis butuh arsip bertimestamp yang disimpan terpisah.
- 9Router menyediakan gateway LLM dan layanan pencarian web terpisah. Mengirim prompt ke model saja tidak otomatis memberinya berita live; sistem harus mengambil berita dari feed eksplisit, memeriksa timestamp/sumber, lalu mengirim ringkasan/kutipan terpilih ke model.

## Riset publik bot Forex + AI dan keputusan desain

Riset ini mencakup repo publik GitHub, dokumentasi MQL5, artikel teknis MQL5, serta diskusi komunitas yang dapat dibaca umum. Materi privat atau tertutup—termasuk grup Telegram privat—tidak diakses. CAPTCHA atau kontrol login tidak dilewati. “Deep web” tidak menjamin data lebih valid; bukti yang dapat diperiksa dan direproduksi lebih penting daripada klaim anonim.

- **Pola arsitektur yang paling layak diadopsi:** repositori `forex-ai-trader` menyatakan Claude mengusulkan transaksi sementara mesin risiko deterministik memegang keputusan akhir, dengan PaperBroker sebagai default, batas spread/kerugian, kill switch, journal SQLite, dan dashboard. Repo tersebut masih kecil (0 stars saat ditinjau), jadi ini referensi pola desain, bukan bukti kinerja atau rekomendasi untuk dipasang langsung. Sumber: https://github.com/Elkhan-Isayev/forex-ai-trader
- **Klaim multi-agent perlu dibaca hati-hati:** `claude-trader` mempromosikan 14 agen dan menyajikan hasil backtest positif. Namun README juga menandai backtest Claude sebenarnya sebagai pekerjaan mendatang; angka yang ditampilkan berasal dari strategi rule-based dan tidak membuktikan bahwa LLM menambah profit. Angka tersebut adalah klaim pemilik repo, bukan audit independen. Repo memiliki 24 stars/11 forks saat diperiksa. Sumber: https://github.com/El-Bach/claude-trader
- **Popularitas bot tidak sama dengan cocok untuk Forex/MT5:** Freqtrade sangat populer dan memiliki dry-run/backtesting serta FreqAI, tetapi proyeknya untuk crypto, bukan konektor Finex MT5. Dokumentasi FreqAI sendiri memperingatkan bahwa contoh bertujuan demonstrasi dan perlu validasi sebelum produksi. Karena itu kita ambil praktik dry-run dan pencatatan, bukan mengadopsi stack tersebut. Sumber: https://github.com/freqtrade/freqtrade dan https://github.com/freqtrade/freqtrade/blob/develop/docs/freqai.md
- **Integrasi LLM langsung dengan order yang ditemukan di artikel MQL5 adalah prototipe, bukan bukti profit:** artikelnya menunjukkan siklus Python, data MT5, panggilan LLM, dan eksekusi. Tutorial semacam ini berguna untuk memahami integrasi, tetapi tidak menunjukkan uji independen yang membuktikan edge berkelanjutan. Sumber: https://www.mql5.com/en/articles/20354
- **Berita berguna untuk konteks risiko, bukan ramalan arah yang pasti:** dokumentasi MQL5 menyebut pengujian strategi berita sulit karena kalender tidak tersedia di Strategy Tester tanpa arsip; waktu rilis aktual dapat berbeda dari waktu terjadwal, sehingga akurasi pengujian dapat terpengaruh. Maka berita harus bisa memicu `NEWS_PAUSE`/`WAIT` dan menjadi konteks bagi AI, tetapi tidak otomatis memberi BUY/SELL. Sumber: https://www.mql5.com/en/book/advanced/calendar/calendar_trading
- **Diskusi komunitas dan hasil sinyal publik bersifat anekdotal/self-reported.** Screenshot, paper result, backtest yang parameternya tidak disertakan, stars/forks, dan klaim keuntungan tidak cukup untuk menyimpulkan profit nyata. Dalam sampel yang ditinjau tidak ditemukan bukti audit independen bahwa bot Forex retail berbasis LLM mempunyai keunggulan profit yang stabil. Ini temuan terbatas pada sampel sumber publik yang diperiksa, bukan klaim bahwa tidak ada sistem semacam itu.

**Perubahan yang diambil dari riset:** LLM tetap boleh mengusulkan arah dan rekomendasi posisi sesuai keinginan pengguna, tetapi seluruh keputusan eksekusi melewati risk engine deterministik. Fase pertama menggunakan mode shadow: model membuat prediksi bertimestamp namun tidak mengirim order; prediksi dibandingkan dengan hasil pasar dan baseline EA. Setelah evaluasi terpisah, fitur order demo dapat dibuka dengan guardrail tetap. Bot hanya bergerak ke gerbang berikut setelah metrik, biaya, latency, dan semua keputusan terekam. Hindari multi-agent, fine-tuning, strategi parameter dinamis, dan pencarian web bebas di setiap candle pada MVP; belum ada bukti bahwa kompleksitas itu meningkatkan kinerja, sementara biaya dan titik gagal bertambah.

## Temuan sinyal MQL5 sebelumnya

- Metrik halaman sinyal bersifat dinamis dan dapat berubah; angka yang dicatat sebelumnya adalah snapshot saat peninjauan 2026-11-04, bukan kondisi saat ini. Pada snapshot tersebut, dua sinyal menunjukkan pertumbuhan positif tetapi drawdown balance sekitar 40% dan profit factor sekitar 1,2; sinyal ketiga menunjukkan pertumbuhan negatif dan drawdown di atas 50%. Catatan persis perlu diverifikasi ulang sebelum dipakai untuk keputusan.
- Ketiga halaman menandai penggunaan algo trading yang tinggi, tetapi tidak mengungkap EA/strategi secara cukup untuk direplikasi atau diaudit. Metrik sinyal juga bukan bukti bahwa akun demo, broker, saldo, atau sistem kita akan mendapat hasil sama.
- Persentase “algo trading” tidak memberitahu bot mana yang dipakai dan tidak menjadi bukti strategi akan menguntungkan di akun pengguna.

## Alur sistem rekomendasi

1. **VPS dan layanan hidup.** Ubuntu menjalankan MT5 desktop melalui Wine, service Python pemantau berita, bridge lokal 9Router, dan monitor kesehatan. Service berjalan terus, termasuk saat pasar tutup; saat pasar tutup tidak ada order.
2. **Periksa feed tanpa memanggil model.** Service memeriksa satu atau beberapa sumber berita yang dipilih pada interval ringan. Ia menyimpan ID/hash berita terakhir yang diproses, timestamp, dan status di SQLite agar restart tidak memicu analisis ulang. Pemeriksaan feed tidak memanggil LLM.
3. **Saring berita.** Terima hanya berita baru, belum kedaluwarsa, dari sumber allowlist, dengan waktu publikasi yang jelas dan relevan terhadap mata uang/simbol. Deduplikasi salinan headline dan gabungkan berita berkaitan menjadi satu batch. Berita lama, duplikat, tidak relevan, tanpa sumber/timestamp, atau dampak tak jelas tidak memicu 9Router. Kalender ekonomi MQL5 dapat melengkapi peristiwa terjadwal dan angka aktual/perkiraan; headline umum memerlukan feed terpisah.
4. **Bangun konteks pasar.** Untuk berita yang lolos, tunggu snapshot candle M5 tertutup dan kumpulkan OHLCV, fitur tren/volatilitas yang ditetapkan, spread, dan kondisi kalender. Jangan kirim password atau data akun pribadi. Jika harga/berita tidak cukup segar, catat dan abaikan event.
5. **Panggil GPT hanya pada event yang memenuhi syarat.** Service mengirim satu batch berita beserta konteks pasar ke `cx/gpt-6-luna` melalui 9Router. Gunakan satu permintaan per event-batch/simbol, cooldown, timeout, retry terbatas, batas token dan maksimum 5 panggilan per hari. Tidak ada plafon biaya dolar; penggunaan dilaporkan jika metrik tersedia. API key hanya berada di secret/environment service. Jika API gagal, jangan ulangi terus-menerus; event menjadi `WAIT` dan masuk cooldown.
6. **Model mengusulkan arah dan profil terbatas.** Schema JSON berversi memuat sumber/ID berita, `forecast_horizon`, `action: BUY|SELL|HOLD|CLOSE|WAIT`, `confidence`, `regime`, `strategy_profile` dari allowlist (`TREND`, `MEAN_REVERSION`, `NEWS_PAUSE`, `NO_TRADE`), `reason_code`, dan `valid_until`. Model tidak menulis parameter baru. HOLD hanya berlaku selama posisi masih di bawah hard stop dan batas rugi. Respons invalid, event basi, hasil terlambat, confidence di bawah ambang teruji, atau schema salah ditolak. Setiap jawaban disimpan bersama waktu input, model/prompt/schema version, sumber data, dan hasil keputusan untuk audit.
7. **EA memeriksa profil dan risiko.** EA memetakan profil yang diizinkan ke konfigurasi beku yang sudah diuji. Ia menunggu konfirmasi candle M5 dan menolak sinyal ketika spread melebar atau melanggar demo-only, filter, batas spread/posisi/risiko, batas rugi harian, atau drawdown maksimum. HOLD AI tidak dapat menonaktifkan atau menggeser hard stop. Harga SL/TP dan volume dihitung EA; model tidak dapat mengubah batas risiko atau mematikan circuit breaker. Jika koneksi model/berita/MT5 tidak sehat, perilaku default adalah tidak membuka order baru.
8. **Eksekusi, kedaluwarsa, dan monitoring.** Hanya sinyal BUY/SELL yang masih berlaku, dipicu berita/setup/trigger posisi, dan lolos semua pemeriksaan dapat membuka satu order demo; cegah order ganda. Usulan strategi kedaluwarsa paling lama setelah tiga candle M5 atau waktu `valid_until`, mana yang lebih dulu. Tanpa trigger, tidak ada panggilan model dan tidak ada entri baru berdasarkan sinyal lama; EA tetap mengelola posisi terbuka dan mengirim status/push MT5.

## Arsitektur usulan

- **MT5 dan EA31337:** MT5 desktop berjalan pada Ubuntu melalui Wine. EA adaptasi membaca rekomendasi lokal, tetapi tetap memegang otoritas atas risiko dan transaksi. Tahap awal hanya login akun demo. Aplikasi MT5 HP login ke nomor akun dan server Finex yang sama.
- **Service berita dan bridge lokal:** service Python berjalan sebagai systemd service, memeriksa feed berita dengan polling ringan, menyimpan ID/hash yang telah diproses di SQLite, lalu menghubungi bridge lokal yang bind hanya ke `127.0.0.1`. API hanya dipanggil jika muncul batch baru yang relevan dan lolos filter. Terapkan cooldown, batas request/token per hari, timeout, deduplikasi, log teredaksi, dan restart otomatis. Port bridge tidak dibuka ke internet. Polling feed dapat tetap berjalan saat tidak ada transaksi; biaya feed/kuota pencarian tetap diperiksa terpisah dari biaya token model.
- **LLM dan berita:** tidak ada pelatihan/fine-tuning. Service Python memantau feed tanpa memanggil LLM; GPT-6 Luna dipanggil untuk berita relevan, setup harga yang lolos prefilter, atau trigger evaluasi posisi. Model membaca harga, berita, waktu/tanggal/hari, sesi pasar, kalender, dan status posisi; lalu mengusulkan BUY/SELL/HOLD/CLOSE/WAIT serta profil strategi dari allowlist. Ia tidak mengubah parameter atau batas risiko. 9Router adalah jalur model/pencarian terpisah; berita harus dipasok secara eksplisit. Anggarkan biaya feed dan model secara terpisah.
- **Validasi LLM:** MQL5 `WebRequest` sinkron dan tidak dapat dipanggil Strategy Tester. Karena itu pisahkan (a) uji EA dengan sinyal replay statis, (b) evaluasi prediksi model dengan log bertanggal dan versi prompt/schema, serta (c) forward test demo langsung. Prediksi API tidak otomatis dapat direproduksi identik di backtest standar.
- **Monitoring HP:** MT5 Android login ke akun demo yang sama dengan terminal VPS. Push diuji untuk order, penolakan, API error, daily stop, dan koneksi putus. Tampilan akun utama melalui MT5; dashboard ekstra belum diperlukan.

## Kebijakan frekuensi aktif M5

- Jalankan pemantauan VPS 24/5 dan evaluasi peluang pada penutupan candle M5.
- Panggil model ketika ada berita baru relevan, setup harga lolos prefilter EA31337, atau posisi melewati pemicu evaluasi rugi yang telah dikunci.
- Batasi paling banyak satu request per simbol per candle. Trigger rugi hanya memicu satu evaluasi saat ambang pertama kali dilewati, dengan cooldown sampai candle/data baru.
- Model boleh menyarankan HOLD atau CLOSE. HOLD tidak mematikan/menggeser SL; model tidak boleh average down, menambah lot untuk mengejar loss, atau menaikkan risiko setelah rugi.
- Tanpa trigger dan tanpa sinyal yang masih berlaku, tidak ada panggilan AI atau entri baru. Posisi terbuka tetap dikelola oleh SL/TP dan aturan EA.
- Tidak ada target trade atau profit harian. Uji sekurangnya 60 hari perdagangan dan jumlah sampel minimum dapat memerlukan waktu lebih lama; jangan melonggarkan filter untuk mempercepat hitungan.
- Pada MVP, keluaran LLM lebih dahulu berjalan dalam **shadow mode** dan tidak mengirim order. Aktivasi demo order memerlukan persetujuan pengguna setelah metrik prediksi dan integrasi ditinjau. Pemicu evaluasi posisi tidak boleh menyebabkan AI menambah posisi atau menahan posisi melewati stop.
## Ruang lingkup

- Membuat satu skill Codex lokal di proyek, dalam Bahasa Indonesia, untuk mengaudit/mengadaptasi EA31337 dan membangun alur keputusan GPT BUY/SELL/HOLD/CLOSE/WAIT melalui 9Router untuk akun demo Finex.
- Tahap implementasi dimulai dengan mencatat commit/tag EA31337, memeriksa source/dependencies/GPL-3.0, memilih antarmuka strategi, lalu membuat salinan kerja terpisah.
- Membaca spesifikasi server dan simbol Finex sebelum memilih satu simbol/timeframe. M5 adalah kandidat yang diminta pengguna, namun hanya dipakai bila data dan pengujian mendukung.
- Menambahkan atau mengonfigurasi guardrail deterministik: akun demo allowlist, batas simbol dan timeframe, lot hasil kalkulasi risiko, SL wajib, filter spread/jam, batas posisi, rugi harian, drawdown total, dan kill switch.
- Menguji kompilasi dan order melalui sinyal replay, uji biaya/risiko historis, evaluasi model di data terpisah, forward test demo, serta kegagalan API/koneksi/restart.
- Memeriksa VPS Ubuntu secara read-only (versi OS, arsitektur, CPU, RAM, disk, display session, jaringan). MT5 desktop melalui Wine, EA dan bridge hanya dipasang setelah rencana implementasi rinci disetujui.
- Menyiapkan monitoring melalui MT5 Android dan ringkasan hasil yang mudah dibaca.
- Lima gerbang demo yang menguji operasi 24/5, kualitas sinyal GPT, biaya dan reliabilitas. Kelulusan tidak mengaktifkan akun real; keputusan real tetap keputusan manusia yang terpisah.

## Bukan tujuan

- Menjanjikan profit, menyebut EA31337 “paling cuan”, atau menilai bot dari stars, growth tunggal, atau win rate saja.
- Menganggap kode dan file `.set` EA31337 sudah aman atau cocok untuk Finex tanpa audit dan pengujian.
- Menganggap override `TradeRequest` saja sudah cukup sampai seluruh rute entry/stop/volume dan jalur Advanced/pending order diaudit serta EA berhasil dikompilasi.
- Melatih/fine-tune GPT untuk menemukan sinyal, atau memanggil model pada setiap tick.
- Membiarkan teks bebas dari model memicu atau mengubah order.
- Menyalin kode/strategi privat dari penjual sinyal atau mengirim transaksi live.
- Mengakses grup privat, mengakali CAPTCHA/login, atau mengumpulkan data yang tidak diberikan secara publik dan sah.
- Mengaktifkan akun real, deposit, penarikan, atau transfer dana dalam rangka demo.
- Menaruh API key, password SSH, password MT5, atau token push dalam source, repo, prompt, screenshot, maupun log.

## Batasan dan asumsi

- Hanya akun demo Finex diizinkan sampai lima gerbang selesai dan pengguna menilai hasilnya.
- Halaman Finex menyebut akun demo virtual USD 5.000, deposit minimum USD 10, dan volume minimum 0,01 lot. Kelayakan modal sekitar Rp200 ribu belum bisa disimpulkan tanpa spesifikasi simbol, margin, biaya, spread, konversi mata uang, dan kerugian nominal pada SL.
- Risiko awal yang diusulkan untuk diuji tercantum pada bagian “Keputusan yang masih perlu dikunci”: maksimum 0,10% equity awal per posisi, batas rugi harian 0,50%, dan penghentian pada drawdown demo 2,0%. Ini pagar kebijakan konservatif untuk eksperimen, bukan nilai yang secara riset terbukti optimal. Lot minimum broker dapat membuat batas tersebut tidak mungkin dipatuhi; trade harus dilewati jika demikian.
- Durasi forward test usulan: minimal 60 hari perdagangan dan 100 transaksi tertutup, gunakan periode yang lebih lama. Ambang performa bersih, PF, dan drawdown dicantumkan pada bagian keputusan untuk ditinjau sebelum pengujian.
- Kredensial yang pernah ditempel di chat dianggap terekspos. Sebelum koneksi VPS/API dilakukan, API key dicabut/diganti dan password SSH dirotasi; kredensial baru dimasukkan secara aman dan tidak dicatat di proyek/chat.
- Kapasitas VPS belum diketahui dan belum dapat dinyatakan memadai.
- EA31337 menggunakan GPL-3.0; rencana perubahan, distribusi, dan penyimpanan hasil adaptasi harus mengikuti pemeriksaan lisensi. Pemeriksaan ini bukan pengganti nasihat hukum.
- Prediksi LLM/berita bukan jaminan arah masa depan. Confidence dan strategi profil perlu dievaluasi pada data yang tidak dipakai untuk mengubah prompt/parameter. Jika kualitas feed, timestamp, model, atau berita tidak dapat diverifikasi, hasilnya WAIT. Koneksi 9Router menambah latensi, biaya, dan ketergantungan internet. Pasar Forex tutup pada akhir pekan dan hari libur broker.

## Lima gerbang demo usulan

1. **Audit dan kesiapan 24/5:** commit EA31337 dipin; source/dependensi/lisensi ditinjau; Ubuntu/Wine/MT5 pulih setelah reboot; akun/server dipastikan demo; secret aman.
2. **Integrasi sinyal aman:** mulai dalam shadow mode tanpa order. Schema BUY/SELL/HOLD/CLOSE/WAIT lulus skenario; request dibatasi satu per simbol per candle dan hanya terjadi pada trigger berita/setup/rugi yang ditetapkan; duplikasi, berita basi, timeout, API mati, port publik, akun bukan demo, atau batas risiko memaksa tidak ada order baru; HOLD tidak pernah mengubah hard stop. Pengguna meninjau shadow report sebelum tahap forward demo yang mengirim order.
3. **Validasi strategi:** replay EA memakai sinyal tetap untuk menguji eksekusi, lot, SL, spread, dan biaya. Evaluasi prediksi LLM memakai arsip harga/berita bertimestamp yang terpisah, hanya memasukkan informasi yang tersedia saat itu, dan menyimpan log keputusan; kriteria performa dikunci sebelum uji tanpa look-ahead atau kebocoran tuning.
4. **Forward demo:** minimal 60 hari perdagangan dan 100 transaksi tertutup (gunakan durasi yang lebih lama), tanpa pelanggaran guardrail; expectancy bersih positif, profit factor minimal 1,2 setelah biaya, drawdown maksimum 2%, dan hasil tidak bergantung pada satu transaksi terbaik. Ini ambang evaluasi awal, bukan jaminan hasil mendatang.
5. **Reliabilitas dan tinjauan:** uji API/network/terminal/VPS restart, weekend/pasar tutup, push MT5 HP, deduplikasi, rekonsiliasi, biaya API, daily stop dan health alert. Pengguna meninjau hasil; akun tetap demo dan tidak berubah otomatis ke real.

## Pemasangan dan monitoring VPS

Sesudah desain dan rencana implementasi disetujui, inventaris VPS Ubuntu dilakukan read-only. MetaTrader menerbitkan panduan Linux/Wine yang mendukung Ubuntu. Tampilkan versi Ubuntu, arsitektur, CPU, RAM, disk kosong, display session, jaringan dan update sebelum instalasi. Uji terminal tetap berjalan saat sesi remote diputus dan pulih setelah reboot. Jika VPS tidak cocok, laporkan alternatif sebelum perubahan. Setelah instalasi demo disetujui, pasang terminal, salinan EA yang diaudit, dan bridge loopback; uji restart/auto-start, log tanpa secret, notifikasi HP, penutupan pasar dan fail-safe.

## Data saat implementasi

- Akun/server demo MT5 yang dapat dipakai dan konfirmasi login HP; jangan kirim password lewat chat.
- MetaQuotes ID untuk uji push notification.
- Spesifikasi VPS dari pemeriksaan read-only.
- Informasi simbol resmi Finex: contract size, tick value/size, volume min/step, margin, spread, swap, dan komisi.
- Sumber kalender/headline yang akan diizinkan, interval polling, cakupan mata uang, aturan timestamp, retensi data, serta biaya dan ketentuan penggunaan feed.
- API key 9Router baru setelah rotasi, hanya dimasukkan melalui secret/environment service dan tidak ditampilkan di log.

## Penerimaan rancangan

Sebelum skill atau EA dibuat, pengguna meninjau dan menyetujui fokus pada EA31337, status GPL-3.0, ruang lingkup audit, saldo/risiko, kriteria lima gerbang, perilaku demo-only, dan peran GPT/9Router sebagai pengusul arah yang dibatasi guardrail EA. Setelah disetujui, dibuat rencana implementasi terperinci untuk ditinjau terpisah sebelum kode atau konfigurasi VPS berubah.

## Keputusan yang masih perlu dikunci sebelum rencana implementasi

Hasil riset tidak menemukan angka risiko universal yang bisa disebut “paling aman” atau menjamin cuan. CFTC menyebut sekitar dua pertiga akun retail OTC forex yang dilaporkan untuk periode Q2 2021–Q1 2022 rugi setelah biaya; angka itu konteks dari dealer terdaftar di AS, bukan estimasi khusus Finex/Indonesia. FINRA juga memperingatkan klaim auto-trading/AI yang menjanjikan profit konsisten atau tanpa risiko. Karena itu, nilai di bawah adalah **usulan kebijakan uji demo konservatif**, bukan angka yang dibuktikan optimal oleh komunitas/riset dan bukan janji hasil.

Diskusi komunitas MQL5/Reddit yang ditinjau menyebut angka berbeda-beda, umumnya berdasarkan pengalaman pribadi dan tanpa audit risiko/rekam transaksi lengkap; beberapa menyarankan 0,5–1%, yang lain menyebut batas 2%. Itu bukan konsensus tervalidasi. Rekomendasi 0,10% di bawah sengaja lebih kecil untuk mengurangi dampak kesalahan saat uji otomatis, bukan karena komunitas membuktikan angka itu menghasilkan profit lebih baik.

1. **Batas risiko usulan untuk forward demo setelah shadow:** risiko maksimum 0,10% equity awal per posisi; rugi harian 0,50% dari equity awal hari; penghentian seluruh entry baru pada drawdown 2,0% dari equity awal fase demo. Hitung rugi harian dari equity termasuk floating PnL, komisi, swap, dan biaya yang tercatat; reset pada tengah malam waktu server broker dan simpan timezone/offset. Jika terminal kehilangan koneksi, data equity tidak segar, atau perhitungan lot minimum 0,01 melebihi batas uang tersebut, jangan buka trade. Satu posisi terbuka maksimum untuk simbol awal; tanpa martingale, grid, averaging down, atau menaikkan lot setelah rugi. Batas ini hanya melindungi eksperimen demo dari perilaku yang tak terkendali; hasil demo tidak memprediksi kerugian real.
2. **Kriteria lulus usulan:** shadow mode minimal 60 hari perdagangan dan sekurangnya 100 sinyal eligible yang tercatat; bila sampel belum tercapai, lanjutkan tanpa melonggarkan filter. Lanjut ke order demo hanya setelah review manusia atas log, ketepatan waktu/sumber data, hasil baseline versus AI, dan simulasi biaya. Forward demo minimal 60 hari perdagangan serta 100 transaksi tertutup (yang lebih lama), expectancy bersih setelah spread/komisi/swap positif, profit factor minimal 1,2, drawdown puncak-ke-lembah maksimum 2%, tanpa satu pun pelanggaran guardrail, dan hasil tidak bergantung pada satu transaksi terbaik. Angka jumlah sampel/PF adalah pagar operasional awal, bukan standar ilmiah yang memastikan edge. Tetap demo meskipun semua kriteria terpenuhi; tidak ada perpindahan otomatis ke real.
3. **Biaya dan data:** mulai tanpa feed berita berbayar. Gunakan sumber resmi yang akses dan ketentuan penggunaannya sudah diperiksa; jangan mengandalkan scraping grup atau pencarian web bebas sebagai sumber sinyal. Pada 2026-11-06 pengguna secara eksplisit menerima biaya API tanpa plafon dolar. Karena 9Router tidak menyediakan plafon per-key yang dapat ditegakkan, sistem tidak boleh menyatakan adanya batas belanja; usage/cost hanya dilaporkan bila datanya tersedia. Pertahankan maksimum 5 panggilan model per hari dan deduplikasi satu panggilan per event/simbol/candle sebagai pengaman operasional. Ini bukan batas pengeluaran. Biaya feed berbayar tetap di luar persetujuan ini.
4. **Saldo uji usulan:** gunakan akun demo Finex standar USD 5.000 sebagai akun operasi, karena Finex menyatakan akun demo mendapat dana virtual tersebut. Tambahkan skenario simulasi terpisah yang dinormalisasi ke setoran rencana Rp200.000 untuk mengecek apakah lot minimum 0,01 akan melampaui batas risiko; jangan mengubah angka equity demo broker secara asumtif. Jika risiko uang pada lot minimum melebihi 0,10% dari saldo simulasi, hasilnya “tidak layak untuk skenario modal itu” dan sistem melewati trade. Nilai demo bukan modal pengguna dan tidak bisa dicairkan.

Angka dan pilihan di atas adalah rekomendasi saya untuk ditinjau, bukan persetujuan pengguna. Keputusan implementasi kecil yang dapat diambil setelah desain disetujui: commit EA31337 yang dipin, jenis adapter lokal, simbol awal berdasarkan spesifikasi Finex, dan detail retry/deduplikasi. Semuanya harus dicatat sebelum pemasangan atau eksekusi demo.

## Sumber

- EA31337 repository: https://github.com/EA31337/EA31337
- EA31337 README: https://github.com/EA31337/EA31337/blob/master/README.md
- EA31337 license: https://github.com/EA31337/EA31337/blob/master/LICENSE
- MQL5 Signal 2335546: https://www.mql5.com/en/signals/2335546
- MQL5 Signal 2339391: https://www.mql5.com/en/signals/2339391
- MQL5 Signal 2390483: https://www.mql5.com/en/signals/2390483
- Finex account terms: https://finex.co.id/trading/accounts
- Finex demo FAQ: https://www.finex.co.id/helpcenter/verifikasi-akun/apakah-akun-demo-saya-perlu-di-verifikasi
- MetaTrader Android push: https://www.metatrader5.com/en/mobile-trading/android/help/push
- 9Router docs: https://docs.9router.com/
- Contoh arsitektur AI Forex dengan risk engine deterministik (kecil, bukan bukti profit): https://github.com/Elkhan-Isayev/forex-ai-trader
- Contoh repo multi-agent AI Forex dengan klaim backtest yang tidak menguji kontribusi LLM: https://github.com/El-Bach/claude-trader
- Freqtrade crypto bot dan dokumentasi FreqAI (referensi dry-run/ML, bukan implementasi Finex MT5): https://github.com/freqtrade/freqtrade dan https://github.com/freqtrade/freqtrade/blob/develop/docs/freqai.md
- Artikel integrasi Python + LLM + MT5 yang diperlakukan sebagai contoh implementasi, bukan validasi profit: https://www.mql5.com/en/articles/20354
- CFTC, Customer Advisory: Eight Things You Should Know Before Trading Forex (statistik Q2 2021–Q1 2022 dari dealer OTC terdaftar AS; bukan angka universal): https://www.cftc.gov/LearnAndProtect/AdvisoriesAndArticles/CustomerAdvisory_MustKnowForex.html
- FINRA, Know the Risks of Auto-Trading Services Offered by Unregistered Entities: https://syndication.finra.org/content/know-risks-auto-trading-services-offered-unregistered-entities
- MetaTrader 5, real ticks dan spread yang berubah: https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation
- Finex, persyaratan akun, saldo demo, leverage, komisi, spread, dan lot minimum (perlu cek ulang sebelum uji): https://finex.co.id/trading/accounts
- Finex Help Center, dana virtual akun demo: https://www.finex.co.id/helpcenter/verifikasi-akun/apakah-akun-demo-saya-perlu-di-verifikasi
- Contoh diskusi komunitas MQL5 tentang risiko per trade (anekdotal; pendapat dan angka beragam): https://www.mql5.com/en/forum/456907
- Contoh diskusi komunitas EA forward test dan paper trading (anekdotal, klaim tidak diaudit): https://www.reddit.com/r/Forex/comments/1txu8d8/ea_forward_testing_watchout_list/
- MQL5 Economic Calendar: https://www.mql5.com/en/docs/calendar
- MQL5 calendar tester limitation: https://www.mql5.com/en/book/advanced/calendar
- MetaTrader Linux/Wine install: https://www.metatrader5.com/en/terminal/help/start_advanced/install_linux
- MQL5 WebRequest constraints: https://www.mql5.com/en/docs/network/webrequest
- MQL5 network allowlist: https://www.mql5.com/en/docs/network
