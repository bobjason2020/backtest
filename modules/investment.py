import pandas as pd
import numpy as np
from datetime import timedelta, date
from typing import Dict, Any, List, Optional, Set, Tuple

from .config import WEEKDAY_MAP
from .fee_calculator import FeeCalculator, calculate_purchase_fee, apply_tracking_error
from .smart_strategy import SmartStrategyConfig, create_strategy, StrategySignal
from .cash_flow import CashFlowAccount
from .utils import TradingCalendar, calculate_total_return, calculate_annualized_return, calculate_years_between


def _get_trading_dates_set(df: pd.DataFrame) -> Set[date]:
    return set(df['日期'].dt.date)


def _find_investment_row(df: pd.DataFrame, target_date: date, dates: pd.Series) -> Optional[pd.Series]:
    row = df[dates == target_date]
    if len(row) > 0:
        return row.iloc[0]
    return None


def _process_single_investment(
    inv_date: date,
    price: float,
    amount: float,
    purchase_fee_rate: float
) -> Dict[str, Any]:
    actual_amount = amount * (1 - purchase_fee_rate)
    purchase_fee = amount * purchase_fee_rate
    shares = actual_amount / price
    
    return {
        '日期': inv_date,
        '收盘价': price,
        '投入金额': amount,
        '申购费用': purchase_fee,
        '实际买入金额': actual_amount,
        '买入份额': shares
    }


def _accumulate_results(
    results: List[Dict[str, Any]],
    new_record: Dict[str, Any],
    total_shares: float,
    total_investment: float,
    total_purchase_fee: float
) -> Tuple[List[Dict[str, Any]], float, float, float]:
    total_shares += new_record['买入份额']
    total_investment += new_record['投入金额']
    total_purchase_fee += new_record['申购费用']
    
    record = new_record.copy()
    record['累计份额'] = total_shares
    record['累计投入'] = total_investment
    record['累计申购费'] = total_purchase_fee
    
    results.append(record)
    
    return results, total_shares, total_investment, total_purchase_fee


def _init_daily_records() -> List[Dict[str, Any]]:
    return []


def _process_daily_fees(
    shares: float,
    price: float,
    fee_calculator: FeeCalculator
) -> Tuple[float, float]:
    if shares <= 0:
        return 0.0, shares
    
    daily_fee_shares = shares * (fee_calculator.management_fee_rate + fee_calculator.custody_fee_rate) / 365
    daily_fee_value = daily_fee_shares * price
    new_shares = shares - daily_fee_shares
    
    return daily_fee_value, new_shares


def _calculate_asset_values(
    shares: float,
    price: float,
    investment: float,
    fee_calculator: Optional[FeeCalculator]
) -> Tuple[float, float, float, float]:
    ideal_asset_value = shares * price
    ideal_avg_cost = investment / shares if shares > 0 else 0
    
    if fee_calculator is None or shares <= 0:
        return ideal_asset_value, ideal_asset_value, ideal_avg_cost, ideal_avg_cost
    
    effective_price = fee_calculator.apply_tracking_error(price)
    stock_asset = shares * effective_price * (1 - fee_calculator.cash_ratio)
    cash_asset = investment * fee_calculator.cash_ratio
    real_asset_value = stock_asset + cash_asset
    real_avg_cost = investment / shares if shares > 0 else 0
    
    return ideal_asset_value, real_asset_value, ideal_avg_cost, real_avg_cost


def _process_smart_buy(
    date: date,
    price: float,
    requested_amount: float,
    multiplier: float,
    fee_calculator: FeeCalculator,
    cash_account: Optional[CashFlowAccount],
    current_shares: float,
    current_investment: float,
    current_purchase_fee: float
) -> Tuple[Dict[str, Any], float, float, float, float, float]:
    actual_amount_raw = requested_amount
    
    if cash_account:
        actual_amount_raw = cash_account.get_available_amount(requested_amount)
        if actual_amount_raw > 0:
            cash_account.withdraw(actual_amount_raw)
    
    if actual_amount_raw <= 0:
        return {
            '日期': date,
            '收盘价': price,
            '操作': '跳过',
            '原因': '现金余额不足' if multiplier > 0 else '无可用资金'
        }, current_shares, current_investment, current_purchase_fee, 0.0, 0.0
    
    actual_amount = actual_amount_raw * (1 - fee_calculator.purchase_fee_rate)
    purchase_fee = actual_amount_raw * fee_calculator.purchase_fee_rate
    shares = actual_amount / price if price > 0 else 0
    
    new_shares = current_shares + shares
    new_investment = current_investment + actual_amount_raw
    new_purchase_fee = current_purchase_fee + purchase_fee
    
    return {
        '日期': date,
        '收盘价': price,
        '操作': '买入',
        '期望投入': requested_amount,
        '投入金额': actual_amount_raw,
        '申购费用': purchase_fee,
        '实际买入金额': actual_amount,
        '买入份额': shares,
        '累计份额': new_shares,
        '累计投入': new_investment,
        '累计申购费': new_purchase_fee
    }, new_shares, new_investment, new_purchase_fee, actual_amount_raw, purchase_fee


