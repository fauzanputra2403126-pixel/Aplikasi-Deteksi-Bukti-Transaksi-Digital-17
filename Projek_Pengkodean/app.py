import streamlit as st
from PIL import Image
import numpy as np
from modules.template_generator import generate_reference_template, PROVIDER_CONFIGS
from modules.converter import extract_multi_fields_ocr, extract_roi_and_foreground, convert_template_to_vector, compute_ela_score
from modules.hamming import compute_forensic_hamming

# 1. Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="VerifyID - Multi-Bank Transaction Forensics",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Custom CSS UI Gen-Z (Dark Theme & Glowing Badges)
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0b0f19 0%, #111827 100%);
        color: #f3f4f6;
    }
    .status-badge-asli {
        background: linear-gradient(135deg, #059669 0%, #10b981 100%);
        color: white;
        padding: 18px 24px;
        border-radius: 14px;
        font-weight: 700;
        font-size: 26px;
        text-align: center;
        box-shadow: 0 4px 25px rgba(16, 185, 129, 0.45);
        margin-bottom: 24px;
    }
    .status-badge-palsu {
        background: linear-gradient(135deg, #dc2626 0%, #ef4444 100%);
        color: white;
        padding: 18px 24px;
        border-radius: 14px;
        font-weight: 700;
        font-size: 26px;
        text-align: center;
        box-shadow: 0 4px 25px rgba(239, 68, 68, 0.45);
        margin-bottom: 24px;
    }
</style>
""", unsafe_allow_html=True)

# 3. Header Utama
st.title("🛡️ VerifyID: Sistem Deteksi Transaksi Digital")
st.caption("Verifikasi Keaslian Resi m-Banking & e-Wallet Berbasis Multi-Field Hamming Forensics")
st.markdown("---")

# 4. Sidebar Panel Parameter Transaksi Multi-Informasi
with st.sidebar:
    st.header("⚙️ Parameter Backend Tagihan")
    
    st.subheader("1. Provider Transfer")
    provider_choice = st.selectbox(
        "Pilih m-Banking / e-Wallet:",
        list(PROVIDER_CONFIGS.keys())
    )
    
    st.subheader("2. Nominal Tagihan Resmi")
    nominal_tagihan_input = st.text_input("Nominal Tagihan (Rp)", value="Rp 500.000")
    
    st.subheader("3. Teks Informasi Penting Lainnya (Opsional)")
    date_tagihan_input = st.text_input("Tanggal Transaksi (dd/mm/yyyy)", value="")
    ref_tagihan_input = st.text_input("No. Referensi / ID Transaksi", value="")
    
    st.markdown("---")
    st.info(f"**Provider:** {provider_choice}\n\n**Metode:** Multi-Field ASCII Hamming & ELA")

# 5. Main Area Input 1 Gambar & Display Preview
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📤 Unggah 1 Bukti Transaksi")
    uploaded_file = st.file_uploader(
        f"Pilih berkas resi ({provider_choice}) - JPG/PNG", 
        type=['png', 'jpg', 'jpeg']
    )
    
    if uploaded_file:
        st.image(uploaded_file, caption=f"Gambar Bukti Uji ({provider_choice})", use_container_width=True)

with col_right:
    st.subheader("🔬 Pratinjau Analisis Forensik Digital")
    if uploaded_file:
        # A. Citra Acuan Resmi Backend (x)
        template_img = generate_reference_template(
            nominal_str=nominal_tagihan_input,
            provider_name=provider_choice
        )
        vec_x, ar_x = convert_template_to_vector(template_img)
        
        # B. Ekstraksi ROI Auto-Centered Gambar Uji Diunggah (y)
        roi_img, vec_y, ar_y = extract_roi_and_foreground(uploaded_file)
        
        c1, c2 = st.columns(2)
        with c1:
            st.image(template_img, caption=f"Acuan Backend ({provider_choice})", use_container_width=True)
        with c2:
            st.image(roi_img, caption="ROI Auto-Centered (y)", use_container_width=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        btn_analyze = st.button("🚀 Verifikasi Keaslian Resi", type="primary", use_container_width=True)

# 6. Output Hasil Verifikasi Forensik
if uploaded_file and 'btn_analyze' in locals() and btn_analyze:
    st.markdown("---")
    st.header("📋 Hasil Evaluasi Integritas Data")
    
    # Ekstraksi Multi-Informasi OCR & ELA Score
    raw_img, digits_found, date_found, ref_found, raw_ocr = extract_multi_fields_ocr(uploaded_file)
    ela_score = compute_ela_score(uploaded_file)
    
    # Jalankan Evaluasi Hamming Multi-Field
    results = compute_forensic_hamming(
        vec_x, vec_y, ar_x, ar_y, 
        nominal_tagihan_input, digits_found, 
        date_tagihan_input, date_found,
        ref_tagihan_input, ref_found,
        ela_score
    )
    
    # Display Banner Status Utama
    if results['verdict'] == "VALID_ASLI":
        st.markdown(f'<div class="status-badge-asli">{results["title_output"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="status-badge-palsu">{results["title_output"]}</div>', unsafe_allow_html=True)
        
    st.write(f"**Keterangan Analisis:** {results['description']}")
    
    # Dashboard Metrik Angka Multi-Field
    st.markdown("### 📊 Dashboard Metrik Hamming Forensik Multi-Field")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("HD ASCII Nominal", f"{results['hd_nom']} bit")
    m2.metric("Total HD ASCII", f"{results['total_hd_ascii']} bit")
    m3.metric("Skor ELA Editan Digital", f"{results['ela_score']:.2f}")
    m4.metric("Kemiripan Piksel Teks", f"{results['fg_sim_ratio']:.2f} %")
    
    # Verifikasi Teorema Matematika
    st.markdown("### 📐 Pembuktian Formulasi Teori Pengkodean")
    if results['is_verified']:
        st.success(f"✅ **Terbukti Mutlak:** Nilai $d(x,y)$ tepat ekuivalen dengan $wt(x \\oplus y)$ pada level ASCII ({results['total_hd_ascii']} bit) dan level Piksel ({results['hd_fg']:,} bit).")
    else:
        st.error("⚠️ Ketidaksesuaian komputasi biner!")
elif not uploaded_file:
    st.info("👆 Silakan pilih provider di sidebar dan unggah 1 lembar gambar resi untuk verifikasi.")