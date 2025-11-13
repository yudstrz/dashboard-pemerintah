import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime

# -----------------------------
# Konfigurasi Halaman
# -----------------------------
st.set_page_config(
    layout="wide",
    page_title="Dashboard Scraper Berita Kementerian/Lembaga",
)

# -----------------------------
# Gaya CSS untuk mempercantik UI
# -----------------------------
st.markdown("""
    <style>
        body { background-color: #f9f9f9; }
        .main-title { font-size: 2rem; font-weight: 700; margin-bottom: 0.5em; color: #1c1c1e; }
        .subheader { color: #555; margin-bottom: 1em; }
        .article-card {
            background-color: white;
            border-radius: 12px;
            padding: 1em 1.5em;
            margin-bottom: 1em;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .article-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 0.2em;
        }
        .article-meta {
            font-size: 0.9rem;
            color: #777;
            margin-bottom: 0.5em;
        }
        .search-bar input {
            border-radius: 8px;
            border: 1px solid #ccc;
        }
    </style>
""", unsafe_allow_html=True)


# -----------------------------
# Fungsi untuk memuat dan mengubah data JSON
# -----------------------------
def load_and_transform_json(json_path, source_name):
    file_path = Path(json_path)
    if not file_path.exists():
        st.warning(f"File tidak ditemukan: {json_path}")
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


# -----------------------------
# Main Function
# -----------------------------
def main():
    st.markdown('<div class="main-title">Dashboard Hasil Scraper Berita</div>', unsafe_allow_html=True)
    st.markdown('<div class="subheader">Menampilkan hasil pengambilan berita dari berbagai sumber kementerian/lembaga.</div>', unsafe_allow_html=True)

    # Konfigurasi sumber data
    DATA_SOURCES = {
        "BKN": r"scraped_bkn.json",
        "Kemdiktisaintek": r"scraped_kemdiktisaintek.json",
        "Kemendikdasmen": r"scraped_kemendikdasmen.json",
        "Kemenkeu": r"scraped_kemenkeu.json",
        "Kemenkop": r"scraped_kemenkop.json",
        "Kemhan": r"scraped_kemhan.json",
        "Kemnaker": r"scraped_kemnaker.json",
        "Komdigi": r"scraped_komdigi.json"
    }

    all_dfs = []
    for source_name, file_path in DATA_SOURCES.items():
        df = load_and_transform_json(file_path, source_name)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        st.error("Tidak ada data yang berhasil dimuat. Periksa kembali file JSON.")
        return

    df_main = pd.concat(all_dfs, ignore_index=True)

    if 'scraped_at' in df_main.columns:
        df_main['scraped_at_dt'] = pd.to_datetime(df_main['scraped_at'], unit='s')
    else:
        df_main['scraped_at_dt'] = None

    # -----------------------------
    # Sidebar Filter
    # -----------------------------
    st.sidebar.header("Filter dan Pencarian")

    sources = sorted(df_main['source'].unique())
    selected_sources = st.sidebar.multiselect("Pilih sumber berita:", sources, default=sources)

    search_term = st.sidebar.text_input("Cari judul artikel:", placeholder="Ketik kata kunci...")

    if df_main['scraped_at_dt'].notnull().any():
        min_date = df_main['scraped_at_dt'].min().date()
        max_date = df_main['scraped_at_dt'].max().date()
        date_range = st.sidebar.date_input("Rentang tanggal scraping:", [min_date, max_date])
    else:
        date_range = None

    sort_order = st.sidebar.radio("Urutkan berdasarkan tanggal:", ["Terbaru", "Terlama"])

    # -----------------------------
    # Terapkan Filter
    # -----------------------------
    df_filtered = df_main[df_main['source'].isin(selected_sources)].copy()

    if search_term:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_term, case=False, na=False)]

    if date_range and 'scraped_at_dt' in df_filtered.columns:
        start, end = date_range
        df_filtered = df_filtered[
            (df_filtered['scraped_at_dt'].dt.date >= start) &
            (df_filtered['scraped_at_dt'].dt.date <= end)
        ]

    if sort_order == "Terbaru":
        df_filtered = df_filtered.sort_values(by='scraped_at_dt', ascending=False)
    else:
        df_filtered = df_filtered.sort_values(by='scraped_at_dt', ascending=True)

    # -----------------------------
    # Ringkasan
    # -----------------------------
    st.markdown("### Ringkasan Data")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Artikel", f"{len(df_filtered):,}")
    col2.metric("Jumlah Sumber", len(selected_sources))
    col3.metric("Rentang Waktu", f"{date_range[0]} - {date_range[1]}" if date_range else "Tidak tersedia")

    # Tombol unduh
    csv_download = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button("Unduh Data (CSV)", data=csv_download, file_name="berita_filtered.csv", mime="text/csv")

    # -----------------------------
    # Tampilan Artikel
    # -----------------------------
    if df_filtered.empty:
        st.warning("Tidak ada artikel yang cocok dengan filter.")
    else:
        st.markdown("### Daftar Artikel")
        for _, row in df_filtered.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="article-card">
                    <div class="article-title">{row['title']}</div>
                    <div class="article-meta">
                        {row['source']} | {row.get('date', 'Tanggal tidak tersedia')} | 
                        {row.get('scraped_at_dt', '')}
                    </div>
                    <div>{row.get('content', '')[:250]}...</div>
                    <a href="{row['url']}" target="_blank">Baca Selengkapnya</a>
                </div>
                """, unsafe_allow_html=True)


# Jalankan aplikasi
if __name__ == "__main__":
    main()