def _process_smart_sell(
    date: date,
    price: float,
    current_shares: float,
    sell_ratio: float,
    fee_calculator: FeeCalculator,
    cash_account: Optional[CashFlowAccount],
    current_investment: float,
    current_redemption_fee: float
) -> Tuple[Dict[str, Any], float, float, float, float, float]:
    if current_shares <= 0 or price <= 0:
        return {
            '日期': date,
            '收盘价': price,
            '操作': '跳过',
            '原因': '无持仓可卖出'
        }, current_shares, current_investment, current_redemption_fee, 0.0, 0.0
    
    sell_shares = current_shares * sell_ratio
    sell_amount_raw = sell_shares * price
    redemption_fee = sell_amount_raw * fee_calculator.redemption_fee_rate
    sell_amount_net = sell_amount_raw - redemption_fee
    
    new_shares = current_shares - sell_shares
    new_investment = current_investment - sell_amount_raw
    new_redemption_fee = current_redemption_fee + redemption_fee
    
    if cash_account:
        cash_account.receive_from_sale(sell_amount_net)
    
    return {
        '日期': date,
        '收盘价': price,
        '操作': '卖出',
        '卖出比例': sell_ratio,
        '卖出份额': sell_shares,
        '卖出金额': sell_amount_raw,
        '赎回费用': redemption_fee,
        '实际卖出金额': sell_amount_net,
        '剩余份额': new_shares,
        '累计投入': new_investment,
        '累计赎回费': new_redemption_fee
    }, new_shares, new_investment, new_redemption_fee, sell_amount_net, redemption_fee


def get_investment_dates(
    df: pd.DataFrame,
    start_date: date,
    end_date: date,
    freq_type: str,
    freq_param: str
) -> List[date]:
    trading_calendar = TradingCalendar(df['日期'])
    investment_dates = []
    
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    if freq_type == "一次性投入":
        current_dt = start_dt
        while current_dt <= end_dt:
            current_date = current_dt.date()
            if trading_calendar.is_trading_day(current_date):
                investment_dates.append(current_date)
                break
            current_dt += timedelta(days=1)
    
    elif freq_type == "按日":
        current_dt = start_dt
        while current_dt <= end_dt:
            current_date = current_dt.date()
            if trading_calendar.is_trading_day(current_date):
                investment_dates.append(current_date)
            current_dt += timedelta(days=1)
    
    elif freq_type == "按周":
        target_weekday = WEEKDAY_MAP[freq_param]
        
        current_dt = start_dt
        while current_dt <= end_dt:
            if current_dt.weekday() == target_weekday:
                current_date = current_dt.date()
                if trading_calendar.is_trading_day(current_date):
                    investment_dates.append(current_date)
                else:
                    next_trading = trading_calendar.get_next_trading_day(current_date, end_dt.date())
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
                if trading_calendar.is_trading_day(target_date):
                    investment_dates.append(target_date)
                else:
                    next_trading = trading_calendar.get_next_trading_day(target_date, end_dt.date())
                    if next_trading and next_trading not in investment_dates:
                        investment_dates.append(next_trading)
            
            if current_dt.month == 12:
                current_dt = current_dt.replace(year=current_dt.year + 1, month=1)
            else:
                current_dt = current_dt.replace(month=current_dt.month + 1)
        
        investment_dates = sorted(list(set(investment_dates)))
    
    return investment_dates


def find_next_trading_day(target_date: date, trading_dates: Set[date], end_date: date) -> Optional[date]:
    current = target_date
    while current <= end_date:
        current += timedelta(days=1)
        if current in trading_dates:
            return current
    return None


