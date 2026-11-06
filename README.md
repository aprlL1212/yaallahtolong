# 🏗️ Structura — Web-Based Structural Analysis & Moving Load Simulation

Aplikasi analisis struktur berbasis web interaktif untuk analisis **Portal 2D (balok & kolom)** menggunakan **Metode Kekakuan Matriks Langsung (*Direct Stiffness Method*)** serta **Simulasi Beban Bergerak (*Moving Load Simulation*)**.

Dibuat menggunakan **Python** & **Streamlit** untuk mempermudah visualisasi dan pemahaman konsep analisis struktur dan mekanika rekayasa.

> ⚠️ **Catatan:** Aplikasi ini dirancang sebagai alat bantu edukasi dan pembelajaran teknik sipil. Bukan pengganti analisis profesional berlisensi.

---

## ✨ Fitur Utama

### 1. 🏗️ Perhitungan Portal 2D (Metode Matriks)
- **Input Geometri & Beban Interaktif:** Node koordinat, profil penampang ($b \times h$), modulus elastisitas ($E$), derajat kebebasan tumpuan (sendi, rol, jepit), beban titik buhul, dan beban merata/titik pada elemen (*UDL*, terpusat).
- **13+ Model Contoh Soal Siap Pakai:** Portal gedung bertingkat, portal industri/gantry, balok menerus multi-bentang, kantilever, balok overhang, balok tangga miring, dll.
- **Hasil & Visualisasi Lengkap:**
  - Bentuk deformasi elastis linier ($K \cdot u = F$) dengan skala perbesaran interaktif.
  - Diagram bidang gaya aksial ($N$), gaya lintang/geser ($V$), dan momen lentur ($M$).
  - Tabel perpindahan DOF, reaksi perletakan, dan gaya ujung elemen.
  - Verifikasi otomatis kesetimbangan statika global ($\sum F_x = 0, \sum F_y = 0, \sum M = 0$).
- **Ekspor Laporan PDF:** Pembuatan berkas laporan analisis resmi lengkap siap unduh dan cetak.
- **Database Proyek Lokal:** Simpan dan buka kembali proyek pemodelan kapan saja.

### 2. 🚚 Simulasi Beban Bergerak (*Moving Load Simulation*)
- **Interaksi Drag & Drop Real-Time:** Geser beban kendaraan/truk langsung di sepanjang jembatan balok menggunakan pointer mouse atau layar sentuh.
- **Dinamika Reaksi Tumpuan:** Nilai reaksi $R_1(x)$ dan $R_2(x)$ terhitung otomatis secara instan dengan verifikasi kesetimbangan $R_1 + R_2 = P$.
- **Growing Moment Graph:** Visualisasi pertumbuhan kurva momen tepat di bawah posisi beban:
  $$M(x) = \frac{P \cdot x \cdot (L - x)}{L}$$
- **Momen Maksimum Absolut:** Deteksi posisi kritis saat berada di tengah bentang ($x = L/2$) dengan nilai $M_{\max} = \frac{PL}{4}$.
- **Garis Pengaruh (*Influence Line*):** Garis pengaruh reaksi $R_1, R_2$, geser $V_c$, dan momen $M_c$ pada sembarang titik tinjauan potongan $c$.
- **Integrasi 1-Klik ke Solver Matriks:** Konversi otomatis model beban bergerak menjadi model diskrit balok/portal 2D untuk diselesaikan dengan metode kekakuan langsung.

---

## 🚀 Cara Menjalankan Aplikasi

### Prasyarat
Pastikan Anda sudah menginstal **Python 3.10+**.

### 1. Clone Repositori
```bash
git clone https://github.com/<username>/structura_app.git
cd structura_app
```

### 2. Buat & Aktifkan Virtual Environment (Disarankan)
- **Windows:**
  ```powershell
  python -m venv .venv
  .venv\Scripts\activate
  ```
- **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Instal Dependensi
```bash
pip install -r requirements.txt
```

### 4. Jalankan Aplikasi
```bash
streamlit run app.py
```
Aplikasi akan terbuka otomatis di peramban Anda di `http://localhost:8501`.

---

## 🧪 Pengujian Otomatis (*Unit Tests*)
Untuk memastikan seluruh perhitungan matriks dan verifikasi analitis berjalan akurat:
```bash
pytest -q
```

---

## 📁 Struktur Repositori
```text
structura_app/
│
├── app.py                   # Antarmuka utama Streamlit (Portal 2D & Beban Bergerak)
├── requirements.txt         # Daftar pustaka Python yang dibutuhkan
├── .gitignore               # Berkas pengabaian Git (cache, db lokal, venv)
├── README.md                # Dokumentasi lengkap proyek
├── LICENSE                  # Lisensi proyek (MIT)
│
├── structura/               # Modul mesin & logika komputasi
│   ├── engine.py            # Mesin analisis matriks kekakuan (K·u = F, reaksi, gaya dalam)
│   ├── moving_load.py       # Simulasi drag & drop beban bergerak & garis pengaruh
│   ├── plots.py             # Visualisasi interaktif Plotly (model, deformasi, BMD/SFD)
│   ├── validation.py        # Validasi kestabilan struktur dan konversi tabel
│   ├── report.py            # Generator laporan dokumen PDF (ReportLab)
│   ├── storage.py           # Penyimpanan proyek ke basis data SQLite lokal
│   └── examples.py          # Koleksi 13+ model soal standar dan kasus khusus
│
└── tests/                   # Kumpulan pengujian unit (pytest)
    ├── test_engine.py       # Verifikasi akurasi solver matriks vs solusi teoritis
    └── test_moving_load.py  # Verifikasi analitis simulasi beban bergerak
```

---

## 📄 Lisensi
Didistribusikan di bawah Lisensi MIT. Lihat berkas [`LICENSE`](LICENSE) untuk informasi lebih lanjut.
