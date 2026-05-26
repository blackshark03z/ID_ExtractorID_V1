# Tool OCR CCCD Việt Nam (Sử dụng AI Gemini)

Công cụ tự động hóa việc nhận diện và trích xuất thông tin Căn cước công dân (CCCD) Việt Nam từ ảnh hoặc file PDF, sử dụng sức mạnh của Google Gemini 2.5 Flash để đạt độ chính xác cao và thông minh hơn hẳn các phương pháp OCR truyền thống.

## 🌟 Tính năng nổi bật

- **Nhận diện chính xác**: Không bị nhầm lẫn giữa chữ O/Q hay số 0 như các tool truyền thống. Tuyệt đối không lấy nhầm tên người ký (Cục trưởng) ở mặt sau làm tên chủ thẻ.
- **Quét đệ quy thông minh**: Tự động duyệt đệ quy ở mọi cấp độ thư mục con để tìm ra các thư mục trực tiếp chứa ảnh/PDF thực tế của từng cá nhân. Tự động bỏ qua các thư mục backup, copy, temp để tránh quét trùng lặp dữ liệu.
- **Tự động trích xuất từ PDF**: Hỗ trợ nhận diện các file PDF chứa ảnh scan thẻ CCCD (kể cả PDF nhiều trang chứa hợp đồng và CCCD xen kẽ). Tool tự động trích xuất các trang thành ảnh có độ phân giải cao để gửi đi xử lý.
- **Tránh trùng lặp tên file (Zero Collision)**: Cơ chế tạo slug thông minh không giới hạn độ dài giúp giải nén đồng thời nhiều file PDF có chung tiền tố dài trong cùng một thư mục mà không bị ghi đè dữ liệu.
- **Tự động ghép cặp & đổi tên**: Thông minh nhận biết đâu là mặt trước, đâu là mặt sau từ một mớ hỗn độn (nhiều ảnh trong 1 folder, hoặc file PDF) và tự động chuẩn hóa đổi tên thành `front.jpg` và `back.jpg`.
- **Đọc trực tiếp file ZIP**: Không cần giải nén thủ công! Chỉ cần ném file `.zip` chứa các folder con vào thư mục `input`, tool sẽ tự bung nén và tìm ra các thư mục con chứa dữ liệu một cách tối ưu.
- **Xoay vòng API Key**: Hỗ trợ cung cấp nhiều API Key cùng lúc để tránh việc bị Google giới hạn rate limit (chống sập tool giữa chừng do quá tải).

## 📋 Yêu cầu hệ thống

- Hệ điều hành: Windows / macOS / Linux
- Python: Phiên bản 3.9 trở lên
- Có kết nối Internet để gọi Google Gemini API

## 🚀 Hướng dẫn cài đặt

1. **Clone mã nguồn (hoặc tải thư mục code)**:
   Mở terminal / cmd (PowerShell) tại thư mục project `ID_Extractor-1`.

2. **Cài đặt thư viện cần thiết**:
   Chạy lệnh sau để cài các package vào Python:
   ```bash
   pip install -r cccd_ocr_tool\requirements.txt
   ```
   *(Thư viện bao gồm: `google-generativeai`, `PyMuPDF`, `Pillow`, `openpyxl`)*

3. **Cấu hình API Key**:
   - Truy cập [Google AI Studio](https://aistudio.google.com/app/apikey) để lấy API Key miễn phí.
   - Mở file `api_keys.txt` ở thư mục gốc (ngang hàng với `input`), dán API Key của bạn vào đó.
   - *Mẹo: Nếu bạn phải xử lý hàng nghìn ảnh, hãy tạo nhiều API Key từ nhiều tài khoản Google khác nhau và dán mỗi key trên 1 dòng trong file `api_keys.txt`. Tool sẽ tự động xoay vòng qua các key này khi bị giới hạn Quota.*

## 💡 Cách sử dụng

**Cách 1: Quét từ thư mục / file ZIP có sẵn trong thư mục `input`**
1. Đặt các folder chứa ảnh/PDF của từng người hoặc ném thẳng file `.zip` (chứa dữ liệu) vào thư mục `input`.
2. Mở Terminal và chạy lệnh:
   ```bash
   python cccd_ocr_tool\main.py
   ```
3. Một menu tương tác sẽ hiện ra liệt kê các folder và file zip có trong `input`. Gõ số tương ứng (hoặc chọn `0` để quét tất cả) và nhấn Enter.

**Cách 2: Quét trực tiếp bằng đường dẫn**
Bạn có thể bỏ qua menu và truyền trực tiếp đường dẫn file ZIP hoặc thư mục bất kỳ từ bên ngoài qua terminal:
```bash
python cccd_ocr_tool\main.py "C:\Users\Name\Downloads\DuLieuCCCD.zip"
```

## 📊 Kết quả đầu ra

1. **File Excel tổng hợp (`cccd_extract.xlsx`)**: Chứa toàn bộ các thông tin đã trích xuất gồm (Họ tên, Số CCCD, Ngày sinh, Giới tính, Nơi thường trú, Ngày hết hạn...). File Excel sẽ được xuất ngay bên cạnh các folder con.
2. **Chuẩn hóa thư mục**: Bên trong thư mục của từng người, bạn sẽ thấy tool tự đổi tên 2 bức ảnh (hoặc ảnh xuất ra từ PDF) đúng nhất thành `front.jpg` và `back.jpg`. Các ảnh lấy từ PDF thừa sẽ bị xóa tự động.
3. **Ghi chú (`ocr_note.txt`)**: Mỗi thư mục con sẽ có một file text ghi lại dữ liệu được lưu, kèm thông báo lỗi nếu ảnh bị nhòe không đọc được thông tin.

## ⚙️ Lưu ý
- API Gemini miễn phí hiện tại cho phép 15 request / phút hoặc ít hơn tùy thời điểm. Tool đã được thiết kế gộp (batch) toàn bộ ảnh của một người vào 1 request duy nhất để tối ưu hóa quota. Nếu bạn thấy tool dừng lại báo "Đang đợi 10s...", đó là do đã chạm ngưỡng limit, nó sẽ tự động chạy tiếp.