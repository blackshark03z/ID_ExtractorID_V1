# ID Extractor - CCCD Information Extraction System

Hệ thống trích xuất thông tin từ CCCD (Căn cước công dân) sử dụng AI Gemini Flash API.

## 🚀 Tính năng chính

- **OCR thông minh**: Sử dụng Gemini Flash API để trích xuất thông tin chính xác
- **Xử lý đa định dạng**: Hỗ trợ ảnh JPG, PNG, PDF
- **Giao diện GUI**: Giao diện đồ họa thân thiện với người dùng
- **Hệ thống checkpoint**: Tự động lưu và khôi phục tiến độ xử lý
- **Quản lý API keys**: Tự động chuyển đổi API keys khi hết quota
- **Validation dữ liệu**: Kiểm tra và cảnh báo số CCCD không hợp lệ
- **Xuất Excel**: Tự động xuất kết quả ra file Excel

## 📋 Thông tin được trích xuất

- **CCCD**: Số căn cước công dân (12 chữ số)
- **Họ tên**: Họ và tên đầy đủ
- **Ngày sinh**: Định dạng dd/mm/yyyy
- **Giới tính**: NAM hoặc NỮ
- **Địa chỉ**: Địa chỉ thường trú
- **Nơi cấp**: Nơi cấp CCCD
- **Ngày cấp**: Ngày cấp CCCD
- **Ngày hết hạn**: Tự động tính toán (15 năm từ ngày cấp)

## 🛠️ Cài đặt

### Yêu cầu hệ thống
- Python 3.7+
- Windows/Linux/macOS

### Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### Cấu hình API keys
1. Tạo file `api_keys.txt`
2. Thêm các Gemini API keys (mỗi key một dòng)
3. Ví dụ:
```
AIzaSyDzvw-vLXTOy0GoSx3Z8K_xyUksO-wesQ
AIzaSyB1234567890abcdefghijklmnop
```

## 📁 Cấu trúc thư mục

```
ID Extract/
├── extract_gemini.py          # Script chính (command line)
├── extract_gui.py             # Giao diện GUI
├── create_api_keys.py         # Tạo API keys tự động
├── test_proxy.py              # Test proxy
├── test_checkpoint.py         # Test checkpoint system
├── requirements.txt           # Dependencies
├── api_keys.txt              # API keys (tạo thủ công)
├── gmail_list.txt            # Danh sách Gmail (tùy chọn)
├── proxy_list.txt            # Danh sách proxy (tùy chọn)
├── README.md                 # Hướng dẫn sử dụng
├── README_API_KEYS.md        # Hướng dẫn tạo API keys
├── README_CHECKPOINT.md      # Hướng dẫn checkpoint
├── Input_file/               # Thư mục chứa file ZIP đầu vào
├── extracted_all/            # Thư mục chứa dữ liệu đã giải nén
└── Excel/                    # Thư mục chứa file Excel kết quả
```

## 🎯 Cách sử dụng

### Sử dụng GUI (Khuyến nghị)
```bash
python extract_gui.py
```

### Sử dụng Command Line
```bash
python extract_gemini.py
```

### Các tính năng bổ sung

#### Tạo API keys tự động
```bash
python create_api_keys.py
```

#### Test proxy
```bash
python test_proxy.py
```

#### Test checkpoint system
```bash
python test_checkpoint.py
```

## ⚙️ Cấu hình

### Test Mode
Trong `extract_gemini.py`, thay đổi:
```python
TEST_MODE = True  # Chỉ xử lý 5 folder đầu tiên
```

### Auto delete expired CCCD
Trong GUI, tích vào checkbox "Auto delete expired CCCD"

### Checkpoint
Trong GUI, tích vào checkbox "Use Checkpoint" để lưu tiến độ

## 🔧 Troubleshooting

### Lỗi API quota
- Thêm nhiều API keys vào `api_keys.txt`
- Sử dụng `create_api_keys.py` để tạo keys tự động

### Lỗi số CCCD thiếu
- Hệ thống sẽ cảnh báo và gợi ý retry
- Kiểm tra chất lượng ảnh đầu vào

### Lỗi kết nối
- Kiểm tra internet connection
- Thử lại sau vài phút

## 📊 Kết quả

Hệ thống sẽ tạo file Excel với các cột:
- CCCD
- HoTen
- NgaySinh
- GioiTinh
- DiaChi
- NoiCap
- NgayCap
- NgayHetHan

## 🤝 Đóng góp

Mọi đóng góp đều được chào đón! Vui lòng:
1. Fork project
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

MIT License - xem file LICENSE để biết thêm chi tiết.

## 📞 Hỗ trợ

Nếu gặp vấn đề, vui lòng tạo issue trên GitHub hoặc liên hệ qua email.

---

**Lưu ý**: Đảm bảo tuân thủ quy định pháp luật về bảo mật thông tin cá nhân khi sử dụng hệ thống này. 