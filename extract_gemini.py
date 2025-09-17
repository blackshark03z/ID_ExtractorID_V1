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
import hashlib
import random

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
exhausted_keys = set()  # Theo dõi các key đã hết quota/tạm thời không dùng
blacklisted_keys = set()  # Theo dõi các key bị suspend/disabled

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
    # Không reset blacklist tự động để tránh dùng lại key bị treo

def get_available_keys_count():
    """Lấy số lượng keys còn khả dụng (không tính exhausted và blacklisted)."""
    return len(api_keys_list) - len(exhausted_keys) - len(blacklisted_keys)

def show_api_keys_status():
    """Hiển thị trạng thái API keys"""
    total_keys = len(api_keys_list)
    available_keys = get_available_keys_count()
    exhausted_count = len(exhausted_keys)
    blacklisted_count = len(blacklisted_keys)
    
    print(f"\n🔑 Trạng thái API Keys:")
    print(f"   📊 Tổng số: {total_keys}")
    print(f"   ✅ Khả dụng: {available_keys}")
    print(f"   ❌ Hết quota/tạm dừng: {exhausted_count}")
    print(f"   ⛔ Bị treo (blacklist): {blacklisted_count}")
    
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
    global current_key_index
    if not api_keys_list:
        return None
    
    # Kiểm tra xem key hiện tại có bị hết quota không
    if current_key_index in exhausted_keys or current_key_index in blacklisted_keys:
        # Tìm key khả dụng tiếp theo
        for i in range(len(api_keys_list)):
            if i not in exhausted_keys and i not in blacklisted_keys:
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
        Bạn là hệ thống trích xuất thông tin từ ảnh Căn cước công dân (CCCD).
        Trả về DUY NHẤT một JSON hợp lệ (không kèm văn bản khác) với CÁC TRƯỜNG SAU:
        {
            "CCCD": "Giá trị của mục 'Số/No.' – CHUỖI 12 CHỮ SỐ",
            "HoTen": "Giá trị của mục 'Họ và tên/Full name' – VIẾT HOA KHÔNG DẤU",
            "NgaySinh": "Giá trị của mục 'Ngày sinh/Date of birth' – dd/mm/yyyy",
            "GioiTinh": "Giá trị của mục 'Giới tính/Sex' – NAM hoặc NU",
            "DiaChi": "Giá trị của mục 'NƠI THƯỜNG TRÚ' hoặc 'PLACE OF RESIDENCE' – VIẾT HOA KHÔNG DẤU (TUYỆT ĐỐI KHÔNG LẤY 'Quê quán/Place of origin')",
            "NgayHetHan": "Giá trị của mục 'Có giá trị đến/Date of expiry' – dd/mm/yyyy hoặc null nếu không có"
        }

        RÀNG BUỘC NGHIÊM NGẶT CHO 'DiaChi':
        - Chỉ chấp nhận đúng 2 nhãn: "NƠI THƯỜNG TRÚ" hoặc "PLACE OF RESIDENCE".
        - Loại trừ tuyệt đối các nhãn: "QUÊ QUÁN", "NƠI SINH", "PLACE OF ORIGIN", "PLACE OF BIRTH", "NATIVE PLACE", "DOMICILE".
        - Nếu vừa có NƠI THƯỜNG TRÚ vừa có QUÊ QUÁN, CHỈ lấy NƠI THƯỜNG TRÚ. Nếu chỉ thấy QUÊ QUÁN, để DiaChi = null.

        YÊU CẦU CHUNG:
        - Chuẩn hóa VIẾT HOA KHÔNG DẤU cho HoTen, GioiTinh, DiaChi.
        - CCCD là CHUỖI 12 CHỮ SỐ. Nếu không đủ 12 số, để trống hoặc null.
        - Ngày theo dd/mm/yyyy; nếu không chắc chắn, để trống hoặc null.
        - Nếu có nhiều ảnh, dùng mặt TRƯỚC cho HoTen/CCCD/NgaySinh, và thông tin hạn; dùng mặt SAU để đối chiếu nếu cần.
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
        
        # Thêm retry logic cho lỗi quota/403 và 5xx với backoff
        max_retries_per_key = 5  # tăng retry per-key để xử lý 5xx/UNAVAILABLE
        max_total_attempts = max(1, len(api_keys_list) * max_retries_per_key)
        attempts = 0
        
        while attempts < max_total_attempts:
            current_key = get_current_api_key()
            if not current_key:
                print("  ❌ Không có API key nào khả dụng")
                print(f"  📊 Trạng thái: {len(exhausted_keys)}/{len(api_keys_list)} keys đã hết quota")
                
                # Xử lý khi tất cả keys hết quota
                action = handle_all_keys_exhausted()
                if action == "retry":
                    continue  # Keys đã reload, thử lại
                elif action == "save_and_exit":
                    return {"error": "all_keys_exhausted", "action": "save_and_exit"}
                elif action == "pause":
                    return {"error": "all_keys_exhausted", "action": "pause"}
                else:
                    return {}
            
            url = f"{GEMINI_API_URL}?key={current_key}"
            
            for attempt in range(max_retries_per_key):
                try:
                    attempts += 1
                    response = requests.post(url, headers=headers, json=data, timeout=30)
                    
                    if response.status_code == 200:
                        return process_response(response)
                    # 429 - rate limit/quota per key → chuyển key
                    elif response.status_code == 429:
                        print(f"  ⚠️  API key {current_key_index + 1} hết quota")
                        if not switch_to_next_api_key():
                            # Tất cả keys đã hết quota
                            action = handle_all_keys_exhausted()
                            if action == "retry":
                                break  # Keys đã reload, thử lại
                            elif action == "save_and_exit":
                                return {"error": "all_keys_exhausted", "action": "save_and_exit"}
                            elif action == "pause":
                                return {"error": "all_keys_exhausted", "action": "pause"}
                            else:
                                return {}
                        break  # Thử key mới
                    # 5xx - lỗi tạm thời máy chủ/model → backoff và thử lại cùng key
                    elif 500 <= response.status_code < 600:
                        try:
                            body = response.text or ""
                        except Exception:
                            body = ""
                        print(f"  ❌ Lỗi API tạm thời: {response.status_code}")
                        if body:
                            print(f"     ↪ {body[:200]}")
                        # Respect Retry-After nếu có, ngược lại exponential backoff + jitter
                        retry_after = response.headers.get('Retry-After') if hasattr(response, 'headers') else None
                        if retry_after:
                            try:
                                wait_seconds = max(1, int(float(retry_after)))
                            except Exception:
                                wait_seconds = 0
                        else:
                            base = 3
                            cap = 60
                            wait_seconds = min(cap, base * (2 ** attempt))
                            wait_seconds = int(wait_seconds + random.uniform(0, 1.5))
                        print(f"  ⏳ Chờ {wait_seconds}s rồi thử lại cùng API key...")
                        time.sleep(wait_seconds)
                        continue
                    elif response.status_code in (401, 403):
                        # Phân biệt lỗi tạm thời vs bị treo/ban
                        try:
                            body = response.text
                        except Exception:
                            body = ""
                        reason = (body or "").lower()
                        temporary_markers = [
                            "quota", "rate limit", "exceeded", "temporar", "overload",
                            "resource_exhausted", "concurrent", "traffic"
                        ]
                        blacklist_markers = [
                            "suspend", "disabled", "deactivat", "ban", "banned",
                            "policy", "violation", "abuse", "blocked by policy"
                        ]
                        if any(m in reason for m in blacklist_markers):
                            print(f"  ⛔ API key {current_key_index + 1} vào blacklist ({response.status_code}).")
                            blacklisted_keys.add(current_key_index)
                        else:
                            print(f"  ⚠️  API key {current_key_index + 1} tạm thời không dùng được ({response.status_code}).")
                            exhausted_keys.add(current_key_index)
                        break  # Thử key khác
                    elif response.status_code == 400:
                        # 400 có thể là "API key not valid" → đưa key vào blacklist để bỏ qua
                        try:
                            body = response.text or ""
                        except Exception:
                            body = ""
                        if "api key not valid" in body.lower() or "invalid api key" in body.lower():
                            print(f"  ⛔ API key {current_key_index + 1} không hợp lệ (400) → blacklist.")
                            blacklisted_keys.add(current_key_index)
                        else:
                            print("  ❌ Lỗi API: 400")
                            if body:
                                print(f"     ↪ {body[:200]}")
                        break
                    else:
                        try:
                            body = response.text
                        except Exception:
                            body = ""
                        print(f"  ❌ Lỗi API: {response.status_code}")
                        if body:
                            print(f"     ↪ {body[:200]}")
                        break
                except Exception as e:
                    print(f"  ❌ Lỗi kết nối: {e}")
                    # Exponential backoff cho lỗi mạng, giữ nguyên key
                    base = 2
                    cap = 45
                    wait_seconds = min(cap, base * (2 ** attempt))
                    wait_seconds = int(wait_seconds + random.uniform(0, 1.5))
                    print(f"  ⏳ Chờ {wait_seconds}s rồi thử lại kết nối...")
                    time.sleep(wait_seconds)
                    continue
            # Nếu tất cả keys đã bị đánh dấu hết/không hợp lệ
            if len(exhausted_keys) >= len(api_keys_list):
                action = handle_all_keys_exhausted()
                if action == "retry":
                    continue
                elif action == "save_and_exit":
                    return {"error": "all_keys_exhausted", "action": "save_and_exit"}
                elif action == "pause":
                    return {"error": "all_keys_exhausted", "action": "pause"}
                else:
                    return {}
            
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
    # Đưa T.jpg/S.jpg lên đầu trước khi khử trùng
    images = prioritize_cccd_filenames(images)
    # Khử trùng ảnh theo nội dung, ưu tiên giữ T.jpg/S.jpg nếu trùng
    images = deduplicate_images_keep_priority(images)
    
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
        
        # Sắp xếp: ưu tiên T.jpg/S.jpg vẫn ở đầu
        images = prioritize_cccd_filenames(sorted(images))
        
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

