# ID Extractor - CCCD Information Extraction System

Hệ thống trích xuất thông tin từ CCCD (Căn cước công dân) sử dụng AI Gemini Flash API.

## 🚀 Tính năng chính

- **OCR thông minh**: Sử dụng Gemini Flash API để trích xuất thông tin chính xác
- **Xử lý đa định dạng**: Hỗ trợ ảnh JPG, PNG, PDF
  
- **Hệ thống checkpoint**: Tự động lưu và khôi phục tiến độ xử lý
- **Quản lý API keys thông minh**: 
  - Tự động chuyển đổi API keys khi hết quota
  - Theo dõi trạng thái keys khả dụng
  - Xử lý thông minh khi tất cả keys hết quota
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

### Thiết lập tự động (Khuyến nghị)
```bash
python setup.py
```
Script này sẽ tự động:
- Tạo các thư mục cần thiết
- Tạo file `api_keys.txt` mẫu
- Tạo các file cấu hình tùy chọn

### Thiết lập thủ công
#### Tạo thư mục
```bash
mkdir Input_file
mkdir extracted_all
mkdir Excel
```

#### Cấu hình API keys
1. Tạo file `api_keys.txt`
2. Thêm các Gemini API keys (mỗi key một dòng)
3. Ví dụ:
```
AIzaSyDzvw-vLXTOy0GoSx3Z8K_xyUksO-wesQ
AIzaSyB1234567890abcdefghijklmnop
```

## 📁 Cấu trúc thư mục

### Cấu trúc sau khi clone (ban đầu)
```
ID_Extractor/
├── extract_gemini.py          # Script chính (command line)
├── setup.py                   # Script thiết lập tự động
├── requirements.txt           # Dependencies
├── README.md                 # Hướng dẫn sử dụng
├── README_API_KEYS.md        # Hướng dẫn tạo API keys
├── README_CHECKPOINT.md      # Hướng dẫn checkpoint
├── LICENSE                   # MIT License
└── .gitignore               # Git ignore rules
```

### Cấu trúc sau khi thiết lập
```
ID_Extractor/
├── extract_gemini.py          # Script chính (command line)
├── setup.py                   # Script thiết lập tự động
├── requirements.txt           # Dependencies
├── api_keys.txt              # API keys (tạo thủ công)
├── gmail_list.txt            # Danh sách Gmail (tùy chọn)
├── proxy_list.txt            # Danh sách proxy (tùy chọn)
├── README.md                 # Hướng dẫn sử dụng
├── README_API_KEYS.md        # Hướng dẫn tạo API keys
├── README_CHECKPOINT.md      # Hướng dẫn checkpoint
├── LICENSE                   # MIT License
├── .gitignore               # Git ignore rules
├── Input_file/               # Thư mục chứa file ZIP đầu vào
│   ├── Test.zip
│   ├── Tenchuan.zip
│   └── ...
├── extracted_all/            # Thư mục chứa dữ liệu đã giải nén
│   ├── Test/
│   │   ├── AN CHI THANH/
│   │   └── BON VAN CHANH/
│   └── Tenchuan/
└── Excel/                    # Thư mục chứa file Excel kết quả
    ├── cccd_data_Test.xlsx
    └── cccd_data_Tenchuan.xlsx
```

## 🎯 Cách sử dụng

### 1. Thiết lập ban đầu

#### Tạo cấu trúc thư mục
Sau khi clone project, tạo các thư mục cần thiết:

```bash
# Tạo thư mục chứa file ZIP đầu vào
mkdir Input_file

# Tạo thư mục chứa dữ liệu đã giải nén
mkdir extracted_all

# Tạo thư mục chứa file Excel kết quả
mkdir Excel
```

#### Cấu hình API keys
1. Tạo file `api_keys.txt` trong thư mục gốc
2. Thêm các Gemini API keys (mỗi key một dòng):
```
AIzaSyDzvw-vLXTOy0GoSx3Z8K_xyXUksO-wesQ
AIzaSyB1234567890abcdefghijklmnop
```

#### Chuẩn bị dữ liệu
1. Đặt file ZIP chứa ảnh CCCD vào thư mục `Input_file/`
2. Cấu trúc file ZIP:
   ```
   Tenchuan.zip
   ├── AN CHI THANH/
   │   ├── CHÍ THANH-1.jpg
   │   └── CHÍ THANH-2.jpg
   ├── BON VAN CHANH/
   │   ├── 5953325 bồn văn chanh cccd-1.jpg
   │   └── 5953325 bồn văn chanh cccd-2.jpg
   └── ...
   ```

### 2. Chạy chương trình

#### Sử dụng Command Line (CLI)
```bash
python extract_gemini.py
```

### Các tính năng bổ sung

  

#### Test proxy
```bash
python test_proxy.py
```

#### Test checkpoint system
```bash
python test_checkpoint.py
```

#### Test API keys exhausted logic
```bash
python test_api_keys_exhausted.py
```

## ⚙️ Cấu hình

### Test Mode
Trong `extract_gemini.py`, thay đổi:
```python
TEST_MODE = True  # Chỉ xử lý 5 folder đầu tiên
```

### Checkpoint
Tiến trình được lưu tự động bằng file `checkpoint.json` trong CLI

## 🔧 Troubleshooting

### Lỗi "Thư mục không tồn tại"
- Đảm bảo đã tạo các thư mục: `Input_file/`, `extracted_all/`, `Excel/`
- Chạy lệnh tạo thư mục như hướng dẫn ở trên

### Lỗi "Không tìm thấy file ZIP"
- Đặt file ZIP vào thư mục `Input_file/`
- Kiểm tra tên file và định dạng (.zip)

### Lỗi API quota
- Thêm nhiều API keys vào `api_keys.txt`
- Hệ thống tự động chuyển đổi API keys khi hết quota
- Khi tất cả keys hết quota, có 4 tùy chọn xử lý:
  1. Chờ reset quota (00:00 UTC)
  2. Thêm API keys mới
  3. Lưu tiến độ và thoát
  4. Tạm dừng và thử lại sau

### Lỗi số CCCD thiếu
- Hệ thống sẽ cảnh báo và gợi ý retry
- Kiểm tra chất lượng ảnh đầu vào

### Lỗi kết nối
- Kiểm tra internet connection
- Thử lại sau vài phút

### Lỗi "Permission denied"
- Đảm bảo có quyền ghi vào thư mục
- Chạy với quyền administrator nếu cần

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