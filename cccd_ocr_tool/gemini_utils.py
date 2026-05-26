import os
import time
import json
import warnings
import google.generativeai as genai
from PIL import Image

# Tắt cảnh báo FutureWarning của google.generativeai để output terminal sạch sẽ
warnings.filterwarnings("ignore", category=FutureWarning)

class GeminiManager:
    def __init__(self, key_file_path):
        self.keys = []
        if os.path.exists(key_file_path):
            with open(key_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        self.keys.append(line)
        self.current_key_idx = 0
        self._configure()
        print(f"\n[HỆ THỐNG] Đã nạp thành công {len(self.keys)} API Keys từ file.")
        
    def _configure(self):
        if not self.keys:
            print("Cảnh báo: Không tìm thấy API Key nào trong file api_keys.txt")
            return
        genai.configure(api_key=self.keys[self.current_key_idx])
        
    def next_key(self):
        if len(self.keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.keys)
            self._configure()
            print(f"  Chuyển sang API Key mới (index {self.current_key_idx})...")
            return True
        return False

    def process_images(self, image_paths):
        if not self.keys:
            return {"error": "No API keys configured"}
            
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Load images
        images = []
        valid_paths = []
        try:
            for path in image_paths:
                if os.path.exists(path):
                    try:
                        with Image.open(path) as img:
                            temp_img = img.convert('RGB')
                            temp_img.load()
                            images.append(temp_img)
                            valid_paths.append(path)
                    except Exception as e:
                        print(f"  Cannot open image {path}: {e}")

            if not images:
                return {"error": "No valid images found"}

            prompt = f"""
            Bạn là một chuyên gia nhận diện Căn cước công dân Việt Nam.
            Tôi gửi cho bạn {len(images)} hình ảnh đính kèm. Đây có thể là các trang được trích xuất từ một hoặc nhiều file PDF và các file ảnh rời trong một thư mục hồ sơ.
            
            QUAN TRỌNG: Danh sách hình ảnh này có thể chứa nhiều hình ảnh không phải CCCD (ví dụ: các trang của hợp đồng, đơn từ, tài liệu khác, hoặc trang trống). Bạn cần quét kỹ qua TẤT CẢ {len(images)} hình ảnh để tìm ra:
            - 1 hình ảnh chứa MẶT TRƯỚC CCCD (có ảnh chân dung chủ thẻ, số CCCD, Họ và tên, Ngày sinh, Giới tính, Quê quán, Nơi thường trú...).
            - 1 hình ảnh chứa MẶT SAU CCCD (có chip điện tử, hai dấu vân tay, đặc điểm nhân dạng, ngày cấp, và chữ ký/dấu của Cục trưởng Cục Cảnh sát...).
            
            Nhiệm vụ 1: Xác định ảnh nào là mặt trước CCCD và ảnh nào là mặt sau CCCD. Hãy trả về index tương ứng của mảng ảnh (từ 0 đến {len(images)-1}). Nếu không tìm thấy mặt trước hoặc mặt sau, trả về -1 cho index đó.
            Nhiệm vụ 2: Trích xuất các thông tin chi tiết và TRẢ VỀ ĐỊNH DẠNG JSON THUẦN TÚY (không dùng markdown code block, chỉ nội dung JSON).
            
            Cấu trúc JSON yêu cầu:
            {{
                "front_index": <int>,
                "back_index": <int>,
                "CCCD": "<chuỗi 12 chữ số>",
                "HoTen": "<Viết hoa, không dấu - BẮT BUỘC lấy từ mặt trước của thẻ, dưới chữ 'HỌ VÀ TÊN / Full name'. TUYỆT ĐỐI KHÔNG LẤY tên người ký ở mặt sau như PHẠM CÔNG NGUYÊN hoặc NGUYỄN QUỐC HÙNG>",
                "NgaySinh": "<dd/mm/yyyy>",
                "GioiTinh": "<NAM hoặc NU>",
                "DiaChi": "<Địa chỉ nơi thường trú / Place of residence - thường ở dòng cuối cùng của mặt trước, không lấy Quê quán / Place of origin>",
                "NoiCap": "<Nơi cấp ở mặt sau - thường là CUC TRUONG CUC CANH SAT QUAN LY HANH CHINH VE TRAT TU XA HOI>",
                "NgayCap": "<dd/mm/yyyy>",
                "NgayHetHan": "<dd/mm/yyyy hoặc KHONG THOI HAN>"
            }}
            
            Lưu ý bổ sung: 
            - Giữ nguyên số 0 ở đầu số CCCD.
            - Nếu không đọc được trường thông tin nào, hãy để chuỗi rỗng "".
            - Tuyệt đối không nhầm lẫn họ tên chủ thẻ ở mặt trước với họ tên Cục trưởng ký ở mặt sau.
            """

            contents = images + [prompt]
            
            max_retries = max(5, len(self.keys) * 3)
            keys_tried_this_round = 0
            
            for attempt in range(max_retries):
                # Khởi tạo lại model trong vòng lặp để đảm bảo nó nhận API Key mới nếu có thay đổi
                model = genai.GenerativeModel('gemini-2.5-flash')
                
                try:
                    response = model.generate_content(contents, request_options={"timeout": 120})
                    
                    text = response.text.strip()
                    # Clean up markdown
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                        
                    data = json.loads(text.strip())
                    # Resolve paths
                    data["front_path"] = valid_paths[data["front_index"]] if data.get("front_index", -1) >= 0 and data["front_index"] < len(valid_paths) else None
                    data["back_path"] = valid_paths[data["back_index"]] if data.get("back_index", -1) >= 0 and data["back_index"] < len(valid_paths) else None
                    
                    return data
                    
                except Exception as e:
                    error_msg = str(e).lower()
                    print(f"  Lỗi gọi Gemini (attempt {attempt+1}/{max_retries}): {e}")
                    if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                        keys_tried_this_round += 1
                        
                        if len(self.keys) > 1 and keys_tried_this_round < len(self.keys):
                            self.next_key()
                            continue
                        else:
                            print("  [Rate Limit] Tất cả các key đều quá tải hoặc bạn chỉ có 1 key.")
                            print("  [Rate Limit] Đang tự động đợi 60 giây để Google reset RPM (5 req/phút)...")
                            time.sleep(60)
                            keys_tried_this_round = 0 # Reset bộ đếm sau khi ngủ
                            if len(self.keys) > 1:
                                self.next_key()
                    elif "403" in error_msg or "api_key" in error_msg or "unauthorized" in error_msg or "expired" in error_msg:
                        print(f"  [LỖI] API Key hiện tại bị TỪ CHỐI TRUY CẬP (403/Invalid/Expired).")
                        if len(self.keys) > 1:
                            del self.keys[self.current_key_idx]
                            if self.current_key_idx >= len(self.keys):
                                self.current_key_idx = 0
                            print(f"  Đang tự động VỨT BỎ key bị lỗi này. Chuyển sang key khác (còn lại {len(self.keys)} keys)...")
                            self._configure()
                            continue
                        else:
                            return {"error": "Lỗi 403: Tất cả API Key đều đã chết hoặc không có quyền truy cập."}
                    else:
                        return {"error": str(e)}
                        
            return {"error": "Failed after all retries due to strict rate limits. Please add more API Keys or wait until tomorrow."}
        finally:
            for img in images:
                try:
                    img.close()
                except:
                    pass

# Global manager instance
gemini_manager = None

def init_gemini(key_file_path):
    global gemini_manager
    gemini_manager = GeminiManager(key_file_path)

def process_with_gemini(image_paths):
    if not gemini_manager:
        raise Exception("GeminiManager not initialized.")
    return gemini_manager.process_images(image_paths)
