#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for ID Extractor
Tự động tạo các thư mục cần thiết và file cấu hình
"""

import os
import sys

def create_directories():
    """Tạo các thư mục cần thiết"""
    directories = [
        'Input_file',
        'extracted_all', 
        'Excel'
    ]
    
    print("🔧 Đang tạo các thư mục cần thiết...")
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✅ Đã tạo thư mục: {directory}/")
        else:
            print(f"ℹ️  Thư mục đã tồn tại: {directory}/")

def create_api_keys_template():
    """Tạo file api_keys.txt mẫu nếu chưa có"""
    if not os.path.exists('api_keys.txt'):
        print("\n🔑 Tạo file api_keys.txt mẫu...")
        with open('api_keys.txt', 'w', encoding='utf-8') as f:
            f.write("# Thêm các Gemini API keys vào đây (mỗi key một dòng)\n")
            f.write("# Ví dụ:\n")
            f.write("# AIzaSyDzvw-vLXTOy0GoSx3Z8K_xyXUksO-wesQ\n")
            f.write("# AIzaSyB1234567890abcdefghijklmnop\n")
        print("✅ Đã tạo file api_keys.txt")
        print("⚠️  Vui lòng thêm API keys thực vào file này!")
    else:
        print("ℹ️  File api_keys.txt đã tồn tại")

def create_sample_files():
    """Tạo các file mẫu tùy chọn"""
    
    # Tạo gmail_list.txt mẫu
    if not os.path.exists('gmail_list.txt'):
        print("\n📧 Tạo file gmail_list.txt mẫu...")
        with open('gmail_list.txt', 'w', encoding='utf-8') as f:
            f.write("# Danh sách Gmail để tạo API keys tự động\n")
            f.write("# Format: Gmail|Password\n")
            f.write("# Ví dụ:\n")
            f.write("# example1@gmail.com|password123\n")
            f.write("# example2@gmail.com|password456\n")
        print("✅ Đã tạo file gmail_list.txt")
    
    # Tạo proxy_list.txt mẫu
    if not os.path.exists('proxy_list.txt'):
        print("\n🌐 Tạo file proxy_list.txt mẫu...")
        with open('proxy_list.txt', 'w', encoding='utf-8') as f:
            f.write("# Danh sách proxy (tùy chọn)\n")
            f.write("# Format: ip:port hoặc ip:port:username:password\n")
            f.write("# Ví dụ:\n")
            f.write("# 192.168.1.1:8080\n")
            f.write("# 10.0.0.1:3128:user:pass\n")
        print("✅ Đã tạo file proxy_list.txt")

def show_next_steps():
    """Hiển thị các bước tiếp theo"""
    print("\n" + "="*50)
    print("🎉 THIẾT LẬP HOÀN TẤT!")
    print("="*50)
    print("\n📋 Các bước tiếp theo:")
    print("1. Thêm Gemini API keys vào file api_keys.txt")
    print("2. Đặt file ZIP chứa ảnh CCCD vào thư mục Input_file/")
    print("3. Chạy chương trình:")
    print("   - GUI: python extract_gui.py")
    print("   - Command line: python extract_gemini.py")
    print("\n📚 Xem README.md để biết thêm chi tiết")
    print("="*50)

def main():
    """Hàm chính"""
    print("🚀 ID Extractor - Setup Script")
    print("="*50)
    
    try:
        # Tạo thư mục
        create_directories()
        
        # Tạo file cấu hình
        create_api_keys_template()
        create_sample_files()
        
        # Hiển thị hướng dẫn
        show_next_steps()
        
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        print("Vui lòng chạy với quyền administrator hoặc kiểm tra quyền ghi file")
        sys.exit(1)

if __name__ == "__main__":
    main() 