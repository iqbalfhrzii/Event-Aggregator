# ⚡ Event Aggregator — FastAPI, SQLite, & Docker

## 🧭 Deskripsi Proyek

Aplikasi ini merupakan layanan **Event Aggregator** berbasis **FastAPI** yang menerima kumpulan (_batch_) event melalui REST API.  
Setiap event disimpan ke database **SQLite**, dan sistem secara otomatis **mendeteksi serta menolak event duplikat** menggunakan kombinasi **`topic + event_id`** sebagai kunci utama.

Event yang sudah disimpan bersifat **persisten**, artinya data tidak hilang meskipun service di-restart atau container dihentikan.

---

**Dibuat oleh:** Iqbal Fahrozi  
**NIM:** 11221034  
**Dosen Pembimbing:** Riska Kurnianto Abdullah  
**Mata Kuliah:** Sistem Terdistribusi (UTS)

---

## ⚙️ Langkah Instalasi & Menjalankan Aplikasi

| Tahap | Perintah                                                                  | Penjelasan                                                 |
| :---- | :------------------------------------------------------------------------ | :--------------------------------------------------------- |
| 1     | `docker build -t event-aggregator .`                                      | Membangun image Docker berdasarkan file `Dockerfile`       |
| 2     | `docker run -d --name aggregator-container -p 8080:8080 event-aggregator` | Menjalankan container dan membuka akses API di port `8080` |
| 3     | _(Opsional)_ `pytest -v`                                                  | Menjalankan seluruh unit test untuk memverifikasi sistem   |
| 4     | _(Opsional)_ `docker-compose up --build`                                  | Menjalankan layanan secara otomatis dengan Docker Compose  |

Setelah container berjalan, aplikasi dapat diakses melalui:  
🌍 **http://localhost:8080**

---

## 📡 Daftar Endpoint API

| Method | Endpoint   | Fungsi                                                | Contoh Respons                                                     |
| :----- | :--------- | :---------------------------------------------------- | :----------------------------------------------------------------- |
| `POST` | `/publish` | Menerima batch event dan melakukan proses deduplikasi | `{ "processed_count": 1, "duplicate_dropped": 0 }`                 |
| `GET`  | `/events`  | Mengambil seluruh event yang tersimpan                | `[ { "topic": "user.login", "event_id": "login-001" } ]`           |
| `GET`  | `/stats`   | Menampilkan statistik penerimaan dan duplikasi event  | `{ "received": 4, "unique_processed": 1, "duplicate_dropped": 3 }` |
| `GET`  | `/health`  | Mengecek status kesehatan aplikasi                    | `{ "status": "healthy" }`                                          |

---

## 🧠 Arsitektur & Asumsi Sistem

| No  | Komponen / Asumsi               | Penjelasan                                                               |
| :-- | :------------------------------ | :----------------------------------------------------------------------- |
| 1   | **FastAPI**                     | Framework web yang digunakan untuk REST API yang ringan dan cepat        |
| 2   | **SQLiteEventStore**            | Modul penyimpanan event dengan dukungan deduplikasi dan persistensi data |
| 3   | **EventService**                | Mengatur antrean event dan pemrosesan asynchronous                       |
| 4   | **Deduplication & Idempotency** | Sistem hanya memproses event unik berdasarkan kombinasi `topic+event_id` |
| 5   | **Persistence**                 | Data tetap tersimpan meskipun container di-restart                       |
| 6   | **Pola At-Least-Once Delivery** | Event dapat dikirim ulang tanpa menyebabkan data ganda                   |

---

## 🧪 Pengujian Sistem

Proyek ini dilengkapi dengan **unit test** menggunakan framework `pytest` untuk memastikan fungsionalitas berjalan dengan benar dan stabil.

| File / Jenis Uji         | Deskripsi Pengujian                              | Tujuan Pengujian                                     |
| :----------------------- | :----------------------------------------------- | :--------------------------------------------------- |
| `test_api.py`            | Uji endpoint `/publish`, `/events`, dan `/stats` | Memastikan seluruh endpoint API bekerja dengan benar |
| `test_dedup.py`          | Uji logika deteksi event duplikat di database    | Memverifikasi idempotency dan deduplikasi berjalan   |
| Batch Test (1000 events) | Uji performa pemrosesan event dalam jumlah besar | Memastikan pemrosesan batch berlangsung < 5 detik    |
| Persistence Test         | Uji setelah container di-restart                 | Memastikan data tetap konsisten dan tidak hilang     |

Untuk menjalankan pengujian:

```bash
pytest -v
```
