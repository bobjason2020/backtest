import pandas as pd
import streamlit as st
import hashlib
import os


def _get_file_hash(uploaded_file):
    if isinstance(uploaded_file, str):
        if os.path.exists(uploaded_file):
            with open(uploaded_file, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        return uploaded_file
    else:
        pos = uploaded_file.tell()
        uploaded_file.seek(0)
        content = uploaded_file.read()
        uploaded_file.seek(pos)
        return hashlib.md5(content).hexdigest()


@st.cache_data(ttl=3600, show_spinner=False)
def _load_excel_from_bytes(file_bytes):
    import io
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期').reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, str(e)


def load_excel_file(uploaded_file):
    try:
        if isinstance(uploaded_file, str):
            with open(uploaded_file, 'rb') as f:
                file_bytes = f.read()
        else:
            pos = uploaded_file.tell()
            uploaded_file.seek(0)
            file_bytes = uploaded_file.read()
            uploaded_file.seek(pos)
        
        return _load_excel_from_bytes(file_bytes)
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


def check_valuation_data(df):
    has_pe = 'PE' in df.columns
    has_pb = 'PB' in df.columns
    valuation_columns = []
    if has_pe:
        valuation_columns.append('PE')
    if has_pb:
        valuation_columns.append('PB')
    return {
        'has_valuation': has_pe or has_pb,
        'valuation_columns': valuation_columns,
        'has_pe': has_pe,
        'has_pb': has_pb
    }


def get_date_range(df):
    min_date = df['日期'].min().date()
    max_date = df['日期'].max().date()
    total_days = (max_date - min_date).days
    max_years = total_days / 365.0
    valuation_info = check_valuation_data(df)
    return {
        'min_date': min_date,
        'max_date': max_date,
        'total_days': total_days,
        'max_years': max_years,
        'record_count': len(df),
        'has_valuation': valuation_info['has_valuation'],
        'valuation_columns': valuation_info['valuation_columns']
    }
