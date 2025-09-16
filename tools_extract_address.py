import sys
import os
import cv2
import numpy as np
import pytesseract
import unicodedata


def remove_accents(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize('NFD', text)
    return ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')


def ocr_image(image_path: str) -> str:
    # Hỗ trợ đường dẫn Unicode trên Windows: đọc bằng np.fromfile + imdecode
    try:
        data = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        img = None
    if img is None:
        raise RuntimeError(f"Cannot read image: {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # nhẹ nhàng tăng tương phản và giảm nhiễu
    gray = cv2.bilateralFilter(gray, d=5, sigmaColor=50, sigmaSpace=50)
    # OCR toàn ảnh
    try:
        text = pytesseract.image_to_string(gray, lang='vie+eng', config='--psm 6')
    except Exception:
        text = pytesseract.image_to_string(gray, lang='eng', config='--psm 6')
    return text


def extract_residence_address(raw_text: str):
    # Chuẩn hóa để dò nhãn, nhưng vẫn trả về bản gốc tốt nhất
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    norm_lines = [remove_accents(ln).upper() for ln in lines]

    positive_markers = [
        'NOI THUONG TRU', 'DIA CHI', 'PLACE OF RESIDENCE', 'PERMANENT ADDRESS', 'ADDRESS'
    ]
    negative_markers = [
        'QUE QUAN', 'NOI SINH', 'PLACE OF BIRTH', 'NATIVE PLACE', 'DOMICILE'
    ]

    # Tìm dòng chứa nhãn tích cực
    for idx, norm in enumerate(norm_lines):
        if any(m in norm for m in positive_markers):
            # Loại nếu dòng này thực ra là nhãn tiêu cực
            if any(m in norm for m in negative_markers):
                continue
            # Cắt phần sau dấu ':' nếu có
            original = lines[idx]
            after = original
            if ':' in original:
                after = original.split(':', 1)[1].strip()
            # Nếu dòng nhãn chỉ là tiêu đề, thử lấy dòng kế tiếp
            if len(after) < 5 and idx + 1 < len(lines):
                cand = lines[idx + 1].strip()
                cand_norm = norm_lines[idx + 1]
                # tránh rơi vào nhãn khác
                if not any(m in cand_norm for m in negative_markers):
                    after = cand
            # Chuẩn hóa viết hoa không dấu để phù hợp yêu cầu
            return remove_accents(after).upper()

    # Nếu không tìm thấy nhãn tích cực, nhưng có nhãn tiêu cực → trả None (front thường không có)
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools_extract_address.py <image_path>")
        sys.exit(2)
    path = sys.argv[1]
    if not os.path.exists(path):
        print(f"NOT_FOUND: {path}")
        sys.exit(3)
    text = ocr_image(path)
    addr = extract_residence_address(text)
    if addr:
        print(f"ADDRESS_OK|{addr}")
    else:
        print("ADDRESS_NOT_FOUND_ON_IMAGE")


if __name__ == '__main__':
    main()

