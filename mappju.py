import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import re
import os

# ---------------------------------------------------------
# 1. Konfigurasi Halaman & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Peta Interaktif PJU Refurbished",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Peta Interaktif Sebaran PJU Refurbished")
st.markdown("Visualisasi Titik PJU Refurbished Tol Jombang-Mojokerto.")

EXCEL_FILE = 'Dokumentasi Penggantian PJU Tol JOMO 2025-2026 (40 Unit) - Final.xlsx'

# ---------------------------------------------------------
# 2. Fungsi Helper & Cleaning Data Koordinat
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
def load_data():
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df.columns = df.columns.str.strip()
        df['lat_clean'] = df['Latitude'].apply(clean_lat)
        df['lon_clean'] = df['Longitude'].apply(clean_lon)
        return df
    else:
        st.error(f"File '{EXCEL_FILE}' tidak ditemukan di folder yang sama!")
        return pd.DataFrame(columns=['No', 'Lokasi', 'Latitude', 'Longitude', 'lat_clean', 'lon_clean'])

# Inisialisasi State Session untuk menyimpan data interaktif
if 'pju_df' not in st.session_state:
    st.session_state.pju_df = load_data()

df = st.session_state.pju_df

# ---------------------------------------------------------
# 3. Sidebar: Form Input & Filter
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
                'lon_clean': lon_input
            }])
            st.session_state.pju_df = pd.concat([st.session_state.pju_df, new_row], ignore_index=True)
            st.sidebar.success(f"Berhasil menambahkan PJU #{new_id} ({lokasi_input})!")
            st.rerun()
        else:
            st.sidebar.warning("Nama lokasi tidak boleh kosong.")

st.sidebar.markdown("---")
st.sidebar.header("🔍 Filter Area")
available_locations = ["Semua Lokasi"] + list(df['Lokasi'].dropna().unique())
selected_loc = st.sidebar.selectbox("Pilih Lokasi:", available_locations)

# Filter Dataframe
if selected_loc != "Semua Lokasi":
    filtered_df = df[df['Lokasi'] == selected_loc]
else:
    filtered_df = df

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
# 5. Rendering Peta Interaktif (Folium)
# ---------------------------------------------------------
# Tentukan pusat peta
valid_coords = filtered_df.dropna(subset=['lat_clean', 'lon_clean'])
if not valid_coords.empty:
    center_lat = valid_coords['lat_clean'].mean()
    center_lon = valid_coords['lon_clean'].mean()
else:
    center_lat, center_lon = -7.47, 112.30

# Inisialisasi Peta
m = folium.Map(
    location=[center_lat, center_lon],
    zoom_start=12,
    tiles="OpenStreetMap"
)

# Menambahkan Marker ke Peta
for _, row in valid_coords.iterrows():
    popup_content = f"""
    <div style="font-family: Arial; width: 180px;">
        <h4 style="margin-bottom:5px; color:#1E88E5;">PJU #{int(row['No'])}</h4>
        <b>Lokasi:</b> {row['Lokasi']}<br>
        <b>Status:</b> <span style="color:green; font-weight:bold;">Refurbished</span><br>
        <hr style="margin:5px 0;">
        <small><b>Lat:</b> {row['lat_clean']:.6f}</small><br>
        <small><b>Long:</b> {row['lon_clean']:.6f}</small>
    </div>
    """
    
    folium.Marker(
        location=[row['lat_clean'], row['lon_clean']],
        popup=folium.Popup(popup_content, max_width=250),
        tooltip=f"PJU #{int(row['No'])} - {row['Lokasi']}",
        icon=folium.Icon(color="green", icon="bolt", prefix="fa")
    ).add_to(m)

# Tampilkan peta di Streamlit
st_folium(m, width="100%", height=550)

# ---------------------------------------------------------
# 6. Tabel Data & Ekspor
# ---------------------------------------------------------
with st.expander("📋 Lihat & Download Data Tabel Koordinat"):
    st.dataframe(filtered_df[['No', 'Lokasi', 'lat_clean', 'lon_clean']], use_container_width=True)
    
    csv_data = filtered_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Data CSV",
        data=csv_data,
        file_name="pju_refurbished_jomo.csv",
        mime="text/csv"
    )
