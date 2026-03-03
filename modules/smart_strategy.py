import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class StrategySignal:
    date: object
    price: float
    signal: str
    multiplier: float
    reason: str


@dataclass
class SmartStrategyConfig:
    strategy_type: str
    base_amount: float
    ma_period: int = 20
    extreme_low_threshold: float = -0.10
    low_threshold: float = -0.05
    high_threshold: float = 0.05
    extreme_high_threshold: float = 0.10
    valuation_column: str = "PE"
    extreme_low_percentile: float = 10.0
    low_percentile: float = 20.0
    high_percentile: float = 80.0
    extreme_high_percentile: float = 90.0
    trend_period: int = 20
    trend_extreme_low_threshold: float = -0.15
    trend_low_threshold: float = -0.10
    trend_high_threshold: float = 0.10
    trend_extreme_high_threshold: float = 0.15
    extreme_low_multiplier: float = 2.0
    low_multiplier: float = 1.5
    normal_multiplier: float = 1.0
    high_multiplier: float = 0.5
    extreme_high_multiplier: float = 0.0


class BaseStrategy(ABC):
    def __init__(self, config: SmartStrategyConfig):
        self.config = config
    
    @abstractmethod
    def calculate_signal(self, df: pd.DataFrame, current_date: object) -> StrategySignal:
        pass
    
    def get_amount_multiplier(self, signal: str) -> float:
        multiplier_map = {
            "extreme_low": self.config.extreme_low_multiplier,
            "low": self.config.low_multiplier,
            "normal": self.config.normal_multiplier,
            "high": self.config.high_multiplier,
            "extreme_high": self.config.extreme_high_multiplier
        }
        return multiplier_map.get(signal, 1.0)


class MovingAverageStrategy(BaseStrategy):
    def calculate_signal(self, df: pd.DataFrame, current_date: object) -> StrategySignal:
        df_filtered = df.loc[df['日期'].dt.date <= current_date]
        
        if len(df_filtered) < self.config.ma_period:
            last_row = df_filtered.iloc[-1]
            return StrategySignal(
                date=current_date,
                price=last_row['收盘价'],
                signal="normal",
                multiplier=1.0,
                reason=f"数据不足{self.config.ma_period}天，使用正常定投"
            )
        
        last_row = df_filtered.iloc[-1]
        current_price = last_row['收盘价']
        
        ma_value = df_filtered.tail(self.config.ma_period)['收盘价'].mean()
        
        deviation = (current_price - ma_value) / ma_value
        
        if deviation <= self.config.extreme_low_threshold:
            signal = "extreme_low"
            reason = f"价格严重低于MA{self.config.ma_period}（偏离{deviation*100:.2f}%），加倍定投"
        elif deviation <= self.config.low_threshold:
            signal = "low"
            reason = f"价格低于MA{self.config.ma_period}（偏离{deviation*100:.2f}%），增加定投"
        elif deviation >= self.config.extreme_high_threshold:
            signal = "extreme_high"
            reason = f"价格严重高于MA{self.config.ma_period}（偏离{deviation*100:.2f}%），暂停定投"
        elif deviation >= self.config.high_threshold:
            signal = "high"
            reason = f"价格高于MA{self.config.ma_period}（偏离{deviation*100:.2f}%），减少定投"
        else:
            signal = "normal"
            reason = f"价格接近MA{self.config.ma_period}（偏离{deviation*100:.2f}%），正常定投"
        
        return StrategySignal(
            date=current_date,
            price=current_price,
            signal=signal,
            multiplier=self.get_amount_multiplier(signal),
            reason=reason
        )


class TrendMomentumStrategy(BaseStrategy):
    def calculate_signal(self, df: pd.DataFrame, current_date: object) -> StrategySignal:
        df_filtered = df.loc[df['日期'].dt.date <= current_date]
        
        if len(df_filtered) < self.config.trend_period + 1:
            last_row = df_filtered.iloc[-1]
            return StrategySignal(
                date=current_date,
                price=last_row['收盘价'],
                signal="normal",
                multiplier=1.0,
                reason=f"数据不足{self.config.trend_period+1}天，使用正常定投"
            )
        
        last_row = df_filtered.iloc[-1]
        current_price = last_row['收盘价']
        
        price_n_days_ago = df_filtered.iloc[-(self.config.trend_period + 1)]['收盘价']
        
        trend_return = (current_price - price_n_days_ago) / price_n_days_ago
        
        if trend_return <= self.config.trend_extreme_low_threshold:
            signal = "extreme_low"
            reason = f"过去{self.config.trend_period}天跌幅{trend_return*100:.2f}%，严重下跌，加倍定投"
        elif trend_return <= self.config.trend_low_threshold:
            signal = "low"
            reason = f"过去{self.config.trend_period}天跌幅{trend_return*100:.2f}%，增加定投"
        elif trend_return >= self.config.trend_extreme_high_threshold:
            signal = "extreme_high"
            reason = f"过去{self.config.trend_period}天涨幅{trend_return*100:.2f}%，严重过热，暂停定投"
        elif trend_return >= self.config.trend_high_threshold:
            signal = "high"
            reason = f"过去{self.config.trend_period}天涨幅{trend_return*100:.2f}%，减少定投"
        else:
            signal = "normal"
            reason = f"过去{self.config.trend_period}天涨跌幅{trend_return*100:.2f}%，正常定投"
        
        return StrategySignal(
            date=current_date,
            price=current_price,
            signal=signal,
            multiplier=self.get_amount_multiplier(signal),
            reason=reason
        )


