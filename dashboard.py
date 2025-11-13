import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(layout="wide", page_title="Dashboard Berita Scraper")

# Fungsi memuat & ubah JSON
def load_and_transform_json(filename, source_name):
    if not os.path.exists(filename):
        st.warning(f"File tidak ditemukan: {filename}")
        return pd.DataFrame()

    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    for url, details in data.items():
        record = details.copy()
        record['url'] = url
        record['source'] = source_name
        records.append(record)
    
    return pd.DataFrame(records)

def main():
    st.title("Dashboard Hasil Web Scraping Kementerian/Lembaga")
    
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

    all_dfs = []
    for source_name, filename in DATA_SOURCES.items():
        df = load_and_transform_json(filename, source_name)
        if not df.empty:
            all_dfs.append(df)
    
    if not all_dfs:
        st.error("Tidak ada data yang berhasil dimuat. Pastikan file JSON berada di direktori yang sama.")
        return

    df_main = pd.concat(all_dfs, ignore_index=True)

    if 'scraped_at' in df_main.columns:
        df_main['scraped_at_dt'] = pd.to_datetime(df_main['scraped_at'], unit='s', errors='coerce')

    # ======== RINGKASAN DATA ========
    st.header("Ringkasan Data")
    sources = sorted(df_main['source'].unique())
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Artikel", f"{len(df_main):,}")
    col2.metric("Jumlah Sumber Aktif", len(sources))
    col3.metric("Total Sumber Tersedia", len(sources))

    # ======== FILTER DATA (bukan di sidebar) ========
    st.markdown("---")
    st.subheader("Filter Data")

    fcol1, fcol2 = st.columns([2, 3])
    with fcol1:
        selected_sources = st.multiselect("Pilih Sumber:", sources, default=sources)
    with fcol2:
        search_term = st.text_input("Cari Judul Artikel:", placeholder="Ketik kata kunci...")

    df_filtered = df_main[df_main['source'].isin(selected_sources)].copy()
    if search_term:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_term, case=False, na=False)]

    # ======== TABEL ARTIKEL ========
    st.header("Data Artikel")
    if df_filtered.empty:
        st.warning("Tidak ada artikel yang cocok dengan filter yang dipilih.")
        return

    st.dataframe(
        df_filtered[['source', 'title', 'date', 'scraped_at_dt']],
        use_container_width=True,
        hide_index=True
    )

    # ======== DISTRIBUSI ARTIKEL ========
    st.header("Distribusi Artikel per Sumber")
    source_counts = df_filtered['source'].value_counts().reset_index()
    source_counts.columns = ['Sumber', 'Jumlah Artikel']
    st.bar_chart(source_counts.set_index('Sumber'))

    # ======== BACA DETAIL ARTIKEL ========
    st.header("Baca Detail Artikel")
    title_options = df_filtered['title'].tolist()
    selected_title = st.selectbox("Pilih judul artikel:", title_options)

    if selected_title:
        article_data = df_filtered[df_filtered['title'] == selected_title].iloc[0]
        st.subheader(article_data['title'])
        st.caption(f"Sumber: {article_data['source']} | Tanggal: {article_data.get('date', 'Tidak tersedia')}")
        with st.expander("Klik untuk membaca konten artikel"):
            st.write(article_data.get('content', 'Konten tidak tersedia.'))
        st.markdown(f"[Link ke Artikel Asli]({article_data['url']})", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