def run_backtest_calculation(
    df: pd.DataFrame,
    investment_dates: List[date],
    amount: float,
    realistic_params: Optional[Dict[str, Any]] = None
) -> Tuple[pd.DataFrame, float, float, float]:
    dates = df['日期'].dt.date
    
    results = []
    total_shares = 0.0
    total_investment = 0.0
    total_purchase_fee = 0.0
    
    purchase_fee_rate = 0
    if realistic_params:
        purchase_fee_rate = realistic_params.get('purchase_fee', 0)
    
    for inv_date in investment_dates:
        row = _find_investment_row(df, inv_date, dates)
        if row is not None:
            close_price = row['收盘价']
            
            record = _process_single_investment(inv_date, close_price, amount, purchase_fee_rate)
            results, total_shares, total_investment, total_purchase_fee = _accumulate_results(
                results, record, total_shares, total_investment, total_purchase_fee
            )
    
    return pd.DataFrame(results), total_shares, total_investment, total_purchase_fee


def calculate_daily_assets(
    df: pd.DataFrame,
    investment_dates: List[date],
    amount: float,
    realistic_params: Optional[Dict[str, Any]] = None
) -> pd.DataFrame:
    dates = df['日期'].dt.date
    
    fee_calculator = None
    if realistic_params:
        fee_calculator = FeeCalculator(
            purchase_fee_rate=realistic_params.get('purchase_fee', 0),
            management_fee_rate=realistic_params.get('management_fee', 0),
            custody_fee_rate=realistic_params.get('custody_fee', 0),
            cash_ratio=realistic_params.get('cash_ratio', 0),
            tracking_error=realistic_params.get('tracking_error', 0),
            tracking_error_mode=realistic_params.get('tracking_error_mode', "固定折扣"),
            random_seed=42
        )
    
    purchase_fee_rate = 0
    if realistic_params:
        purchase_fee_rate = realistic_params.get('purchase_fee', 0)
    
    investment_by_date = {}
    for inv_date in investment_dates:
        row = _find_investment_row(df, inv_date, dates)
        if row is not None:
            close_price = row['收盘价']
            actual_amount = amount * (1 - purchase_fee_rate)
            shares = actual_amount / close_price
            investment_by_date[inv_date] = {
                'amount': amount,
                'shares': shares,
                'purchase_fee': amount * purchase_fee_rate
            }
    
    daily_records = _init_daily_records()
    running_investment = 0.0
    running_shares_ideal = 0.0
    running_shares_real = 0.0
    running_purchase_fee = 0.0
    running_management_fee = 0.0
    
    for idx in range(len(df)):
        current_date = dates.iloc[idx]
        close_price = df['收盘价'].iloc[idx]
        
        if current_date in investment_by_date:
            running_investment += investment_by_date[current_date]['amount']
            running_shares_ideal += investment_by_date[current_date]['shares']
            running_shares_real += investment_by_date[current_date]['shares']
            running_purchase_fee += investment_by_date[current_date]['purchase_fee']
        
        ideal_asset_value, real_asset_value, ideal_avg_cost, real_avg_cost = _calculate_asset_values(
            running_shares_real, close_price, running_investment, fee_calculator
        )
        
        if fee_calculator and running_shares_real > 0:
            daily_fee_value, running_shares_real = _process_daily_fees(
                running_shares_real, close_price, fee_calculator
            )
            running_management_fee += daily_fee_value
            
            ideal_asset_value, real_asset_value, ideal_avg_cost, real_avg_cost = _calculate_asset_values(
                running_shares_real, close_price, running_investment, fee_calculator
            )
        
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


def calculate_lump_sum_return(
    df: pd.DataFrame,
    start_date: date,
    end_date: date
) -> Tuple[float, float]:
    df_filtered = df[(df['日期'].dt.date >= start_date) & (df['日期'].dt.date <= end_date)]
    if len(df_filtered) == 0:
        return 0, 0
    
    start_price = df_filtered.iloc[0]['收盘价']
    end_price = df_filtered.iloc[-1]['收盘价']
    
    total_return = calculate_total_return(end_price, start_price)
    
    years = calculate_years_between(start_date, end_date)
    if years > 0:
        annualized = calculate_annualized_return(total_return, years)
    else:
        annualized = 0
    
    return total_return, annualized


