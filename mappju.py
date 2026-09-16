import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import openpyxl
import re
import os
import base64

# ---------------------------------------------------------
# 1. Konfigurasi Halaman & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Peta Interaktif PJU Refurbished Tol JOMO",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Peta Interaktif Sebaran PJU Refurbished - Tol JOMO")
st.markdown("Visualisasi Titik PJU Refurbished")

EXCEL_FILE = 'Dokumentasi Penggantian PJU Tol JOMO 2025-2026 (40 Unit) - Final.xlsx'
IMG_DIR = 'extracted_images'

# ---------------------------------------------------------
# 2. Extract Gambar dari Excel & Cleaning Data
# ---------------------------------------------------------
def clean_lat(x):
    s = str(x).strip()
    s = re.sub(r'[^\d\.-]', '', s)
    if not s or s == '-':
        return None
    if '.' in s:
        return float(s)
    if s.startswith('-'):
        return float(s[:2] + '.' + s[2:])
    return float(s[0] + '.' + s[1:])

def clean_lon(x):
    s = str(x).strip()
    s = re.sub(r'[^\d\.-]', '', s)
    if not s or s == '-':
        return None
    if '.' in s:
        return float(s)
    return float(s[:3] + '.' + s[3:])

@st.cache_data
def extract_images_and_load_data():
    if not os.path.exists(EXCEL_FILE):
        st.error(f"File '{EXCEL_FILE}' tidak ditemukan!")
        return pd.DataFrame()

    # Ekstrak data tabel
    df = pd.read_excel(EXCEL_FILE)
    df.columns = df.columns.str.strip()
    df['lat_clean'] = df['Latitude'].apply(clean_lat)
    df['lon_clean'] = df['Longitude'].apply(clean_lon)

    # Ekstrak gambar dari Excel
    os.makedirs(IMG_DIR, exist_ok=True)
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)
    sheet = wb.active

    img_map = {}
    for i, img in enumerate(sheet._images):
        try:
            row = img.anchor._from.row + 1  # 1-indexed row di excel
            img_data = img._data()
            img_path = os.path.join(IMG_DIR, f"pju_row_{row}.png")
            
            with open(img_path, "wb") as f:
                f.write(img_data)

            # Konversi gambar ke base64 agar mudah ditampilkan di HTML Folium
            with open(img_path, "rb") as f:
                b64_str = base64.b64encode(f.read()).decode('utf-8')
                img_map[row] = f"data:image/png;base64,{b64_str}"
        except Exception as e:
            pass

    # Petakan base64 image ke dataframe berdasarkan nomor baris Excel (Header = Baris 2)
    df['img_base64'] = [img_map.get(idx + 3, None) for idx in df.index]
    return df

# Load State Data
if 'pju_df' not in st.session_state:
    st.session_state.pju_df = extract_images_and_load_data()

df = st.session_state.pju_df

# ---------------------------------------------------------
# 3. Sidebar: Form Input & Filter Area
# ---------------------------------------------------------
st.sidebar.header("📍 Tambah Titik PJU Baru")
with st.sidebar.form("form_add_pju"):
    lokasi_input = st.text_input("Nama Lokasi / Area (misal: GT Bandar)")
    lat_input = st.number_input("Latitude", value=-7.447000, format="%.6f")
    lon_input = st.number_input("Longitude", value=112.406000, format="%.6f")
    
    submit_btn = st.form_submit_button("➕ Tambah ke Peta")
    
    if submit_btn:
        if lokasi_input.strip() != "":
            new_id = len(st.session_state.pju_df) + 1
            new_row = pd.DataFrame([{
                'No': new_id,
                'Lokasi': lokasi_input,
                'Latitude': lat_input,
                'Longitude': lon_input,
                'lat_clean': lat_input,
                'lon_clean': lon_input,
                'img_base64': None
            }])
            st.session_state.pju_df = pd.concat([st.session_state.pju_df, new_row], ignore_index=True)
            st.sidebar.success(f"Berhasil menambahkan PJU #{new_id} ({lokasi_input})!")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filter Area")
available_locations = ["Semua Lokasi"] + list(df['Lokasi'].dropna().unique())
selected_loc = st.sidebar.selectbox("Pilih Lokasi:", available_locations)

filtered_df = df if selected_loc == "Semua Lokasi" else df[df['Lokasi'] == selected_loc]

# ---------------------------------------------------------
# 4. Ringkasan KPI Cards
# ---------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total PJU Refurbished", f"{len(df)} Unit")
col2.metric("Target Total PJU", "752+ Unit")
col3.metric("Persentase Refurbished", f"{(len(df)/600)*100:.1f}%")
col4.metric("Jumlah Area Tercover", f"{df['Lokasi'].nunique()} Area")

st.markdown("---")

# ---------------------------------------------------------
# 5. Rendering Peta Interaktif + Popup Foto
# ---------------------------------------------------------
valid_coords = filtered_df.dropna(subset=['lat_clean', 'lon_clean'])

center_lat = valid_coords['lat_clean'].mean() if not valid_coords.empty else -7.47
center_lon = valid_coords['lon_clean'].mean() if not valid_coords.empty else 112.30

m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

for _, row in valid_coords.iterrows():
    # Cek apakah ada foto
    if pd.notna(row['img_base64']):
        img_html = f'<img src="{row["img_base64"]}" style="width:100%; max-height:180px; object-fit:cover; border-radius:5px; margin-top:8px;" />'
    else:
        img_html = '<div style="background:#f0f0f0; color:#777; text-align:center; padding:10px; margin-top:8px; border-radius:5px;"><small>Tidak ada foto</small></div>'

    popup_content = f"""
    <div style="font-family: Arial, sans-serif; width: 200px;">
        <h4 style="margin:0 0 5px 0; color:#1E88E5;">PJU #{int(row['No'])}</h4>
        <b>Lokasi:</b> {row['Lokasi']}<br>
        <b>Status:</b> <span style="color:green; font-weight:bold;">Refurbished</span><br>
        <small><b>Lat:</b> {row['lat_clean']:.6f}</small><br>
        <small><b>Long:</b> {row['lon_clean']:.6f}</small>
        {img_html}
    </div>
    """
    
    folium.Marker(
        location=[row['lat_clean'], row['lon_clean']],
        popup=folium.Popup(popup_content, max_width=240),
        tooltip=f"PJU #{int(row['No'])} - {row['Lokasi']}",
        icon=folium.Icon(color="green", icon="bolt", prefix="fa")
    ).add_to(m)

st_folium(m, width="100%", height=600)
