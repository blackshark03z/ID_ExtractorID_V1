import sys
import os
import re
import cv2
import pytesseract
import unicodedata
import numpy as np


def remove_accents(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')


def ocr_image_unicode(image_path: str):
    data = np.fromfile(image_path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError(f"Cannot read image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
    text_vie = pytesseract.image_to_string(gray, lang='vie+eng', config='--psm 6')
    return text_vie


def parse_front_fields(raw_text: str):
    # Normalize for regex matching but keep original for fallback
    text_norm = remove_accents(raw_text).upper()

    # CCCD: 12 digits somewhere
    cccd_match = re.search(r"\b(\d{12})\b", text_norm)
    cccd = cccd_match.group(1) if cccd_match else None

    # Ngay sinh: dd/mm/yyyy
    dob_match = re.search(r"\b(\d{2}[\-/](\d{2})[\-/](\d{4}))\b", text_norm)
    ngay_sinh = dob_match.group(1).replace('-', '/') if dob_match else None

    # Gioi tinh: NAM or NU
    gioi_tinh = None
    if re.search(r"\bNAM\b", text_norm):
        gioi_tinh = "NAM"
    elif re.search(r"\bNU\b|\bN U\b", text_norm):
        gioi_tinh = "NU"

    # Ho ten: Attempt to locate after labels like HO VA TEN / FULL NAME
    ho_ten = None
    name_labels = ["HO VA TEN", "FULL NAME"]
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    norm_lines = [remove_accents(ln).upper() for ln in lines]
    for i, nl in enumerate(norm_lines):
        if any(lbl in nl for lbl in name_labels):
            # Name could be on same line after ':' or next line
            original = lines[i]
            name = None
            if ':' in original:
                name = original.split(':', 1)[1].strip()
            if not name and i + 1 < len(lines):
                name = lines[i + 1].strip()
            if name:
                ho_ten = remove_accents(name).upper()
                break

    result = {
        'CCCD': cccd,
        'HoTen': ho_ten,
        'NgaySinh': ngay_sinh,
        'GioiTinh': gioi_tinh,
    }
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools_extract_front.py <image_path>")
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"NOT_FOUND: {path}")
        sys.exit(3)
    text = ocr_image_unicode(path)
    info = parse_front_fields(text)
    print("FRONT_INFO|" + "|".join([
        (info.get('HoTen') or ''),
        (info.get('CCCD') or ''),
        (info.get('GioiTinh') or ''),
        (info.get('NgaySinh') or ''),
    ]))


if __name__ == '__main__':
    main()

