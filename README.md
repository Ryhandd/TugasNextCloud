# Asisten AI Akademik Nex — Panduan Deploy

Sesuai laporan "Asisten AI Akademik dan Kurikulum Terintegrasi Nextcloud Berbasis
LLM Lokal pada Politeknik Negeri Manado" — 4 fitur: Viva Voce, Generator RPS/PBL,
RAG Regulasi, Pemeriksa EYD.

## Arsitektur

- **Mesin AI**: Ollama `gpt-oss:20b` di Google Colab, diekspos publik via
  ngrok domain tetap `https://subscribe-cancel-reckless.ngrok-free.dev/v1`
- **UI chat**: aplikasi Streamlit ini di-deploy ke Streamlit Community Cloud
  (URL selalu hidup 24/7, tidak seperti Colab)
- **Nextcloud Debian VM**: tidak dipakai untuk AI (RAM 1.9 GB, disk 82%) —
  tetap murni file server

> Dosen mengakses link Streamlit dari mana pun, tanpa satu jaringan dengan
> VirtualBox, tanpa akun Nextcloud.

## Langkah deploy (±10 menit)

### 1. Buat repo GitHub
Buat repo publik (mis. `asisten-ai-nex`), unggah `app.py` + `requirements.txt`.
**Jangan upload `secrets.example.toml`** (di dalamnya ada URL backend).

### 2. Deploy ke Streamlit Cloud
1. Buka https://share.streamlit.io → login (pakai GitHub)
2. **Create app** → pilih repo & branch → main file `app.py`
3. URL jadi: `https://ai-rayhand-<username>.streamlit.app`
   (prefiks `ai-rayhand` bisa disesuaikan di kolom "Custom subdomain")

### 3. Isi Secrets
Menu app → **Settings → Secrets**, tempel:

```toml
BACKEND_URL = "https://subscribe-cancel-reckless.ngrok-free.dev/v1"
API_KEY = "ollama-local"
MODEL = "gpt-oss:20b"
```

### 4. Aktifkan Colab
Jalankan cell "AKTIFKAN AI" di Colab (Ollama + ngrok). Tunggu `✓ AKTIF`.

### 5. Tes
Buka link Streamlit → tombol **🩺 Cek Status Backend AI** → harus hijau.

## Keamanan (penting)

URL ngrok + API key saat ini TIDAK memvalidasi apa pun: siapa pun yang tahu
URL bisa memakai GPU Colab. Untuk demo kelas ini biasanya cukup, tetapi jika
ingin membatasi, tambahkan middleware API key di Colab atau rotasi URL ngrok
secara berkala.

## Sesuai SOP Polimdo 2025

- Setiap keluaran AI diberi catatan *human-in-the-loop* (Bagian 5 SOP)
- Dokumen yang diunggah pengguna hanya diproses in-memory di sesi browser
  masing-masing, tidak disimpan di server — dokumen internal tidak menginap
  di layanan pihak ketiga
