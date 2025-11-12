import streamlit as st
import pandas as pd
import json
from pathlib import Path

# Set konfigurasi halaman (opsional, tapi membuat tampilan lebih baik)
st.set_page_config(layout="wide", page_title="Dashboard Berita Scraper")

# Fungsi untuk memuat dan mengubah data dari satu file JSON
def load_and_transform_json(json_path, source_name):
    """
    Membaca file JSON, mengubah struktur (dari dict ke list),
    dan menambahkannya ke DataFrame.
    """
    file_path = Path(json_path)
    if not file_path.exists():
        # Jika file tidak ada, tampilkan peringatan dan kembalikan DataFrame kosong
        st.warning(f"File tidak ditemukan: {json_path}")
        return pd.DataFrame()

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    # Loop melalui struktur JSON (dimana URL adalah key)
    for url, details in data.items():
        record = details.copy()  # Salin semua detail (title, date, content, dll)
        record['url'] = url      # Tambahkan URL sebagai kolom terpisah
        record['source'] = source_name  # Tambahkan nama sumber
        records.append(record)
    
    return pd.DataFrame(records)

# ---- Fungsi Utama Aplikasi ----
def main():
    st.title("📊 Dashboard Hasil Web Scraping Kementerian/Lembaga")
    
    # --- KONFIGURASI DATA ---
    DATA_SOURCES = {
        "BKN": "scraped_bkn.json",
        "Kemdiktisaintek": "scraped_kemdiktisaintek.json",
        "Kemendikdasmen": "scraped_kemendikdasmen.json",
        "Kemenkeu": "scraped_kemenkeu.json",
        "Kemenkop": "scraped_kemenkop.json",
        "Kemhan": "scraped_kemhan.json",
        "Kemnaker": "scraped_kemnaker.json",
        "Komdigi": "scraped_komdigi.json"
    }

    BASE_PATH = Path(r"D:\MAXY ACADEMY\scrapper\data")

    # --- MEMUAT DAN MENGGABUNGKAN DATA ---
    all_dfs = []
    for source_name, filename in DATA_SOURCES.items():
        full_path = BASE_PATH / filename
        df = load_and_transform_json(full_path, source_name)
        if not df.empty:
            all_dfs.append(df)
    
    if not all_dfs:
        st.error("Tidak ada data yang berhasil dimuat. Periksa BASE_PATH dan nama file di konfigurasi DATA_SOURCES.")
        return

    df_main = pd.concat(all_dfs, ignore_index=True)

    # Konversi kolom tanggal (jika ada) dan timestamp
    if 'scraped_at' in df_main.columns:
        df_main['scraped_at_dt'] = pd.to_datetime(df_main['scraped_at'], unit='s')
    
    # ---- Sidebar untuk Filter ----
    st.sidebar.header("Filter Data")
    
    # Filter berdasarkan Sumber Berita
    sources = sorted(df_main['source'].unique())
    selected_sources = st.sidebar.multiselect("Pilih Sumber:", sources, default=sources)
    
    # --- FITUR PENCARIAN BARU ---
    search_term = st.sidebar.text_input("Cari Judul Artikel:", placeholder="Ketik kata kunci...")

    # --- APLIKASIKAN FILTER ---
    # 1. Filter berdasarkan sumber yang dipilih
    df_filtered = df_main[df_main['source'].isin(selected_sources)].copy()

    # 2. Filter berdasarkan kata kunci pencarian (jika ada)
    if search_term:
        # .str.contains() untuk mencari substring
        # case=False agar pencarian tidak case-sensitive (huruf besar/kecil tidak berpengaruh)
        # na=False untuk mengabaikan nilai NaN (kosong) di kolom judul
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_term, case=False, na=False)]

    # ---- Tampilan Utama Dashboard ----
    
    # 1. Ringkasan Data
    st.header("📈 Ringkasan Data")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Artikel (Setelah Filter)", f"{len(df_filtered):,}")
    col2.metric("Jumlah Sumber Aktif", len(selected_sources))
    col3.metric("Total Sumber Tersedia", len(sources))

    # Cek jika ada data setelah difilter
    if df_filtered.empty:
        st.warning("Tidak ada artikel yang cocok dengan filter yang Anda pilih. Coba ubah sumber atau kata kunci pencarian.")
    else:
        # 2. Tabel Data Interaktif
        st.header("📋 Data Artikel")
        st.dataframe(
            df_filtered[['source', 'title', 'date', 'scraped_at_dt']],
            use_container_width=True,
            hide_index=True
        )

        # 3. Visualisasi Jumlah Artikel per Sumber
        st.header("📊 Distribusi Artikel per Sumber")
        source_counts = df_filtered['source'].value_counts().reset_index()
        source_counts.columns = ['Sumber', 'Jumlah Artikel']
        st.bar_chart(source_counts.set_index('Sumber'))

        # 4. Detail Artikel (pilih dari dropdown)
        st.header("📖 Baca Detail Artikel")
        
        # Buat daftar judul untuk dipilih dari data yang sudah difilter
        title_options = df_filtered['title'].tolist()
        selected_title = st.selectbox("Pilih judul artikel untuk dibaca:", title_options)

        if selected_title:
            # Dapatkan semua data untuk artikel yang dipilih
            article_data = df_filtered[df_filtered['title'] == selected_title].iloc[0]
            
            st.subheader(article_data['title'])
            st.caption(f"Sumber: {article_data['source']} | Tanggal: {article_data.get('date', 'Tidak tersedia')}")
            
            # Gunakan st.expander agar konten tidak memakan banyak tempat
            with st.expander("Klik untuk membaca konten artikel"):
                st.write(article_data.get('content', 'Konten tidak tersedia.'))
            
            st.markdown(f"[🔗 Link ke Artikel Asli]({article_data['url']})", unsafe_allow_html=True)


# Menjalankan aplikasi
if __name__ == "__main__":
    main()