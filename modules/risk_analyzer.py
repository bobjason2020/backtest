import numpy as np


def _calculate_cumulative_return(daily_assets_df, value_col='实际持仓市值'):
    df = daily_assets_df.copy()
    df['累计收益率'] = (df[value_col] - df['累计投入']) / df['累计投入'] * 100
    df['累计收益率'] = df['累计收益率'].replace([np.inf, -np.inf], 0)
    return df


def calculate_max_drawdown(daily_assets_df, value_col='实际持仓市值'):
    df = _calculate_cumulative_return(daily_assets_df, value_col)
    return df['累计收益率'].min()


def calculate_max_pullback(daily_assets_df, value_col='实际持仓市值'):
    peak = daily_assets_df[value_col].expanding().max()
    drawdown_series = (daily_assets_df[value_col] - peak) / peak * 100
    return drawdown_series.min()


def calculate_loss_statistics(daily_assets_df, value_col='实际持仓市值'):
    df = _calculate_cumulative_return(daily_assets_df, value_col)
    loss_days = (df['累计收益率'] < 0).sum()
    total_days = len(df)
    loss_ratio = loss_days / total_days * 100 if total_days > 0 else 0
    return loss_days, total_days, loss_ratio


def find_recovery_date(daily_assets_df, value_col='实际持仓市值', start_date=None):
    df = _calculate_cumulative_return(daily_assets_df, value_col)
    
    recovery_date = None
    cumulative_positive = False
    
    for idx, row in df.iterrows():
        if row['累计收益率'] >= 0:
            if not cumulative_positive:
                cumulative_positive = True
        else:
            cumulative_positive = False
        
        if cumulative_positive:
            subsequent = df.loc[idx:]
            if (subsequent['累计收益率'] < 0).sum() == 0:
                recovery_date = row['日期']
                break
    
    if recovery_date is not None and start_date is not None:
        recovery_days = (recovery_date.date() - start_date).days
    else:
        recovery_days = None
    
    return recovery_date, recovery_days


def analyze_risk_metrics(daily_assets_df, realistic_params=None, start_date=None):
    if realistic_params:
        value_col = '实际持仓市值'
    else:
        value_col = '理想持仓市值'
    
    max_drawdown = calculate_max_drawdown(daily_assets_df, value_col)
    max_pullback = calculate_max_pullback(daily_assets_df, value_col)
    loss_days, total_days, loss_ratio = calculate_loss_statistics(daily_assets_df, value_col)
    recovery_date, recovery_days = find_recovery_date(daily_assets_df, value_col, start_date)
    
    return {
        'max_drawdown': max_drawdown,
        'max_pullback': max_pullback,
        'loss_days': loss_days,
        'total_trading_days': total_days,
        'loss_ratio': loss_ratio,
        'recovery_date': recovery_date,
        'recovery_days': recovery_days
    }
