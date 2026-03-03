import pandas as pd
import numpy as np
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from .investment import get_investment_dates, run_backtest_calculation


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
    
    df_date_col = df.copy()
    df_date_col['日期_date'] = df_date_col['日期'].dt.date
    
    end_row = df_date_col[df_date_col['日期_date'] == actual_end_date]
    if len(end_row) == 0:
        end_row = df_date_col[df_date_col['日期_date'] <= actual_end_date].tail(1)
    
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


def run_probability_analysis(df, analysis_start_date, analysis_end_date, investment_duration_years,
                             freq_type, freq_param, amount, realistic_params=None, 
                             sampling='monthly', progress_callback=None):
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
    
    for i, start_date in enumerate(start_dates):
        result = run_single_backtest(
            df, start_date, investment_duration_years, freq_type, freq_param, amount, realistic_params
        )
        if result is not None:
            results.append(result)
        
        if progress_callback and (i + 1) % max(1, total // 100) == 0:
            progress_callback(i + 1, total)
    
    return results


def calculate_probability_statistics(results, realistic_params=None):
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
