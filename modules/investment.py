import pandas as pd
import numpy as np
from datetime import timedelta

from .config import WEEKDAY_MAP
from .fee_calculator import calculate_purchase_fee, apply_tracking_error
from .smart_strategy import SmartStrategyConfig, create_strategy, StrategySignal
from .cash_flow import CashFlowAccount


def get_investment_dates(df, start_date, end_date, freq_type, freq_param):
    trading_dates = set(df['日期'].dt.date)
    investment_dates = []
    
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    if freq_type == "一次性投入":
        current_dt = start_dt
        while current_dt <= end_dt:
            current_date = current_dt.date()
            if current_date in trading_dates:
                investment_dates.append(current_date)
                break
            current_dt += timedelta(days=1)
    
    elif freq_type == "按日":
        current_dt = start_dt
        while current_dt <= end_dt:
            current_date = current_dt.date()
            if current_date in trading_dates:
                investment_dates.append(current_date)
            current_dt += timedelta(days=1)
    
    elif freq_type == "按周":
        target_weekday = WEEKDAY_MAP[freq_param]
        
        current_dt = start_dt
        while current_dt <= end_dt:
            if current_dt.weekday() == target_weekday:
                current_date = current_dt.date()
                if current_date in trading_dates:
                    investment_dates.append(current_date)
                else:
                    next_trading = find_next_trading_day(current_date, trading_dates, end_dt.date())
                    if next_trading and next_trading not in investment_dates:
                        investment_dates.append(next_trading)
            current_dt += timedelta(days=1)
        investment_dates = sorted(list(set(investment_dates)))
    
    elif freq_type == "按月":
        current_dt = start_dt.replace(day=1)
        
        while current_dt <= end_dt:
            if freq_param == "月底":
                next_month = current_dt.replace(day=28) + timedelta(days=4)
                last_day = next_month - timedelta(days=next_month.day)
                target_date = last_day.date()
            else:
                target_day = int(freq_param.replace("号", ""))
                try:
                    target_date = current_dt.replace(day=target_day).date()
                except ValueError:
                    target_date = current_dt.replace(day=28).date()
            
            if target_date < start_dt.date():
                pass
            elif target_date > end_dt.date():
                break
            else:
                if target_date in trading_dates:
                    investment_dates.append(target_date)
                else:
                    next_trading = find_next_trading_day(target_date, trading_dates, end_dt.date())
                    if next_trading and next_trading not in investment_dates:
                        investment_dates.append(next_trading)
            
            if current_dt.month == 12:
                current_dt = current_dt.replace(year=current_dt.year + 1, month=1)
            else:
                current_dt = current_dt.replace(month=current_dt.month + 1)
        
        investment_dates = sorted(list(set(investment_dates)))
    
    return investment_dates


def find_next_trading_day(target_date, trading_dates, end_date):
    current = target_date
    while current <= end_date:
        current += timedelta(days=1)
        if current in trading_dates:
            return current
    return None


def run_backtest_calculation(df, investment_dates, amount, realistic_params=None):
    dates = df['日期'].dt.date
    
    results = []
    total_shares = 0
    total_investment = 0
    total_purchase_fee = 0
    
    purchase_fee_rate = 0
    if realistic_params:
        purchase_fee_rate = realistic_params.get('purchase_fee', 0)
    
    for inv_date in investment_dates:
        row = df[dates == inv_date]
        if len(row) > 0:
            close_price = row['收盘价'].values[0]
            
            actual_amount = amount * (1 - purchase_fee_rate)
            purchase_fee = amount * purchase_fee_rate
            shares = actual_amount / close_price
            
            total_shares += shares
            total_investment += amount
            total_purchase_fee += purchase_fee
            
            results.append({
                '日期': inv_date,
                '收盘价': close_price,
                '投入金额': amount,
                '申购费用': purchase_fee,
                '实际买入金额': actual_amount,
                '买入份额': shares,
                '累计份额': total_shares,
                '累计投入': total_investment,
                '累计申购费': total_purchase_fee
            })
    
    return pd.DataFrame(results), total_shares, total_investment, total_purchase_fee


