from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json

PAGE_TITLE = "定投收益回测工具"
PAGE_LAYOUT = "wide"
SIDEBAR_STATE = "expanded"

WEEKDAY_MAP = {
    "周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4
}

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五"]

MONTH_OPTIONS = [f"{i}号" for i in range(1, 29)] + ["月底"]

DEFAULT_AMOUNT = 1000
MIN_AMOUNT = 100
MAX_AMOUNT = 1000000
AMOUNT_STEP = 100

DEFAULT_MANAGEMENT_FEE = 0.5
DEFAULT_CUSTODY_FEE = 0.1
DEFAULT_PURCHASE_FEE = 0.12
DEFAULT_REDEMPTION_FEE = 0.0
DEFAULT_CASH_RATIO = 5.0
DEFAULT_TRACKING_ERROR = 0.1

DEFAULT_HOLDING_YEARS = 3.0
MIN_HOLDING_YEARS = 0.5
HOLDING_YEARS_STEP = 0.5

CHART_HEIGHT = 400
CHART_MARGIN = dict(l=0, r=0, t=30, b=0)

DURATION_OPTIONS = [1, 2, 3, 5, 7, 10]
DEFAULT_DURATION = 5
MIN_DURATION = 0.5
MAX_DURATION = 30
DURATION_STEP = 0.5

SAMPLING_OPTIONS = ["每月采样", "每周采样", "每日采样"]
DEFAULT_SAMPLING = "每月采样"

STRATEGY_TYPES = ["均线偏离", "趋势动量", "估值分位", "组合策略"]
DEFAULT_STRATEGY = "均线偏离"

MA_PERIODS = [5, 10, 20, 60, 120, 250]
DEFAULT_MA_PERIOD = 20

DEFAULT_EXTREME_LOW_THRESHOLD = -10.0
DEFAULT_LOW_THRESHOLD = -5.0
DEFAULT_HIGH_THRESHOLD = 5.0
DEFAULT_EXTREME_HIGH_THRESHOLD = 10.0

VALUATION_COLUMNS = ["PE", "PB"]
DEFAULT_VALUATION_COLUMN = "PE"

DEFAULT_EXTREME_LOW_PERCENTILE = 10.0
DEFAULT_LOW_PERCENTILE = 20.0
DEFAULT_HIGH_PERCENTILE = 80.0
DEFAULT_EXTREME_HIGH_PERCENTILE = 90.0

DEFAULT_TREND_PERIOD = 20
DEFAULT_TREND_EXTREME_LOW_THRESHOLD = -15.0
DEFAULT_TREND_LOW_THRESHOLD = -10.0
DEFAULT_TREND_HIGH_THRESHOLD = 10.0
DEFAULT_TREND_EXTREME_HIGH_THRESHOLD = 15.0

DEFAULT_EXTREME_LOW_MULTIPLIER = 2.0
DEFAULT_LOW_MULTIPLIER = 1.5
DEFAULT_NORMAL_MULTIPLIER = 1.0
DEFAULT_HIGH_MULTIPLIER = 0.5
DEFAULT_EXTREME_HIGH_MULTIPLIER = 0.0

MA_STRATEGY_PRESETS = {
    "保守型": {
        "ma_period": 20,
        "extreme_high_threshold": 15.0,
        "extreme_high_multiplier": 0.5,
        "high_threshold": 10.0,
        "high_multiplier": 0.8,
        "normal_multiplier": 1.0,
        "low_threshold": -10.0,
        "low_multiplier": 1.2,
        "extreme_low_threshold": -15.0,
        "extreme_low_multiplier": 1.5
    },
    "均衡型（默认）": {
        "ma_period": 20,
        "extreme_high_threshold": 10.0,
        "extreme_high_multiplier": 0.0,
        "high_threshold": 5.0,
        "high_multiplier": 0.5,
        "normal_multiplier": 1.0,
        "low_threshold": -5.0,
        "low_multiplier": 1.5,
        "extreme_low_threshold": -10.0,
        "extreme_low_multiplier": 2.0
    },
    "激进型": {
        "ma_period": 20,
        "extreme_high_threshold": 8.0,
        "extreme_high_multiplier": 0.0,
        "high_threshold": 4.0,
        "high_multiplier": 0.3,
        "normal_multiplier": 1.0,
        "low_threshold": -4.0,
        "low_multiplier": 2.0,
        "extreme_low_threshold": -8.0,
        "extreme_low_multiplier": 3.0
    },
    "长线均线": {
        "ma_period": 60,
        "extreme_high_threshold": 15.0,
        "extreme_high_multiplier": 0.0,
        "high_threshold": 10.0,
        "high_multiplier": 0.5,
        "normal_multiplier": 1.0,
        "low_threshold": -10.0,
        "low_multiplier": 1.5,
        "extreme_low_threshold": -20.0,
        "extreme_low_multiplier": 2.5
    }
}

MA_PRESETS_FILE = Path("data/ma_strategy_presets.json")