# ---- Khử trùng ảnh, ưu tiên T.jpg/S.jpg khi trùng nội dung ----
def _file_md5(path):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        return hashlib.md5(data).hexdigest()
    except Exception:
        return None

def _is_priority_name(path):
    name = os.path.basename(path).lower()
    return name in ("t.jpg", "s.jpg")

def deduplicate_images_keep_priority(images):
    """Loại ảnh trùng nội dung (md5), giữ 1 ảnh/nhóm; ưu tiên T.jpg/S.jpg."""
    hash_to_best = {}
    for p in images:
        h = _file_md5(p)
        if h is None:
            # Nếu không tính được hash, coi như duy nhất
            hash_to_best[p] = p
            continue
        if h not in hash_to_best:
            hash_to_best[h] = p
        else:
            # Nếu đã có, chọn ảnh ưu tiên nếu có tên T.jpg/S.jpg
            current_best = hash_to_best[h]
            if _is_priority_name(p) and not _is_priority_name(current_best):
                hash_to_best[h] = p
            # Nếu cả hai đều không/đều ưu tiên, giữ nguyên ảnh đã chọn trước
    # Trả về danh sách sau khi khử trùng
    return list({v for v in hash_to_best.values()})

def prioritize_cccd_filenames(images):
    """Đưa các ảnh tên T.jpg, S.jpg lên đầu danh sách."""
    priority = []
    others = []
    for p in images:
        if _is_priority_name(p):
            priority.append(p)
        else:
            others.append(p)
    # Giữ thứ tự ổn định cho phần còn lại
    return priority + others

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

