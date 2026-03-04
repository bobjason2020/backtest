import io
from typing import Dict, Any, Optional, Union
import pandas as pd
import streamlit as st

from .utils import CacheManager, hash_file
from .exceptions import DataValidationError


class DataLoader:
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self._cache_manager = cache_manager

    def load(self, file_source: Union[str, object]) -> tuple[Optional[pd.DataFrame], Optional[str]]:
        try:
            file_hash = self.get_data_hash(file_source)
            
            if self._cache_manager is not None:
                cached_data = self._cache_manager.get(f"df_{file_hash}")
                if cached_data is not None:
                    return cached_data, None
            
            if isinstance(file_source, str):
                with open(file_source, 'rb') as f:
                    file_bytes = f.read()
            else:
                pos = file_source.tell()
                file_source.seek(0)
                file_bytes = file_source.read()
                file_source.seek(pos)
            
            df = self._parse_excel(file_bytes)
            
            if self._cache_manager is not None and df is not None:
                self._cache_manager.set(f"df_{file_hash}", df, ttl=3600)
            
            return df, None
        except Exception as e:
            return None, str(e)

    def _parse_excel(self, file_bytes: bytes) -> pd.DataFrame:
        df = pd.read_excel(io.BytesIO(file_bytes))
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期').reset_index(drop=True)
        return df

    def validate(self, df: pd.DataFrame) -> bool:
        required_columns = ['日期', '收盘价']
        missing = [col for col in required_columns if col not in df.columns]
        
        if missing:
            raise DataValidationError(
                f"缺少必要列: {', '.join(missing)}",
                field_name='columns',
                invalid_value=missing,
                details={'required_columns': required_columns}
            )
        
        if len(df) == 0:
            raise DataValidationError(
                "数据为空",
                field_name='data',
                invalid_value=None,
                details={'record_count': 0}
            )
        
        try:
            if '日期' in df.columns:
                pd.to_datetime(df['日期'])
        except Exception as e:
            raise DataValidationError(
                f"日期格式无效: {str(e)}",
                field_name='日期',
                invalid_value=str(df['日期'].head()),
                details={'error': str(e)}
            )
        
        return True

    def get_date_range(self, df: pd.DataFrame) -> Dict[str, Any]:
        min_date = df['日期'].min().date()
        max_date = df['日期'].max().date()
        total_days = (max_date - min_date).days
        max_years = total_days / 365.0
        valuation_info = self.check_valuation_data(df)
        
        return {
            'min_date': min_date,
            'max_date': max_date,
            'total_days': total_days,
            'max_years': max_years,
            'record_count': len(df),
            'has_valuation': valuation_info['has_valuation'],
            'valuation_columns': valuation_info['valuation_columns']
        }

    def check_valuation_data(self, df: pd.DataFrame) -> Dict[str, Any]:
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

    def get_data_hash(self, file_source: Union[str, object]) -> str:
        return hash_file(file_source)


_default_loader = DataLoader()


@st.cache_data(ttl=3600, show_spinner=False)
def _load_excel_from_bytes(file_bytes: bytes) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    try:
        df = pd.read_excel(io.BytesIO(file_bytes))
        df['日期'] = pd.to_datetime(df['日期'])
        df = df.sort_values('日期').reset_index(drop=True)
        return df, None
    except Exception as e:
        return None, str(e)


def load_excel_file(uploaded_file: Union[str, object]) -> tuple[Optional[pd.DataFrame], Optional[str]]:
    return _default_loader.load(uploaded_file)


def validate_data(df: pd.DataFrame) -> tuple[bool, Optional[str]]:
    try:
        _default_loader.validate(df)
        return True, None
    except DataValidationError as e:
        return False, e.message


def get_date_range(df: pd.DataFrame) -> Dict[str, Any]:
    return _default_loader.get_date_range(df)


def check_valuation_data(df: pd.DataFrame) -> Dict[str, Any]:
    return _default_loader.check_valuation_data(df)
