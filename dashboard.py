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
# Gaya CSS untuk mempercantik tampilan
# -----------------------------
st.markdown("""
    <style>
        .main-title { 
            font-size: 2rem; 
            font-weight: 700; 
            margin-bottom: 0.3em; 
            color: #1c1c1e; 
        }
        .subheader { 
            color: #555; 
            margin-bottom: 1.5em; 
        }
        .metric-container {
            background: #f9f9f9;
            border-radius: 10px;
            padding: 0.8em 1em;
            text-align: center;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
        }
        .metric-label {
            color: #666;
            font-size: 0.9rem;
        }
        a {
            color: #0073e6;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
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

    # --- Konfigurasi sumber data ---
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

    # --- Muat semua data ---
    all_dfs = []
    for source_name, file_path in DATA_SOURCES.items():
        df = load_and_transform_json(file_path, source_name)
        if not df.empty:
            all_dfs.append(df)

    if not all_dfs:
        st.error("Tidak ada data yang berhasil dimuat. Periksa kembali file JSON.")
        return

    df_main = pd.concat(all_dfs, ignore_index=True)

    # Konversi kolom scraped_at (jika ada)
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
    # Ringkasan Data
    # -----------------------------
    st.markdown("### Ringkasan Data")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"<div class='metric-container'><div class='metric-value'>{len(df_filtered):,}</div><div class='metric-label'>Total Artikel</div></div>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<div class='metric-container'><div class='metric-value'>{len(selected_sources)}</div><div class='metric-label'>Jumlah Sumber Dipilih</div></div>", unsafe_allow_html=True)
    with col3:
        if date_range:
            st.markdown(f"<div class='metric-container'><div class='metric-value'>{date_range[0]} - {date_range[1]}</div><div class='metric-label'>Rentang Tanggal</div></div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='metric-container'><div class='metric-value'>-</div><div class='metric-label'>Rentang Tanggal</div></div>", unsafe_allow_html=True)

    # -----------------------------
    # Tombol Unduh
    # -----------------------------
    csv_download = df_filtered.to_csv(index=False).encode('utf-8')
    st.download_button("Unduh Data (CSV)", data=csv_download, file_name="berita_filtered.csv", mime="text/csv")

    # -----------------------------
    # Tabel Artikel (dengan URL bisa diklik)
    # -----------------------------
    st.markdown("### Data Artikel")

    if df_filtered.empty:
        st.warning("Tidak ada artikel yang cocok dengan filter.")
        return

    # Ubah kolom URL jadi hyperlink
    df_display = df_filtered.copy()
    if 'url' in df_display.columns:
        df_display['url'] = df_display['url'].apply(lambda x: f'<a href="{x}" target="_blank">Buka Artikel</a>')

    # Pilih kolom utama
    display_cols = ['source', 'title', 'date', 'scraped_at_dt', 'url']
    available_cols = [c for c in display_cols if c in df_display.columns]

    # Tampilkan tabel dengan link aktif
    st.markdown(df_display[available_cols].to_html(escape=False, index=False), unsafe_allow_html=True)

    # -----------------------------
    # Detail Artikel
    # -----------------------------
    st.markdown("### Lihat Detail Artikel")
    title_options = df_filtered['title'].tolist()
    selected_title = st.selectbox("Pilih artikel untuk melihat detail:", title_options)

    if selected_title:
        article = df_filtered[df_filtered['title'] == selected_title].iloc[0]
        st.subheader(article['title'])
        st.caption(f"Sumber: {article['source']} | Tanggal: {article.get('date', '-')}")
        st.write(article.get('content', 'Konten tidak tersedia.'))
        st.markdown(f"[Buka Artikel Asli]({article['url']})", unsafe_allow_html=True)


# Jalankan aplikasi
if __name__ == "__main__":
    main()
