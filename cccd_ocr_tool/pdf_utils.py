import fitz # PyMuPDF
import os
import re

def _pdf_slug(pdf_path):
    """
    Tạo chuỗi slug từ tên file PDF để dùng trong tên file ảnh.
    Ví dụ: 'cc huy.pdf' -> 'cc_huy'
    """
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    # Thay các ký tự không phải chữ/số thành _
    slug = re.sub(r'[^\w]', '_', basename, flags=re.UNICODE)
    # Rút gọn _ liên tiếp, bỏ đầu/cuối
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug  # Không giới hạn ký tự để tránh trùng lặp tên file khi nhiều PDF chung tiền tố

def extract_images_from_pdf(pdf_path, output_dir):
    """
    Renders all pages from a PDF file to images and saves them to output_dir.
    Returns a list of saved image paths.
    """
    saved_paths = []
    pdf_slug = _pdf_slug(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc[page_index]
            # Render trang PDF thành ảnh với độ phân giải cao (zoom = 2.0 ~ 144 DPI)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            img_name = f"extracted_pdf_{pdf_slug}_page_{page_index}.png"
            img_path = os.path.join(output_dir, img_name)
            pix.save(img_path)
            saved_paths.append(img_path)
    except Exception as e:
        print(f"  Loi khi giai nen PDF {pdf_path}: {e}")
        
    return saved_paths
