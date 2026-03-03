import pandas as pd
import numpy as np
from datetime import timedelta
from dateutil.relativedelta import relativedelta
import streamlit as st
import json
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from .investment import get_investment_dates, run_backtest_calculation, run_smart_backtest_calculation
from .smart_strategy import SmartStrategyConfig, create_strategy


def _hash_df(df):
    if df is None:
        return "None"
    return str(pd.util.hash_pandas_object(df).sum())


def _hash_params(params):
    if params is None:
        return "None"
    if isinstance(params, dict):
        return json.dumps(params, sort_keys=True, default=str)
    return str(params)


def _results_to_hashable(results):
    if not results:
        return "empty"
    hash_parts = []
    for r in results[:10]:
        hash_parts.append(json.dumps(r, sort_keys=True, default=str))
    return str(hashsum(hash_parts))


def hashsum(parts):
    import hashlib
    return hashlib.md5('|'.join(parts).encode()).hexdigest()


def get_all_possible_start_dates(df, analysis_start_date, analysis_end_date, investment_duration_years):
    df_filtered = df[(df['日期'].dt.date >= analysis_start_date) & (df['日期'].dt.date <= analysis_end_date)]
    if len(df_filtered) == 0:
        return []
    
    trading_dates = df_filtered['日期'].dt.date.tolist()
    
    duration_days = int(investment_duration_years * 365)
    max_data_date = df['日期'].max().date()
    
    valid_start_dates = []
    for date in trading_dates:
        end_date = date + timedelta(days=duration_days)
        if end_date <= max_data_date:
            valid_start_dates.append(date)
    
    return sorted(list(set(valid_start_dates)))


def run_single_backtest(df, start_date, investment_duration_years, freq_type, freq_param, amount, realistic_params=None):
    duration_days = int(investment_duration_years * 365)
    end_date = start_date + timedelta(days=duration_days)
    
    trading_dates = set(df['日期'].dt.date)
    actual_end_date = end_date
    while actual_end_date not in trading_dates and actual_end_date <= df['日期'].max().date():
        actual_end_date += timedelta(days=1)
    
    investment_dates = get_investment_dates(df, start_date, actual_end_date, freq_type, freq_param)
    
    if len(investment_dates) == 0:
        return None
    
    results_df, total_shares_ideal, total_investment, total_purchase_fee = run_backtest_calculation(
        df, investment_dates, amount, realistic_params
    )
    
    if len(results_df) == 0:
        return None
    
    dates = df['日期'].dt.date
    end_row = df[dates == actual_end_date]
    if len(end_row) == 0:
        end_row = df[dates <= actual_end_date].tail(1)
    
    if len(end_row) == 0:
        return None
    
    end_price = end_row['收盘价'].values[0]
    
    ideal_final_asset = total_shares_ideal * end_price
    ideal_total_return = (ideal_final_asset - total_investment) / total_investment * 100
    
    actual_years = (actual_end_date - start_date).days / 365.0
    
    if actual_years > 0:
        ideal_annualized = ((1 + ideal_total_return / 100) ** (1 / actual_years) - 1) * 100
    else:
        ideal_annualized = 0
    
    real_final_asset = ideal_final_asset
    real_total_return = ideal_total_return
    real_annualized = ideal_annualized
    total_fees = total_purchase_fee
    
    if realistic_params:
        management_fee_rate = realistic_params.get('management_fee', 0)
        custody_fee_rate = realistic_params.get('custody_fee', 0)
        cash_ratio = realistic_params.get('cash_ratio', 0)
        tracking_error = realistic_params.get('tracking_error', 0)
        tracking_error_mode = realistic_params.get('tracking_error_mode', "固定折扣")
        redemption_fee_rate = realistic_params.get('redemption_fee', 0)
        
        daily_fee_rate = (management_fee_rate + custody_fee_rate) / 365
        total_days = (actual_end_date - start_date).days
        
        avg_daily_shares = total_shares_ideal
        fee_reduction_factor = 1 - daily_fee_rate * total_days / 2
        real_shares = total_shares_ideal * fee_reduction_factor
        
        from .fee_calculator import apply_tracking_error
        effective_price = apply_tracking_error(end_price, tracking_error, tracking_error_mode)
        
        stock_asset = real_shares * effective_price * (1 - cash_ratio)
        cash_asset = total_investment * cash_ratio
        real_final_asset = stock_asset + cash_asset
        
        redemption_fee = real_final_asset * redemption_fee_rate
        real_final_asset -= redemption_fee
        
        total_management_fee = total_shares_ideal * (1 - fee_reduction_factor) * end_price
        total_fees = total_purchase_fee + total_management_fee + redemption_fee
        
        real_total_return = (real_final_asset - total_investment) / total_investment * 100
        
        if actual_years > 0:
            real_annualized = ((1 + real_total_return / 100) ** (1 / actual_years) - 1) * 100
        else:
            real_annualized = 0
    
    return {
        'start_date': start_date,
        'end_date': actual_end_date,
        'investment_count': len(investment_dates),
        'total_investment': total_investment,
        'ideal_final_asset': ideal_final_asset,
        'ideal_total_return': ideal_total_return,
        'ideal_annualized': ideal_annualized,
        'real_final_asset': real_final_asset,
        'real_total_return': real_total_return,
        'real_annualized': real_annualized,
        'total_fees': total_fees,
        'actual_years': actual_years
    }


