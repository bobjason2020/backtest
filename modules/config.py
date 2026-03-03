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

MA_PRESETS_FILE = "data/ma_strategy_presets.json"

import json
import os

def load_custom_presets():
    if os.path.exists(MA_PRESETS_FILE):
        try:
            with open(MA_PRESETS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_custom_preset(name, params):
    presets = load_custom_presets()
    presets[name] = params
    os.makedirs(os.path.dirname(MA_PRESETS_FILE), exist_ok=True)
    with open(MA_PRESETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(presets, f, ensure_ascii=False, indent=2)

def get_all_presets():
    all_presets = MA_STRATEGY_PRESETS.copy()
    custom = load_custom_presets()
    all_presets.update(custom)
    return all_presets