def calculate_daily_assets(df, investment_dates, amount, realistic_params=None):
    dates = df['日期'].dt.date
    
    purchase_fee_rate = 0
    management_fee_rate = 0
    custody_fee_rate = 0
    cash_ratio = 0
    tracking_error = 0
    tracking_error_mode = "固定折扣"
    
    if realistic_params:
        purchase_fee_rate = realistic_params.get('purchase_fee', 0)
        management_fee_rate = realistic_params.get('management_fee', 0)
        custody_fee_rate = realistic_params.get('custody_fee', 0)
        cash_ratio = realistic_params.get('cash_ratio', 0)
        tracking_error = realistic_params.get('tracking_error', 0)
        tracking_error_mode = realistic_params.get('tracking_error_mode', "固定折扣")
    
    investment_by_date = {}
    
    for inv_date in investment_dates:
        row = df[dates == inv_date]
        if len(row) > 0:
            close_price = row['收盘价'].values[0]
            actual_amount = amount * (1 - purchase_fee_rate)
            shares = actual_amount / close_price
            investment_by_date[inv_date] = {
                'amount': amount,
                'shares': shares,
                'purchase_fee': amount * purchase_fee_rate
            }
    
    daily_records = []
    running_investment = 0
    running_shares_ideal = 0
    running_shares_real = 0
    running_purchase_fee = 0
    running_management_fee = 0
    
    np.random.seed(42)
    
    for idx, row in df.iterrows():
        current_date = dates.iloc[idx]
        close_price = row['收盘价']
        
        if current_date in investment_by_date:
            running_investment += investment_by_date[current_date]['amount']
            running_shares_ideal += investment_by_date[current_date]['shares']
            running_shares_real += investment_by_date[current_date]['shares']
            running_purchase_fee += investment_by_date[current_date]['purchase_fee']
        
        ideal_asset_value = running_shares_ideal * close_price
        ideal_avg_cost = running_investment / running_shares_ideal if running_shares_ideal > 0 else 0
        
        if realistic_params and running_shares_real > 0:
            daily_fee_rate = (management_fee_rate + custody_fee_rate) / 365
            daily_fee_shares = running_shares_real * daily_fee_rate
            running_management_fee += daily_fee_shares * close_price
            running_shares_real -= daily_fee_shares
            
            effective_price = apply_tracking_error(close_price, tracking_error, tracking_error_mode)
            
            stock_asset = running_shares_real * effective_price * (1 - cash_ratio)
            cash_asset = running_investment * cash_ratio
            real_asset_value = stock_asset + cash_asset
            real_avg_cost = running_investment / running_shares_real if running_shares_real > 0 else 0
        else:
            real_asset_value = ideal_asset_value
            real_avg_cost = ideal_avg_cost
            running_shares_real = running_shares_ideal
        
        daily_records.append({
            '日期': df['日期'].iloc[idx],
            '收盘价': close_price,
            '累计投入': running_investment,
            '理想持仓份额': running_shares_ideal,
            '实际持仓份额': running_shares_real,
            '理想持仓市值': ideal_asset_value,
            '实际持仓市值': real_asset_value,
            '理想持仓均价': ideal_avg_cost,
            '实际持仓均价': real_avg_cost,
            '累计申购费': running_purchase_fee,
            '累计管理费': running_management_fee
        })
    
    return pd.DataFrame(daily_records)


def calculate_lump_sum_return(df, start_date, end_date):
    df_filtered = df[(df['日期'].dt.date >= start_date) & (df['日期'].dt.date <= end_date)]
    if len(df_filtered) == 0:
        return 0, 0
    
    start_price = df_filtered.iloc[0]['收盘价']
    end_price = df_filtered.iloc[-1]['收盘价']
    
    total_return = (end_price - start_price) / start_price * 100
    
    days = (end_date - start_date).days
    years = days / 365.0
    if years > 0:
        annualized = ((end_price / start_price) ** (1 / years) - 1) * 100
    else:
        annualized = 0
    
    return total_return, annualized


