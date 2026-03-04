import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple


class RiskAnalyzer:
    def __init__(self, daily_assets_df: pd.DataFrame, value_col: str = '实际持仓市值'):
        self.daily_assets_df = daily_assets_df.copy()
        self.value_col = value_col
        self._prepare_data()
    
    def _prepare_data(self) -> None:
        self.daily_assets_df['累计收益率'] = (
            (self.daily_assets_df[self.value_col] - self.daily_assets_df['累计投入']) 
            / self.daily_assets_df['累计投入'] * 100
        )
        self.daily_assets_df['累计收益率'] = self.daily_assets_df['累计收益率'].replace([np.inf, -np.inf], 0)
        
        peak = self.daily_assets_df[self.value_col].expanding().max()
        self.daily_assets_df['回撤'] = (
            (self.daily_assets_df[self.value_col] - peak) / peak * 100
        )
        
        self.daily_assets_df['日收益率'] = self.daily_assets_df[self.value_col].pct_change()
    
    def calculate_max_drawdown(self) -> Dict[str, Any]:
        max_drawdown = self.daily_assets_df['累计收益率'].min()
        return {
            'name': '最大亏损',
            'value': max_drawdown,
            'unit': '%',
            'description': '累计收益率的最小值'
        }
    
    def calculate_max_pullback(self) -> Dict[str, Any]:
        max_pullback = self.daily_assets_df['回撤'].min()
        return {
            'name': '最大回撤',
            'value': max_pullback,
            'unit': '%',
            'description': '从历史最高点的最大跌幅'
        }
    
    def calculate_loss_statistics(self) -> Dict[str, Any]:
        loss_days = (self.daily_assets_df['累计收益率'] < 0).sum()
        total_days = len(self.daily_assets_df)
        loss_ratio = loss_days / total_days * 100 if total_days > 0 else 0
        
        return {
            'name': '亏损统计',
            'loss_days': loss_days,
            'total_trading_days': total_days,
            'loss_ratio': loss_ratio,
            'unit': '天/%',
            'description': f'亏损天数: {loss_days}/{total_days}, 占比: {loss_ratio:.2f}%'
        }
    
    def find_recovery_date(self, start_date=None) -> Dict[str, Any]:
        recovery_date = None
        cumulative_positive = False
        
        for idx, row in self.daily_assets_df.iterrows():
            if row['累计收益率'] >= 0:
                if not cumulative_positive:
                    cumulative_positive = True
            else:
                cumulative_positive = False
            
            if cumulative_positive:
                subsequent = self.daily_assets_df.loc[idx:]
                if (subsequent['累计收益率'] < 0).sum() == 0:
                    recovery_date = row['日期']
                    break
        
        recovery_days = None
        if recovery_date is not None and start_date is not None:
            recovery_days = (recovery_date.date() - start_date).days
        
        return {
            'name': '回本日期',
            'recovery_date': recovery_date,
            'recovery_days': recovery_days,
            'description': f'首次回本日期: {recovery_date}, 所需天数: {recovery_days}'
        }
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.03) -> Dict[str, Any]:
        daily_returns = self.daily_assets_df['日收益率'].dropna()
        
        if len(daily_returns) == 0:
            return {
                'name': '夏普比率',
                'value': 0,
                'description': '无有效收益率数据'
            }
        
        annualized_return = daily_returns.mean() * 252
        annualized_volatility = daily_returns.std() * np.sqrt(252)
        
        if annualized_volatility == 0:
            sharpe_ratio = 0
        else:
            sharpe_ratio = (annualized_return - risk_free_rate) / annualized_volatility
        
        return {
            'name': '夏普比率',
            'value': sharpe_ratio,
            'annualized_return': annualized_return,
            'annualized_volatility': annualized_volatility,
            'description': f'年化收益率: {annualized_return:.4f}, 年化波动率: {annualized_volatility:.4f}'
        }
    
    def calculate_volatility(self) -> Dict[str, Any]:
        daily_returns = self.daily_assets_df['日收益率'].dropna()
        
        if len(daily_returns) == 0:
            return {
                'name': '波动率',
                'value': 0,
                'unit': '%',
                'description': '无有效收益率数据'
            }
        
        annualized_volatility = daily_returns.std() * np.sqrt(252) * 100
        
        return {
            'name': '波动率',
            'value': annualized_volatility,
            'unit': '%',
            'description': '年化波动率'
        }
    
    def calculate_max_consecutive_loss_days(self) -> Dict[str, Any]:
        is_loss = self.daily_assets_df['日收益率'] < 0
        consecutive_losses = (is_loss != is_loss.shift()).cumsum()
        max_consecutive = is_loss.groupby(consecutive_losses).sum().max() if len(is_loss) > 0 else 0
        
        return {
            'name': '最大连续亏损天数',
            'value': int(max_consecutive),
            'unit': '天',
            'description': '连续亏损的最长天数'
        }
    
    def get_all_metrics(self, start_date=None) -> Dict[str, Any]:
        max_drawdown = self.calculate_max_drawdown()
        max_pullback = self.calculate_max_pullback()
        loss_stats = self.calculate_loss_statistics()
        recovery = self.find_recovery_date(start_date)
        sharpe = self.calculate_sharpe_ratio()
        volatility = self.calculate_volatility()
        consecutive_loss = self.calculate_max_consecutive_loss_days()
        
        return {
            'max_drawdown': max_drawdown['value'],
            'max_pullback': max_pullback['value'],
            'loss_days': loss_stats['loss_days'],
            'total_trading_days': loss_stats['total_trading_days'],
            'loss_ratio': loss_stats['loss_ratio'],
            'recovery_date': recovery['recovery_date'],
            'recovery_days': recovery['recovery_days'],
            'sharpe_ratio': sharpe['value'],
            'volatility': volatility['value'],
            'max_consecutive_loss_days': consecutive_loss['value']
        }


def calculate_max_drawdown(daily_assets_df, value_col='实际持仓市值'):
    analyzer = RiskAnalyzer(daily_assets_df, value_col)
    result = analyzer.calculate_max_drawdown()
    return result['value']


def calculate_max_pullback(daily_assets_df, value_col='实际持仓市值'):
    analyzer = RiskAnalyzer(daily_assets_df, value_col)
    result = analyzer.calculate_max_pullback()
    return result['value']


def calculate_loss_statistics(daily_assets_df, value_col='实际持仓市值'):
    analyzer = RiskAnalyzer(daily_assets_df, value_col)
    result = analyzer.calculate_loss_statistics()
    return result['loss_days'], result['total_trading_days'], result['loss_ratio']


def find_recovery_date(daily_assets_df, value_col='实际持仓市值', start_date=None):
    analyzer = RiskAnalyzer(daily_assets_df, value_col)
    result = analyzer.find_recovery_date(start_date)
    return result['recovery_date'], result['recovery_days']


def analyze_risk_metrics(daily_assets_df, realistic_params=None, start_date=None):
    if realistic_params:
        value_col = '实际持仓市值'
    else:
        value_col = '理想持仓市值'
    
    analyzer = RiskAnalyzer(daily_assets_df, value_col)
    return analyzer.get_all_metrics(start_date)
