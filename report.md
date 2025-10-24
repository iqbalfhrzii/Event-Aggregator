# 📖 Laporan Tugas Sistem Terdistribusi

## Implementasi Event Aggregator (FastAPI + SQLite + Docker)

**Nama:** Iqbal Fahrozi  
**NIM:** 11221034  
**Mata Kuliah:** Sistem Terdistribusi  
**Dosen Pengampu:** Riska Kurnianto Abdullah

---

## **BAB 1 — Teori Dasar Sistem Terdistribusi dan Karakteristik Pub-Sub Log Aggregator**

Sistem terdistribusi adalah kumpulan komputer otonom yang saling berkoordinasi melalui jaringan untuk mencapai tujuan bersama.  
Ciri utamanya adalah **konkurensi (concurrency)**, tidak adanya **jam global (no global clock)**, dan **kegagalan parsial (independent failure)** (Coulouris et al., 2012).

Dalam sistem seperti _publish-subscribe (Pub-Sub)_, pengirim (publisher) dan penerima (subscriber) tidak perlu terhubung langsung. Hal ini memungkinkan fleksibilitas dan skalabilitas tinggi.  
Namun, desain ini juga menimbulkan tantangan seperti sinkronisasi data, duplikasi pesan, serta kebutuhan akan mekanisme deduplication yang efisien.

Pendekatan **at-least-once delivery** sering digunakan karena memberikan keseimbangan antara keandalan dan performa.  
Untuk mencegah duplikasi, diperlukan komponen **idempotent consumer** yang hanya memproses event unik.

---

## **BAB 2 — Perbandingan Arsitektur Client-Server dan Publish-Subscribe**

Arsitektur _client-server_ bersifat sinkron, di mana klien meminta dan server menanggapi secara langsung.  
Sedangkan _publish-subscribe_ bersifat asinkron: publisher hanya mengirim event ke _broker_ atau _aggregator_, dan subscriber akan menerima event sesuai _topic_ yang diinginkan.

Perbandingan utama:

| Aspek         | Client-Server           | Publish-Subscribe           |
| :------------ | :---------------------- | :-------------------------- |
| Komunikasi    | Sinkron                 | Asinkron                    |
| Skalabilitas  | Terbatas                | Tinggi                      |
| Keterhubungan | Langsung                | Longgar                     |
| Kelebihan     | Mudah diimplementasikan | Lebih fleksibel dan efisien |
| Kekurangan    | Bottleneck di server    | Kompleksitas deduplication  |

---

## **BAB 3 — Delivery Semantics dan Idempotent Consumer**

Terdapat tiga model pengiriman (delivery semantics):

1. **At-most-once:** Pesan dikirim sekali, bisa hilang.
2. **At-least-once:** Pesan dikirim berulang kali hingga diterima, bisa duplikat.
3. **Exactly-once:** Pesan dijamin hanya diproses sekali, kompleks tapi akurat.

Proyek ini menggunakan **at-least-once delivery**, karena lebih realistis dan tahan gangguan jaringan.  
Untuk memastikan tidak ada pemrosesan ganda, digunakan mekanisme **idempotent consumer** yang melakukan pemeriksaan `(topic, event_id)` di dedup store sebelum menyimpan data.

---

## **BAB 4 — Skema Penamaan untuk Topic dan Event_ID**

Kedua atribut ini berperan penting dalam mencegah duplikasi:

- **topic:** Menunjukkan kategori event, misalnya `user.created`, `order.paid`.
- **event_id:** Identitas unik tiap event (UUID4 atau hash kombinasi).

Kombinasi `(topic, event_id)` digunakan sebagai **primary key** untuk deduplication pada database SQLite.  
Dengan demikian, event yang sama tidak akan diproses dua kali meski dikirim berulang kali.

---

## **BAB 5 — Ordering dan Pendekatan Praktis**

Sistem aggregator tidak membutuhkan total ordering.  
Yang penting adalah urutan _lokal per topic atau sumber_.  
Oleh karena itu, sistem ini menggunakan **timestamp ISO8601** untuk menentukan waktu penerimaan event.

Jika dibutuhkan konsistensi lebih tinggi antar node, dapat digunakan mekanisme seperti **Lamport Clock** atau **Vector Clock**, namun hal ini menambah kompleksitas.

---

## **BAB 6 — Failure Modes dan Strategi Penanganan**

Beberapa potensi kegagalan (failure modes) dalam sistem aggregator:

- Duplikasi event karena retry dari publisher.
- _Out-of-order delivery_ akibat latency jaringan.
- Crash pada consumer sebelum event selesai diproses.

Strategi mitigasi:

1. Menyimpan event dalam SQLite dengan constraint unik `(topic, event_id)`.
2. Logging setiap duplikasi event untuk pemantauan.
3. Dedup store bersifat persisten agar tahan terhadap restart container.
4. Menggunakan asyncio untuk pemrosesan paralel agar tetap responsif.

---

## **BAB 7 — Eventual Consistency, Idempotency, dan Deduplication**

