import streamlit as st
import pandas as pd
import json
import numpy as np
from pathlib import Path
import google.generativeai as genai
from sklearn.metrics.pairwise import cosine_similarity

# --- Konfigurasi Halaman Streamlit ---
st.set_page_config(
    layout="centered", 
    page_title="Chatbot RAG Artikel",
    page_icon="🤖"
)

# --- Konfigurasi Sumber Data ---
# (Sesuai dengan path file Anda, asumsikan di folder yang sama)
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

# --- Fungsi Pemuatan Data (Sama seperti sebelumnya) ---
def load_and_transform_json(json_path, source_name):
    file_path = Path(json_path)
    if not file_path.exists():
        st.warning(f"File tidak ditemukan: {json_path}")
        return pd.DataFrame()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        st.warning(f"Error membaca JSON dari: {json_path}. File mungkin kosong atau rusak.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error tidak terduga saat membuka {json_path}: {e}")
        return pd.DataFrame()

    records = []
    # Memastikan 'data' adalah dictionary sebelum di-loop
    if not isinstance(data, dict):
        st.warning(f"Format data di {json_path} tidak terduga (bukan dict).")
        return pd.DataFrame()
        
    for url, details in data.items():
        # Memastikan 'details' adalah dict
        if isinstance(details, dict):
            record = details.copy()
            record['url'] = url
            record['source'] = source_name
            # Pastikan kolom 'content' ada, jika tidak, isi dengan string kosong
            if 'content' not in record:
                record['content'] = "" # Penting untuk embedding
            records.append(record)
        
    return pd.DataFrame(records)

# --- Fungsi Pemuatan & Caching Data ---
@st.cache_data
def load_all_data(data_sources):
    """Memuat semua data dari file JSON dan menggabungkannya."""
    all_dfs = []
    for source_name, filename in data_sources.items():
        df = load_and_transform_json(filename, source_name)
        if not df.empty:
            all_dfs.append(df)
            
    if not all_dfs:
        return pd.DataFrame()
        
    df_main = pd.concat(all_dfs, ignore_index=True)
    # Menghapus duplikat jika ada
    df_main = df_main.drop_duplicates(subset=['url'])
    # Memastikan tidak ada konten yang kosong (NaN)
    df_main['content'] = df_main['content'].fillna("")
    df_main['title'] = df_main['title'].fillna("")
    return df_main

# --- Fungsi Inti RAG (Embedding) ---
@st.cache_data
def get_all_embeddings(df, api_key):
    """
    Membuat embedding untuk setiap artikel di DataFrame.
    Ini hanya akan berjalan sekali per sesi berkat @st.cache_data.
    """
    # Konfigurasi model embedding
    genai.configure(api_key=api_key)
    
    # Menambahkan kolom 'embedding' baru
    # Kita akan memproses dalam batch jika datanya besar (di sini contoh sederhana)
    embeddings = []
    
    # Menggunakan progress bar
    progress_bar = st.progress(0, text="Membuat embeddings untuk basis data...")
    
    total_articles = len(df)
    for i, row in df.iterrows():
        # Hanya buat embedding jika kontennya tidak kosong
        if row['content']:
            try:
                # Menggunakan model embedding Google
                response = genai.embed_content(
                    model="models/embedding-001", # Model embedding
                    content=row['content'],
                    task_type="RETRIEVAL_DOCUMENT"
                )
                embeddings.append(response['embedding'])
            except Exception as e:
                st.error(f"Error saat membuat embedding untuk '{row['title']}': {e}")
                embeddings.append(None) # Tambah None jika gagal
        else:
            embeddings.append(None) # Tambah None jika konten kosong
            
        # Update progress bar
        progress_bar.progress((i + 1) / total_articles, text=f"Memproses artikel {i+1}/{total_articles}")
    
    progress_bar.empty() # Hapus progress bar
    df['embedding'] = embeddings
    
    # Hapus baris yang gagal di-embed
    df_clean = df.dropna(subset=['embedding'])
    return df_clean

def get_relevant_articles(query, df_with_embeddings, api_key, top_k=3):
    """Mencari artikel paling relevan berdasarkan query."""
    if df_with_embeddings.empty:
        return pd.DataFrame()
        
    genai.configure(api_key=api_key)
    
    # 1. Buat embedding untuk query
    try:
        query_embedding = genai.embed_content(
            model="models/embedding-001",
            content=query,
            task_type="RETRIEVAL_QUERY" # Task type berbeda untuk query!
        )['embedding']
    except Exception as e:
        st.error(f"Error membuat embedding untuk query: {e}")
        return pd.DataFrame()

    # 2. Siapkan matriks embedding dokumen
    # Ubah list embedding di DataFrame menjadi matriks NumPy
    document_embeddings = np.array(df_with_embeddings['embedding'].tolist())
    
    # 3. Hitung cosine similarity
    # query_embedding perlu di-reshape agar menjadi 2D array
    similarities = cosine_similarity(
        np.array(query_embedding).reshape(1, -1),
        document_embeddings
    )
    
    # 4. Dapatkan Tqp-K
    # [0] karena similarities adalah 2D array [1, N]
    top_k_indices = similarities[0].argsort()[-top_k:][::-1]
    
    # 5. Kembalikan DataFrame artikel yang relevan
    relevant_df = df_with_embeddings.iloc[top_k_indices].copy()
    relevant_df['similarity'] = similarities[0][top_k_indices]
    
    # Filter hasil yang similarity-nya terlalu rendah (opsional, tapi bagus)
    relevant_df = relevant_df[relevant_df['similarity'] > 0.4]
    
    return relevant_df