@dataclass
class ConfigManager:
    page_title: str = PAGE_TITLE
    page_layout: str = PAGE_LAYOUT
    sidebar_state: str = SIDEBAR_STATE
    
    default_amount: float = DEFAULT_AMOUNT
    min_amount: float = MIN_AMOUNT
    max_amount: float = MAX_AMOUNT
    amount_step: float = AMOUNT_STEP
    
    default_management_fee: float = DEFAULT_MANAGEMENT_FEE
    default_custody_fee: float = DEFAULT_CUSTODY_FEE
    default_purchase_fee: float = DEFAULT_PURCHASE_FEE
    default_redemption_fee: float = DEFAULT_REDEMPTION_FEE
    default_cash_ratio: float = DEFAULT_CASH_RATIO
    default_tracking_error: float = DEFAULT_TRACKING_ERROR
    
    default_holding_years: float = DEFAULT_HOLDING_YEARS
    min_holding_years: float = MIN_HOLDING_YEARS
    holding_years_step: float = HOLDING_YEARS_STEP
    
    chart_height: int = CHART_HEIGHT
    chart_margin: Dict[str, int] = field(default_factory=lambda: dict(CHART_MARGIN))
    
    default_duration: float = DEFAULT_DURATION
    min_duration: float = MIN_DURATION
    max_duration: float = MAX_DURATION
    duration_step: float = DURATION_STEP
    
    default_sampling: str = DEFAULT_SAMPLING
    default_strategy: str = DEFAULT_STRATEGY
    
    default_ma_period: int = DEFAULT_MA_PERIOD
    default_extreme_low_threshold: float = DEFAULT_EXTREME_LOW_THRESHOLD
    default_low_threshold: float = DEFAULT_LOW_THRESHOLD
    default_high_threshold: float = DEFAULT_HIGH_THRESHOLD
    default_extreme_high_threshold: float = DEFAULT_EXTREME_HIGH_THRESHOLD
    
    default_valuation_column: str = DEFAULT_VALUATION_COLUMN
    default_extreme_low_percentile: float = DEFAULT_EXTREME_LOW_PERCENTILE
    default_low_percentile: float = DEFAULT_LOW_PERCENTILE
    default_high_percentile: float = DEFAULT_HIGH_PERCENTILE
    default_extreme_high_percentile: float = DEFAULT_EXTREME_HIGH_PERCENTILE
    
    default_trend_period: int = DEFAULT_TREND_PERIOD
    default_trend_extreme_low_threshold: float = DEFAULT_TREND_EXTREME_LOW_THRESHOLD
    default_trend_low_threshold: float = DEFAULT_TREND_LOW_THRESHOLD
    default_trend_high_threshold: float = DEFAULT_TREND_HIGH_THRESHOLD
    default_trend_extreme_high_threshold: float = DEFAULT_TREND_EXTREME_HIGH_THRESHOLD
    
    default_extreme_low_multiplier: float = DEFAULT_EXTREME_LOW_MULTIPLIER
    default_low_multiplier: float = DEFAULT_LOW_MULTIPLIER
    default_normal_multiplier: float = DEFAULT_NORMAL_MULTIPLIER
    default_high_multiplier: float = DEFAULT_HIGH_MULTIPLIER
    default_extreme_high_multiplier: float = DEFAULT_EXTREME_HIGH_MULTIPLIER
    
    _custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def get(self, key: str, default: Any = None) -> Any:
        if key in self._custom_config:
            return self._custom_config[key]
        if hasattr(self, key):
            return getattr(self, key)
        return default
    
    def set(self, key: str, value: Any) -> None:
        self._custom_config[key] = value
    
    def validate(self) -> bool:
        if not (self.min_amount <= self.default_amount <= self.max_amount):
            return False
        
        fee_fields = [
            'default_management_fee',
            'default_custody_fee', 
            'default_purchase_fee',
            'default_redemption_fee'
        ]
        for fee_field in fee_fields:
            fee_value = getattr(self, fee_field)
            if not (0 <= fee_value <= 100):
                return False
        
        if self.default_holding_years < self.min_holding_years:
            return False
        
        if not (self.min_duration <= self.default_duration <= self.max_duration):
            return False
        
        if self.default_ma_period <= 0:
            return False
        
        return True
    
    def validate_amount(self, amount: float) -> bool:
        return self.min_amount <= amount <= self.max_amount
    
    def validate_fee_rate(self, fee_rate: float) -> bool:
        return 0 <= fee_rate <= 100
    
    def validate_duration(self, duration: float) -> bool:
        return self.min_duration <= duration <= self.max_duration
    
    def validate_holding_years(self, holding_years: float) -> bool:
        return holding_years >= self.min_holding_years
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result.pop('_custom_config', None)
        return result
    
    def update_from_dict(self, config_dict: Dict[str, Any]) -> None:
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                self._custom_config[key] = value


def load_custom_presets() -> Dict[str, Dict[str, Any]]:
    if not MA_PRESETS_FILE.exists():
        return {}
    try:
        with open(MA_PRESETS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}
    except (json.JSONDecodeError, IOError, PermissionError):
        return {}


def save_custom_preset(name: str, params: Dict[str, Any]) -> bool:
    if not name or not isinstance(name, str):
        return False
    if not isinstance(params, dict):
        return False
    
    required_keys = [
        'ma_period', 'extreme_high_threshold', 'extreme_high_multiplier',
        'high_threshold', 'high_multiplier', 'normal_multiplier',
        'low_threshold', 'low_multiplier', 'extreme_low_threshold',
        'extreme_low_multiplier'
    ]
    
    for key in required_keys:
        if key not in params:
            return False
    
    try:
        presets = load_custom_presets()
        presets[name] = params
        MA_PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MA_PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
        return True
    except (IOError, PermissionError, json.JSONEncodeError):
        return False


def delete_custom_preset(name: str) -> bool:
    if not name or not isinstance(name, str):
        return False
    
    try:
        presets = load_custom_presets()
        if name not in presets:
            return False
        
        del presets[name]
        MA_PRESETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MA_PRESETS_FILE, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
        return True
    except (IOError, PermissionError, json.JSONEncodeError):
        return False


def get_all_presets() -> Dict[str, Dict[str, Any]]:
    all_presets = MA_STRATEGY_PRESETS.copy()
    custom = load_custom_presets()
    all_presets.update(custom)
    return all_presets


_config_manager_instance: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance
