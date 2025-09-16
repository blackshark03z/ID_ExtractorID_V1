import zipfile
import os
import pandas as pd
import re
import glob
import base64
import requests
import json
import time
from PIL import Image
import fitz  # PyMuPDF
from datetime import datetime, timedelta
import shutil

# ---- Cấu hình Gemini API ----
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# ---- Hàm đọc API keys từ file ----
def load_api_keys():
    """Đọc danh sách API keys từ file api_keys.txt"""
    api_keys = []
    try:
        with open("api_keys.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Bỏ qua comment và dòng trống
                if line and not line.startswith("#") and not line.startswith("//"):
                    api_keys.append(line)
    except FileNotFoundError:
        print("❌ Không tìm thấy file api_keys.txt")
        print("📝 Vui lòng tạo file api_keys.txt với danh sách API keys")
        return []
    
    if not api_keys:
        print("❌ Không có API key nào trong file api_keys.txt")
        return []
    
    print(f"✅ Đã tải {len(api_keys)} API keys")
    return api_keys

# ---- Biến global cho API keys ----
api_keys_list = load_api_keys()
current_key_index = 0
exhausted_keys = set()  # Theo dõi các key đã hết quota

# ---- Cấu hình đường dẫn ----
# Người dùng sẽ nhập file zip đầu vào
zip_path = None
extract_dir = None

# ---- Cấu hình test mode ----
TEST_MODE = False  # Tắt test mode để xử lý tất cả folders
MAX_FOLDERS = 5 if TEST_MODE else 999

# ---- Hàm encode ảnh sang base64 ----
def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Lỗi encode ảnh {image_path}: {e}")
        return None

# ---- Hàm trích xuất ảnh từ PDF ----
def extract_images_from_pdf(pdf_path):
    try:
        # Mở file PDF
        pdf_document = fitz.open(pdf_path)
        images = []
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Lấy danh sách ảnh trong trang
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                # Lấy ảnh từ PDF
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                
                # Lưu ảnh tạm thời
                temp_image_path = f"temp_image_{page_num}_{img_index}.jpg"
                with open(temp_image_path, "wb") as image_file:
                    image_file.write(image_bytes)
                
                images.append(temp_image_path)
        
        pdf_document.close()
        return images
    except Exception as e:
        print(f"Lỗi trích xuất ảnh từ PDF {pdf_path}: {e}")
        return []

# ---- Hàm thay đổi API key ----
def switch_to_next_api_key():
    """Chuyển sang API key tiếp theo"""
    global current_key_index, exhausted_keys
    
    # Đánh dấu key hiện tại đã hết quota
    exhausted_keys.add(current_key_index)
    
    # Tìm key tiếp theo chưa hết quota
    original_index = current_key_index
    for _ in range(len(api_keys_list)):
        current_key_index = (current_key_index + 1) % len(api_keys_list)
        if current_key_index not in exhausted_keys:
            print(f"🔄 Chuyển sang API key {current_key_index + 1}/{len(api_keys_list)}")
            return True
    
    # Nếu tất cả keys đã hết quota
    print(f"❌ Tất cả {len(api_keys_list)} API keys đã hết quota!")
    return False

def reset_exhausted_keys():
    """Reset danh sách keys đã hết quota (có thể do reset quota hàng ngày)"""
    global exhausted_keys
    exhausted_keys.clear()
    print("🔄 Reset danh sách keys đã hết quota")

def get_available_keys_count():
    """Lấy số lượng keys còn khả dụng"""
    return len(api_keys_list) - len(exhausted_keys)

def show_api_keys_status():
    """Hiển thị trạng thái API keys"""
    total_keys = len(api_keys_list)
    available_keys = get_available_keys_count()
    exhausted_count = len(exhausted_keys)
    
    print(f"\n🔑 Trạng thái API Keys:")
    print(f"   📊 Tổng số: {total_keys}")
    print(f"   ✅ Khả dụng: {available_keys}")
    print(f"   ❌ Hết quota: {exhausted_count}")
    
    if available_keys == 0:
        print(f"   ⚠️  TẤT CẢ KEYS ĐÃ HẾT QUOTA!")
    elif available_keys <= total_keys * 0.2:  # Còn ít hơn 20%
        print(f"   ⚠️  Còn ít keys khả dụng ({available_keys}/{total_keys})")
    else:
        print(f"   ✅ Đủ keys để tiếp tục")

def handle_all_keys_exhausted():
    """Xử lý khi tất cả API keys hết quota"""
    print("\n" + "="*60)
    print("🚨 TẤT CẢ API KEYS ĐÃ HẾT QUOTA!")
    print("="*60)
    print("\n📋 Các tùy chọn xử lý:")
    print("1. 🔄 Chờ reset quota (thường vào 00:00 UTC)")
    print("2. ➕ Thêm API keys mới vào file api_keys.txt")
    print("3. 💾 Lưu tiến độ hiện tại và thoát")
    print("4. ⏸️  Tạm dừng và thử lại sau")
    
    while True:
        choice = input("\n🎯 Chọn tùy chọn (1-4): ").strip()
        
        if choice == "1":
            print("⏰ Chờ reset quota...")
            print("💡 Thời gian reset thường là 00:00 UTC (07:00 VN)")
            wait_time = input("⏱️  Nhập số phút chờ (Enter để chờ 60 phút): ").strip()
            try:
                wait_minutes = int(wait_time) if wait_time else 60
                print(f"⏳ Chờ {wait_minutes} phút...")
                time.sleep(wait_minutes * 60)
                reset_exhausted_keys()
                return "retry"
            except ValueError:
                print("❌ Số phút không hợp lệ")
        
        elif choice == "2":
            print("📝 Vui lòng thêm API keys mới vào file api_keys.txt")
            print("💡 Sau khi thêm, nhấn Enter để tiếp tục...")
            input()
            # Reload API keys
            global api_keys_list
            api_keys_list = load_api_keys()
            reset_exhausted_keys()
            return "retry"
        
        elif choice == "3":
            print("💾 Lưu tiến độ và thoát...")
            return "save_and_exit"
        
        elif choice == "4":
            print("⏸️  Tạm dừng xử lý...")
            return "pause"
        
        else:
            print("❌ Lựa chọn không hợp lệ, vui lòng chọn 1-4")

# ---- Hàm lấy API key hiện tại ----
def get_current_api_key():
    """Lấy API key hiện tại"""
    if not api_keys_list:
        return None
    
    # Kiểm tra xem key hiện tại có bị hết quota không
    if current_key_index in exhausted_keys:
        # Tìm key khả dụng tiếp theo
        for i in range(len(api_keys_list)):
            if i not in exhausted_keys:
                global current_key_index
                current_key_index = i
                break
        else:
            # Không có key nào khả dụng
            return None
    
    return api_keys_list[current_key_index]

# ---- Hàm gọi Gemini API ----
def extract_info_with_gemini(image_paths):
    try:
        # Chuẩn bị prompt cho Gemini
        prompt = """
        Hãy trích xuất thông tin từ ảnh CCCD (Căn cước công dân) và trả về dưới dạng JSON với các trường sau:
        {
            "CCCD": "Số căn cước công dân (12 chữ số)",
            "HoTen": "Họ và tên đầy đủ",
            "NgaySinh": "Ngày sinh (định dạng dd/mm/yyyy)",
            "GioiTinh": "Giới tính (NAM hoặc NỮ)",
            "DiaChi": "Địa chỉ thường trú",
            "NoiCap": "Nơi cấp CCCD",
            "NgayCap": "Ngày cấp (định dạng dd/mm/yyyy)"
        }
        
        Lưu ý QUAN TRỌNG:
        - Số CCCD phải có đúng 12 chữ số, không thiếu không thừa
        - Nếu số CCCD bị mờ/nhỏ, hãy cố gắng đọc kỹ từng chữ số
        - Số CCCD thường nằm ở góc trên bên phải hoặc giữa mặt trước
        - Nếu không đọc được số CCCD, để trống hoặc null
        - Chỉ trả về JSON, không có text khác
        - Đảm bảo định dạng JSON hợp lệ
        - Ưu tiên độ chính xác hơn là tốc độ
        """
        
        # Chuẩn bị nội dung cho API
        parts = [{"text": prompt}]
        
        # Thêm ảnh vào parts
        for img_path in image_paths:
            base64_image = encode_image_to_base64(img_path)
            if base64_image:
                parts.append({
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64_image
                    }
                })
        
        # Gọi API
        headers = {
            "Content-Type": "application/json"
        }
        
        data = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "topK": 1,
                "topP": 1,
                "maxOutputTokens": 2048
            }
        }
        
        # Thêm retry logic cho lỗi quota với thay đổi API key
        max_retries_per_key = 2
        
        while True:
            current_key = get_current_api_key()
            if not current_key:
                print("  ❌ Không có API key nào khả dụng")
                print(f"  📊 Trạng thái: {len(exhausted_keys)}/{len(api_keys_list)} keys đã hết quota")
                
                # Xử lý khi tất cả keys hết quota
                action = handle_all_keys_exhausted()
                if action == "retry":
                    continue  # Thử lại với keys mới
                elif action == "save_and_exit":
                    return {"error": "all_keys_exhausted", "action": "save_and_exit"}
                elif action == "pause":
                    return {"error": "all_keys_exhausted", "action": "pause"}
                else:
                    return {}
            
            url = f"{GEMINI_API_URL}?key={current_key}"
            
            for attempt in range(max_retries_per_key):
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                    
                    if response.status_code == 200:
                        return process_response(response)
                    elif response.status_code == 429:
                        print(f"  ⚠️  API key {current_key_index + 1} hết quota")
                        if not switch_to_next_api_key():
                            # Tất cả keys đã hết quota
                            action = handle_all_keys_exhausted()
                            if action == "retry":
                                break  # Thử lại với keys mới
                            elif action == "save_and_exit":
                                return {"error": "all_keys_exhausted", "action": "save_and_exit"}
                            elif action == "pause":
                                return {"error": "all_keys_exhausted", "action": "pause"}
                            else:
                                return {}
                        break  # Thử key mới
                    else:
                        print(f"  ❌ Lỗi API: {response.status_code}")
                        break
                except Exception as e:
                    print(f"  ❌ Lỗi kết nối: {e}")
                    if attempt < max_retries_per_key - 1:
                        time.sleep(30)
                        continue
                    else:
                        if not switch_to_next_api_key():
                            # Tất cả keys đã hết quota
                            action = handle_all_keys_exhausted()
                            if action == "retry":
                                break  # Thử lại với keys mới
                            elif action == "save_and_exit":
                                return {"error": "all_keys_exhausted", "action": "save_and_exit"}
                            elif action == "pause":
                                return {"error": "all_keys_exhausted", "action": "pause"}
                            else:
                                return {}
                        break
            
    except Exception as e:
        print(f"Lỗi gọi Gemini API: {e}")
        return {}

# ---- Hàm xử lý response từ Gemini ----
def process_response(response):
    """Xử lý response từ Gemini API"""
    try:
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            text_response = result['candidates'][0]['content']['parts'][0]['text']
            
            # Tìm và parse JSON từ response
            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                try:
                    parsed_data = json.loads(json_str)
                    
                    # Tính ngày hết hạn nếu có ngày cấp
                    if parsed_data.get('NgayCap') and parsed_data['NgayCap']:
                        try:
                            ngay_cap = datetime.strptime(parsed_data['NgayCap'], "%d/%m/%Y")
                            ngay_het_han = ngay_cap + timedelta(days=15*365)
                            parsed_data['NgayHetHan'] = ngay_het_han.strftime("%d/%m/%Y")
                        except Exception as e:
                            print(f"Lỗi tính ngày hết hạn: {e}")
                    
                    # Validation số CCCD
                    if parsed_data.get('CCCD'):
                        cccd = str(parsed_data['CCCD']).strip()
                        # Loại bỏ ký tự không phải số
                        cccd_clean = re.sub(r'[^0-9]', '', cccd)
                        
                        if len(cccd_clean) != 12:
                            print(f"  ⚠️ Số CCCD không đủ 12 chữ số: {cccd_clean} (có {len(cccd_clean)} chữ số)")
                            # Có thể thử lại nếu số CCCD không đủ
                            if len(cccd_clean) < 12:
                                print(f"  🔄 Số CCCD thiếu {12 - len(cccd_clean)} chữ số, có thể cần retry")
                        else:
                            parsed_data['CCCD'] = cccd_clean
                            print(f"  ✅ Số CCCD hợp lệ: {cccd_clean}")
                    
                    return parsed_data
                except json.JSONDecodeError as e:
                    print(f"Lỗi parse JSON: {e}")
                    print(f"Response: {text_response}")
                    return {}
            else:
                print(f"Không tìm thấy JSON trong response: {text_response}")
                return {}
        else:
            print("Không có candidates trong response")
            return {}
    except Exception as e:
        print(f"Lỗi xử lý response: {e}")
        return {}
            
    except Exception as e:
        print(f"Lỗi gọi Gemini API: {e}")
        return {}

# ---- Hàm xử lý folder CCCD ----
def process_cccd_folder(folder_path):
    # Tìm tất cả file ảnh trong folder
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
    images = []
    for ext in image_extensions:
        images.extend(glob.glob(os.path.join(folder_path, ext)))
        images.extend(glob.glob(os.path.join(folder_path, ext.upper())))
    
    # Tìm file PDF
    pdf_files = glob.glob(os.path.join(folder_path, "*.pdf"))
    pdf_files.extend(glob.glob(os.path.join(folder_path, "*.PDF")))
    
    print(f"  Tìm thấy {len(images)} ảnh và {len(pdf_files)} file PDF")
    
    # ƯU TIÊN: Thử xử lý PDF trước
    if pdf_files:
        print(f"  Ưu tiên xử lý từ file PDF...")
        
        for pdf_file in pdf_files:
            print(f"    Đang trích xuất ảnh từ: {os.path.basename(pdf_file)}")
            
            # Trích xuất ảnh từ PDF
            pdf_images = extract_images_from_pdf(pdf_file)
            
            if pdf_images:
                print(f"    Trích xuất được {len(pdf_images)} ảnh từ PDF")
                
                # Gửi ảnh từ PDF đến Gemini
                info = extract_info_with_gemini(pdf_images[:2])  # Chỉ xử lý 2 ảnh đầu
                
                # Dọn dẹp file tạm
                for temp_img in pdf_images:
                    try:
                        os.remove(temp_img)
                    except:
                        pass
                
                # Nếu thành công, trả về kết quả
                if info and any(info.values()):
                    return info
    
    # Nếu PDF không thành công, thử xử lý ảnh trực tiếp
    if images:
        print(f"  Thử xử lý từ ảnh trực tiếp...")
        
        # Sắp xếp ảnh theo tên để đảm bảo thứ tự
        images.sort()
        
        # Chỉ xử lý 2 ảnh đầu tiên (mặt trước và mặt sau)
        images_to_process = images[:2]
        
        print(f"    Đang gửi {len(images_to_process)} ảnh đến Gemini...")
        
        # Gọi Gemini API
        info = extract_info_with_gemini(images_to_process)
        
        # Kiểm tra xem có phải lỗi hết quota không
        if isinstance(info, dict) and info.get("error") == "all_keys_exhausted":
            return info  # Trả về lỗi để xử lý ở cấp cao hơn
        
        # Nếu thành công, trả về kết quả
        if info and any(info.values()):
            return info
    
    # Nếu không có gì, trả về dict rỗng
    return {}

