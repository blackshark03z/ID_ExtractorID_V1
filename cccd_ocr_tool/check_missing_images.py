"""
Script kiểm tra các folder bị thiếu ảnh sau khi extract từ PDF.

Vấn de da duoc fix trong pdf_utils.py:
  - Truoc day: nhieu PDF trong cung 1 folder co the ghi de anh cua nhau
    vi dung cung ten 'extracted_pdf_{page}_{img}' -> mat anh.
  - Sau fix: ten file anh bao gom slug cua ten PDF nen khong con xung dot.

Script nay giup xac dinh:
  - Folder nao bi anh huong boi bug cu (co PDF, thieu front/back)
    -> Se duoc xu ly dung khi chay lai main.py
  - Folder nao that su thieu anh (khong co PDF de bu)
    -> Can bo sung anh thu cong

Cach dung:
    python cccd_ocr_tool/check_missing_images.py
    python cccd_ocr_tool/check_missing_images.py "input/500 p1_extracted/500 p1"
"""
import os
import sys
import fitz  # PyMuPDF

FRONT_IMAGE_NAME = "front.jpg"
BACK_IMAGE_NAME = "back.jpg"
OCR_NOTE_NAME = "ocr_note.txt"
MIN_IMAGE_BYTES = 5000  # Ngưỡng lọc ảnh thumbnail nhỏ (giống pdf_utils.py)


def count_extractable_images_from_pdf(pdf_path):
    """Đếm số ảnh hợp lệ (> MIN_IMAGE_BYTES) có thể extract từ PDF."""
    count = 0
    try:
        doc = fitz.open(pdf_path)
        for page_index in range(len(doc)):
            page = doc[page_index]
            for img in page.get_images():
                xref = img[0]
                base_image = doc.extract_image(xref)
                if len(base_image["image"]) > MIN_IMAGE_BYTES:
                    count += 1
        doc.close()
    except Exception as e:
        print(f"  [LỖI ĐỌC PDF] {pdf_path}: {e}")
    return count


def analyze_folder(folder_path):
    """
    Phân tích một folder và trả về dict mô tả tình trạng.
    """
    files = os.listdir(folder_path)
    files_lower = [f.lower() for f in files]

    has_front = FRONT_IMAGE_NAME in files
    has_back = BACK_IMAGE_NAME in files
    has_ocr_note = OCR_NOTE_NAME in files

    # Tìm các PDF trong folder
    pdfs = [os.path.join(folder_path, f) for f in files if f.lower().endswith('.pdf')]

    # Tìm ảnh rời (không phải front/back)
    loose_images = [f for f in files
                    if f.lower().endswith(('.jpg', '.jpeg', '.png'))
                    and f != FRONT_IMAGE_NAME and f != BACK_IMAGE_NAME]

    # Đếm tổng ảnh extractable từ tất cả PDF
    total_pdf_images = 0
    pdf_details = []
    for pdf in pdfs:
        n = count_extractable_images_from_pdf(pdf)
        total_pdf_images += n
        pdf_details.append((os.path.basename(pdf), n))

    # Tổng ảnh sẵn có (không tính front/back đã chuẩn hóa)
    available_images = (1 if has_front else 0) + (1 if has_back else 0) + len(loose_images) + total_pdf_images

    return {
        "folder": os.path.basename(folder_path),
        "path": folder_path,
        "has_front": has_front,
        "has_back": has_back,
        "has_ocr_note": has_ocr_note,
        "pdfs": pdf_details,
        "loose_images": loose_images,
        "total_pdf_images": total_pdf_images,
        "total_available": available_images,
    }


def find_data_root(base_path):
    """Drill down nếu chỉ có 1 subfolder (giống logic main.py)."""
    current = base_path
    while True:
        items = os.listdir(current)
        dirs = [d for d in items if os.path.isdir(os.path.join(current, d))]
        files = [f for f in items if os.path.isfile(os.path.join(current, f)) and not f.startswith('.')]
        if len(dirs) == 1 and len(files) == 0:
            current = os.path.join(current, dirs[0])
        else:
            return current