# ---- Hỏi tiếp tục hay làm lại khi có checkpoint của cùng file ----
def ask_resume_or_restart_for_zip(selected_zip_path: str):
    """Nếu checkpoint khớp cùng zip, hỏi người dùng muốn tiếp tục hay làm lại.
    Trả về tuple (mode, checkpoint_data) với mode trong {"resume", "restart", "none"}.
    """
    cp = load_checkpoint()
    if not cp:
        return "none", None
    if cp.get('zip_file') != selected_zip_path:
        return "none", None
    processed = len(cp.get('processed_folders', []))
    print("\n" + "="*50)
    print("🔄 PHÁT HIỆN CHECKPOINT CHO FILE ZIP ĐANG CHỌN")
    print("="*50)
    print(f"📂 File: {os.path.basename(selected_zip_path)}")
    print(f"📊 Đã xử lý: {processed} folder")
    print("1. ⏭️  Tiếp tục từ checkpoint hiện tại")
    print("2. 🗑️  Làm lại từ đầu (xóa checkpoint)")
    while True:
        choice = input("\n🎯 Chọn (1-2): ").strip()
        if choice in ("1", ""):
            print("✅ Tiếp tục từ checkpoint hiện tại")
            return "resume", cp
        if choice == "2":
            if clear_checkpoint() is None:
                pass
            return "restart", None
        print("❌ Lựa chọn không hợp lệ, vui lòng chọn 1-2")

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
    
    # Hỏi tiếp tục hay làm lại nếu có checkpoint của đúng file zip
    mode, checkpoint_data = ask_resume_or_restart_for_zip(zip_path)

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
    
    # Chuẩn bị trạng thái theo lựa chọn
    processed_folders = []
    if mode == "resume" and checkpoint_data:
        processed_folders = checkpoint_data.get('processed_folders', [])
        start_index = len(processed_folders)
        print(f"🔄 Tiếp tục từ folder {start_index + 1}/{len(all_person_folders)}")
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
                            try:
                                print(f"  ⚠️  CCCD đã hết hạn ({info['NgayHetHan']}) - Đổi tên folder thêm ' hết hạn'")
                                parent_dir = os.path.dirname(folder_path)
                                base_name = os.path.basename(folder_path)
                                new_name = base_name + " hết hạn"
                                new_path = os.path.join(parent_dir, new_name)
                                # Tránh đè nếu đã tồn tại tên mới
                                if os.path.exists(new_path):
                                    ts = datetime.now().strftime("_%Y%m%d_%H%M%S")
                                    new_path = os.path.join(parent_dir, new_name + ts)
                                os.rename(folder_path, new_path)
                                processed_folders.append(new_path)
                            except Exception as e:
                                print(f"  ❌ Không thể đổi tên folder hết hạn: {e}")
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