# ---- Quản lý checkpoint ----
def save_checkpoint(processed_folders, current_zip_file):
    """Lưu tiến độ xử lý"""
    checkpoint_data = {
        "zip_file": current_zip_file,
        "processed_folders": processed_folders,
        "timestamp": datetime.now().isoformat(),
        "current_key_index": current_key_index
    }
    try:
        with open("checkpoint.json", "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu checkpoint: {len(processed_folders)} folders đã xử lý")
    except Exception as e:
        print(f"❌ Lỗi lưu checkpoint: {e}")

def load_checkpoint():
    """Tải tiến độ xử lý từ checkpoint"""
    try:
        with open("checkpoint.json", "r", encoding="utf-8") as f:
            checkpoint_data = json.load(f)
        
        # Kiểm tra xem checkpoint có còn hợp lệ không
        if os.path.exists(checkpoint_data.get("zip_file", "")):
            print(f"📂 Tìm thấy checkpoint: {len(checkpoint_data.get('processed_folders', []))} folders đã xử lý")
            return checkpoint_data
        else:
            print("⚠️  Checkpoint không hợp lệ (file zip không tồn tại)")
            return None
    except FileNotFoundError:
        print("ℹ️  Không tìm thấy checkpoint - bắt đầu từ đầu")
        return None
    except Exception as e:
        print(f"❌ Lỗi đọc checkpoint: {e}")
        return None