def _run_single_backtest_wrapper(args):
    df, start_date, investment_duration_years, freq_type, freq_param, amount, realistic_params = args
    return run_single_backtest(df, start_date, investment_duration_years, freq_type, freq_param, amount, realistic_params)


def _run_single_smart_backtest_wrapper(args):
    df, start_date, investment_duration_years, freq_type, freq_param, base_amount, strategy_config, realistic_params = args
    return run_single_smart_backtest(df, start_date, investment_duration_years, freq_type, freq_param, base_amount, strategy_config, realistic_params)


def _run_comparison_backtest_wrapper(args):
    df, start_date, investment_duration_years, freq_type, freq_param, base_amount, strategy_config, realistic_params = args
    fixed = run_single_backtest(df, start_date, investment_duration_years, freq_type, freq_param, base_amount, realistic_params)
    smart = run_single_smart_backtest(df, start_date, investment_duration_years, freq_type, freq_param, base_amount, strategy_config, realistic_params)
    return fixed, smart


def run_probability_analysis(df, analysis_start_date, analysis_end_date, investment_duration_years,
                             freq_type, freq_param, amount, realistic_params=None, 
                             sampling='monthly', progress_callback=None):
    start_time = time.time()
    
    start_dates = get_all_possible_start_dates(df, analysis_start_date, analysis_end_date, investment_duration_years)
    
    if sampling == 'monthly':
        sampled_dates = []
        current_year = None
        current_month = None
        for date in start_dates:
            if date.year != current_year or date.month != current_month:
                sampled_dates.append(date)
                current_year = date.year
                current_month = date.month
        start_dates = sampled_dates
    elif sampling == 'weekly':
        sampled_dates = []
        last_date = None
        for date in start_dates:
            if last_date is None or (date - last_date).days >= 7:
                sampled_dates.append(date)
                last_date = date
        start_dates = sampled_dates
    
    results = []
    total = len(start_dates)
    
    num_workers = min(multiprocessing.cpu_count(), 8)
    
    if num_workers > 1 and total > 4:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_date = {
                executor.submit(_run_single_backtest_wrapper, 
                               (df, start_date, investment_duration_years, 
                                freq_type, freq_param, amount, realistic_params)): start_date
                for start_date in start_dates
            }
            
            completed = 0
            for future in as_completed(future_to_date):
                result = future.result()
                if result is not None:
                    results.append(result)
                completed += 1
                if progress_callback and completed % max(1, total // 100) == 0:
                    progress_callback(completed, total)
    else:
        for i, start_date in enumerate(start_dates):
            result = run_single_backtest(
                df, start_date, investment_duration_years, freq_type, freq_param, amount, realistic_params
            )
            if result is not None:
                results.append(result)
            
            if progress_callback and (i + 1) % max(1, total // 100) == 0:
                progress_callback(i + 1, total)
    
    elapsed_time = time.time() - start_time
    return results, elapsed_time


def calculate_probability_statistics(results, realistic_params=None):
    if not results:
        return None
    
    results_hash = _results_to_hashable(results)
    params_hash = _hash_params(realistic_params)
    
    return _calculate_probability_statistics_cached(results_hash, results, params_hash, realistic_params)


@st.cache_data(ttl=3600, show_spinner=False)
def _calculate_probability_statistics_cached(results_hash, results, params_hash, realistic_params=None):
    if not results:
        return None
    
    df = pd.DataFrame(results)
    
    if realistic_params:
        return_col = 'real_total_return'
        annualized_col = 'real_annualized'
        asset_col = 'real_final_asset'
    else:
        return_col = 'ideal_total_return'
        annualized_col = 'ideal_annualized'
        asset_col = 'ideal_final_asset'
    
    total_count = len(df)
    profit_count = (df[return_col] > 0).sum()
    profit_probability = profit_count / total_count * 100
    
    avg_return = df[return_col].mean()
    median_return = df[return_col].median()
    max_return = df[return_col].max()
    min_return = df[return_col].min()
    std_return = df[return_col].std()
    
    avg_annualized = df[annualized_col].mean()
    median_annualized = df[annualized_col].median()
    max_annualized = df[annualized_col].max()
    min_annualized = df[annualized_col].min()
    
    return_bins = [-float('inf'), -50, -30, -20, -10, 0, 10, 20, 30, 50, float('inf')]
    return_labels = ['<-50%', '-50%~-30%', '-30%~-20%', '-20%~-10%', '-10%~0%', 
                     '0%~10%', '10%~20%', '20%~30%', '30%~50%', '>50%']
    
    df['return_bin'] = pd.cut(df[return_col], bins=return_bins, labels=return_labels)
    return_distribution = df['return_bin'].value_counts().sort_index()
    return_distribution_pct = (return_distribution / total_count * 100).round(2)
    
    thresholds = [-20, -10, 0, 5, 10, 15, 20, 30]
    cumulative_prob = {}
    for threshold in thresholds:
        prob = (df[return_col] >= threshold).sum() / total_count * 100
        cumulative_prob[f'>={threshold}%'] = prob
    
    annualized_bins = [-float('inf'), -20, -15, -10, -5, 0, 5, 10, 15, 20, float('inf')]
    annualized_labels = ['<-20%', '-20%~-15%', '-15%~-10%', '-10%~-5%', '-5%~0%', 
                         '0%~5%', '5%~10%', '10%~15%', '15%~20%', '>20%']
    
    df['annualized_bin'] = pd.cut(df[annualized_col], bins=annualized_bins, labels=annualized_labels)
    annualized_distribution = df['annualized_bin'].value_counts().sort_index()
    annualized_distribution_pct = (annualized_distribution / total_count * 100).round(2)
    
    annualized_thresholds = [-2, 0, 2, 4, 6, 8, 10, 12]
    annualized_cumulative_prob = {}
    for threshold in annualized_thresholds:
        prob = (df[annualized_col] >= threshold).sum() / total_count * 100
        annualized_cumulative_prob[f'>={threshold}%'] = prob
    
    avg_investment_count = df['investment_count'].mean()
    avg_total_investment = df['total_investment'].mean()
    avg_years = df['actual_years'].mean()
    
    return {
        'total_count': total_count,
        'profit_count': profit_count,
        'profit_probability': profit_probability,
        'avg_return': avg_return,
        'median_return': median_return,
        'max_return': max_return,
        'min_return': min_return,
        'std_return': std_return,
        'avg_annualized': avg_annualized,
        'median_annualized': median_annualized,
        'max_annualized': max_annualized,
        'min_annualized': min_annualized,
        'return_distribution': return_distribution.to_dict(),
        'return_distribution_pct': return_distribution_pct.to_dict(),
        'cumulative_prob': cumulative_prob,
        'annualized_distribution': annualized_distribution.to_dict(),
        'annualized_distribution_pct': annualized_distribution_pct.to_dict(),
        'annualized_cumulative_prob': annualized_cumulative_prob,
        'avg_investment_count': avg_investment_count,
        'avg_total_investment': avg_total_investment,
        'avg_years': avg_years,
        'results_df': df
    }


def run_single_smart_backtest(df, start_date, investment_duration_years, freq_type, freq_param, 
                               base_amount, strategy_config, realistic_params=None):
    duration_days = int(investment_duration_years * 365)
    end_date = start_date + timedelta(days=duration_days)
    
    trading_dates = set(df['日期'].dt.date)
    actual_end_date = end_date
    while actual_end_date not in trading_dates and actual_end_date <= df['日期'].max().date():
        actual_end_date += timedelta(days=1)
    
    investment_dates = get_investment_dates(df, start_date, actual_end_date, freq_type, freq_param)
    
    if len(investment_dates) == 0:
        return None
    
    results_df, total_shares_ideal, total_investment, total_purchase_fee = run_smart_backtest_calculation(
        df, investment_dates, base_amount, strategy_config, realistic_params
    )
    
    if len(results_df) == 0:
        return None
    
    dates = df['日期'].dt.date
    end_row = df[dates == actual_end_date]
    if len(end_row) == 0:
        end_row = df[dates <= actual_end_date].tail(1)
    
    if len(end_row) == 0:
        return None
    
    end_price = end_row['收盘价'].values[0]
    
    ideal_final_asset = total_shares_ideal * end_price
    ideal_total_return = (ideal_final_asset - total_investment) / total_investment * 100 if total_investment > 0 else 0
    
    actual_years = (actual_end_date - start_date).days / 365.0
    
    if actual_years > 0 and ideal_total_return > -100:
        ideal_annualized = ((1 + ideal_total_return / 100) ** (1 / actual_years) - 1) * 100
    else:
        ideal_annualized = 0
    
    real_final_asset = ideal_final_asset
    real_total_return = ideal_total_return
    real_annualized = ideal_annualized
    total_fees = total_purchase_fee
    
    if realistic_params:
        management_fee_rate = realistic_params.get('management_fee', 0)
        custody_fee_rate = realistic_params.get('custody_fee', 0)
        cash_ratio = realistic_params.get('cash_ratio', 0)
        tracking_error = realistic_params.get('tracking_error', 0)
        tracking_error_mode = realistic_params.get('tracking_error_mode', "固定折扣")
        redemption_fee_rate = realistic_params.get('redemption_fee', 0)
        
        daily_fee_rate = (management_fee_rate + custody_fee_rate) / 365
        total_days = (actual_end_date - start_date).days
        
        fee_reduction_factor = 1 - daily_fee_rate * total_days / 2
        real_shares = total_shares_ideal * fee_reduction_factor
        
        from .fee_calculator import apply_tracking_error
        effective_price = apply_tracking_error(end_price, tracking_error, tracking_error_mode)
        
        stock_asset = real_shares * effective_price * (1 - cash_ratio)
        cash_asset = total_investment * cash_ratio
        real_final_asset = stock_asset + cash_asset
        
        redemption_fee = real_final_asset * redemption_fee_rate
        real_final_asset -= redemption_fee
        
        total_management_fee = total_shares_ideal * (1 - fee_reduction_factor) * end_price
        total_fees = total_purchase_fee + total_management_fee + redemption_fee
        
        real_total_return = (real_final_asset - total_investment) / total_investment * 100 if total_investment > 0 else 0
        
        if actual_years > 0 and real_total_return > -100:
            real_annualized = ((1 + real_total_return / 100) ** (1 / actual_years) - 1) * 100
        else:
            real_annualized = 0
    
    return {
        'start_date': start_date,
        'end_date': actual_end_date,
        'investment_count': len(investment_dates),
        'total_investment': total_investment,
        'ideal_final_asset': ideal_final_asset,
        'ideal_total_return': ideal_total_return,
        'ideal_annualized': ideal_annualized,
        'real_final_asset': real_final_asset,
        'real_total_return': real_total_return,
        'real_annualized': real_annualized,
        'total_fees': total_fees,
        'actual_years': actual_years
    }


def run_smart_probability_analysis(df, analysis_start_date, analysis_end_date, investment_duration_years,
                                    freq_type, freq_param, base_amount, strategy_config, realistic_params=None, 
                                    sampling='monthly', progress_callback=None):
    start_time = time.time()
    
    start_dates = get_all_possible_start_dates(df, analysis_start_date, analysis_end_date, investment_duration_years)
    
    if sampling == 'monthly':
        sampled_dates = []
        current_year = None
        current_month = None
        for date in start_dates:
            if date.year != current_year or date.month != current_month:
                sampled_dates.append(date)
                current_year = date.year
                current_month = date.month
        start_dates = sampled_dates
    elif sampling == 'weekly':
        sampled_dates = []
        last_date = None
        for date in start_dates:
            if last_date is None or (date - last_date).days >= 7:
                sampled_dates.append(date)
                last_date = date
        start_dates = sampled_dates
    
    results = []
    total = len(start_dates)
    
    num_workers = min(multiprocessing.cpu_count(), 8)
    
    if num_workers > 1 and total > 4:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_date = {
                executor.submit(_run_single_smart_backtest_wrapper, 
                               (df, start_date, investment_duration_years,
                                freq_type, freq_param, base_amount, strategy_config, realistic_params)): start_date
                for start_date in start_dates
            }
            
            completed = 0
            for future in as_completed(future_to_date):
                result = future.result()
                if result is not None:
                    results.append(result)
                completed += 1
                if progress_callback and completed % max(1, total // 100) == 0:
                    progress_callback(completed, total)
    else:
        for i, start_date in enumerate(start_dates):
            result = run_single_smart_backtest(
                df, start_date, investment_duration_years, freq_type, freq_param, 
                base_amount, strategy_config, realistic_params
            )
            if result is not None:
                results.append(result)
            
            if progress_callback and (i + 1) % max(1, total // 100) == 0:
                progress_callback(i + 1, total)
    
    elapsed_time = time.time() - start_time
    return results, elapsed_time


def run_comparison_probability_analysis(df, analysis_start_date, analysis_end_date, investment_duration_years,
                                         freq_type, freq_param, base_amount, strategy_config, realistic_params=None, 
                                         sampling='monthly', progress_callback=None):
    start_time = time.time()
    
    start_dates = get_all_possible_start_dates(df, analysis_start_date, analysis_end_date, investment_duration_years)
    
    if sampling == 'monthly':
        sampled_dates = []
        current_year = None
        current_month = None
        for date in start_dates:
            if date.year != current_year or date.month != current_month:
                sampled_dates.append(date)
                current_year = date.year
                current_month = date.month
        start_dates = sampled_dates
    elif sampling == 'weekly':
        sampled_dates = []
        last_date = None
        for date in start_dates:
            if last_date is None or (date - last_date).days >= 7:
                sampled_dates.append(date)
                last_date = date
        start_dates = sampled_dates
    
    fixed_results = []
    smart_results = []
    total = len(start_dates)
    
    num_workers = min(multiprocessing.cpu_count(), 8)
    
    if num_workers > 1 and total > 4:
        from concurrent.futures import ProcessPoolExecutor, as_completed
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_date = {
                executor.submit(_run_comparison_backtest_wrapper, 
                               (df, start_date, investment_duration_years, freq_type, freq_param, 
                                base_amount, strategy_config, realistic_params)): start_date
                for start_date in start_dates
            }
            
            completed = 0
            for future in as_completed(future_to_date):
                fixed_result, smart_result = future.result()
                if fixed_result is not None and smart_result is not None:
                    fixed_results.append(fixed_result)
                    smart_results.append(smart_result)
                completed += 1
                if progress_callback and completed % max(1, total // 100) == 0:
                    progress_callback(completed, total)
    else:
        for i, start_date in enumerate(start_dates):
            fixed_result = run_single_backtest(
                df, start_date, investment_duration_years, freq_type, freq_param, base_amount, realistic_params
            )
            smart_result = run_single_smart_backtest(
                df, start_date, investment_duration_years, freq_type, freq_param, 
                base_amount, strategy_config, realistic_params
            )
            
            if fixed_result is not None and smart_result is not None:
                fixed_results.append(fixed_result)
                smart_results.append(smart_result)
            
            if progress_callback and (i + 1) % max(1, total // 100) == 0:
                progress_callback(i + 1, total)
    
    elapsed_time = time.time() - start_time
    return fixed_results, smart_results, elapsed_time


def calculate_comparison_statistics(fixed_results, smart_results, realistic_params=None):
    if not fixed_results or not smart_results:
        return None
    
    fixed_hash = _results_to_hashable(fixed_results)
    smart_hash = _results_to_hashable(smart_results)
    params_hash = _hash_params(realistic_params)
    
    return _calculate_comparison_statistics_cached(fixed_hash, smart_hash, params_hash, fixed_results, smart_results, realistic_params)


@st.cache_data(ttl=3600, show_spinner=False)
def _calculate_comparison_statistics_cached(fixed_hash, smart_hash, params_hash, fixed_results, smart_results, realistic_params=None):
    if not fixed_results or not smart_results:
        return None
    
    fixed_df = pd.DataFrame(fixed_results)
    smart_df = pd.DataFrame(smart_results)
    
    if realistic_params:
        return_col = 'real_total_return'
        annualized_col = 'real_annualized'
    else:
        return_col = 'ideal_total_return'
        annualized_col = 'ideal_annualized'
    
    total_count = len(fixed_df)
    
    fixed_profit_prob = (fixed_df[return_col] > 0).sum() / total_count * 100
    smart_profit_prob = (smart_df[return_col] > 0).sum() / total_count * 100
    
    fixed_avg_return = fixed_df[return_col].mean()
    smart_avg_return = smart_df[return_col].mean()
    
    fixed_median_return = fixed_df[return_col].median()
    smart_median_return = smart_df[return_col].median()
    
    fixed_avg_annualized = fixed_df[annualized_col].mean()
    smart_avg_annualized = smart_df[annualized_col].mean()
    
    fixed_avg_investment = fixed_df['total_investment'].mean()
    smart_avg_investment = smart_df['total_investment'].mean()
    
    return_diff = smart_df[return_col].values - fixed_df[return_col].values
    annualized_diff = smart_df[annualized_col].values - fixed_df[annualized_col].values
    
    smart_win_count = (return_diff > 0).sum()
    smart_win_rate = smart_win_count / total_count * 100
    
    avg_return_diff = np.mean(return_diff)
    avg_annualized_diff = np.mean(annualized_diff)
    
    return {
        'total_count': total_count,
        'fixed_profit_probability': fixed_profit_prob,
        'smart_profit_probability': smart_profit_prob,
        'fixed_avg_return': fixed_avg_return,
        'smart_avg_return': smart_avg_return,
        'fixed_median_return': fixed_median_return,
        'smart_median_return': smart_median_return,
        'fixed_avg_annualized': fixed_avg_annualized,
        'smart_avg_annualized': smart_avg_annualized,
        'fixed_avg_investment': fixed_avg_investment,
        'smart_avg_investment': smart_avg_investment,
        'smart_win_rate': smart_win_rate,
        'smart_win_count': smart_win_count,
        'avg_return_diff': avg_return_diff,
        'avg_annualized_diff': avg_annualized_diff,
        'fixed_results_df': fixed_df,
        'smart_results_df': smart_df,
        'return_diff': return_diff.tolist(),
        'annualized_diff': annualized_diff.tolist()
    }
