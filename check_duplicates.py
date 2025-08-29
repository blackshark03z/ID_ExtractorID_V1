import pandas as pd
import os

def check_duplicates_in_excel(excel_path):
    """
    Kiểm tra trùng lặp dữ liệu trong file Excel CCCD
    """
    print("🔍 Bắt đầu kiểm tra trùng lặp dữ liệu...")
    
    try:
        # Đọc file Excel
        df = pd.read_excel(excel_path)
        print(f"📊 Tổng số bản ghi: {len(df)}")
        
        # Hiển thị thông tin cơ bản
        print(f"📋 Các cột trong file: {list(df.columns)}")
        print(f"📅 Dữ liệu từ: {df.index[0]} đến {df.index[-1]}")
        
        # Kiểm tra trùng lặp theo từng trường
        duplicates_report = {}
        
        # 1. Kiểm tra trùng lặp CCCD
        if 'CCCD' in df.columns:
            cccd_duplicates = df[df['CCCD'].duplicated(keep=False)]
            if len(cccd_duplicates) > 0:
                duplicates_report['CCCD'] = cccd_duplicates
                print(f"\n⚠️  PHÁT HIỆN TRÙNG LẶP CCCD: {len(cccd_duplicates)} bản ghi")
                for idx, row in cccd_duplicates.iterrows():
                    print(f"   - CCCD: {row['CCCD']} | Họ tên: {row['HoTen']} | Dòng: {idx+2}")
            else:
                print(f"\n✅ Không có trùng lặp CCCD")
        
        # 2. Kiểm tra trùng lặp họ tên
        if 'HoTen' in df.columns:
            ho_ten_duplicates = df[df['HoTen'].duplicated(keep=False)]
            if len(ho_ten_duplicates) > 0:
                duplicates_report['HoTen'] = ho_ten_duplicates
                print(f"\n⚠️  PHÁT HIỆN TRÙNG LẶP HỌ TÊN: {len(ho_ten_duplicates)} bản ghi")
                for idx, row in ho_ten_duplicates.iterrows():
                    print(f"   - Họ tên: {row['HoTen']} | CCCD: {row['CCCD']} | Dòng: {idx+2}")
            else:
                print(f"\n✅ Không có trùng lặp họ tên")
        
        # 3. Kiểm tra trùng lặp hoàn toàn (tất cả các trường)
        all_duplicates = df[df.duplicated(keep=False)]
        if len(all_duplicates) > 0:
            duplicates_report['All'] = all_duplicates
            print(f"\n⚠️  PHÁT HIỆN BẢN GHI TRÙNG LẶP HOÀN TOÀN: {len(all_duplicates)} bản ghi")
            for idx, row in all_duplicates.iterrows():
                print(f"   - Dòng {idx+2}: {row['HoTen']} - {row['CCCD']}")
        else:
            print(f"\n✅ Không có bản ghi trùng lặp hoàn toàn")
        
        # 4. Kiểm tra trùng lặp theo tổ hợp CCCD + Họ tên
        if 'CCCD' in df.columns and 'HoTen' in df.columns:
            df_temp = df.copy()
            df_temp['CCCD_HoTen'] = df_temp['CCCD'].astype(str) + '_' + df_temp['HoTen'].astype(str)
            cccd_ho_ten_duplicates = df_temp[df_temp['CCCD_HoTen'].duplicated(keep=False)]
            if len(cccd_ho_ten_duplicates) > 0:
                duplicates_report['CCCD_HoTen'] = cccd_ho_ten_duplicates
                print(f"\n⚠️  PHÁT HIỆN TRÙNG LẶP CCCD + HỌ TÊN: {len(cccd_ho_ten_duplicates)} bản ghi")
                for idx, row in cccd_ho_ten_duplicates.iterrows():
                    print(f"   - Dòng {idx+2}: {row['HoTen']} - {row['CCCD']}")
            else:
                print(f"\n✅ Không có trùng lặp CCCD + Họ tên")
        
        # 5. Thống kê tổng quan
        print(f"\n📈 THỐNG KÊ TỔNG QUAN:")
        print(f"- Tổng số bản ghi: {len(df)}")
        print(f"- Số CCCD duy nhất: {df['CCCD'].nunique()}")
        print(f"- Số họ tên duy nhất: {df['HoTen'].nunique()}")
        
        # 6. Kiểm tra dữ liệu null/empty
        print(f"\n🔍 KIỂM TRA DỮ LIỆU THIẾU:")
        for col in df.columns:
            null_count = df[col].isnull().sum()
            empty_count = (df[col] == '').sum() if df[col].dtype == 'object' else 0
            total_missing = null_count + empty_count
            if total_missing > 0:
                print(f"   - {col}: {total_missing} bản ghi thiếu ({total_missing/len(df)*100:.1f}%)")
            else:
                print(f"   - {col}: ✅ Đầy đủ")
        
        # 7. Xuất báo cáo chi tiết nếu có trùng lặp
        if duplicates_report:
            report_path = excel_path.replace('.xlsx', '_duplicates_report.xlsx')
            
            with pd.ExcelWriter(report_path, engine='openpyxl') as writer:
                # Sheet tổng quan
                summary_data = {
                    'Loại trùng lặp': [],
                    'Số bản ghi': [],
                    'Mô tả': []
                }
                
                for dup_type, dup_df in duplicates_report.items():
                    summary_data['Loại trùng lặp'].append(dup_type)
                    summary_data['Số bản ghi'].append(len(dup_df))
                    if dup_type == 'CCCD':
                        summary_data['Mô tả'].append('Trùng lặp số CCCD')
                    elif dup_type == 'HoTen':
                        summary_data['Mô tả'].append('Trùng lặp họ tên')
                    elif dup_type == 'CCCD_HoTen':
                        summary_data['Mô tả'].append('Trùng lặp CCCD + Họ tên')
                    else:
                        summary_data['Mô tả'].append('Trùng lặp hoàn toàn')
                
                summary_df = pd.DataFrame(summary_data)
                summary_df.to_excel(writer, sheet_name='Tổng quan', index=False)
                
                # Sheet chi tiết từng loại trùng lặp
                for dup_type, dup_df in duplicates_report.items():
                    sheet_name = f'Trùng_lặp_{dup_type}'[:31]  # Excel giới hạn 31 ký tự
                    dup_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            print(f"\n📄 Báo cáo chi tiết đã được lưu tại: {report_path}")
        
        # 8. Đề xuất xử lý
        if duplicates_report:
            print(f"\n💡 ĐỀ XUẤT XỬ LÝ:")
            print(f"1. Kiểm tra lại nguồn dữ liệu gốc")
            print(f"2. Xác định bản ghi nào là chính xác nhất")
            print(f"3. Xóa các bản ghi trùng lặp không cần thiết")
            print(f"4. Cập nhật lại file Excel sau khi xử lý")
        else:
            print(f"\n🎉 Dữ liệu sạch, không có trùng lặp!")
        
        return duplicates_report
        
    except Exception as e:
        print(f"❌ Lỗi khi kiểm tra file Excel: {e}")
        return None

def main():
    # Đường dẫn file Excel
    excel_path = r"D:\ID Extract\cccd_data_gemini.xlsx"
    
    # Kiểm tra file có tồn tại không
    if not os.path.exists(excel_path):
        print(f"❌ Không tìm thấy file: {excel_path}")
        return
    
    # Thực hiện kiểm tra trùng lặp
    duplicates = check_duplicates_in_excel(excel_path)
    
    if duplicates:
        print(f"\n🔍 Tóm tắt: Phát hiện {len(duplicates)} loại trùng lặp")
    else:
        print(f"\n✅ Tóm tắt: Dữ liệu không có trùng lặp")

if __name__ == "__main__":
    main() 