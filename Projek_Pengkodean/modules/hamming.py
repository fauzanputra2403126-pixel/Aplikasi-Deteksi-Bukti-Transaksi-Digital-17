import numpy as np
from modules.template_generator import string_to_ascii_binary_vector, clean_nominal_string

def compute_ascii_hamming(str1, str2):
    """Menghitung Hamming Distance dan Weight Vektor Biner ASCII antara dua string."""
    s1 = str(str1).strip()
    s2 = str(str2).strip()
    max_len = max(len(s1), len(s2), 1)
    s1_pad = s1.ljust(max_len, ' ')
    s2_pad = s2.ljust(max_len, ' ')
    
    vec1 = string_to_ascii_binary_vector(s1_pad)
    vec2 = string_to_ascii_binary_vector(s2_pad)
    
    xor_vec = np.bitwise_xor(vec1, vec2)
    hd = int(np.sum(xor_vec))
    hw = int(np.count_nonzero(xor_vec))
    sim = (1.0 - (hd / len(vec1))) * 100.0
    return hd, hw, len(vec1), sim

def compute_forensic_hamming(
    vector_x, vector_y, ar_x, ar_y, 
    nominal_tagihan, nominal_resi_ocr, 
    date_tagihan="", date_resi_ocr="",
    ref_tagihan="", ref_resi_ocr="",
    ela_score=0.0, ela_threshold=18.0
):
    """
    Mesin Keputusan Forensik Multi-Field:
    1. Metrik Biner ASCII Nominal, Tanggal, & No. Referensi
    2. Metrik Biner Piksel Teks (Foreground Only)
    3. Deteksi Manipulasi Digital ELA
    """
    str_nom_x = clean_nominal_string(nominal_tagihan)
    str_nom_y = clean_nominal_string(nominal_resi_ocr) if nominal_resi_ocr else "0"
    
    # 1. ASCII Hamming Nominal
    hd_nom, hw_nom, bits_nom, sim_nom = compute_ascii_hamming(str_nom_x, str_nom_y)
    
    # 2. ASCII Hamming Tanggal Transaksi (jika diisi)
    date_x = str(date_tagihan).strip()
    date_y = str(date_resi_ocr).strip() if date_resi_ocr else date_x
    hd_date, hw_date, bits_date, sim_date = compute_ascii_hamming(date_x, date_y)
    
    # 3. ASCII Hamming No. Referensi (jika diisi)
    ref_x = str(ref_tagihan).strip()
    ref_y = str(ref_resi_ocr).strip() if ref_resi_ocr else ref_x
    hd_ref, hw_ref, bits_ref, sim_ref = compute_ascii_hamming(ref_x, ref_y)
    
    total_hd_ascii = hd_nom + (hd_date if date_x else 0) + (hd_ref if ref_x else 0)
    total_hw_ascii = hw_nom + (hw_date if date_x else 0) + (hw_ref if ref_x else 0)
    
    # 4. Foreground Pixel Hamming
    fg_mask = (vector_x == 1) | (vector_y == 1)
    total_fg_pixels = int(np.sum(fg_mask))
    
    if total_fg_pixels == 0:
        fg_sim_ratio = 100.0
        hd_fg = 0
        hw_fg = 0
    else:
        err_fg = np.bitwise_xor(vector_x[fg_mask], vector_y[fg_mask])
        hd_fg = int(np.sum(err_fg))
        hw_fg = int(np.count_nonzero(err_fg))
        fg_sim_ratio = (1.0 - (hd_fg / total_fg_pixels)) * 100.0
        
    # Verifikasi Teorema Matematika: d(x,y) == wt(e)
    is_verified = (total_hd_ascii == total_hw_ascii) and (hd_fg == hw_fg)
    
    # Kondisi Kelulusan Forensik Multi-Field
    is_nominal_match = (hd_nom == 0 and str_nom_x == str_nom_y)
    is_date_match = (hd_date == 0) if date_x else True
    is_ref_match = (hd_ref == 0) if ref_x else True
    is_ela_clean = (ela_score <= ela_threshold)
    
    if is_nominal_match and is_date_match and is_ref_match and is_ela_clean:
        verdict = "VALID_ASLI"
        title_output = "🟢 BUKTI TRANSAKSI INI ASLI"
        description = (
            f"Dokumen terverifikasi 100% VALID & ASLI. Teks informasi penting "
            f"(Nominal = Rp {int(str_nom_x):,}) cocok sempurna (ASCII Hamming Distance = 0 bit) "
            f"dan gambar bebas dari artefak manipulasi digital (Skor ELA = {ela_score:.2f})."
        )
    else:
        verdict = "MANIPULASI_PALSU"
        title_output = "🔴 BUKTI TRANSAKSI INI PALSU"
        
        reasons = []
        if not is_nominal_match:
            reasons.append(f"Ketidakcocokan nominal biner ASCII (d_nom = {hd_nom} bit, Tagihan: Rp {int(str_nom_x):,} vs Resi: Rp {str_nom_y})")
        if date_x and not is_date_match:
            reasons.append(f"Ketidakcocokan tanggal transaksi (d_date = {hd_date} bit)")
        if ref_x and not is_ref_match:
            reasons.append(f"Ketidakcocokan No. Referensi (d_ref = {hd_ref} bit)")
        if not is_ela_clean:
            reasons.append(f"Terdeteksi artefak editan gambar digital (Skor ELA = {ela_score:.2f} > {ela_threshold})")
            
        description = "TERINDIKASI MANIPULASI / PALSU! Alasan: " + " & ".join(reasons) + "."

    return {
        'total_hd_ascii': total_hd_ascii,
        'total_hw_ascii': total_hw_ascii,
        'hd_nom': hd_nom,
        'hw_nom': hw_nom,
        'sim_nom': sim_nom,
        'hd_date': hd_date,
        'sim_date': sim_date,
        'hd_ref': hd_ref,
        'sim_ref': sim_ref,
        'total_fg_pixels': total_fg_pixels,
        'hd_fg': hd_fg,
        'hw_fg': hw_fg,
        'fg_sim_ratio': fg_sim_ratio,
        'ela_score': ela_score,
        'is_verified': is_verified,
        'verdict': verdict,
        'title_output': title_output,
        'description': description
    }