import streamlit as st
import pandas as pd
import json
from pathlib import Path

# --------------------------------------------------
# KONFIGURASI DASAR
# --------------------------------------------------
st.set_page_config(
    layout="wide",
    page_title="Dashboard Berita Scraper",
    page_icon="📰"
)

# --------------------------------------------------
# FUNGSI MEMUAT DATA JSON
# --------------------------------------------------
def load_and_transform_json(json_path, source_name):
    """
    Membaca file JSON, ubah dari dict ke list, lalu jadi DataFrame.
    """
    file_path = Path(json_path)
    if not file_path.exists():
        st.warning(f"⚠️ File tidak ditemukan: {json_path}")
        return pd.DataFrame()

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for url, details in data.items():
        record = details.copy()
        record['url'] = url
        record['source'] = source_name
        records.append(record)

    return pd.DataFrame(records)

# --------------------------------------------------
# FUNGSI UTAMA
# --------------------------------------------------
def main():
    st.title("🗞️ Dashboard Hasil Web Scraping Kementerian/Lembaga")
    st.markdown("Menampilkan hasil scraping berita dari berbagai sumber resmi pemerintah.")

    # --- KONFIGURASI FILE SUMBER DATA ---
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

    # --- MEMUAT SEMUA FILE ---
    all_dfs = []
    for source_name, filename in DATA_SOURCES.items():
        df = load_and_transform_json(BASE_PATH / filename, source_name)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        st.error("❌ Tidak ada data yang berhasil dimuat. Periksa BASE_PATH dan nama file.")
        return

    df_main = pd.concat(all_dfs, ignore_index=True)

    # Tambahkan kolom waktu scraping (jika ada)
    if 'scraped_at' in df_main.columns:
        df_main['scraped_at_dt'] = pd.to_datetime(df_main['scraped_at'], unit='s')
    else:
        df_main['scraped_at_dt'] = pd.NaT

    # --------------------------------------------------
    # SIDEBAR: FILTER
    # --------------------------------------------------
    st.sidebar.header("🔍 Filter Data")
    sources = sorted(df_main['source'].unique())
    selected_sources = st.sidebar.multiselect("Pilih sumber berita:", sources, default=sources)

    search_term = st.sidebar.text_input("Cari judul artikel:", placeholder="Ketik kata kunci...")

    # Terapkan filter
    df_filtered = df_main[df_main['source'].isin(selected_sources)].copy()
    if search_term:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_term, case=False, na=False)]

    # --------------------------------------------------
    # RINGKASAN
    # --------------------------------------------------
    st.header("📈 Ringkasan Data")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Artikel (setelah filter)", f"{len(df_filtered):,}")
    col2.metric("Jumlah Sumber Aktif", len(selected_sources))
    col3.metric("Total Sumber Tersedia", len(sources))

    if df_filtered.empty:
        st.warning("⚠️ Tidak ada artikel yang cocok dengan filter.")
        return

    # --------------------------------------------------
    # TABEL ARTIKEL
    # --------------------------------------------------
    st.header("📋 Daftar Artikel")
    st.caption("Klik satu baris untuk melihat konten artikel di bawah tabel.")

    # Pilih kolom yang ingin ditampilkan
    display_cols = ['source', 'title', 'date', 'scraped_at_dt']
    df_show = df_filtered[display_cols].copy()
    df_show.index = range(1, len(df_show) + 1)

    # Gunakan dataframe interaktif (Streamlit 1.28+ mendukung row selection)
    selected_rows = st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=False,
        selection_mode="single-row",
        key="table_select"
    )

    # --------------------------------------------------
    # TAMPILKAN DETAIL ARTIKEL (OTOMATIS DARI ROW DIPILIH)
    # --------------------------------------------------
    # Dapatkan indeks baris yang dipilih
    selected_indices = st.session_state.get("table_select", {}).get("selection", {}).get("rows", [])
    if selected_indices:
        selected_idx = selected_indices[0]
        article_data = df_filtered.iloc[selected_idx]

        st.markdown("---")
        st.subheader(article_data['title'])
        st.caption(f"🕓 {article_data.get('date', 'Tanggal tidak tersedia')} | 🏛️ {article_data['source']}")
        
        with st.expander("📖 Lihat Konten Artikel", expanded=True):
            st.write(article_data.get('content', 'Konten tidak tersedia.'))

        st.markdown(f"[🔗 Baca artikel asli]({article_data['url']})", unsafe_allow_html=True)
    else:
        st.info("👆 Klik salah satu artikel di tabel untuk menampilkan isi beritanya di sini.")

    # --------------------------------------------------
    # CHART DISTRIBUSI ARTIKEL
    # --------------------------------------------------
    st.header("📊 Distribusi Artikel per Sumber")
    source_counts = df_filtered['source'].value_counts().reset_index()
    source_counts.columns = ['Sumber', 'Jumlah Artikel']
    st.bar_chart(source_counts.set_index('Sumber'))


# --------------------------------------------------
# MAIN ENTRY
# --------------------------------------------------
if __name__ == "__main__":
    main()
