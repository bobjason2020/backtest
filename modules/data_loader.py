import pandas as pd


def load_excel_file(uploaded_file):
    try:
        df = pd.read_excel(uploaded_file)
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期').reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, str(e)


def validate_data(df):
    required_columns = ['日期', '收盘价']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return False, f"缺少必要列: {', '.join(missing)}"
    if len(df) == 0:
        return False, "数据为空"
    return True, None


def get_date_range(df):
    min_date = df['日期'].min().date()
    max_date = df['日期'].max().date()
    total_days = (max_date - min_date).days
    max_years = total_days / 365.0
    return {
        'min_date': min_date,
        'max_date': max_date,
        'total_days': total_days,
        'max_years': max_years,
        'record_count': len(df)
    }
