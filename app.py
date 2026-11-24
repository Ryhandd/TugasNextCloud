# -*- coding: utf-8 -*-
"""
Asisten AI Akademik Nex — Streamlit UI
Sesuai laporan: "Asisten AI Akademik dan Kurikulum Terintegrasi Nextcloud
Berbasis LLM Lokal pada Politeknik Negeri Manado" (Rayhand N. U. Wumu, 2026).

Empat fitur (Tabel 1.1 laporan):
  1. AI Viva Voce Simulator
  2. Generator RPS & Bank Soal PBL
  3. Pencarian Semantik Dokumen Akademik (RAG)
  4. Pemeriksa Tata Bahasa & EYD

Backend: Ollama di Google Colab via tunnel ngrok (OpenAI-compatible /v1).
Catatan kepatuhan SOP Polimdo 2025: draf/saran AI wajib diperiksa manusia
(human-in-the-loop) — dispendilkan di footer tiap jawaban.
"""

import os
import json
import urllib.request

import streamlit as st

# ---------------- Konfigurasi ----------------
BACKEND_URL = st.secrets.get("BACKEND_URL", os.environ.get("BACKEND_URL", ""))
API_KEY = st.secrets.get("API_KEY", os.environ.get("API_KEY", "ollama-local"))
MODEL = st.secrets.get("MODEL", os.environ.get("MODEL", "gpt-oss:20b"))

st.set_page_config(
    page_title="Asisten AI Akademik Nex",
    page_icon="🎓",
    layout="centered",
)

# ---------------- Prompt sistem (Lampiran 2 laporan) ----------------
PROMPTS = {
    "viva": (
        "Anda adalah Dosen Penguji Sidang Tugas Akhir di Politeknik Negeri Manado "
        "yang kritis, teliti, dan mengutamakan ketajaman metodologi riset. "
        "Tugas Anda:\n"
        "1. Teliti naskah draf laporan yang diberikan mahasiswa: periksa kelemahan data, "
        "ketidakterhubungan antara masalah dan metode, atau asumsi yang belum terbukti.\n"
        "2. Ajukan pertanyaan cecaran konseptual yang menantang mahasiswa untuk membela "
        "argumen penelitiannya.\n"
        "3. Jangan memberikan jawaban langsung; dorong mahasiswa mengemukakan justifikasi "
        "ilmiah secara mandiri.\n"
        "4. Jawab selalu dalam Bahasa Indonesia yang baku."
    ),
    "rps": (
        "Anda adalah Perancang Kurikulum Pendidikan Vokasi Politeknik Negeri Manado. "
        "Berdasarkan informasi modul mata kuliah dan CPMK yang diberikan, susunlah:\n"
        "1. Draf RPS standar Polimdo (CPL, CPMK, sub-CPMK, 16 pertemuan, metode, asesmen).\n"
        "2. Satu studi kasus nyata industri berbasis Problem-Based Learning (PBL).\n"
        "3. Tiga butir pertanyaan pemecahan masalah bertingkat (analisis, sintesis, evaluasi).\n"
        "4. Rubrik penilaian analitik (kriteria skor 1-4) yang terukur dan objektif.\n"
        "5. Jawab selalu dalam Bahasa Indonesia yang baku. Hasil ini adalah DRAF yang wajib "
        "disunting dan disahkan dosen pengampu (human-in-the-loop)."
    ),
    "rag": (
        "Anda adalah Asisten Regulasi Akademik Politeknik Negeri Manado. Jawab pertanyaan "
        "pengguna HANYA berdasarkan potongan dokumen resmi yang diberikan dalam konteks. "
        "Jika jawaban tidak ada di dalam konteks, katakan terus terang bahwa informasi "
        "tidak ditemukan pada dokumen yang tersedia — jangan mengarang. "
        "Sebutkan dokumen/bagian sumber dari konteks yang Anda pakai. "
        "Jawab dalam Bahasa Indonesia yang baku."
    ),
    "eyd": (
        "Anda adalah Penyunting Bahasa Indonesia yang ahli EYD (Ejaan Yang Disempurnakan) "
        "dan tata kalimat ilmiah. Periksa teks yang diberikan:\n"
        "1. Temukan kesalahan ejaan, preposisi (di/dari/ke), kapitalisasi, dan struktur "
        "kalimat ilmiah.\n"
        "2. Tampilkan daftar koreksi: kutipan asli -> perbaikan -> alasan singkat.\n"
        "3. Sajikan juga versi teks yang sudah diperbaiki secara utuh.\n"
        "4. JANGAN mengubah substansi, istilah teknis, atau gagasan penulis — hanya "
        "perbaikan bahasa. Jawab dalam Bahasa Indonesia yang baku."
    ),
}

