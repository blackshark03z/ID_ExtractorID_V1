import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import argparse
import shutil
import unicodedata
from datetime import datetime
from config import FRONT_IMAGE_NAME, BACK_IMAGE_NAME, OCR_NOTE_NAME, EXCEL_OUTPUT_NAME
from excel_export import create_excel_report
from pdf_utils import extract_images_from_pdf
from gemini_utils import init_gemini, process_with_gemini

def normalize_folder_name(name):
    """
    Converts a Vietnamese name to uppercase ASCII without diacritics.
    E.g. 'Nguyễn Văn An' -> 'NGUYEN VAN AN'
    """
    if not name:
        return ""
    # Decompose unicode characters (NFD): tách ký tự + dấu thành 2 code points riêng
    nfkd = unicodedata.normalize('NFD', name)
    # Giữ lại chỉ các ký tự không phải combining (tức là bỏ dấu)
    ascii_str = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Viết hoa và bỏ khoảng trắng thừa
    return ' '.join(ascii_str.upper().split())


def is_expired(ngayhethan_str):
    """
    Checks if the CCCD is expired compared to the current date.
    Returns True if expired, False otherwise (or if unreadable).
    """
    if not ngayhethan_str or "KHONG THOI HAN" in ngayhethan_str.upper():
        return False
        
    try:
        expiry_date = datetime.strptime(ngayhethan_str, "%d/%m/%Y").date()
        today = datetime.today().date()
        return expiry_date < today
    except ValueError:
        return False

def generate_ocr_note(folder_path, parsed_data):
    """Generates the ocr_note.txt file in the folder."""
    note_path = os.path.join(folder_path, OCR_NOTE_NAME)
    
    content = [
        "===== GEMINI PARSED ====="
    ]
    
    fields = [
        "CCCD", "HoTen", "NgaySinh", "GioiTinh", "DiaChi", 
        "NoiCap", "NgayCap", "NgayHetHan", "GhiChu"
    ]
    
    for field in fields:
        val = parsed_data.get(field, "")
        content.append(f"{field}: {val}")
        
    try:
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(content))
    except Exception as e:
        print(f"  Error writing note to {note_path}: {e}")

