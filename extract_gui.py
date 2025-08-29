#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI Application cho hệ thống Extract CCCD
Sử dụng tkinter với giao diện hiện đại
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import sys
import json
from datetime import datetime
import queue
import time

# Import các module từ extract_gemini.py
try:
    from extract_gemini import (
        load_api_keys, switch_to_next_api_key, get_current_api_key,
        save_checkpoint, load_checkpoint, clear_checkpoint,
        process_cccd_folder, extract_info_with_gemini,
        current_key_index
    )
except ImportError as e:
    print(f"Lỗi import: {e}")
    # Fallback - sẽ import sau khi GUI khởi tạo
    pass

class CCCDExtractGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 CCCD Extract System - GUI")
        self.root.geometry("1000x700")
        self.root.configure(bg='#f0f0f0')
        
        # Biến global
        self.processing = False
        self.log_queue = queue.Queue()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Sẵn sàng")
        
        # API keys
        self.api_keys_list = load_api_keys()
        self.current_key_index = 0
        
        # Setup GUI
        self.setup_gui()
        self.setup_styles()
        
        # Start log monitor
        self.monitor_log()
    
    def setup_styles(self):
        """Thiết lập style cho GUI"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure styles
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), foreground='#34495e')
        style.configure('Status.TLabel', font=('Arial', 10), foreground='#7f8c8d')
        style.configure('Success.TLabel', font=('Arial', 10), foreground='#27ae60')
        style.configure('Error.TLabel', font=('Arial', 10), foreground='#e74c3c')
        
        # Button styles
        style.configure('Primary.TButton', font=('Arial', 10, 'bold'))
        style.configure('Success.TButton', font=('Arial', 10, 'bold'))
        style.configure('Danger.TButton', font=('Arial', 10, 'bold'))
    
    def setup_gui(self):
        """Thiết lập giao diện chính"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🚀 CCCD Extract System", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Left Panel - Controls
        self.setup_left_panel(main_frame)
        
        # Right Panel - Log & Progress
        self.setup_right_panel(main_frame)
        
        # Bottom Panel - Status & Actions
        self.setup_bottom_panel(main_frame)
    
    def setup_left_panel(self, parent):
        """Thiết lập panel bên trái - Controls"""
        left_frame = ttk.LabelFrame(parent, text="⚙️ Cài đặt", padding="10")
        left_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        
        # File Selection
        file_frame = ttk.LabelFrame(left_frame, text="📁 Chọn file ZIP", padding="5")
        file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="File ZIP:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var, state='readonly')
        self.file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 5), pady=2)
        
        ttk.Button(file_frame, text="📂 Browse", command=self.browse_file, style='Primary.TButton').grid(row=0, column=2, pady=2)
        
        # API Keys Status
        api_frame = ttk.LabelFrame(left_frame, text="🔑 API Keys", padding="5")
        api_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        api_frame.columnconfigure(0, weight=1)
        
        self.api_status_label = ttk.Label(api_frame, text=f"API Keys: {len(self.api_keys_list)}", style='Status.TLabel')
        self.api_status_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.current_key_label = ttk.Label(api_frame, text=f"Key hiện tại: 1/{len(self.api_keys_list)}", style='Status.TLabel')
        self.current_key_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        
        ttk.Button(api_frame, text="🔄 Switch Key", command=self.switch_api_key, style='Primary.TButton').grid(row=2, column=0, pady=5)
        
        # Settings
        settings_frame = ttk.LabelFrame(left_frame, text="⚙️ Cài đặt", padding="5")
        settings_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(0, weight=1)
        
        # Test mode
        self.test_mode_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="🧪 Test Mode (chỉ xử lý 5 folder)", 
                       variable=self.test_mode_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Auto delete expired
        self.auto_delete_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="🗑️ Tự động xóa CCCD hết hạn", 
                       variable=self.auto_delete_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        # Checkpoint
        self.use_checkpoint_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="💾 Sử dụng Checkpoint", 
                       variable=self.use_checkpoint_var).grid(row=2, column=0, sticky=tk.W, pady=2)
        
        # Actions
        actions_frame = ttk.LabelFrame(left_frame, text="🎯 Hành động", padding="5")
        actions_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        actions_frame.columnconfigure(0, weight=1)
        
        self.start_button = ttk.Button(actions_frame, text="▶️ Bắt đầu xử lý", 
                                      command=self.start_processing, style='Success.TButton')
        self.start_button.grid(row=0, column=0, pady=5)
        
        self.stop_button = ttk.Button(actions_frame, text="⏹️ Dừng", 
                                     command=self.stop_processing, style='Danger.TButton', state='disabled')
        self.stop_button.grid(row=1, column=0, pady=5)
        
        ttk.Button(actions_frame, text="🗑️ Xóa Checkpoint", 
                  command=self.clear_checkpoint_gui).grid(row=2, column=0, pady=5)
        
        ttk.Button(actions_frame, text="📂 Mở thư mục Excel", 
                  command=self.open_excel_folder).grid(row=3, column=0, pady=5)
        
        ttk.Button(actions_frame, text="🔧 Kiểm tra API Keys", 
                  command=self.test_api_keys).grid(row=4, column=0, pady=5)
    
    def setup_right_panel(self, parent):
        """Thiết lập panel bên phải - Log & Progress"""
        right_frame = ttk.Frame(parent)
        right_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
        # Progress
        progress_frame = ttk.LabelFrame(right_frame, text="📊 Tiến độ", padding="5")
        progress_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0%", style='Status.TLabel')
        self.progress_label.grid(row=1, column=0, pady=2)
        
        # Log
        log_frame = ttk.LabelFrame(right_frame, text="📝 Log", padding="5")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, width=60, 
                                                 font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # Log controls
        log_controls = ttk.Frame(log_frame)
        log_controls.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Button(log_controls, text="🗑️ Clear Log", 
                  command=self.clear_log).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(log_controls, text="💾 Save Log", 
                  command=self.save_log).grid(row=0, column=1, padx=5)
    
    def setup_bottom_panel(self, parent):
        """Thiết lập panel dưới - Status & Actions"""
        bottom_frame = ttk.Frame(parent)
        bottom_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        bottom_frame.columnconfigure(1, weight=1)
        
        # Status
        status_frame = ttk.LabelFrame(bottom_frame, text="📊 Trạng thái", padding="5")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, style='Status.TLabel')
        self.status_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        
        # Statistics
        stats_frame = ttk.LabelFrame(bottom_frame, text="📈 Thống kê", padding="5")
        stats_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        stats_frame.columnconfigure(0, weight=1)
        
        self.stats_label = ttk.Label(stats_frame, text="Chưa có dữ liệu", style='Status.TLabel')
        self.stats_label.grid(row=0, column=0, sticky=tk.W, pady=2)
    
    def browse_file(self):
        """Chọn file ZIP"""
        file_path = filedialog.askopenfilename(
            title="Chọn file ZIP",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            self.log_message(f"📁 Đã chọn file: {os.path.basename(file_path)}")
    
    def switch_api_key(self):
        """Chuyển API key"""
        if self.api_keys_list:
            switch_to_next_api_key()
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys_list)
            self.current_key_label.config(text=f"Key hiện tại: {self.current_key_index + 1}/{len(self.api_keys_list)}")
            self.log_message(f"🔄 Chuyển sang API key {self.current_key_index + 1}/{len(self.api_keys_list)}")
    
    def clear_checkpoint_gui(self):
        """Xóa checkpoint từ GUI"""
        if messagebox.askyesno("Xác nhận", "Bạn có chắc muốn xóa checkpoint?"):
            clear_checkpoint()
            self.log_message("🗑️ Đã xóa checkpoint")
    
    def clear_log(self):
        """Xóa log"""
        self.log_text.delete(1.0, tk.END)
        self.log_message("🗑️ Đã xóa log")
    
    def save_log(self):
        """Lưu log"""
        file_path = filedialog.asksaveasfilename(
            title="Lưu log",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log_message(f"💾 Đã lưu log: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu log: {e}")
    
    def log_message(self, message):
        """Thêm message vào log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Add to queue for thread-safe logging
        self.log_queue.put(log_entry)
    
    def monitor_log(self):
        """Monitor log queue và update GUI"""
        try:
            while True:
                log_entry = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, log_entry)
                self.log_text.see(tk.END)
                self.log_text.update_idletasks()
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.monitor_log)
    
    def start_processing(self):
        """Bắt đầu xử lý"""
        if not self.file_path_var.get():
            messagebox.showerror("Lỗi", "Vui lòng chọn file ZIP!")
            return
        
        if not self.api_keys_list:
            messagebox.showerror("Lỗi", "Không có API key nào!")
            return
        
        if self.processing:
            return
        
        # Start processing in separate thread
        self.processing = True
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.status_var.set("Đang xử lý...")
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self.process_file)
        self.processing_thread.daemon = True
        self.processing_thread.start()
    
    def stop_processing(self):
        """Dừng xử lý"""
        if self.processing:
            self.processing = False
            self.status_var.set("Đã dừng")
            self.log_message("⚠️ Đã dừng xử lý theo yêu cầu")
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
    
    def process_file(self):
        """Xử lý file trong thread riêng"""
        try:
            zip_path = self.file_path_var.get()
            self.log_message(f"🚀 Bắt đầu xử lý: {os.path.basename(zip_path)}")
            
            # Import các module cần thiết
            import zipfile
            import glob
            import pandas as pd
            from datetime import datetime, timedelta
            import shutil
            
            # Tạo tên thư mục extract dựa trên tên file zip
            zip_name = os.path.splitext(os.path.basename(zip_path))[0]
            base_extract_dir = os.path.join(os.path.dirname(zip_path), "extracted_all")
            extract_dir = os.path.join(base_extract_dir, zip_name)
            
            self.log_message(f"📦 File zip: {zip_path}")
            self.log_message(f"📁 Thư mục extract: {extract_dir}")
            
            # Tạo folder tổng nếu chưa có
            if not os.path.exists(base_extract_dir):
                os.makedirs(base_extract_dir)
                self.log_message(f"📁 Đã tạo folder tổng: {base_extract_dir}")
            
            # Giải nén zip nếu chưa có thư mục extracted
            if not os.path.exists(extract_dir):
                self.log_message("📦 Đang giải nén file zip...")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            
            # Tìm tất cả folder con trong extracted
            all_person_folders = []
            for root, dirs, files in os.walk(extract_dir):
                for dir_name in dirs:
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
            if self.test_mode_var.get():
                all_person_folders = all_person_folders[:5]
                self.log_message("⚠️ CHẠY Ở CHẾ ĐỘ TEST - Chỉ xử lý 5 folder đầu tiên")
            
            self.log_message(f"📁 Tìm thấy {len(all_person_folders)} folder cần xử lý")
            
            # Tải checkpoint nếu được bật
            processed_folders = []
            if self.use_checkpoint_var.get():
                checkpoint_data = load_checkpoint()
                if checkpoint_data and checkpoint_data.get('zip_file') == zip_path:
                    processed_folders = checkpoint_data.get('processed_folders', [])
                    start_index = len(processed_folders)
                    self.log_message(f"🔄 Tiếp tục từ folder {start_index + 1}/{len(all_person_folders)}")
                    
                    # Khôi phục API key index
                    global current_key_index
                    current_key_index = checkpoint_data.get('current_key_index', 0)
                    self.log_message(f"🔑 Sử dụng API key {current_key_index + 1}/{len(self.api_keys_list)}")
                else:
                    start_index = 0
                    self.log_message("🚀 Bắt đầu xử lý từ đầu")
            else:
                start_index = 0
                self.log_message("🚀 Bắt đầu xử lý từ đầu")
            
            # Xử lý từng folder
            rows = []
            for i in range(start_index, len(all_person_folders)):
                if not self.processing:
                    break
                
                folder_path = all_person_folders[i]
                person_folder = os.path.basename(folder_path)
                
                # Update progress
                progress = (i + 1) / len(all_person_folders) * 100
                self.progress_var.set(progress)
                self.progress_label.config(text=f"{progress:.1f}%")
                
                self.log_message(f"\n[{i + 1}/{len(all_person_folders)}] Đang xử lý folder: {person_folder}")
                
                # Xử lý folder
                info = process_cccd_folder(folder_path)
                
                if info and any(info.values()):
                    # Kiểm tra CCCD có hết hạn không
                    if self.auto_delete_var.get() and 'NgayHetHan' in info and info['NgayHetHan']:
                        try:
                            expiry_date = datetime.strptime(info['NgayHetHan'], '%d/%m/%Y')
                            today = datetime.now()
                            
                            if expiry_date < today:
                                self.log_message(f"  ⚠️ CCCD đã hết hạn ({info['NgayHetHan']}) - Xóa folder")
                                shutil.rmtree(folder_path)
                                processed_folders.append(folder_path)
                                if self.use_checkpoint_var.get():
                                    save_checkpoint(processed_folders, zip_path)
                                continue
                            elif expiry_date < today + timedelta(days=30):
                                self.log_message(f"  ⚠️ CCCD sắp hết hạn ({info['NgayHetHan']})")
                        except:
                            pass
                    
                    rows.append(info)
                    self.log_message(f"  ✅ Đã trích xuất: {info.get('HoTen', 'N/A')} - {info.get('CCCD', 'N/A')}")
                    
                    # Update statistics
                    self.stats_label.config(text=f"Đã xử lý: {len(rows)}/{len(all_person_folders)}")
                else:
                    self.log_message(f"  ❌ Không thể trích xuất thông tin từ {person_folder}")
                
                # Lưu checkpoint sau mỗi folder
                processed_folders.append(folder_path)
                if self.use_checkpoint_var.get():
                    save_checkpoint(processed_folders, zip_path)
                
                # Delay nhỏ để tránh rate limit
                if i < len(all_person_folders) - 1:
                    time.sleep(1)
            
            # Hoàn thành - xóa checkpoint
            if self.use_checkpoint_var.get():
                clear_checkpoint()
            
            # Xuất Excel
            if rows:
                df = pd.DataFrame(rows)
                columns_order = ["CCCD", "HoTen", "NgaySinh", "GioiTinh", "DiaChi", "NoiCap", "NgayCap", "NgayHetHan"]
                df = df.reindex(columns=columns_order)
                
                # Tạo folder Excel nếu chưa có
                excel_dir = os.path.join(os.path.dirname(zip_path), "Excel")
                if not os.path.exists(excel_dir):
                    os.makedirs(excel_dir)
                    self.log_message(f"📁 Đã tạo thư mục Excel: {excel_dir}")
                
                excel_path = os.path.join(excel_dir, f"cccd_data_{zip_name}.xlsx")
                df.to_excel(excel_path, index=False)
                
                self.log_message(f"\n🎉 Hoàn thành! Đã trích xuất {len(rows)} bản ghi")
                self.log_message(f"📄 File Excel: {excel_path}")
                
                # Hiển thị thống kê
                self.log_message(f"\n📊 Thống kê:")
                self.log_message(f"- Tổng số bản ghi: {len(rows)}")
                self.log_message(f"- Có CCCD: {df['CCCD'].notna().sum()}")
                self.log_message(f"- Có họ tên: {df['HoTen'].notna().sum()}")
                self.log_message(f"- Có ngày sinh: {df['NgaySinh'].notna().sum()}")
                self.log_message(f"- Có giới tính: {df['GioiTinh'].notna().sum()}")
                self.log_message(f"- Có địa chỉ: {df['DiaChi'].notna().sum()}")
                self.log_message(f"- Có nơi cấp: {df['NoiCap'].notna().sum()}")
                self.log_message(f"- Có ngày cấp: {df['NgayCap'].notna().sum()}")
                self.log_message(f"- Có ngày hết hạn: {df['NgayHetHan'].notna().sum()}")
                
                # Update final statistics
                self.stats_label.config(text=f"Hoàn thành: {len(rows)} bản ghi | File: {os.path.basename(excel_path)}")
                
                # Hiển thị dữ liệu mẫu
                self.log_message(f"\n📋 Dữ liệu mẫu:")
                for i, row in df.iterrows():
                    self.log_message(f"  {i+1}. {row['HoTen']} - {row['CCCD']} - {row['GioiTinh']}")
            else:
                self.log_message("❌ Không có dữ liệu nào được trích xuất!")
                self.stats_label.config(text="Không có dữ liệu được trích xuất")
            
        except Exception as e:
            self.log_message(f"❌ Lỗi: {e}")
            messagebox.showerror("Lỗi", f"Lỗi xử lý: {e}")
        finally:
            self.processing = False
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled')
            self.status_var.set("Hoàn thành")
    
    def open_excel_folder(self):
        """Mở thư mục Excel"""
        try:
            if self.file_path_var.get():
                excel_dir = os.path.join(os.path.dirname(self.file_path_var.get()), "Excel")
                if os.path.exists(excel_dir):
                    os.startfile(excel_dir)
                    self.log_message(f"📂 Đã mở thư mục Excel: {excel_dir}")
                else:
                    messagebox.showinfo("Thông báo", "Thư mục Excel chưa tồn tại!")
            else:
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn file ZIP trước!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể mở thư mục: {e}")
    
    def test_api_keys(self):
        """Kiểm tra API keys"""
        if not self.api_keys_list:
            messagebox.showwarning("Cảnh báo", "Không có API key nào!")
            return
        
        self.log_message("🔧 Bắt đầu kiểm tra API keys...")
        
        # Test trong thread riêng
        test_thread = threading.Thread(target=self._test_api_keys_thread)
        test_thread.daemon = True
        test_thread.start()
    
    def _test_api_keys_thread(self):
        """Test API keys trong thread riêng"""
        try:
            import requests
            
            for i, api_key in enumerate(self.api_keys_list):
                if not self.processing:  # Sử dụng processing flag để dừng
                    break
                
                self.log_message(f"🔑 Đang test API key {i + 1}/{len(self.api_keys_list)}")
                
                # Test với một request đơn giản
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                data = {
                    "contents": [{
                        "role": "user",
                        "parts": [{"text": "Hello"}]
                    }]
                }
                
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=10)
                    if response.status_code == 200:
                        self.log_message(f"  ✅ API key {i + 1} hoạt động tốt")
                    elif response.status_code == 429:
                        self.log_message(f"  ⚠️ API key {i + 1} hết quota")
                    else:
                        self.log_message(f"  ❌ API key {i + 1} lỗi: {response.status_code}")
                except Exception as e:
                    self.log_message(f"  ❌ API key {i + 1} lỗi kết nối: {e}")
                
                time.sleep(1)  # Delay giữa các test
            
            self.log_message("🔧 Hoàn thành kiểm tra API keys!")
            
        except Exception as e:
            self.log_message(f"❌ Lỗi kiểm tra API keys: {e}")
    
    def on_closing(self):
        """Xử lý khi đóng GUI"""
        if self.processing:
            if messagebox.askyesno("Xác nhận", "Đang xử lý. Bạn có chắc muốn thoát?"):
                self.processing = False
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    """Main function"""
    root = tk.Tk()
    app = CCCDExtractGUI(root)
    
    # Center window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    # Xử lý đóng window
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    root.mainloop()

if __name__ == "__main__":
    main() 