def run_smart_backtest_calculation(df, investment_dates, base_amount, strategy_config, realistic_params=None, use_cash_flow=True):
    dates = df['日期'].dt.date
    
    strategy = create_strategy(strategy_config)
    cash_account = CashFlowAccount() if use_cash_flow else None
    
    results = []
    total_shares = 0
    total_investment = 0
    total_purchase_fee = 0
    total_deposited = 0
    
    purchase_fee_rate = 0
    if realistic_params:
        purchase_fee_rate = realistic_params.get('purchase_fee', 0)
    
    for inv_date in investment_dates:
        row = df[dates == inv_date]
        if len(row) > 0:
            close_price = row['收盘价'].values[0]
            
            signal = strategy.calculate_signal(df, inv_date)
            requested_amount = base_amount * signal.multiplier
            
            if use_cash_flow and cash_account:
                cash_account.deposit(base_amount)
                total_deposited += base_amount
                
                actual_amount_raw = cash_account.get_available_amount(requested_amount)
                if actual_amount_raw > 0:
                    cash_account.withdraw(actual_amount_raw)
            else:
                actual_amount_raw = requested_amount
            
            actual_amount = actual_amount_raw * (1 - purchase_fee_rate)
            purchase_fee = actual_amount_raw * purchase_fee_rate
            shares = actual_amount / close_price if close_price > 0 else 0
            
            total_shares += shares
            total_investment += actual_amount_raw
            total_purchase_fee += purchase_fee
            
            results.append({
                '日期': inv_date,
                '收盘价': close_price,
                '信号': signal.signal,
                '倍数': signal.multiplier,
                '期望投入': requested_amount,
                '投入金额': actual_amount_raw,
                '申购费用': purchase_fee,
                '实际买入金额': actual_amount,
                '买入份额': shares,
                '累计份额': total_shares,
                '累计投入': total_investment,
                '累计申购费': total_purchase_fee,
                '原因': signal.reason
            })
    
    cash_balance = cash_account.balance if cash_account else 0
    total_deposited = total_deposited if use_cash_flow else total_investment
    
    return pd.DataFrame(results), total_shares, total_investment, total_purchase_fee, total_deposited, cash_balance


