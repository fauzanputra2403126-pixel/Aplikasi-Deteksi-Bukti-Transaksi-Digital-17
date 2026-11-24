import numpy as np
from PIL import Image, ImageOps, ImageChops
import pytesseract, io, re

def extract_multi_fields_ocr(img_input):
    """
    Mengekstrak Teks Informasi Penting dari Resi menggunakan OCR:
    - Nominal Digits
    - Tanggal & Waktu Transaksi
    - Nomor Referensi / ID Transaksi
    """
    if isinstance(img_input, Image.Image):
        raw_img = img_input.convert('RGB')
    else:
        raw_img = Image.open(img_input).convert('RGB')
        
    gray = ImageOps.autocontrast(raw_img.convert('L'))
    
    try:
        ocr_text = pytesseract.image_to_string(gray, config='--psm 6')
    except Exception:
        try:
            ocr_text = pytesseract.image_to_string(raw_img)
        except Exception:
            ocr_text = ""
            
    # 1. Ekstraksi Nominal Digits
    digits = ''.join(re.findall(r'\d+', ocr_text))
    
    # 2. Ekstraksi Pola Tanggal (dd/mm/yyyy atau dd-mm-yyyy atau dd Month yyyy)
    date_matches = re.findall(r'\d{1,2}[\/\-\s]\d{1,2}[\/\-\s]\d{2,4}', ocr_text)
    extracted_date = date_matches[0] if date_matches else ""
    
    # 3. Ekstraksi No. Referensi Transaksi
    ref_matches = re.findall(r'[A-Za-z0-9]{8,20}', ocr_text)
    extracted_ref = ref_matches[0] if ref_matches else ""
    
    return raw_img, digits, extracted_date, extracted_ref, ocr_text

# Alias Kompatibilitas Fungsi OCR
extract_nominal_ocr = extract_multi_fields_ocr

def extract_roi_and_foreground(img_input, target_size=(280, 80)):
    """
    Ekstraksi ROI & Masker Piksel Teks (Foreground Only):
    Mengambil gambar, mengisolasi area teks nominal, binarisasi (1 = Teks, 0 = Latar),
    dan meratakannya menjadi Vektor Biner 1D.
    """
    if isinstance(img_input, Image.Image):
        raw_img = img_input.convert('L')
    else:
        raw_img = Image.open(img_input).convert('L')
        
    contrast_img = ImageOps.autocontrast(raw_img)
    np_img = np.array(contrast_img)
    mean_val = np.mean(np_img)
    threshold = int(mean_val * 0.85)
    
    binary_np = np.where(np_img < threshold, 0, 255).astype(np.uint8)
    binary_pil = Image.fromarray(binary_np)
    
    inverted = ImageOps.invert(binary_pil)
    bbox = inverted.getbbox()
    
    if bbox:
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        aspect_ratio = w / float(max(h, 1))
        cropped_text = binary_pil.crop(bbox)
    else:
        aspect_ratio = 1.0
        cropped_text = binary_pil
        
    canvas = Image.new('L', target_size, color=255)
    cw, ch = cropped_text.size
    tw, th = target_size
    
    scale = min((tw - 20) / max(cw, 1), (th - 20) / max(ch, 1), 1.0)
    new_w = max(int(cw * scale), 1)
    new_h = max(int(ch * scale), 1)
    
    resized_text = cropped_text.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    paste_x = (tw - new_w) // 2
    paste_y = (th - new_h) // 2
    canvas.paste(resized_text, (paste_x, paste_y))
    
    # Binarisasi: Bit 1 = Piksel Teks (Foreground), Bit 0 = Latar Belakang
    np_canvas = np.array(canvas)
    binary_matrix = np.where(np_canvas < 128, 1, 0).astype(np.uint8)
    binary_vector = binary_matrix.flatten()
    
    return canvas, binary_vector, aspect_ratio

# Alias Kompatibilitas Fungsi ROI
extract_roi_and_binarize = extract_roi_and_foreground

def convert_template_to_vector(template_pil_image, target_size=(280, 80)):
    """Mengonversi Gambar Acuan Backend (x) ke Vektor Biner 1D dan Rasio Aspek."""
    canvas, vec, aspect_ratio = extract_roi_and_foreground(template_pil_image, target_size=target_size)
    return vec, aspect_ratio

def compute_ela_score(img_input, quality=90):
    """Menghitung Skor Error Level Analysis (ELA) untuk deteksi editan foto."""
    if isinstance(img_input, Image.Image):
        img = img_input.convert('RGB')
    else:
        img = Image.open(img_input).convert('RGB')
        
    buffer = io.BytesIO()
    img.save(buffer, 'JPEG', quality=quality)
    buffer.seek(0)
    resaved = Image.open(buffer)
    
    diff = ImageChops.difference(img, resaved)
    np_diff = np.array(diff)
    return float(np.mean(np_diff))