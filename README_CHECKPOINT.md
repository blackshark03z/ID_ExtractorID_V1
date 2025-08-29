# 🔄 Tính năng Checkpoint - Tiếp tục từ chỗ dừng

## 📋 Tổng quan

Tính năng **Checkpoint** cho phép script tiếp tục xử lý từ chỗ dừng khi gặp lỗi hoặc hết quota API, thay vì phải chạy lại từ đầu.

## 🎯 Lợi ích

### ✅ **Tiết kiệm thời gian**
- Không cần xử lý lại các folder đã hoàn thành
- Tiếp tục ngay từ folder tiếp theo

### ✅ **Tiết kiệm API quota**
- Không gọi API lại cho các folder đã xử lý
- Chỉ sử dụng quota cho phần còn lại

### ✅ **Xử lý lỗi thông minh**
- Tự động lưu tiến độ khi gặp lỗi
- Có thể dừng và tiếp tục bất cứ lúc nào

## 🔧 Cách hoạt động

### **1. Lưu checkpoint**
```python
# Sau mỗi folder được xử lý
processed_folders.append(folder_path)
save_checkpoint(processed_folders, zip_path)
```

### **2. Tải checkpoint**
```python
# Khi bắt đầu script
checkpoint_data = load_checkpoint()
if checkpoint_data and checkpoint_data.get('zip_file') == zip_path:
    # Tiếp tục từ checkpoint
    processed_folders = checkpoint_data.get('processed_folders', [])
    start_index = len(processed_folders)
```

### **3. Xóa checkpoint**
```python
# Sau khi hoàn thành tất cả
clear_checkpoint()
```

## 📁 File checkpoint

### **checkpoint.json**
```json
{
  "zip_file": "D:/ID Extract/Input_file/Test.zip",
  "processed_folders": [
    "D:/ID Extract/extracted_all/Test/AN CHI THANH",
    "D:/ID Extract/extracted_all/Test/BON VAN CHANH"
  ],
  "timestamp": "2024-01-15T10:30:00",
  "current_key_index": 1
}
```

## 🚀 Các trường hợp sử dụng

### **1. Hết quota API**
```
❌ Tất cả API keys đã hết quota
💾 Tiến độ đã được lưu. Có thể tiếp tục sau.
```

**Giải pháp:**
- Tạo thêm API keys
- Chạy lại script → Tự động tiếp tục từ chỗ dừng

### **2. Lỗi mạng/Timeout**
```
❌ Lỗi kết nối: Connection timeout
💾 Tiến độ đã được lưu. Có thể tiếp tục sau.
```

**Giải pháp:**
- Kiểm tra kết nối mạng
- Chạy lại script → Tự động tiếp tục

### **3. Dừng thủ công (Ctrl+C)**
```
⚠️  Đã dừng xử lý. Tiến độ đã được lưu.
💡 Để tiếp tục, chạy lại script với cùng file zip.
```

**Giải pháp:**
- Chạy lại script → Tự động tiếp tục

### **4. Lỗi xử lý folder**
```
❌ Không thể trích xuất thông tin từ folder X
💾 Tiến độ đã được lưu. Có thể tiếp tục sau.
```

**Giải pháp:**
- Script vẫn tiếp tục với folder tiếp theo
- Folder lỗi được đánh dấu đã xử lý

## 🧪 Test tính năng

### **Chạy script test:**
```bash
python test_checkpoint.py
```

### **Các chức năng test:**
1. **Tạo checkpoint demo** - Tạo file checkpoint mẫu
2. **Xem thông tin checkpoint** - Hiển thị chi tiết checkpoint
3. **Xóa checkpoint** - Xóa file checkpoint

## 📊 Thống kê checkpoint

### **Thông tin được lưu:**
- ✅ File zip đang xử lý
- ✅ Danh sách folders đã xử lý
- ✅ API key hiện tại đang sử dụng
- ✅ Thời gian tạo checkpoint

### **Thông tin KHÔNG được lưu:**
- ❌ Dữ liệu đã trích xuất (để tránh trùng lặp)
- ❌ File Excel tạm thời
- ❌ Thông tin nhạy cảm

## ⚠️ Lưu ý quan trọng

### **1. File zip phải giống nhau**
- Checkpoint chỉ hoạt động với cùng file zip
- Nếu đổi file zip → Bắt đầu từ đầu

### **2. Không xóa file checkpoint**
- File `checkpoint.json` chứa tiến độ
- Xóa file → Mất tiến độ

### **3. Backup dữ liệu**
- Luôn backup file Excel đã tạo
- Checkpoint chỉ lưu tiến độ, không lưu kết quả

## 🔄 Quy trình sử dụng

### **Lần đầu chạy:**
```bash
python extract_gemini.py
# Chọn file zip → Bắt đầu xử lý từ đầu
```

### **Gặp lỗi/quota:**
```bash
# Script tự động lưu checkpoint và dừng
# Tạo thêm API keys hoặc sửa lỗi
```

### **Tiếp tục:**
```bash
python extract_gemini.py
# Chọn cùng file zip → Tự động tiếp tục từ checkpoint
```

## 📈 Hiệu quả

### **Trước khi có checkpoint:**
- ❌ Hết quota → Chạy lại từ đầu
- ❌ Lỗi mạng → Chạy lại từ đầu  
- ❌ Dừng thủ công → Chạy lại từ đầu

### **Sau khi có checkpoint:**
- ✅ Hết quota → Tiếp tục từ chỗ dừng
- ✅ Lỗi mạng → Tiếp tục từ chỗ dừng
- ✅ Dừng thủ công → Tiếp tục từ chỗ dừng

## 🎉 Kết luận

Tính năng checkpoint giúp:
- **Tiết kiệm 80-90% thời gian** khi gặp lỗi
- **Tiết kiệm API quota** đáng kể
- **Xử lý file lớn** một cách an toàn
- **Trải nghiệm người dùng** tốt hơn 