def calculate_smart_daily_assets(df, investment_dates, base_amount, strategy_config, realistic_params=None, use_cash_flow=True):
    dates = df['日期'].dt.date
    
    strategy = create_strategy(strategy_config)
    cash_account = CashFlowAccount() if use_cash_flow else None
    
    purchase_fee_rate = 0
    management_fee_rate = 0
    custody_fee_rate = 0
    cash_ratio = 0
    tracking_error = 0
    tracking_error_mode = "固定折扣"
    
    if realistic_params:
        purchase_fee_rate = realistic_params.get('purchase_fee', 0)
        management_fee_rate = realistic_params.get('management_fee', 0)
        custody_fee_rate = realistic_params.get('custody_fee', 0)
        cash_ratio = realistic_params.get('cash_ratio', 0)
        tracking_error = realistic_params.get('tracking_error', 0)
        tracking_error_mode = realistic_params.get('tracking_error_mode', "固定折扣")
    
    investment_by_date = {}
    total_deposited = 0
    
    for inv_date in investment_dates:
        row = df[dates == inv_date]
        if len(row) > 0:
            close_price = row['收盘价'].values[0]
            signal = strategy.calculate_signal(df, inv_date)
            requested_amount = base_amount * signal.multiplier
            
            if use_cash_flow and cash_account:
                cash_account.deposit(base_amount)
                total_deposited += base_amount
                
                actual_amount_raw = cash_account.get_available_amount(requested_amount)
                if actual_amount_raw > 0:
                    cash_account.withdraw(actual_amount_raw)
            else:
                actual_amount_raw = requested_amount
            
            actual_amount = actual_amount_raw * (1 - purchase_fee_rate)
            shares = actual_amount / close_price if close_price > 0 else 0
            investment_by_date[inv_date] = {
                'amount': actual_amount_raw,
                'shares': shares,
                'purchase_fee': actual_amount_raw * purchase_fee_rate,
                'signal': signal.signal,
                'multiplier': signal.multiplier,
                'requested': requested_amount,
                'cash_balance': cash_account.balance if cash_account else 0
            }
    
    daily_records = []
    running_investment = 0
    running_shares_ideal = 0
    running_shares_real = 0
    running_purchase_fee = 0
    running_management_fee = 0
    running_deposited = 0
    running_cash_balance = 0
    
    np.random.seed(42)
    
    for idx in range(len(df)):
        current_date = dates.iloc[idx]
        close_price = df['收盘价'].iloc[idx]
        
        if current_date in investment_by_date:
            inv_data = investment_by_date[current_date]
            running_investment += inv_data['amount']
            running_shares_ideal += inv_data['shares']
            running_shares_real += inv_data['shares']
            running_purchase_fee += inv_data['purchase_fee']
            running_deposited += base_amount if use_cash_flow else inv_data['amount']
            running_cash_balance = inv_data.get('cash_balance', 0)
        
        ideal_asset_value = running_shares_ideal * close_price
        ideal_avg_cost = running_investment / running_shares_ideal if running_shares_ideal > 0 else 0
        
        if realistic_params and running_shares_real > 0:
            daily_fee_rate = (management_fee_rate + custody_fee_rate) / 365
            daily_fee_shares = running_shares_real * daily_fee_rate
            running_management_fee += daily_fee_shares * close_price
            running_shares_real -= daily_fee_shares
            
            effective_price = apply_tracking_error(close_price, tracking_error, tracking_error_mode)
            
            stock_asset = running_shares_real * effective_price * (1 - cash_ratio)
            cash_asset = running_investment * cash_ratio
            real_asset_value = stock_asset + cash_asset
            real_avg_cost = running_investment / running_shares_real if running_shares_real > 0 else 0
        else:
            real_asset_value = ideal_asset_value
            real_avg_cost = ideal_avg_cost
            running_shares_real = running_shares_ideal
        
        total_asset = ideal_asset_value + running_cash_balance if use_cash_flow else ideal_asset_value
        
        daily_records.append({
            '日期': df['日期'].iloc[idx],
            '收盘价': close_price,
            '累计存入': running_deposited if use_cash_flow else running_investment,
            '累计投入': running_investment,
            '现金余额': running_cash_balance,
            '总资产': total_asset,
            '理想持仓份额': running_shares_ideal,
            '实际持仓份额': running_shares_real,
            '理想持仓市值': ideal_asset_value,
            '实际持仓市值': real_asset_value,
            '理想持仓均价': ideal_avg_cost,
            '实际持仓均价': real_avg_cost,
            '累计申购费': running_purchase_fee,
            '累计管理费': running_management_fee
        })
    
    cash_balance = cash_account.balance if cash_account else 0
    
    return pd.DataFrame(daily_records), investment_by_date, total_deposited, cash_balance


def run_comparison_backtest(df, investment_dates, base_amount, strategy_config, realistic_params=None, use_cash_flow=True):
    fixed_results_df, fixed_shares, fixed_investment, fixed_fees = run_backtest_calculation(
        df, investment_dates, base_amount, realistic_params
    )
    
    fixed_daily_df = calculate_daily_assets(
        df, investment_dates, base_amount, realistic_params
    )
    
    smart_results_df, smart_shares, smart_investment, smart_fees, smart_deposited, smart_cash_balance = run_smart_backtest_calculation(
        df, investment_dates, base_amount, strategy_config, realistic_params, use_cash_flow
    )
    
    smart_daily_df, smart_investment_by_date, smart_total_deposited, smart_final_cash = calculate_smart_daily_assets(
        df, investment_dates, base_amount, strategy_config, realistic_params, use_cash_flow
    )
    
    return {
        'fixed': {
            'results_df': fixed_results_df,
            'daily_df': fixed_daily_df,
            'total_shares': fixed_shares,
            'total_investment': fixed_investment,
            'total_fees': fixed_fees,
            'total_deposited': fixed_investment
        },
        'smart': {
            'results_df': smart_results_df,
            'daily_df': smart_daily_df,
            'total_shares': smart_shares,
            'total_investment': smart_investment,
            'total_fees': smart_fees,
            'investment_by_date': smart_investment_by_date,
            'total_deposited': smart_deposited,
            'cash_balance': smart_cash_balance
        }
    }
