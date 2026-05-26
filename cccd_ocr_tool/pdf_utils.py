import fitz # PyMuPDF
import os
import re

def _pdf_slug(pdf_path):
    """
    Tạo chuỗi slug ngắn từ tên file PDF để dùng trong tên file ảnh.
    Ví dụ: 'cc huy.pdf' -> 'cc_huy'
    Giới hạn 20 ký tự để không làm tên file quá dài.
    """
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    # Thay các ký tự không phải chữ/số thành _
    slug = re.sub(r'[^\w]', '_', basename, flags=re.UNICODE)
    # Rút gọn _ liên tiếp, bỏ đầu/cuối
    slug = re.sub(r'_+', '_', slug).strip('_')
    return slug[:20]  # Giới hạn 20 ký tự

def extract_images_from_pdf(pdf_path, output_dir):
    """
    Extracts all images from a PDF file and saves them to output_dir.
    Returns a list of saved image paths.

    Tên file ảnh bao gồm slug từ tên PDF để tránh xung đột khi có
    nhiều file PDF trong cùng một thư mục (ví dụ: cc huy.pdf + honh huy.pdf
    đều có page 0, img 0 → tên khác nhau tránh ghi đè).
    """
    saved_paths = []
    pdf_slug = _pdf_slug(pdf_path)
    try:
        doc = fitz.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc[page_index]
            image_list = page.get_images()
            for img_index, img in enumerate(image_list):
                xref = img[0]
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Check if it's a valid image and not too small (ignore tiny icons/lines)
                if len(image_bytes) > 5000:
                    # Đặt tên bao gồm slug PDF để tránh xung đột giữa các PDF khác nhau
                    img_name = f"extracted_pdf_{pdf_slug}_{page_index}_{img_index}.{image_ext}"
                    img_path = os.path.join(output_dir, img_name)
                    with open(img_path, "wb") as f:
                        f.write(image_bytes)
                    saved_paths.append(img_path)
    except Exception as e:
        print(f"  Loi khi giai nen PDF {pdf_path}: {e}")
        
    return saved_paths