def run_smart_backtest_calculation(
    df: pd.DataFrame,
    investment_dates: List[date],
    base_amount: float,
    strategy_config: SmartStrategyConfig,
    realistic_params: Optional[Dict[str, Any]] = None,
    use_cash_flow: bool = True
) -> Tuple[pd.DataFrame, float, float, float, float, float, float, float]:
    dates = df['日期'].dt.date
    
    strategy = create_strategy(strategy_config)
    cash_account = CashFlowAccount() if use_cash_flow else None
    
    results = []
    total_shares = 0.0
    total_investment = 0.0
    total_purchase_fee = 0.0
    total_deposited = 0.0
    total_from_sale = 0.0
    total_redemption_fee = 0.0
    
    fee_calculator = FeeCalculator()
    if realistic_params:
        fee_calculator = FeeCalculator(
            purchase_fee_rate=realistic_params.get('purchase_fee', 0),
            redemption_fee_rate=realistic_params.get('redemption_fee', 0)
        )
    
    for inv_date in investment_dates:
        row = _find_investment_row(df, inv_date, dates)
        if row is None:
            continue
        
        close_price = row['收盘价']
        signal = strategy.calculate_signal(df, inv_date)
        multiplier = signal.multiplier
        
        if use_cash_flow and cash_account:
            cash_account.deposit(base_amount)
            total_deposited += base_amount
        
        if multiplier < 0:
            sell_ratio = min(abs(multiplier), 1.0)
            record, total_shares, total_investment, total_redemption_fee, sell_amount_net, _ = _process_smart_sell(
                inv_date, close_price, total_shares, sell_ratio, fee_calculator, 
                cash_account, total_investment, total_redemption_fee
            )
            
            if '卖出金额' in record:
                total_from_sale += sell_amount_net
            
            record['信号'] = signal.signal
            record['倍数'] = multiplier
            record['原因'] = signal.reason
            results.append(record)
        else:
            requested_amount = base_amount * multiplier
            record, total_shares, total_investment, total_purchase_fee, _, _ = _process_smart_buy(
                inv_date, close_price, requested_amount, multiplier, fee_calculator,
                cash_account, total_shares, total_investment, total_purchase_fee
            )
            
            record['信号'] = signal.signal
            record['倍数'] = multiplier
            record['原因'] = signal.reason
            results.append(record)
    
    cash_balance = cash_account.balance if cash_account else 0
    total_deposited = total_deposited if use_cash_flow else total_investment
    
    return pd.DataFrame(results), total_shares, total_investment, total_purchase_fee, total_deposited, cash_balance, total_from_sale, total_redemption_fee