def clear_checkpoint():
    """Xóa checkpoint sau khi hoàn thành"""
    try:
        if os.path.exists("checkpoint.json"):
            os.remove("checkpoint.json")
            print("🗑️  Đã xóa checkpoint")
    except Exception as e:
        print(f"❌ Lỗi xóa checkpoint: {e}")

# ---- Main process ----
def main():
    print("🚀 Bắt đầu trích xuất thông tin CCCD với Gemini Flash...")
    
    # Nhập file zip đầu vào
    global zip_path, extract_dir
    
    # Tạo thư mục Input_file nếu chưa có
    input_dir = r"D:\ID Extract\Input_file"
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        print(f"📁 Đã tạo thư mục input: {input_dir}")
    
    # Liệt kê các file zip trong thư mục Input_file
    zip_files = []
    for file in os.listdir(input_dir):
        if file.lower().endswith('.zip'):
            zip_files.append(file)
    
    if not zip_files:
        print(f"❌ Không tìm thấy file zip nào trong thư mục: {input_dir}")
        print("Vui lòng đặt file zip vào thư mục Input_file và chạy lại!")
        return
    
    print(f"📁 Tìm thấy {len(zip_files)} file zip trong thư mục Input_file:")
    for i, file in enumerate(zip_files, 1):
        print(f"  {i}. {file}")
    
    while True:
        try:
            choice = input(f"\n📋 Chọn file zip (1-{len(zip_files)}) hoặc Enter để chọn file đầu tiên: ").strip()
            
            if not choice:
                choice = "1"
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(zip_files):
                selected_file = zip_files[choice_idx]
                zip_path = os.path.join(input_dir, selected_file)
                break
            else:
                print(f"❌ Vui lòng chọn số từ 1 đến {len(zip_files)}")
        except ValueError:
            print("❌ Vui lòng nhập số hợp lệ")
    
    # Tạo tên thư mục extract dựa trên tên file zip
    zip_name = os.path.splitext(os.path.basename(zip_path))[0]
    # Tạo folder tổng chứa tất cả extracted
    base_extract_dir = os.path.join(os.path.dirname(input_dir), "extracted_all")
    extract_dir = os.path.join(base_extract_dir, zip_name)
    
    print(f"📦 File zip: {zip_path}")
    print(f"📁 Thư mục extract: {extract_dir}")
    
    # Hiển thị trạng thái API keys
    show_api_keys_status()
    
    if TEST_MODE:
        print("⚠️  CHẠY Ở CHẾ ĐỘ TEST - Chỉ xử lý 2 folder đầu tiên")
    
    # Tạo folder tổng nếu chưa có
    base_extract_dir = os.path.join(os.path.dirname(input_dir), "extracted_all")
    if not os.path.exists(base_extract_dir):
        os.makedirs(base_extract_dir)
        print(f"📁 Đã tạo folder tổng: {base_extract_dir}")
    
    # Giải nén zip nếu chưa có thư mục extracted
    if not os.path.exists(extract_dir):
        print("📦 Đang giải nén file zip...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
    
    # Duyệt folder con - xử lý cấu trúc thư mục lồng nhau
    rows = []
    
    # Tìm tất cả folder con trong extracted
    all_person_folders = []
    for root, dirs, files in os.walk(extract_dir):
        for dir_name in dirs:
            # Kiểm tra xem folder có chứa ảnh hoặc PDF không
            dir_path = os.path.join(root, dir_name)
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.bmp', '*.tiff']
            pdf_files = ['*.pdf', '*.PDF']
            
            has_content = False
            for ext in image_extensions:
                if glob.glob(os.path.join(dir_path, ext)) or glob.glob(os.path.join(dir_path, ext.upper())):
                    has_content = True
                    break
            
            if not has_content:
                for pdf in pdf_files:
                    if glob.glob(os.path.join(dir_path, pdf)):
                        has_content = True
                        break
            
            if has_content:
                all_person_folders.append(dir_path)
    
    # Giới hạn số folder trong test mode
    all_person_folders = all_person_folders[:MAX_FOLDERS]
    
    print(f"📁 Tìm thấy {len(all_person_folders)} folder cần xử lý")
    
    # Tải checkpoint
    checkpoint_data = load_checkpoint()
    processed_folders = []
    
    if checkpoint_data and checkpoint_data.get('zip_file') == zip_path:
        # Tiếp tục từ checkpoint
        processed_folders = checkpoint_data.get('processed_folders', [])
        start_index = len(processed_folders)
        print(f"🔄 Tiếp tục từ folder {start_index + 1}/{len(all_person_folders)}")
        
        # Khôi phục API key index
        global current_key_index
        current_key_index = checkpoint_data.get('current_key_index', 0)
        print(f"🔑 Sử dụng API key {current_key_index + 1}/{len(api_keys_list)}")
    else:
        start_index = 0
        print("🚀 Bắt đầu xử lý từ đầu")
    
    try:
        for i in range(start_index, len(all_person_folders)):
            folder_path = all_person_folders[i]
            person_folder = os.path.basename(folder_path)
            print(f"\n[{i + 1}/{len(all_person_folders)}] Đang xử lý folder: {person_folder}")
            
            info = process_cccd_folder(folder_path)
            
            # Kiểm tra xem có phải lỗi hết quota không
            if isinstance(info, dict) and info.get("error") == "all_keys_exhausted":
                action = info.get("action")
                if action == "save_and_exit":
                    print(f"\n💾 Lưu tiến độ và thoát...")
                    save_checkpoint(processed_folders, zip_path)
                    return
                elif action == "pause":
                    print(f"\n⏸️  Tạm dừng xử lý...")
                    save_checkpoint(processed_folders, zip_path)
                    print(f"💡 Để tiếp tục, chạy lại script với cùng file zip.")
                    return
                else:
                    # Thử lại với keys mới
                    continue
            
            if info and any(info.values()):
                # Kiểm tra CCCD có hết hạn không
                if 'NgayHetHan' in info and info['NgayHetHan']:
                    try:
                        expiry_date = datetime.strptime(info['NgayHetHan'], '%d/%m/%Y')
                        today = datetime.now()
                        
                        if expiry_date < today:
                            print(f"  ⚠️  CCCD đã hết hạn ({info['NgayHetHan']}) - Xóa folder")
                            shutil.rmtree(folder_path)
                            processed_folders.append(folder_path)
                            save_checkpoint(processed_folders, zip_path)
                            continue
                        elif expiry_date < today + timedelta(days=30):
                            print(f"  ⚠️  CCCD sắp hết hạn ({info['NgayHetHan']})")
                    except:
                        pass
                
                rows.append(info)
                print(f"  ✅ Đã trích xuất: {info.get('HoTen', 'N/A')} - {info.get('CCCD', 'N/A')}")
            else:
                print(f"  ❌ Không thể trích xuất thông tin từ {person_folder}")
            
            # Lưu checkpoint sau mỗi folder
            processed_folders.append(folder_path)
            save_checkpoint(processed_folders, zip_path)
            
            # Hiển thị trạng thái API keys mỗi 10 folder
            if (i + 1) % 10 == 0:
                show_api_keys_status()
            
            # Delay nhỏ để tránh rate limit
            if i < len(all_person_folders) - 1:
                time.sleep(1)
        
        # Hoàn thành - xóa checkpoint
        clear_checkpoint()
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Đã dừng xử lý. Tiến độ đã được lưu.")
        print(f"💡 Để tiếp tục, chạy lại script với cùng file zip.")
        return
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        print(f"💾 Tiến độ đã được lưu. Có thể tiếp tục sau.")
        return
    
    # Xuất Excel
    if rows:
        df = pd.DataFrame(rows)
        # Sắp xếp cột theo thứ tự mong muốn
        columns_order = ["CCCD", "HoTen", "NgaySinh", "GioiTinh", "DiaChi", "NoiCap", "NgayCap", "NgayHetHan"]
        df = df.reindex(columns=columns_order)
        
        # Tạo tên file Excel dựa trên tên file zip
        zip_name = os.path.splitext(os.path.basename(zip_path))[0]
        
        # Tạo folder Excel nếu chưa có
        excel_dir = os.path.join(os.path.dirname(input_dir), "Excel")
        if not os.path.exists(excel_dir):
            os.makedirs(excel_dir)
            print(f"📁 Đã tạo thư mục Excel: {excel_dir}")
        
        excel_path = os.path.join(excel_dir, f"cccd_data_{zip_name}.xlsx")
        df.to_excel(excel_path, index=False)
        print(f"\n🎉 Hoàn thành! Đã trích xuất {len(rows)} bản ghi")
        print(f"📄 File Excel: {excel_path}")
        
        # Hiển thị thống kê
        print(f"\n📊 Thống kê:")
        print(f"- Tổng số bản ghi: {len(rows)}")
        print(f"- Có CCCD: {df['CCCD'].notna().sum()}")
        print(f"- Có họ tên: {df['HoTen'].notna().sum()}")
        print(f"- Có ngày sinh: {df['NgaySinh'].notna().sum()}")
        print(f"- Có giới tính: {df['GioiTinh'].notna().sum()}")
        print(f"- Có địa chỉ: {df['DiaChi'].notna().sum()}")
        print(f"- Có nơi cấp: {df['NoiCap'].notna().sum()}")
        print(f"- Có ngày cấp: {df['NgayCap'].notna().sum()}")
        print(f"- Có ngày hết hạn: {df['NgayHetHan'].notna().sum()}")
        
        # Hiển thị dữ liệu mẫu
        print(f"\n📋 Dữ liệu mẫu:")
        for i, row in df.iterrows():
            print(f"  {i+1}. {row['HoTen']} - {row['CCCD']} - {row['GioiTinh']}")
    else:
        print("❌ Không có dữ liệu nào được trích xuất!")

if __name__ == "__main__":
    main() 