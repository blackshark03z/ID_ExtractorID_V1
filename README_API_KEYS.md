# Hướng dẫn tạo API Keys từ danh sách Gmail

## 📋 Chuẩn bị

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Cài đặt Chrome WebDriver
- Tải Chrome WebDriver từ: https://chromedriver.chromium.org/
- Đặt file `chromedriver.exe` vào thư mục project hoặc PATH

### 3. Chuẩn bị file Gmail
Tạo file `gmail_list.txt` với format:
```
# Danh sách Gmail và mật khẩu
# Format: Gmail|Password
example1@gmail.com|password123
example2@gmail.com|password456
```

### 4. Chuẩn bị file Proxy (Tùy chọn)
Tạo file `proxy_list.txt` với format:
```
# Danh sách Proxy
# Format: ip:port hoặc ip:port:username:password
192.168.1.1:8080
192.168.1.1:8080:user:pass
```

## 🚀 Sử dụng

### Phương pháp 1: Tự động với Proxy (Khuyến nghị)
```bash
python create_api_keys.py
```
- Chọn `y` để tạo tự động
- Script sẽ tự động đăng nhập và tạo API keys
- **Tính năng mới**: Sử dụng proxy ngẫu nhiên cho mỗi Gmail
- **Lưu ý**: Có thể cần xác thực 2 yếu tố

### Phương pháp 2: Hướng dẫn thủ công (An toàn hơn)
```bash
python create_api_keys.py
```
- Chọn `n` để tạo thủ công
- Script sẽ hướng dẫn từng bước
- Bạn tự thực hiện và nhập API keys

## ⚠️ Lưu ý quan trọng

### Bảo mật
- **KHÔNG** chia sẻ file `gmail_list.txt` chứa mật khẩu
- **KHÔNG** commit file này lên Git
- Xóa file sau khi tạo xong API keys

### Giới hạn Google
- Google có thể chặn nếu tạo quá nhiều keys
- **Giải pháp**: Sử dụng proxy để thay đổi IP
- Nên tạo từng ít một (5-10 keys/lần)
- Có thể cần xác thực 2 yếu tố

### Xử lý lỗi
- Nếu bị chặn, đợi 24h rồi thử lại
- Nếu cần xác thực 2 yếu tố, thực hiện thủ công
- Kiểm tra email spam nếu không nhận được thông báo

## 📁 File output

Sau khi chạy thành công, file `api_keys.txt` sẽ được cập nhật:
```
# Danh sách API Keys cho Gemini
# Mỗi dòng một key, bỏ trống dòng để bỏ qua
# Key hiện tại:
AIzaSyYourNewKey1
AIzaSyYourNewKey2
AIzaSyYourNewKey3
```

## 🔧 Troubleshooting

### Lỗi Chrome WebDriver
```
WebDriverException: Message: unknown error: cannot find Chrome binary
```
**Giải pháp**: Cài đặt Chrome browser hoặc chỉ định đường dẫn Chrome

### Lỗi Proxy
```
Proxy connection failed
```
**Giải pháp**: 
- Kiểm tra proxy có hoạt động không
- Thử proxy khác
- Sử dụng proxy trả phí thay vì miễn phí

### Lỗi xác thực 2 yếu tố
```
ElementNotInteractableException: element not interactable
```
**Giải pháp**: Thực hiện thủ công hoặc tạm thời tắt 2FA

### Lỗi bị chặn
```
Access denied
```
**Giải pháp**: Đợi 24h, sử dụng VPN, hoặc tạo thủ công

## 📞 Hỗ trợ

Nếu gặp vấn đề, hãy:
1. Kiểm tra log lỗi
2. Thử phương pháp thủ công
3. Liên hệ hỗ trợ 