def main():
    # Fix encoding cho Windows console
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    # Xác định thư mục gốc
    if len(sys.argv) > 1:
        root = os.path.abspath(sys.argv[1])
    else:
        # Mặc định: dùng thư mục input và auto-detect
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        input_dir = os.path.join(project_root, "input")

        # Tìm thư mục _extracted
        extracted_dirs = [
            os.path.join(input_dir, d)
            for d in os.listdir(input_dir)
            if os.path.isdir(os.path.join(input_dir, d)) and d.endswith('_extracted')
        ]

        if extracted_dirs:
            root = find_data_root(extracted_dirs[0])
            print(f"[AUTO] Sử dụng thư mục: {root}")
        else:
            # Thử dùng thư mục input trực tiếp
            root = find_data_root(input_dir)
            print(f"[AUTO] Sử dụng thư mục: {root}")

    if not os.path.isdir(root):
        print(f"[LỖI] Không tìm thấy thư mục: {root}")
        sys.exit(1)

    # Lấy danh sách tất cả subfolder
    subfolders = sorted([
        os.path.join(root, d)
        for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d))
        and d not in ["cccd_ocr_tool", "result", ".git", ".gemini"]
    ])

    total = len(subfolders)
    print(f"\n{'='*60}")
    print(f"  KIỂM TRA FOLDER BỊ THIẾU ẢNH")
    print(f"{'='*60}")
    print(f"Tổng số folder: {total}\n")

    # Phân loại kết quả
    ok_folders = []                 # OK: có đủ front + back
    missing_has_pdf = []            # Thiếu front/back NHƯNG có PDF -> bug cũ, sẽ tự sửa khi chạy lại
    missing_no_pdf = []             # Thiếu front/back, KHÔNG có PDF -> cần can thiệp thủ công
    no_images_at_all = []           # Hoàn toàn trống

    for i, folder_path in enumerate(subfolders, 1):
        folder_name = os.path.basename(folder_path)
        print(f"\r[{i}/{total}] Dang kiem tra: {folder_name:<40}", end="", flush=True)

        info = analyze_folder(folder_path)

        has_any_image_source = info["has_front"] or info["has_back"] or info["loose_images"] or info["total_pdf_images"] > 0

        if not has_any_image_source:
            no_images_at_all.append(info)
        elif info["has_front"] and info["has_back"]:
            ok_folders.append(info)
        elif info["pdfs"]:
            # Thiếu front hoặc back nhưng có PDF -> có thể do bug tên file cũ
            # Sau khi fix pdf_utils.py, chạy lại sẽ extract đủ ảnh
            missing_has_pdf.append(info)
        else:
            # Thiếu front hoặc back, không có PDF -> cần bổ sung thủ công
            missing_no_pdf.append(info)

    print()  # Xuống dòng sau progress

    # ========== BÁO CÁO ==========
    print(f"\n{'='*60}")
    print(f"  KET QUA KIEM TRA")
    print(f"{'='*60}")
    print(f"OK  Folder du front + back                 : {len(ok_folders)}")
    print(f"PDF Thieu front/back nhung co PDF (tu sua) : {len(missing_has_pdf)}")
    print(f"ERR Thieu front/back, khong co PDF         : {len(missing_no_pdf)}")
    print(f"NIL Khong co anh lan PDF                   : {len(no_images_at_all)}")

    # Chi tiết folder thiếu ảnh nhưng có PDF (sẽ được tự sửa)
    if missing_has_pdf:
        print(f"\n{'='*60}")
        print(f"  [PDF] FOLDER THIEU ANH NHUNG CO PDF")
        print(f"  -> Nhung folder nay se duoc xu ly dung khi chay lai main.py")
        print(f"     (da fix bug ten file trong pdf_utils.py)")
        print(f"{'='*60}")
        for info in missing_has_pdf:
            missing = []
            if not info["has_front"]: missing.append("front.jpg")
            if not info["has_back"]: missing.append("back.jpg")
            print(f"\n  Folder: {info['folder']}  (thieu: {', '.join(missing)})")
            if info["loose_images"]:
                print(f"    anh roi   : {info['loose_images']}")
            for pdf_name, pdf_img_count in info["pdfs"]:
                print(f"    PDF '{pdf_name}': {pdf_img_count} anh co the extract")
            print(f"    Tong anh san co: {info['total_available']}")

    if missing_no_pdf:
        print(f"\n{'='*60}")
        print(f"  [ERR] FOLDER THIEU ANH, KHONG CO PDF (can bo sung thu cong)")
        print(f"{'='*60}")
        for info in missing_no_pdf:
            missing = []
            if not info["has_front"]: missing.append("front.jpg")
            if not info["has_back"]: missing.append("back.jpg")
            print(f"  Folder: {info['folder']}  ->  thieu: {', '.join(missing)}")

    if no_images_at_all:
        print(f"\n{'='*60}")
        print(f"  [NIL] FOLDER HOAN TOAN TRONG")
        print(f"{'='*60}")
        for info in no_images_at_all:
            print(f"  Folder: {info['folder']}")

    # Tóm tắt cuối
    problem_count = len(missing_has_pdf) + len(missing_no_pdf) + len(no_images_at_all)
    print(f"\n{'='*60}")
    print(f"  TONG KET: {problem_count}/{total} folder co van de")
    if missing_has_pdf:
        print(f"  -> {len(missing_has_pdf)} folder se duoc tu xu ly khi chay lai main.py (da fix pdf_utils.py)")
    if missing_no_pdf:
        print(f"  -> {len(missing_no_pdf)} folder can bo sung anh thu cong")
    print(f"{'='*60}\n")

    # Ghi ra file log
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    log_path = os.path.join(project_root, "missing_images_report.txt")
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("KIEM TRA FOLDER BI THIEU ANH\n")
            f.write(f"Thu muc goc: {root}\n")
            f.write(f"Tong folder: {total}\n\n")
            f.write(f"OK (du front + back): {len(ok_folders)}\n")
            f.write(f"Thieu anh nhung co PDF (se tu sua): {len(missing_has_pdf)}\n")
            f.write(f"Thieu anh, khong co PDF (can thu cong): {len(missing_no_pdf)}\n")
            f.write(f"Hoan toan trong: {len(no_images_at_all)}\n\n")

            if missing_has_pdf:
                f.write("=== FOLDER THIEU ANH NHUNG CO PDF (TU SUA KHI CHAY LAI) ===\n")
                for info in missing_has_pdf:
                    f.write(f"\n{info['folder']}\n")
                    f.write(f"  has_front: {info['has_front']}, has_back: {info['has_back']}\n")
                    if info["loose_images"]:
                        f.write(f"  anh roi: {info['loose_images']}\n")
                    for pdf_name, n in info["pdfs"]:
                        f.write(f"  PDF '{pdf_name}': {n} anh\n")
                    f.write(f"  Tong anh san co: {info['total_available']}\n")

            if missing_no_pdf:
                f.write("\n=== FOLDER THIEU ANH, KHONG CO PDF (CAN THU CONG) ===\n")
                for info in missing_no_pdf:
                    missing = []
                    if not info["has_front"]: missing.append("front.jpg")
                    if not info["has_back"]: missing.append("back.jpg")
                    f.write(f"  {info['folder']}  ->  thieu: {', '.join(missing)}\n")

            if no_images_at_all:
                f.write("\n=== FOLDER HOAN TOAN TRONG ===\n")
                for info in no_images_at_all:
                    f.write(f"  {info['folder']}\n")

        print(f"Da ghi bao cao ra: {log_path}\n")
    except Exception as e:
        print(f"Khong the ghi file log: {e}\n")


if __name__ == "__main__":
    main()