def calculate_smart_daily_assets(
    df: pd.DataFrame,
    investment_dates: List[date],
    base_amount: float,
    strategy_config: SmartStrategyConfig,
    realistic_params: Optional[Dict[str, Any]] = None,
    use_cash_flow: bool = True
) -> Tuple[pd.DataFrame, Dict[date, Dict[str, Any]], float, float, float]:
    dates = df['日期'].dt.date
    
    strategy = create_strategy(strategy_config)
    cash_account = CashFlowAccount() if use_cash_flow else None
    
    fee_calculator = FeeCalculator(random_seed=42)
    if realistic_params:
        fee_calculator = FeeCalculator(
            purchase_fee_rate=realistic_params.get('purchase_fee', 0),
            management_fee_rate=realistic_params.get('management_fee', 0),
            custody_fee_rate=realistic_params.get('custody_fee', 0),
            cash_ratio=realistic_params.get('cash_ratio', 0),
            tracking_error=realistic_params.get('tracking_error', 0),
            tracking_error_mode=realistic_params.get('tracking_error_mode', "固定折扣"),
            redemption_fee_rate=realistic_params.get('redemption_fee', 0),
            random_seed=42
        )
    
    signals_by_date = {}
    for inv_date in investment_dates:
        row = _find_investment_row(df, inv_date, dates)
        if row is not None:
            signal = strategy.calculate_signal(df, inv_date)
            signals_by_date[inv_date] = {
                'signal': signal.signal,
                'multiplier': signal.multiplier,
                'reason': signal.reason
            }
    
    daily_records = _init_daily_records()
    running_investment = 0.0
    running_shares_ideal = 0.0
    running_shares_real = 0.0
    running_purchase_fee = 0.0
    running_management_fee = 0.0
    running_redemption_fee = 0.0
    running_deposited = 0.0
    running_from_sale = 0.0
    
    for idx in range(len(df)):
        current_date = dates.iloc[idx]
        close_price = df['收盘价'].iloc[idx]
        
        if current_date in signals_by_date:
            sig_data = signals_by_date[current_date]
            multiplier = sig_data['multiplier']
            
            if use_cash_flow and cash_account:
                cash_account.deposit(base_amount)
                running_deposited += base_amount
            
            if multiplier < 0:
                sell_ratio = min(abs(multiplier), 1.0)
                if running_shares_ideal > 0:
                    _, running_shares_ideal, running_investment, running_redemption_fee, sell_amount_net, _ = _process_smart_sell(
                        current_date, close_price, running_shares_ideal, sell_ratio, fee_calculator,
                        cash_account, running_investment, running_redemption_fee
                    )
                    running_shares_real = running_shares_ideal
                    running_from_sale += sell_amount_net
            else:
                requested_amount = base_amount * multiplier
                
                if use_cash_flow and cash_account:
                    actual_amount_raw = cash_account.get_available_amount(requested_amount)
                    if actual_amount_raw > 0:
                        cash_account.withdraw(actual_amount_raw)
                else:
                    actual_amount_raw = requested_amount
                
                if actual_amount_raw > 0:
                    actual_amount = actual_amount_raw * (1 - fee_calculator.purchase_fee_rate)
                    shares = actual_amount / close_price if close_price > 0 else 0
                    
                    running_shares_ideal += shares
                    running_shares_real += shares
                    running_investment += actual_amount_raw
                    running_purchase_fee += actual_amount_raw * fee_calculator.purchase_fee_rate
        
        ideal_asset_value, real_asset_value, ideal_avg_cost, real_avg_cost = _calculate_asset_values(
            running_shares_real, close_price, running_investment, fee_calculator
        )
        
        if realistic_params and running_shares_real > 0:
            daily_fee_value, running_shares_real = _process_daily_fees(
                running_shares_real, close_price, fee_calculator
            )
            running_management_fee += daily_fee_value
            
            ideal_asset_value, real_asset_value, ideal_avg_cost, real_avg_cost = _calculate_asset_values(
                running_shares_real, close_price, running_investment, fee_calculator
            )
        
        cash_balance = cash_account.balance if cash_account else 0
        total_asset = ideal_asset_value + cash_balance if use_cash_flow else ideal_asset_value
        
        daily_records.append({
            '日期': df['日期'].iloc[idx],
            '收盘价': close_price,
            '累计存入': running_deposited if use_cash_flow else running_investment,
            '累计投入': running_investment,
            '现金余额': cash_balance,
            '总资产': total_asset,
            '理想持仓份额': running_shares_ideal,
            '实际持仓份额': running_shares_real,
            '理想持仓市值': ideal_asset_value,
            '实际持仓市值': real_asset_value,
            '理想持仓均价': ideal_avg_cost,
            '实际持仓均价': real_avg_cost,
            '累计申购费': running_purchase_fee,
            '累计管理费': running_management_fee,
            '累计赎回费': running_redemption_fee,
            '累计卖出收入': running_from_sale
        })
    
    final_cash_balance = cash_account.balance if cash_account else 0
    
    return pd.DataFrame(daily_records), signals_by_date, running_deposited, final_cash_balance, running_from_sale


def run_comparison_backtest(
    df: pd.DataFrame,
    investment_dates: List[date],
    base_amount: float,
    strategy_config: SmartStrategyConfig,
    realistic_params: Optional[Dict[str, Any]] = None,
    use_cash_flow: bool = True
) -> Dict[str, Any]:
    fixed_results_df, fixed_shares, fixed_investment, fixed_fees = run_backtest_calculation(
        df, investment_dates, base_amount, realistic_params
    )
    
    fixed_daily_df = calculate_daily_assets(
        df, investment_dates, base_amount, realistic_params
    )
    
    smart_results_df, smart_shares, smart_investment, smart_fees, smart_deposited, smart_cash_balance, smart_from_sale, smart_redemption_fees = run_smart_backtest_calculation(
        df, investment_dates, base_amount, strategy_config, realistic_params, use_cash_flow
    )
    
    smart_daily_df, smart_signals_by_date, smart_total_deposited, smart_final_cash, smart_total_from_sale = calculate_smart_daily_assets(
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
            'signals_by_date': smart_signals_by_date,
            'total_deposited': smart_total_deposited,
            'cash_balance': smart_final_cash,
            'total_from_sale': smart_total_from_sale,
            'total_redemption_fees': smart_redemption_fees
        }
    }
