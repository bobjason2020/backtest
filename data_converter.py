import pandas as pd
import os
from datetime import datetime

SOURCE_DIR = "原始数据"
TARGET_DIR = "可用数据"

def convert_date(date_val):
    if pd.isna(date_val):
        return None
    date_str = str(int(date_val))
    try:
        return datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        return None

def process_file(source_path, target_path, filename):
    print(f"\n处理文件: {filename}")
    
    df = pd.read_excel(source_path)
    
    print(f"  原始列名: {df.columns.tolist()}")
    
    if '日期Date' not in df.columns or '收盘Close' not in df.columns:
        print(f"  警告: 文件缺少必要的列（日期Date 或 收盘Close）")
        return False
    
    result_df = pd.DataFrame()
    
    result_df['日期'] = df['日期Date'].apply(convert_date)
    result_df['收盘价'] = df['收盘Close']
    
    result_df = result_df.dropna(subset=['日期'])
    
    result_df = result_df.sort_values('日期').reset_index(drop=True)
    
    base_name = os.path.splitext(filename)[0]
    target_file = os.path.join(TARGET_DIR, f"{base_name}.xlsx")
    
    result_df.to_excel(target_file, index=False)
    
    print(f"  成功转换!")
    print(f"  记录数: {len(result_df)}")
    print(f"  日期范围: {result_df['日期'].min().strftime('%Y-%m-%d')} ~ {result_df['日期'].max().strftime('%Y-%m-%d')}")
    print(f"  输出文件: {target_file}")
    
    return True

def main():
    print("=" * 60)
    print("数据格式转换工具")
    print("=" * 60)
    print(f"源目录: {SOURCE_DIR}")
    print(f"目标目录: {TARGET_DIR}")
    
    if not os.path.exists(SOURCE_DIR):
        print(f"错误: 源目录 '{SOURCE_DIR}' 不存在")
        return
    
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        print(f"创建目标目录: {TARGET_DIR}")
    
    xlsx_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.xlsx')]
    
    if not xlsx_files:
        print("源目录中没有找到xlsx文件")
        return
    
    print(f"\n找到 {len(xlsx_files)} 个xlsx文件")
    
    success_count = 0
    for filename in xlsx_files:
        source_path = os.path.join(SOURCE_DIR, filename)
        try:
            if process_file(source_path, os.path.join(TARGET_DIR, filename), filename):
                success_count += 1
        except Exception as e:
            print(f"  处理失败: {e}")
    
    print("\n" + "=" * 60)
    print(f"转换完成! 成功: {success_count}/{len(xlsx_files)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