def process_folder(folder_path, force_rescan=False):
    """
    Processes a single folder.
    Returns a dictionary of parsed data.
    """
    std_front = os.path.join(folder_path, FRONT_IMAGE_NAME)
    std_back = os.path.join(folder_path, BACK_IMAGE_NAME)
    note_path = os.path.join(folder_path, OCR_NOTE_NAME)
    
    # CHECKPOINT LOGIC: Đọc lại từ file note nếu đã quét
    if not force_rescan and os.path.exists(note_path):
        parsed_data = {"FolderName": os.path.basename(folder_path)}
        try:
            with open(note_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        parsed_data[k.strip()] = v.strip()
            
            # Check valid parsing (đầy đủ 4 trường bắt buộc: CCCD, HoTen, NgaySinh, DiaChi)
            has_min_fields = all(str(parsed_data.get(f) or "").strip() for f in ["CCCD", "HoTen", "NgaySinh", "DiaChi"])
            if has_min_fields:
                print("    -> [CHECKPOINT] Đã quét trước đó, tải dữ liệu từ cache.")
                # Giả lập status OK
                status = {"front": "OK", "back": "OK"}
                if "MISSING FRONT" in parsed_data.get("GhiChu", ""): status["front"] = "MISSING"
                if "MISSING BACK" in parsed_data.get("GhiChu", ""): status["back"] = "MISSING"
                return parsed_data, status
        except Exception:
            pass # Nếu lỗi đọc note thì chạy lại Gemini bình thường
            
    image_paths = []
    # Đưa ảnh front/back rời vào trước (để chiếm index 0 và 1)
    if os.path.exists(std_front): image_paths.append(std_front)
    if os.path.exists(std_back): image_paths.append(std_back)
    
    # Tìm các file ảnh khác có sẵn trong thư mục
    for f in os.listdir(folder_path):
        f_lower = f.lower()
        if f_lower.endswith(('.jpg', '.jpeg', '.png')):
            full_path = os.path.join(folder_path, f)
            if f != FRONT_IMAGE_NAME and f != BACK_IMAGE_NAME and not f_lower.endswith('_backup.jpg') and not f_lower.startswith('extracted_pdf_'):
                image_paths.append(full_path)
    
    # Tìm và trích xuất ảnh từ PDF
    pdfs = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.pdf')]
    pdf_images = []
    for pdf in pdfs:
        pdf_images.extend(extract_images_from_pdf(pdf, folder_path))
        
    image_paths.extend(pdf_images)
    
    if not image_paths:
        return {"GhiChu": "NO IMAGES OR PDF FOUND IN FOLDER"}, {"front": "MISSING", "back": "MISSING"}
        
    print(f"    -> Đang gộp {len(image_paths)} ảnh gửi lên Gemini trong 1 lượt duy nhất...")
    data = process_with_gemini(image_paths)
    
    if "error" in data:
        # Dọn dẹp ảnh rác nếu có lỗi
        for p in pdf_images:
            try: os.remove(p)
            except: pass
        
        # Ngừng toàn bộ chương trình nếu lỗi do API Key chết (tránh lặp lại lỗi cho hàng trăm thư mục)
        if "403" in data["error"] or "API Key" in data["error"]:
            print(f"\n[!!! LỖI NGHIÊM TRỌNG] {data['error']}")
            print("Vui lòng thay API Key mới vào file api_keys.txt rồi chạy lại tool.")
            import sys
            sys.exit(1)
            
        return {"GhiChu": f"GEMINI ERROR: {data['error']}"}, {"front": "ERROR", "back": "ERROR"}
        
    front_path_resolved = data.pop("front_path", None)
    back_path_resolved = data.pop("back_path", None)
    
    # Cần đổi tên/chuẩn hóa lại thành front.jpg và back.jpg nếu Gemini chọn ảnh từ PDF
    try:
        if front_path_resolved and os.path.abspath(front_path_resolved) != os.path.abspath(std_front):
            # Backup ảnh cũ nếu bị ghi đè
            if os.path.exists(std_front):
                shutil.move(std_front, os.path.join(folder_path, "front_backup.jpg"))
            shutil.copy2(front_path_resolved, std_front)
            
        if back_path_resolved and os.path.abspath(back_path_resolved) != os.path.abspath(std_back):
            if os.path.exists(std_back):
                shutil.move(std_back, os.path.join(folder_path, "back_backup.jpg"))
            shutil.copy2(back_path_resolved, std_back)
    except Exception as e:
        print(f"  Warning: Lỗi khi lưu đè ảnh chuẩn: {e}")
        
    # Xóa các ảnh rác đã extract từ PDF để dọn dẹp
    for p in pdf_images:
        try: os.remove(p)
        except: pass
            
    status = {"front": "OK" if front_path_resolved else "MISSING", "back": "OK" if back_path_resolved else "MISSING"}
    
    parsed_data = {
        "FolderName": os.path.basename(folder_path),
        "CCCD": data.get("CCCD", ""),
        "HoTen": data.get("HoTen", ""),
        "NgaySinh": data.get("NgaySinh", ""),
        "GioiTinh": data.get("GioiTinh", ""),
        "DiaChi": data.get("DiaChi", ""),
        "NoiCap": data.get("NoiCap", ""),
        "NgayCap": data.get("NgayCap", ""),
        "NgayHetHan": data.get("NgayHetHan", "")
    }
    
    notes = []
    if not front_path_resolved: notes.append("MISSING FRONT IMAGE")
    if not back_path_resolved: notes.append("MISSING BACK IMAGE")
    if not parsed_data.get("DiaChi"): notes.append("KHONG DOC RO DIA CHI")
    if not parsed_data.get("NgayHetHan"): notes.append("KHONG DOC RO NGAY HET HAN")
    if not parsed_data.get("NoiCap"): notes.append("KHONG DOC RO NOI CAP")
    if not parsed_data.get("NgayCap"): notes.append("KHONG DOC RO NGAY CAP")
        
    parsed_data["GhiChu"] = "; ".join(notes)
    
    # Chỉ lưu checkpoint khi trích xuất đủ 4 trường tối thiểu: CCCD, HoTen, NgaySinh, DiaChi
    has_min_fields = all(str(parsed_data.get(f) or "").strip() for f in ["CCCD", "HoTen", "NgaySinh", "DiaChi"])
    if has_min_fields:
        generate_ocr_note(folder_path, parsed_data)
    else:
        print("    -> [CẢNH BÁO] Thiếu trường bắt buộc (CCCD/HoTen/NgaySinh/DiaChi). Không lưu checkpoint.")
        # Xóa file note cũ nếu có để tránh lần sau lại đọc nhầm
        if os.path.exists(note_path):
            try:
                os.remove(note_path)
            except Exception as e:
                print(f"      Không thể xóa file note cũ không hợp lệ: {e}")
    
    return parsed_data, status

import zipfile

def find_person_folders(root_path):
    """
    Finds all subdirectories under root_path that contain at least one image or PDF file.
    Avoids folders containing system/backup patterns in their names.
    """
    person_folders = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        parts = os.path.normpath(dirpath).split(os.sep)
        
        # Skip system, git, result, or tool folders
        if any(p in ["cccd_ocr_tool", "result", ".git", ".gemini", "__pycache__"] for p in parts):
            continue
            
        # Skip any path containing backup, copy, temp (case-insensitive)
        if any("backup" in p.lower() or "copy" in p.lower() or "temp" in p.lower() for p in parts):
            continue
            
        # Check if the directory directly contains any media files
        has_media = False
        for f in filenames:
            f_lower = f.lower()
            if f_lower.endswith(('.jpg', '.jpeg', '.png', '.pdf')):
                if f_lower == OCR_NOTE_NAME.lower() or f_lower == EXCEL_OUTPUT_NAME.lower():
                    continue
                if f_lower.endswith('_backup.jpg') or f_lower.startswith('extracted_pdf_'):
                    continue
                has_media = True
                break
                
        if has_media:
            person_folders.append(dirpath)
            
    return person_folders

def find_data_root(extracted_path):
    """
    Finds the actual directory containing the person folders.
    If the extracted zip has a single root folder (e.g. Zip -> Tong -> [A, B, C]),
    it drills down to 'Tong'.
    """
    current_dir = extracted_path
    while True:
        items = os.listdir(current_dir)
        dirs = [d for d in items if os.path.isdir(os.path.join(current_dir, d))]
        # Nếu thư mục hiện tại chỉ có duy nhất 1 thư mục con và không có file nào khác (hoặc chỉ có file rác ẩn)
        files = [f for f in items if os.path.isfile(os.path.join(current_dir, f)) and not f.startswith('.')]
        if len(dirs) == 1 and len(files) == 0:
            current_dir = os.path.join(current_dir, dirs[0])
        else:
            return current_dir

def main():
    parser = argparse.ArgumentParser(description="Tool OCR CCCD Vietnam (Gemini API)")
    parser.add_argument("path", nargs="?", default=None, help="Đường dẫn đến thư mục hoặc file ZIP")
    args = parser.parse_args()
    
    input_dir = os.path.abspath("input")
    target_path = args.path
    
    print("=== TOOL OCR CCCD VIỆT NAM (GEMINI API) ===")
    
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        
    root_folder = None
    subfolders_to_process = []
    
    if target_path is None:
        menu_items = []
        for item in os.listdir(input_dir):
            item_path = os.path.join(input_dir, item)
            # Ẩn thư mục extract rác để menu gọn gàng
            if os.path.isdir(item_path) and not item.endswith('_extracted'):
                menu_items.append({"name": item, "path": item_path, "type": "dir"})
            elif item.lower().endswith('.zip'):
                menu_items.append({"name": item, "path": item_path, "type": "zip"})
                
        if not menu_items:
            print(f"\nThư mục '{input_dir}' hiện đang trống.")
            print("Vui lòng copy các thư mục dữ liệu hoặc file ZIP vào 'input' và chạy lại tool.")
            sys.exit(0)
            
        print(f"Đã tìm thấy thư mục 'input': {input_dir}")
        print("\nDanh sách thư mục / file ZIP cần quét:")
        print("[0] Quét TẤT CẢ các thư mục (bỏ qua file ZIP)")
        for i, item in enumerate(menu_items, 1):
            icon = "[DIR]" if item["type"] == "dir" else "[ZIP]"
            print(f"[{i}] {icon} {item['name']}")
            
        while True:
            choice = input(f"\nNhập số để chọn (0-{len(menu_items)}): ").strip()
            if choice.isdigit():
                choice_idx = int(choice)
                if 0 <= choice_idx <= len(menu_items):
                    break
            print("Lựa chọn không hợp lệ, vui lòng thử lại.")
            
        if choice_idx == 0:
            root_folder = input_dir
            subfolders_to_process = find_person_folders(input_dir)
        else:
            selected_item = menu_items[choice_idx - 1]
            if selected_item["type"] == "zip":
                target_path = selected_item["path"]
            else:
                root_folder = selected_item["path"]
                subfolders_to_process = find_person_folders(root_folder)
                
    # Xử lý nếu target_path là file ZIP (nhập qua arg hoặc chọn từ menu)
    if target_path and target_path.lower().endswith('.zip'):
        if not os.path.exists(target_path):
            print(f"Lỗi: Không tìm thấy file ZIP tại {target_path}")
            sys.exit(1)
            
        extract_dir = os.path.join(input_dir, os.path.splitext(os.path.basename(target_path))[0] + "_extracted")
        if not os.path.exists(extract_dir):
            print(f"Đang giải nén file ZIP ra {extract_dir}...")
            os.makedirs(extract_dir, exist_ok=True)
            try:
                with zipfile.ZipFile(target_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            except Exception as e:
                print(f"Lỗi khi giải nén ZIP: {e}")
                sys.exit(1)
        else:
            print(f"Thư mục giải nén đã tồn tại: {extract_dir}")
            
        root_folder = find_data_root(extract_dir)
        print(f"Đã xác định thư mục chứa dữ liệu: {root_folder}")
        subfolders_to_process = find_person_folders(root_folder)
                
    # Xử lý nếu target_path là thư mục truyền trực tiếp
    elif target_path and os.path.isdir(target_path):
        root_folder = os.path.abspath(target_path)
        subfolders_to_process = find_person_folders(root_folder)
                
    # Sắp xếp theo tên Alphabet để thứ tự quét không bị nhảy lộn xộn
    subfolders_to_process.sort()
                
    total_folders = len(subfolders_to_process)
    if total_folders == 0:
        print("Không tìm thấy thư mục con nào để xử lý.")
        sys.exit(0)
        
    # Phát hiện tiến trình cũ (Checkpoint)
    existing_notes = sum(1 for f in subfolders_to_process if os.path.exists(os.path.join(f, OCR_NOTE_NAME)))
    force_rescan = False
    if existing_notes > 0:
        print(f"\n[CHECKPOINT] Phát hiện {existing_notes}/{total_folders} thư mục đã được quét từ trước.")
        print("[1] Tiếp tục (Tải dữ liệu cũ từ file để tiết kiệm API - Khuyên dùng khi bị crash)")
        print("[2] Quét lại từ đầu (Gọi lại API toàn bộ, ghi đè dữ liệu cũ)")
        while True:
            c = input("Nhập lựa chọn (1-2) [mặc định 1]: ").strip()
            if c == "" or c == "1":
                force_rescan = False
                break
            elif c == "2":
                force_rescan = True
                break
            print("Lựa chọn không hợp lệ.")
            
    # Khởi tạo Gemini
    # Tìm file api_keys.txt ở thư mục gốc (D:\ID_Extractor-1) hoặc hiện tại
    key_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api_keys.txt")
    if not os.path.exists(key_file):
        key_file = "api_keys.txt"
        
    init_gemini(key_file)
        
    print(f"\nSẽ xử lý {total_folders} thư mục...")
    
    exported_data = []
    expired_count = 0
    missing_count = 0
    
    for i, folder_path in enumerate(subfolders_to_process, 1):
        folder_name = os.path.basename(folder_path)
        print(f"[{i}/{total_folders}] {folder_name}")
        
        parsed_data, status = process_folder(folder_path, force_rescan=force_rescan)
        
        # Kiểm tra điều kiện tối thiểu 4 trường: CCCD, HoTen, NgaySinh, DiaChi
        has_min_fields = all(str(parsed_data.get(f) or "").strip() for f in ["CCCD", "HoTen", "NgaySinh", "DiaChi"])
        if not has_min_fields:
            missing_fields = [f for f in ["CCCD", "HoTen", "NgaySinh", "DiaChi"] if not str(parsed_data.get(f) or "").strip()]
            print(f"  [BỎ QUA] Thư mục '{folder_name}' không trích xuất đủ 4 trường bắt buộc (thiếu: {', '.join(missing_fields)}). Không ghi ra Excel.")
            continue
            
        # --- TỰ ĐỘNG ĐỔI TÊN THƯ MỤC THEO HỌ TÊN TRÊN CCCD ---
        ho_ten = parsed_data.get("HoTen", "")
        expected_name = normalize_folder_name(ho_ten)
        current_name = normalize_folder_name(folder_name)
        
        if expected_name and expected_name != current_name:
            new_folder_path = os.path.join(os.path.dirname(folder_path), expected_name)
            try:
                # Nếu tên đích đã tồn tại, thêm hậu tố để tránh xung đột
                if os.path.exists(new_folder_path) and os.path.abspath(new_folder_path) != os.path.abspath(folder_path):
                    suffix = 1
                    while os.path.exists(f"{new_folder_path}_{suffix}"):
                        suffix += 1
                    new_folder_path = f"{new_folder_path}_{suffix}"
                os.rename(folder_path, new_folder_path)
                print(f"  [RENAME] '{folder_name}' -> '{os.path.basename(new_folder_path)}'")
                folder_path = new_folder_path
                parsed_data["FolderName"] = os.path.basename(new_folder_path)
            except Exception as e:
                print(f"  [RENAME] Lỗi khi đổi tên thư mục: {e}")
        # --------------------------------------------------------

        # Check expired
        ngay_het_han = parsed_data.get("NgayHetHan", "")
        if is_expired(ngay_het_han):
            print(f"  EXPIRED_SKIPPED: {ngay_het_han}. Đang tự động xóa thư mục...")
            try:
                shutil.rmtree(folder_path)
                print("    -> Đã xóa thư mục thành công.")
            except Exception as e:
                print(f"    -> Lỗi khi xóa thư mục: {e}")
            expired_count += 1
            continue
            
        print(f"  Image front: {status['front']}")
        print(f"  Image back : {status['back']}")
        
        if status["front"] != "OK" or status["back"] != "OK":
            missing_count += 1
            
        ghi_chu = parsed_data.get("GhiChu", "OK")
        print(f"  Parsed   : {ghi_chu}")
        
        exported_data.append(parsed_data)
        
    # Export
    output_excel = os.path.join(root_folder, EXCEL_OUTPUT_NAME)
    while True:
        try:
            create_excel_report(exported_data, output_excel)
            excel_status = output_excel
            break
        except PermissionError:
            print(f"\n[CẢNH BÁO] Không thể lưu file Excel: {output_excel}")
            print("Nguyên nhân: File đang được mở bằng phần mềm khác (như Microsoft Excel).")
            input("Hành động: Vui lòng ĐÓNG file đó lại, sau đó nhấn ENTER tại đây để lưu lại...")
        except Exception as e:
            excel_status = f"FAILED: {e}"
            break
        
    print("\nDone.")
    print(f"Total folders: {total_folders}")
    print(f"Exported rows: {len(exported_data)}")
    print(f"Expired skipped: {expired_count}")
    print(f"Missing front/back: {missing_count}")
    print(f"Excel: {excel_status}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Đã dừng chương trình bởi người dùng (Ctrl+C).")
        sys.exit(0)