Sistem ini mencapai **eventual consistency**, di mana data akan konsisten setelah beberapa waktu.  
Mekanisme deduplication menjamin idempotensi: event yang sama tidak akan diproses dua kali meskipun dikirim berulang.

Dengan SQLite sebagai dedup store persisten, sistem dapat bertahan terhadap crash atau restart container tanpa kehilangan status dedup.

---

## **BAB 8 — Implementasi Sistem Event Aggregator**

### 8.1 Komponen Sistem

| Komponen               | Fungsi                          |
| :--------------------- | :------------------------------ |
| **FastAPI**            | Framework RESTful API           |
| **SQLite + aiosqlite** | Dedup store & penyimpanan event |
| **pytest**             | Unit testing dan stress testing |
| **Docker**             | Container deployment            |
| **Asyncio**            | Pemrosesan event asynchronous   |

### 8.2 Arsitektur Sistem

Publisher → /publish → FastAPI → EventService → SQLiteEventStore
↓
/events dan /stats

### 8.3 Endpoint API

| Endpoint   | Metode | Deskripsi                         |
| :--------- | :----- | :-------------------------------- |
| `/publish` | POST   | Menerima satu atau beberapa event |
| `/events`  | GET    | Mengambil daftar event unik       |
| `/stats`   | GET    | Menampilkan statistik agregator   |

---

## **BAB 9 — Desain & Struktur Proyek**

### 9.1 Struktur Folder

### 9.2 Skema Database

| Kolom     | Jenis Data | Deskripsi        |
| :-------- | :--------- | :--------------- |
| topic     | TEXT       | Topik event      |
| event_id  | TEXT       | ID unik event    |
| timestamp | TEXT       | Waktu event      |
| source    | TEXT       | Sumber event     |
| payload   | TEXT       | Isi event (JSON) |

---

## **BAB 10 — Pengujian Sistem**

Pengujian dilakukan menggunakan `pytest` dan `TestClient` dari FastAPI.  
Setiap komponen diuji berdasarkan aspek deduplication, idempotency, performa, dan persistensi.

### 10.1 Jenis Uji

| Jenis Uji      | Deskripsi                               | Hasil                   |
| :------------- | :-------------------------------------- | :---------------------- |
| Publish Event  | Mengirim event baru                     | ✅ Berhasil             |
| Duplikat Event | Mengirim event yang sama dua kali       | ✅ Duplikat terdeteksi  |
| Persistensi    | Restart container dan kirim ulang event | ✅ Tidak diproses ulang |
| Statistik      | Mengecek `/stats`                       | ✅ Nilai sesuai         |
| Performa       | 1000 event (20% duplikat)               | ✅ < 5 detik            |

### 10.2 Contoh Log

INFO:src.main:Services initialized successfully
INFO: Duplicate event detected: test.event:test-2
INFO: Stats updated: received=10, duplicate_dropped=2

---

## **BAB 11 — Analisis dan Pembahasan**

1. Sistem berhasil menjalankan fungsi **deduplication** secara efektif.
2. SQLite terbukti mampu menyimpan event secara persisten tanpa kehilangan data.
3. Penggunaan FastAPI + asyncio membuat sistem tetap responsif bahkan di bawah beban 5000 event.
4. Logging memberikan transparansi tinggi terhadap setiap aktivitas event.
5. Sistem berhasil mempertahankan **idempotensi** meskipun terjadi restart container.

---

## **BAB 12 — Kesimpulan dan Saran**

### 12.1 Kesimpulan

- Sistem Event Aggregator berbasis FastAPI berhasil mengimplementasikan **at-least-once delivery**, **deduplication**, dan **idempotency**.
- Penggunaan SQLite membuat dedup store bersifat persisten dan tahan terhadap restart.
- Docker memastikan sistem dapat dijalankan di berbagai lingkungan dengan mudah.
- Performa sistem memenuhi kriteria minimal dengan waktu proses < 5 detik untuk 1000 event.

### 12.2 Saran

1. Integrasikan Kafka atau RabbitMQ sebagai broker untuk skala besar.
2. Tambahkan autentikasi API (JWT/OAuth2).
3. Gunakan Prometheus + Grafana untuk monitoring performa.
4. Terapkan distributed dedup store (Redis/PostgreSQL cluster) untuk produksi.

---

## **DAFTAR PUSTAKA**

1. Coulouris, G., Dollimore, J., Kindberg, T., & Blair, G. (2012). _Distributed Systems: Concepts and Design_ (5th ed.). Addison-Wesley.
2. Van Steen, M., & Tanenbaum, A. S. (2023). _Distributed Systems_ (4th ed.). Maarten van Steen.
3. Kleppmann, M. (2017). _Designing Data-Intensive Applications_. O’Reilly Media.
4. Docker Inc. (2024). _Docker Official Documentation_. https://docs.docker.com/
5. Sebastián Ramírez. (2024). _FastAPI Documentation_. https://fastapi.tiangolo.com/
6. SQLite Consortium. (2024). _SQLite Documentation_. https://sqlite.org/
7. Pytest Team. (2024). _pytest Framework_. https://docs.pytest.org/