def get_gemini_response(prompt, api_key):
    """Mendapatkan jawaban dari Gemini berdasarkan prompt RAG."""
    genai.configure(api_key=api_key)
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            prompt,
            # Konfigurasi keamanan untuk mengurangi pemblokiran
            safety_settings={
                'HATE_SPEECH': 'BLOCK_NONE',
                'HARASSMENT': 'BLOCK_NONE',
                'SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                'DANGEROUS_CONTENT': 'BLOCK_NONE'
            }
        )
        return response.text
    except Exception as e:
        st.error(f"Error saat menghubungi Gemini: {e}")
        return "Maaf, terjadi kesalahan saat memproses jawaban."


# --- Tampilan Utama Streamlit ---
st.title("🤖 Chatbot RAG Artikel Kementerian")
st.caption("Tanya jawab seputar artikel dari data JSON Anda.")

# --- 1. Input API Key di Sidebar ---
st.sidebar.header("Konfigurasi")
api_key = st.sidebar.text_input(
    "Masukkan Google API Key Anda:", 
    type="password",
    help="Dapatkan API Key Anda dari Google AI Studio."
)

if not api_key:
    st.info("Silakan masukkan Google API Key Anda di sidebar untuk memulai.")
    st.stop()

# --- 2. Muat dan Proses Data (Hanya jika API Key ada) ---
try:
    with st.spinner("Memuat dan memproses data artikel..."):
        # Muat data mentah
        df_raw = load_all_data(DATA_SOURCES)
        
        if df_raw.empty:
            st.error("Gagal memuat data. Periksa nama file dan format JSON Anda.")
            st.stop()
            
        # Buat embeddings (ini akan di-cache)
        df_with_embeddings = get_all_embeddings(df_raw.copy(), api_key)
        
        if df_with_embeddings.empty:
            st.error("Gagal membuat embeddings. Pastikan API Key valid dan konten JSON tidak kosong.")
            st.stop()

    # Tampilkan info data di sidebar
    st.sidebar.success(f"Basis data siap! ({len(df_with_embeddings)} artikel terindeks)")

except Exception as e:
    st.error(f"Terjadi kesalahan saat inisialisasi: {e}")
    st.sidebar.error("API Key tidak valid atau terjadi error.")
    st.stop()


# --- 3. Inisialisasi Riwayat Chat ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan riwayat chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 4. Input Chat dari Pengguna ---
if prompt := st.chat_input("Tulis pertanyaan Anda di sini..."):
    # Tampilkan pesan pengguna
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Proses jawaban AI
    with st.chat_message("assistant"):
        with st.spinner("Mencari jawaban..."):
            
            # 1. RETRIEVE: Dapatkan artikel relevan
            relevant_articles = get_relevant_articles(prompt, df_with_embeddings, api_key)

            # 2. AUGMENT: Buat prompt untuk Gemini
            if relevant_articles.empty:
                # Jika tidak ada artikel relevan
                context_str = "Tidak ada konteks yang ditemukan."
                full_prompt = (
                    "Anda adalah asisten AI yang ramah.\n"
                    f"Pengguna bertanya: '{prompt}'\n"
                    "Jawab dengan jujur bahwa Anda tidak menemukan informasi tersebut dalam basis data artikel yang Anda miliki. Jangan mencoba menjawab dari pengetahuan umum Anda."
                )
            else:
                # Jika ada artikel relevan, format sebagai konteks
                context_str = ""
                for i, row in relevant_articles.iterrows():
                    context_str += f"--- Konteks {i+1} (Sumber: {row['source']}) ---\n"
                    context_str += f"Judul: {row['title']}\n"
                    context_str += f"Konten: {row['content'][:1000]}...\n\n" # Ambil 1000 karakter pertama
                
                full_prompt = (
                    "Anda adalah asisten AI yang sangat teliti. Tugas Anda adalah menjawab pertanyaan pengguna HANYA berdasarkan konteks yang diberikan di bawah ini. "
                    "Jika jawaban tidak ada di dalam konteks, katakan 'Maaf, saya tidak menemukan informasi tersebut dalam artikel yang tersedia.'\n"
                    "Jangan pernah menggunakan pengetahuan eksternal Anda.\n\n"
                    "--- KONTEKS ARTIKEL ---\n"
                    f"{context_str}"
                    "------------------------\n\n"
                    f"PERTANYAAN PENGGUNA: {prompt}\n\n"
                    "JAWABAN (berdasarkan konteks di atas):"
                )

            # 3. GENERATE: Dapatkan jawaban dari Gemini
            response_text = get_gemini_response(full_prompt, api_key)
            
            # Tampilkan jawaban
            st.markdown(response_text)
            
            # Tampilkan sumber jika ada
            if not relevant_articles.empty:
                with st.expander("Lihat Sumber Artikel yang Digunakan"):
                    for i, row in relevant_articles.iterrows():
                        st.caption(f"**Sumber: {row['source']}** ([Link]({row['url']}))")
                        st.write(f"**Judul:** {row['title']}")
                        st.write(f"*(Relevansi: {row['similarity']:.2f})*")

            # Simpan jawaban ke riwayat
            st.session_state.messages.append({"role": "assistant", "content": response_text})
