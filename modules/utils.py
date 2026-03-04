import hashlib
import json
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Union
from datetime import date, timedelta
import pandas as pd


class CacheManager:
    def __init__(self, default_ttl: Optional[int] = None):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        if entry['expires_at'] is not None and time.time() > entry['expires_at']:
            del self._cache[key]
            return None
        
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        expires_at = None
        effective_ttl = ttl if ttl is not None else self.default_ttl
        if effective_ttl is not None:
            expires_at = time.time() + effective_ttl
        
        self._cache[key] = {
            'value': value,
            'expires_at': expires_at
        }
    
    def invalidate(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        self._cache.clear()


def hash_params(params: Dict[str, Any]) -> str:
    sorted_items = sorted(params.items(), key=lambda x: x[0])
    params_str = json.dumps(sorted_items, sort_keys=True, default=str)
    return hashlib.md5(params_str.encode('utf-8')).hexdigest()


def hash_dataframe(df: pd.DataFrame) -> str:
    df_hash = hashlib.md5()
    df_hash.update(pd.util.hash_pandas_object(df).values)
    df_hash.update(str(df.columns.tolist()).encode('utf-8'))
    df_hash.update(str(df.dtypes.tolist()).encode('utf-8'))
    return df_hash.hexdigest()


def hash_file(file_path_or_object: Union[str, object]) -> str:
    if isinstance(file_path_or_object, str):
        with open(file_path_or_object, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    else:
        pos = file_path_or_object.tell()
        file_path_or_object.seek(0)
        content = file_path_or_object.read()
        file_path_or_object.seek(pos)
        return hashlib.md5(content).hexdigest()


class TradingCalendar:
    def __init__(self, trading_dates: Union[Set[date], List[date], pd.Series]):
        if isinstance(trading_dates, pd.Series):
            self._trading_dates: Set[date] = set(trading_dates.dt.date.tolist())
        elif isinstance(trading_dates, list):
            self._trading_dates = set(trading_dates)
        else:
            self._trading_dates = trading_dates.copy()
        
        self._sorted_dates: Optional[List[date]] = None
    
    def _ensure_sorted_dates(self) -> None:
        if self._sorted_dates is None:
            self._sorted_dates = sorted(self._trading_dates)
    
    def is_trading_day(self, date_obj: date) -> bool:
        return date_obj in self._trading_dates
    
    def get_next_trading_day(self, date_obj: date, max_date: Optional[date] = None) -> Optional[date]:
        self._ensure_sorted_dates()
        
        for trading_date in self._sorted_dates:
            if trading_date > date_obj:
                if max_date is None or trading_date <= max_date:
                    return trading_date
                break
        
        return None
    
    def get_previous_trading_day(self, date_obj: date, min_date: Optional[date] = None) -> Optional[date]:
        self._ensure_sorted_dates()
        
        for trading_date in reversed(self._sorted_dates):
            if trading_date < date_obj:
                if min_date is None or trading_date >= min_date:
                    return trading_date
                break
        
        return None
    
    def get_trading_days_between(self, start_date: date, end_date: date) -> List[date]:
        self._ensure_sorted_dates()
        
        result = []
        for trading_date in self._sorted_dates:
            if start_date <= trading_date <= end_date:
                result.append(trading_date)
            elif trading_date > end_date:
                break
        
        return result


def calculate_total_return(final_value: float, initial_value: float) -> float:
    if initial_value == 0:
        return 0.0
    return (final_value - initial_value) / initial_value * 100


def calculate_annualized_return(total_return: float, years: float) -> float:
    if years <= 0:
        return 0.0
    
    total_return_decimal = total_return / 100
    annualized_decimal = (1 + total_return_decimal) ** (1 / years) - 1
    return annualized_decimal * 100


def calculate_years_between(start_date: date, end_date: date) -> float:
    days = (end_date - start_date).days
    return days / 365.0


def get_date_range_info(df: pd.DataFrame) -> Dict[str, Any]:
    if '日期' not in df.columns or len(df) == 0:
        return {
            'min_date': None,
            'max_date': None,
            'total_days': 0,
            'total_years': 0.0,
            'record_count': 0
        }
    
    min_date = df['日期'].min().date()
    max_date = df['日期'].max().date()
    total_days = (max_date - min_date).days
    total_years = total_days / 365.0
    
    return {
        'min_date': min_date,
        'max_date': max_date,
        'total_days': total_days,
        'total_years': total_years,
        'record_count': len(df)
    }


def filter_df_by_date_range(
    df: pd.DataFrame, 
    start_date: date, 
    end_date: date,
    date_column: str = '日期'
) -> pd.DataFrame:
    if date_column not in df.columns:
        return df
    
    mask = (df[date_column].dt.date >= start_date) & (df[date_column].dt.date <= end_date)
    return df[mask].reset_index(drop=True)