class ValuationStrategy(BaseStrategy):
    def calculate_signal(self, df: pd.DataFrame, current_date: object) -> StrategySignal:
        df_filtered = df.loc[df['日期'].dt.date <= current_date]
        
        valuation_col = self.config.valuation_column
        if valuation_col not in df_filtered.columns:
            last_row = df_filtered.iloc[-1]
            return StrategySignal(
                date=current_date,
                price=last_row['收盘价'],
                signal="normal",
                multiplier=1.0,
                reason=f"缺少{valuation_col}数据，使用正常定投"
            )
        
        last_row = df_filtered.iloc[-1]
        current_price = last_row['收盘价']
        current_valuation = last_row[valuation_col]
        
        if pd.isna(current_valuation):
            return StrategySignal(
                date=current_date,
                price=current_price,
                signal="normal",
                multiplier=1.0,
                reason=f"{valuation_col}数据缺失，使用正常定投"
            )
        
        historical_valuations = df_filtered[valuation_col].dropna()
        
        if len(historical_valuations) < 30:
            return StrategySignal(
                date=current_date,
                price=current_price,
                signal="normal",
                multiplier=1.0,
                reason=f"历史{valuation_col}数据不足，使用正常定投"
            )
        
        percentile = (historical_valuations < current_valuation).sum() / len(historical_valuations) * 100
        
        if percentile <= self.config.extreme_low_percentile:
            signal = "extreme_low"
            reason = f"{valuation_col}={current_valuation:.2f}，处于历史{percentile:.1f}%分位（极度低估），加倍定投"
        elif percentile <= self.config.low_percentile:
            signal = "low"
            reason = f"{valuation_col}={current_valuation:.2f}，处于历史{percentile:.1f}%分位（低估），增加定投"
        elif percentile >= self.config.extreme_high_percentile:
            signal = "extreme_high"
            reason = f"{valuation_col}={current_valuation:.2f}，处于历史{percentile:.1f}%分位（极度高估），暂停定投"
        elif percentile >= self.config.high_percentile:
            signal = "high"
            reason = f"{valuation_col}={current_valuation:.2f}，处于历史{percentile:.1f}%分位（高估），减少定投"
        else:
            signal = "normal"
            reason = f"{valuation_col}={current_valuation:.2f}，处于历史{percentile:.1f}%分位（正常），正常定投"
        
        return StrategySignal(
            date=current_date,
            price=current_price,
            signal=signal,
            multiplier=self.get_amount_multiplier(signal),
            reason=reason
        )


class CombinedStrategy(BaseStrategy):
    def __init__(self, config: SmartStrategyConfig, strategies: List[BaseStrategy]):
        super().__init__(config)
        self.strategies = strategies
    
    def calculate_signal(self, df: pd.DataFrame, current_date: object) -> StrategySignal:
        signals = []
        for strategy in self.strategies:
            sig = strategy.calculate_signal(df, current_date)
            signals.append(sig)
        
        avg_multiplier = np.mean([s.multiplier for s in signals])
        
        combined_reasons = [s.reason for s in signals]
        
        if avg_multiplier >= 1.8:
            final_signal = "extreme_low"
        elif avg_multiplier >= 1.3:
            final_signal = "low"
        elif avg_multiplier <= 0.2:
            final_signal = "extreme_high"
        elif avg_multiplier < 0.8:
            final_signal = "high"
        else:
            final_signal = "normal"
        
        last_row = df[df['日期'].dt.date <= current_date].iloc[-1]
        
        return StrategySignal(
            date=current_date,
            price=last_row['收盘价'],
            signal=final_signal,
            multiplier=avg_multiplier,
            reason=" | ".join(combined_reasons)
        )


def create_strategy(config: SmartStrategyConfig) -> BaseStrategy:
    if config.strategy_type == "均线偏离":
        return MovingAverageStrategy(config)
    elif config.strategy_type == "趋势动量":
        return TrendMomentumStrategy(config)
    elif config.strategy_type == "估值分位":
        return ValuationStrategy(config)
    elif config.strategy_type == "组合策略":
        ma_strategy = MovingAverageStrategy(config)
        trend_strategy = TrendMomentumStrategy(config)
        strategies = [ma_strategy, trend_strategy]
        return CombinedStrategy(config, strategies)
    else:
        return MovingAverageStrategy(config)


def get_investment_amount(df: pd.DataFrame, current_date: object, 
                          strategy: BaseStrategy, base_amount: float) -> Tuple[float, StrategySignal]:
    signal = strategy.calculate_signal(df, current_date)
    actual_amount = base_amount * signal.multiplier
    return actual_amount, signal


def generate_strategy_signals(df: pd.DataFrame, investment_dates: List, 
                              config: SmartStrategyConfig) -> List[StrategySignal]:
    strategy = create_strategy(config)
    signals = []
    
    for inv_date in investment_dates:
        signal = strategy.calculate_signal(df, inv_date)
        signals.append(signal)
    
    return signals


def calculate_smart_investment_amounts(df: pd.DataFrame, investment_dates: List,
                                        config: SmartStrategyConfig) -> pd.DataFrame:
    strategy = create_strategy(config)
    records = []
    
    for inv_date in investment_dates:
        amount, signal = get_investment_amount(df, inv_date, strategy, config.base_amount)
        records.append({
            '日期': inv_date,
            '收盘价': signal.price,
            '信号': signal.signal,
            '倍数': signal.multiplier,
            '定投金额': amount,
            '原因': signal.reason
        })
    
    return pd.DataFrame(records)