FEATURE_INFO = {
    "viva": {
        "judul": "🎓 Simulator Viva Voce",
        "desk": "Unggah/tempel draf laporan PKL/TA. AI berperan penguji yang melontarkan pertanyaan kritis — latih nalar Anda sebelum sidang.",
    },
    "rps": {
        "judul": "📋 Generator RPS & Bank Soal PBL",
        "desk": "Khusus dosen: isi parameter mata kuliah, dapatkan draf RPS + studi kasus PBL + rubrik penilaian siap sunting.",
    },
    "rag": {
        "judul": "🔎 Tanya Regulasi (RAG)",
        "desk": "Ajukan pertanyaan seputar regulasi/panduan. Jawaban hanya dari dokumen yang Anda unggah, disertai sumber.",
    },
    "eyd": {
        "judul": "✍️ Pemeriksa EYD & Tata Kalimat",
        "desk": "Tempel teks akademik. AI memindai EYD dan struktur kalimat ilmiah tanpa mengubah substansi.",
    },
}


# ---------------- Klien LLM ----------------
def chat(messages, temperature=0.7, max_tokens=2048):
    """Panggilan OpenAI-compatible ke Ollama di Colab (via ngrok)."""
    if not BACKEND_URL:
        return None, "Backend belum dikonfigurasi (BACKEND_URL)."
    url = BACKEND_URL.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
        "ngrok-skip-browser-warning": "true",
    })
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read())
        content = data["choices"][0]["message"].get("content", "").strip()
        if not content:  # kadang reasoning terisi, content kosong
            content = data["choices"][0]["message"].get("reasoning", "").strip()
        return content, None
    except Exception as e:
        return None, f"{e}"


def retrieve_chunks(query, text, chunk_size=1200, top_k=5):
    """RAG sederhana in-session: potong dokumen, pilih potongan paling relevan
    berdasarkan kata kunci (tanpa server embedding — sesuai batas VM kampus)."""
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    terms = [w.lower() for w in query.split() if len(w) > 3]
    scored = []
    for c in chunks:
        cl = c.lower()
        score = sum(cl.count(t) for t in terms)
        scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return "\n\n---\n\n".join(c for _, c in scored[:top_k]) if scored else text[:6000]


# ---------------- UI ----------------
st.title("🎓 Asisten AI Akademik Nex")
st.caption("Politeknik Negeri Manado — LLM lokal sesuai SOP Penggunaan AI Polimdo 2025")

st.sidebar.header("Pilih Fitur")
fitur = st.sidebar.radio(
    "Empat layanan sesuai laporan:",
    list(FEATURE_INFO.keys()),
    format_func=lambda f: FEATURE_INFO[f]["judul"],
)
st.sidebar.divider()
st.sidebar.markdown(
    f"**Model:** `{MODEL}`\n\n"
    "⚠️ **Human-in-the-loop:** seluruh keluaran AI adalah draf/saran yang "
    "wajib diperiksa dan disunting oleh pengguna (SOP Polimdo 2025 Bagian 5)."
)

info = FEATURE_INFO[fitur]
st.header(info["judul"])
st.markdown(info["desk"])

# ---------- Fitur 1: Viva Voce ----------
if fitur == "viva":
    tab1, tab2 = st.tabs(["1️⃣ Analisis Awal Naskah", "2️⃣ Sesi Tanya-Jawab"])
    with tab1:
        naskah = st.text_area(
            "Tempel draf laporan / abstrak / Bab Metode Anda:",
            height=250, key="naskah",
        )
        if st.button("🔍 Minta Penguji Menganalisis", type="primary"):
            if len(naskah) < 100:
                st.warning("Naskah terlalu pendek (minimal ±100 karakter).")
            else:
                with st.spinner("Penguji sedang menelaah naskah..."):
                    out, err = chat([
                        {"role": "system", "content": PROMPTS["viva"]},
                        {"role": "user", "content":
                            "Telaah draf laporan berikut, lalu ajukan 3 pertanyaan "
                            "cecaran konseptual yang paling menantang.\n\n"
                            f"<naskah_draf_mahasiswa>\n{naskah[:8000]}\n</naskah_draf_mahasiswa>"},
                    ], temperature=0.6, max_tokens=1500)
                if err:
                    st.error(f"Gagal menghubungi backend: {err}")
                else:
                    st.markdown(out)
                    st.info("💡 Human-in-the-loop: gunakan pertanyaan ini untuk melatih diri; "
                            "penilaian akhir tetap di tangan penguji manusia.")
    with tab2:
        st.markdown("Jawab pertanyaan penguji, AI akan mengejar dengan pertanyaan lanjutan.")
        if "vv_hist" not in st.session_state:
            st.session_state.vv_hist = []
        user_q = st.chat_input("Tulis jawaban / pertanyaan Anda...")
        for m in st.session_state.vv_hist:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
        if user_q:
            st.session_state.vv_hist.append({"role": "user", "content": user_q})
            with st.chat_message("user"):
                st.markdown(user_q)
            msgs = [{"role": "system", "content": PROMPTS["viva"]}] + \
                   st.session_state.vv_hist[-12:]
            with st.chat_message("assistant"):
                with st.spinner("Penguji menimbang..."):
                    out, err = chat(msgs, temperature=0.7)
                if err:
                    st.error(err)
                elif out:
                    st.markdown(out)
                    st.session_state.vv_hist.append({"role": "assistant", "content": out})

# ---------- Fitur 2: RPS & PBL ----------
elif fitur == "rps":
    with st.form("rps_form"):
        c1, c2 = st.columns(2)
        mk = c1.text_input("Nama Mata Kuliah", "Pemrograman Web")
        semester = c2.selectbox("Semester", list(range(1, 9)), index=3)
        cpl = st.text_area("Capaian Pembelajaran Lulusan (CPL) terkait:",
                           "Mampu merancang dan membangun aplikasi berbasis web sesuai kebutuhan industri.")
        cpmk = st.text_area("CPMK / sub-CPMK (pisahkan per baris):",
                            "Mahasiswa mampu membuat halaman web statis\n"
                            "Mahasiswa mampu membangun aplikasi web dinamis dengan basis data")
        jml_pertemuan = st.number_input("Jumlah pertemuan", 8, 20, 16)
        submitted = st.form_submit_button("🛠️ Generate Draf RPS + Soal PBL", type="primary")
    if submitted:
        prompt_user = (
            f"Buatkan draf RPS mata kuliah '{mk}' semester {semester} dengan {jml_pertemuan} pertemuan.\n"
            f"CPL:\n{cpl}\nCPMK:\n{cpmk}\n\n"
            "Kemudian tambahkan: satu studi kasus PBL dari industri lokal Sulawesi Utara, "
            "3 pertanyaan PBL bertingkat, dan rubrik penilaian analitik skor 1-4."
        )
        with st.spinner("Menyusun draf RPS & bank soal (bisa 1-3 menit)..."):
            out, err = chat([
                {"role": "system", "content": PROMPTS["rps"]},
                {"role": "user", "content": prompt_user},
            ], temperature=0.5, max_tokens=4000)
        if err:
            st.error(f"Gagal menghubungi backend: {err}")
        else:
            st.markdown(out)
            st.download_button("💾 Unduh Draf (Markdown)", out,
                               file_name=f"RPS_{mk.replace(' ', '_')}.md")
            st.info("💡 Draf ini wajib disunting dosen pengampu sebelum disahkan.")

# ---------- Fitur 3: RAG Regulasi ----------
elif fitur == "rag":
    dok = st.file_uploader("Unggah dokumen regulasi/panduan (TXT atau PDF):",
                           type=["txt", "md", "pdf"])
    corpus = ""
    if dok is not None:
        raw = dok.read()
        if dok.name.lower().endswith("pdf"):
            try:
                import io
                from pypdf import PdfReader
                corpus = "\n".join(
                    (p.extract_text() or "") for p in PdfReader(io.BytesIO(raw)).pages)
            except Exception as e:
                st.error(f"Gagal membaca PDF: {e}")
        else:
            corpus = raw.decode("utf-8", errors="replace")
        st.success(f"Dokumen dimuat: {dok.name} ({len(corpus):,} karakter)")

    if corpus:
        q = st.chat_input("Tanyakan isi regulasi, misal: 'Berapa batas SKS mengulang?'")
        if "rag_hist" not in st.session_state:
            st.session_state.rag_hist = []
        for m in st.session_state.rag_hist:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])
        if q:
            st.session_state.rag_hist.append({"role": "user", "content": q})
            with st.chat_message("user"):
                st.markdown(q)
            konteks = retrieve_chunks(q, corpus)
            with st.chat_message("assistant"):
                with st.spinner("Menelusuri dokumen..."):
                    out, err = chat([
                        {"role": "system", "content": PROMPTS["rag"]},
                        {"role": "user", "content":
                            f"KONTEKS DOKUMEN RESMI:\n{konteks}\n\n"
                            f"PERTANYAAN: {q}"},
                    ], temperature=0.2)
                if err:
                    st.error(err)
                elif out:
                    st.markdown(out)
                    st.session_state.rag_hist.append({"role": "assistant", "content": out})
    else:
        st.info("Unggah dokumen regulasi terlebih dahulu (PDF/TXT).")

# ---------- Fitur 4: EYD ----------
elif fitur == "eyd":
    teks = st.text_area("Tempel teks akademik yang ingin diperiksa:", height=250)
    if st.button("📝 Periksa EYD & Tata Kalimat", type="primary"):
        if len(teks) < 20:
            st.warning("Teks terlalu pendek.")
        else:
            with st.spinner("Menyunting..."):
                out, err = chat([
                    {"role": "system", "content": PROMPTS["eyd"]},
                    {"role": "user", "content": f"Periksa teks berikut:\n\n{teks[:8000]}"},
                ], temperature=0.2, max_tokens=3000)
            if err:
                st.error(f"Gagal menghubungi backend: {err}")
            else:
                st.markdown(out)
                st.info("💡 Terapkan koreksi secara sadar; AI hanya menyaran, manusia yang memutuskan.")

# ---------------- Status backend ----------------
st.divider()
if st.button("🩺 Cek Status Backend AI"):
    if not BACKEND_URL:
        st.error("BACKEND_URL belum diset di Secrets.")
    else:
        req = urllib.request.Request(
            BACKEND_URL.rstrip("/") + "/models",
            headers={"Authorization": f"Bearer {API_KEY}",
                     "ngrok-skip-browser-warning": "true"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                models = [m["id"] for m in json.loads(r.read())["data"]]
            if MODEL in models:
                st.success(f"Backend hidup — model `{MODEL}` tersedia.")
            else:
                st.warning(f"Backend hidup, tapi `{MODEL}` tidak ada. Tersedia: {models}")
        except Exception as e:
            st.error(f"Backend tidak dapat dihubungi: {e}")
