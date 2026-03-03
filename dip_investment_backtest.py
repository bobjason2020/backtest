import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import random

st.set_page_config(page_title="定投收益回测工具", layout="wide", initial_sidebar_state="expanded")

st.title("定投收益回测工具")
st.markdown("---")

with st.sidebar:
    st.header("参数设置")
    
    uploaded_file = st.file_uploader("选择数据文件", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            df['日期'] = pd.to_datetime(df['日期'])
            df = df.sort_values('日期').reset_index(drop=True)
            
            min_date = df['日期'].min().date()
            max_date = df['日期'].max().date()
            total_days = (max_date - min_date).days
            max_years = total_days / 365.0
            
            st.success(f"数据加载成功！\n共 {len(df)} 条记录\n日期范围: {min_date} ~ {max_date}")
            
            st.subheader("定投区间")
            date_mode = st.radio("日期选择方式", ["手动选择日期", "按持有年限", "随机持有年限"], horizontal=True, index=2)
            
            start_date = None
            end_date = None
            
            if date_mode == "手动选择日期":
                col1, col2 = st.columns(2)
                with col1:
                    start_date = st.date_input("开始日期", value=min_date, min_value=min_date, max_value=max_date)
                with col2:
                    end_date = st.date_input("结束日期", value=max_date, min_value=min_date, max_value=max_date)
            
            elif date_mode == "按持有年限":
                start_date = st.date_input("开始日期", value=min_date, min_value=min_date, max_value=max_date)
                holding_years = st.number_input("持有年限", min_value=0.5, max_value=float(int(max_years * 10) / 10), value=3.0, step=0.5)
                end_date = start_date + timedelta(days=int(holding_years * 365))
                if end_date > max_date:
                    end_date = max_date
                    st.warning(f"持有年限超出数据范围，结束日期已调整为 {end_date}")
                st.info(f"结束日期: {end_date}")
            
            elif date_mode == "随机持有年限":
                holding_years = st.number_input("持有年限", min_value=0.5, max_value=float(int(max_years * 10) / 10), value=3.0, step=0.5)
                random_seed = st.checkbox("固定随机种子", value=False)
                if random_seed:
                    seed_value = st.number_input("随机种子", min_value=0, max_value=99999, value=42, step=1)
                else:
                    seed_value = None
                
                max_start_date = max_date - timedelta(days=int(holding_years * 365))
                if max_start_date < min_date:
                    st.warning(f"持有年限 {holding_years} 年超出数据范围，请减小持有年限")
                    start_date = min_date
                    end_date = max_date
                else:
                    if seed_value is not None:
                        random.seed(seed_value)
                    random_days = random.randint(0, (max_start_date - min_date).days)
                    start_date = min_date + timedelta(days=random_days)
                    end_date = start_date + timedelta(days=int(holding_years * 365))
                    if end_date > max_date:
                        end_date = max_date
                    st.info(f"随机选择的时间段:\n开始: {start_date}\n结束: {end_date}")
            
            st.subheader("定投频率")
            freq_type = st.radio("选择频率", ["按日", "按周", "按月"], horizontal=True, index=1)
            
            freq_param = None
            if freq_type == "按周":
                weekdays = ["周一", "周二", "周三", "周四", "周五"]
                weekday_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4}
                freq_param = st.selectbox("选择定投日", weekdays, index=0)
            elif freq_type == "按月":
                month_options = [f"{i}号" for i in range(1, 29)] + ["月底"]
                freq_param = st.selectbox("选择定投日", month_options, index=0)
            
            st.subheader("定投金额")
            amount = st.number_input("每次定投金额（元）", min_value=100, max_value=1000000, value=1000, step=100)
            
            st.subheader("基金现实因素")
            consider_realistic = st.checkbox("考虑基金现实因素", value=True)
            
            realistic_params = None
            if consider_realistic:
                st.markdown("**费用参数**")
                col_fee1, col_fee2 = st.columns(2)
                with col_fee1:
                    management_fee = st.number_input("管理费率（年化%）", min_value=0.0, max_value=3.0, value=0.5, step=0.01)
                with col_fee2:
                    custody_fee = st.number_input("托管费率（年化%）", min_value=0.0, max_value=1.0, value=0.1, step=0.01)
                
                col_fee3, col_fee4 = st.columns(2)
                with col_fee3:
                    purchase_fee = st.number_input("申购费率（%）", min_value=0.0, max_value=2.0, value=0.12, step=0.01)
                with col_fee4:
                    redemption_fee = st.number_input("赎回费率（%）", min_value=0.0, max_value=2.0, value=0.0, step=0.01)
                
                st.markdown("**跟踪因素**")
                cash_ratio = st.number_input("现金比例（%）", min_value=0.0, max_value=20.0, value=5.0, step=0.1)
                
                tracking_error_mode = st.radio("跟踪误差模式", ["固定折扣", "随机模拟"], horizontal=True)
                tracking_error = st.number_input("跟踪误差（年化%）", min_value=0.0, max_value=5.0, value=0.1, step=0.01)
                
                realistic_params = {
                    'management_fee': management_fee / 100,
                    'custody_fee': custody_fee / 100,
                    'purchase_fee': purchase_fee / 100,
                    'redemption_fee': redemption_fee / 100,
                    'cash_ratio': cash_ratio / 100,
                    'tracking_error': tracking_error / 100,
                    'tracking_error_mode': tracking_error_mode
                }
            
            run_backtest = st.button("开始回测", type="primary", use_container_width=True)
            
        except Exception as e:
            st.error(f"文件读取错误: {e}")
            df = None
    else:
        st.info("请上传 Excel 数据文件")
        df = None
        run_backtest = False

def get_investment_dates(df, start_date, end_date, freq_type, freq_param):
    trading_dates = set(df['日期'].dt.date)
    investment_dates = []
    
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    if freq_type == "按日":
        current_dt = start_dt
        while current_dt <= end_dt:
            current_date = current_dt.date()
            if current_date in trading_dates:
                investment_dates.append(current_date)
            current_dt += timedelta(days=1)
    
    elif freq_type == "按周":
        weekday_map = {"周一": 0, "周二": 1, "周三": 2, "周四": 3, "周五": 4}
        target_weekday = weekday_map[freq_param]
        
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
    df_calc = df.copy()
    df_calc['日期_date'] = df_calc['日期'].dt.date
    
    results = []
    total_shares = 0
    total_investment = 0
    total_purchase_fee = 0
    
    purchase_fee_rate = 0
    if realistic_params:
        purchase_fee_rate = realistic_params.get('purchase_fee', 0)
    
    for inv_date in investment_dates:
        row = df_calc[df_calc['日期_date'] == inv_date]
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
    df_daily = df.copy()
    df_daily['日期_date'] = df_daily['日期'].dt.date
    
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
        row = df_daily[df_daily['日期_date'] == inv_date]
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
    
    for idx, row in df_daily.iterrows():
        current_date = row['日期_date']
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
            
            if tracking_error_mode == "固定折扣":
                effective_price = close_price * (1 - tracking_error)
            else:
                daily_tracking_error = tracking_error / np.sqrt(252)
                random_factor = np.random.normal(0, daily_tracking_error)
                effective_price = close_price * (1 + random_factor)
            
            stock_asset = running_shares_real * effective_price * (1 - cash_ratio)
            cash_asset = running_investment * cash_ratio
            real_asset_value = stock_asset + cash_asset
            real_avg_cost = running_investment / running_shares_real if running_shares_real > 0 else 0
        else:
            real_asset_value = ideal_asset_value
            real_avg_cost = ideal_avg_cost
            running_shares_real = running_shares_ideal
        
        daily_records.append({
            '日期': row['日期'],
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

if run_backtest and df is not None:
    if start_date >= end_date:
        st.error("开始日期必须早于结束日期！")
    else:
        with st.spinner("正在计算回测结果..."):
            investment_dates = get_investment_dates(df, start_date, end_date, freq_type, freq_param)
            
            if len(investment_dates) == 0:
                st.warning("在选定的时间范围内没有找到有效的定投日期！")
            else:
                results_df, total_shares_ideal, total_investment, total_purchase_fee = run_backtest_calculation(df, investment_dates, amount, realistic_params)
                
                daily_assets_df = calculate_daily_assets(df, investment_dates, amount, realistic_params)
                daily_assets_df = daily_assets_df[
                    (daily_assets_df['日期'].dt.date >= start_date) & 
                    (daily_assets_df['日期'].dt.date <= end_date)
                ]
                
                last_row = daily_assets_df.iloc[-1]
                last_price = last_row['收盘价']
                
                ideal_final_asset = last_row['理想持仓市值']
                ideal_total_return = (ideal_final_asset - total_investment) / total_investment * 100
                ideal_avg_cost = total_investment / total_shares_ideal if total_shares_ideal > 0 else 0
                
                if realistic_params:
                    real_final_asset = last_row['实际持仓市值']
                    real_shares = last_row['实际持仓份额']
                    total_management_fee = last_row['累计管理费']
                    
                    redemption_fee = real_final_asset * realistic_params.get('redemption_fee', 0)
                    final_asset_after_redemption = real_final_asset - redemption_fee
                    
                    real_total_return = (final_asset_after_redemption - total_investment) / total_investment * 100
                    real_avg_cost = total_investment / real_shares if real_shares > 0 else 0
                    
                    total_fees = total_purchase_fee + total_management_fee + redemption_fee
                    return_loss = ideal_total_return - real_total_return
                    
                    daily_assets_df['实际累计收益率_tmp'] = (daily_assets_df['实际持仓市值'] - daily_assets_df['累计投入']) / daily_assets_df['累计投入'] * 100
                    daily_assets_df['实际累计收益率_tmp'] = daily_assets_df['实际累计收益率_tmp'].replace([np.inf, -np.inf], 0)
                    
                    real_max_drawdown = daily_assets_df['实际累计收益率_tmp'].min()
                    
                    real_peak = daily_assets_df['实际持仓市值'].expanding().max()
                    real_drawdown_series = (daily_assets_df['实际持仓市值'] - real_peak) / real_peak * 100
                    real_max_pullback = real_drawdown_series.min()
                    
                    real_loss_days = (daily_assets_df['实际累计收益率_tmp'] < 0).sum()
                    total_trading_days = len(daily_assets_df)
                    real_loss_ratio = real_loss_days / total_trading_days * 100 if total_trading_days > 0 else 0
                    
                    real_recovery_date = None
                    cumulative_positive = False
                    for idx, row in daily_assets_df.iterrows():
                        if row['实际累计收益率_tmp'] >= 0:
                            if not cumulative_positive:
                                cumulative_positive = True
                        else:
                            cumulative_positive = False
                        
                        if cumulative_positive:
                            subsequent = daily_assets_df.loc[idx:]
                            if (subsequent['实际累计收益率_tmp'] < 0).sum() == 0:
                                real_recovery_date = row['日期']
                                break
                    
                    if real_recovery_date is not None:
                        real_recovery_days = (real_recovery_date.date() - start_date).days
                    else:
                        real_recovery_days = None
                else:
                    real_final_asset = ideal_final_asset
                    real_shares = total_shares_ideal
                    real_total_return = ideal_total_return
                    real_avg_cost = ideal_avg_cost
                    total_purchase_fee = 0
                    total_management_fee = 0
                    redemption_fee = 0
                    total_fees = 0
                    return_loss = 0
                    final_asset_after_redemption = ideal_final_asset
                    
                    daily_assets_df['理想累计收益率_tmp'] = (daily_assets_df['理想持仓市值'] - daily_assets_df['累计投入']) / daily_assets_df['累计投入'] * 100
                    daily_assets_df['理想累计收益率_tmp'] = daily_assets_df['理想累计收益率_tmp'].replace([np.inf, -np.inf], 0)
                    
                    real_max_drawdown = daily_assets_df['理想累计收益率_tmp'].min()
                    
                    real_peak = daily_assets_df['理想持仓市值'].expanding().max()
                    real_drawdown_series = (daily_assets_df['理想持仓市值'] - real_peak) / real_peak * 100
                    real_max_pullback = real_drawdown_series.min()
                    
                    real_loss_days = (daily_assets_df['理想累计收益率_tmp'] < 0).sum()
                    total_trading_days = len(daily_assets_df)
                    real_loss_ratio = real_loss_days / total_trading_days * 100 if total_trading_days > 0 else 0
                    
                    real_recovery_date = None
                    cumulative_positive = False
                    for idx, row in daily_assets_df.iterrows():
                        if row['理想累计收益率_tmp'] >= 0:
                            if not cumulative_positive:
                                cumulative_positive = True
                        else:
                            cumulative_positive = False
                        
                        if cumulative_positive:
                            subsequent = daily_assets_df.loc[idx:]
                            if (subsequent['理想累计收益率_tmp'] < 0).sum() == 0:
                                real_recovery_date = row['日期']
                                break
                    
                    if real_recovery_date is not None:
                        real_recovery_days = (real_recovery_date.date() - start_date).days
                    else:
                        real_recovery_days = None
                
                days = (end_date - start_date).days
                years = days / 365.0 if days > 0 else 0
                ideal_dip_annualized = ((1 + ideal_total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
                real_dip_annualized = ((1 + real_total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
                
                lump_total_return, lump_annualized = calculate_lump_sum_return(df, start_date, end_date)
                
                st.header(f"回测结果（{start_date} ~ {end_date}）")
                
                if realistic_params:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总投入本金", f"¥{total_investment:,.2f}")
                    with col2:
                        st.metric("期末总资产", f"¥{final_asset_after_redemption:,.2f}")
                    with col3:
                        st.metric("累计收益率", f"{real_total_return:.2f}%")
                    with col4:
                        st.metric("平均持仓成本", f"¥{real_avg_cost:,.2f}")
                    
                    col5, col6, col7, col8 = st.columns(4)
                    with col5:
                        st.metric("定投年化收益率", f"{real_dip_annualized:.2f}%", help="基于定投区间总时间计算的年化收益率")
                    with col6:
                        st.metric("一次性投入年化收益率", f"{lump_annualized:.2f}%", help="假设在开始日期一次性投入的年化收益率")
                    with col7:
                        st.metric("定投时长", f"{years:.2f}年")
                    with col8:
                        st.metric("定投次数", f"{len(investment_dates)}次")
                    
                    st.markdown("---")
                    st.subheader("投资风险")
                    col_risk1, col_risk2, col_risk3, col_risk4 = st.columns(4)
                    with col_risk1:
                        st.metric("最大亏损", f"{real_max_drawdown:.2f}%", help="相对于投入本金的最大亏损百分比")
                    with col_risk2:
                        st.metric("最大回撤", f"{real_max_pullback:.2f}%", help="从历史最高点到后续最低点的最大跌幅")
                    with col_risk3:
                        st.metric("累计亏损时长", f"{real_loss_days}天", help="累计收益率为负的总天数")
                    with col_risk4:
                        st.metric("亏损时长占比", f"{real_loss_ratio:.1f}%", help="亏损天数占总交易日的比例")
                    
                    col_risk5, col_risk6 = st.columns(2)
                    with col_risk5:
                        if real_recovery_days is not None:
                            st.metric("回本时间", f"{real_recovery_days}天", help="从开始投资到再也不亏损所用的时间")
                        else:
                            st.metric("回本时间", "未回本", help="整个投资期间未能回本")
                    with col_risk6:
                        if real_recovery_date is not None:
                            st.metric("回本日期", f"{real_recovery_date.date()}")
                        else:
                            st.metric("回本日期", "未回本")
                    
                    st.markdown("---")
                    st.subheader("理想收益 vs 实际收益")
                    col9, col10, col11, col12 = st.columns(4)
                    with col9:
                        st.metric("理想期末资产", f"¥{ideal_final_asset:,.2f}")
                    with col10:
                        st.metric("理想累计收益率", f"{ideal_total_return:.2f}%")
                    with col11:
                        st.metric("理想年化收益率", f"{ideal_dip_annualized:.2f}%")
                    with col12:
                        st.empty()
                    
                    col13, col14, col15, col16 = st.columns(4)
                    with col13:
                        st.metric("实际期末资产", f"¥{final_asset_after_redemption:,.2f}", f"-{ideal_final_asset - final_asset_after_redemption:,.2f}")
                    with col14:
                        st.metric("实际累计收益率", f"{real_total_return:.2f}%", f"-{return_loss:.2f}%")
                    with col15:
                        st.metric("实际年化收益率", f"{real_dip_annualized:.2f}%", f"-{ideal_dip_annualized - real_dip_annualized:.2f}%")
                    with col16:
                        st.empty()
                    
                    st.markdown("---")
                    st.subheader("费用明细")
                    col_fee1, col_fee2, col_fee3, col_fee4 = st.columns(4)
                    with col_fee1:
                        st.metric("累计申购费", f"¥{total_purchase_fee:,.2f}")
                    with col_fee2:
                        st.metric("累计管理费", f"¥{total_management_fee:,.2f}", help="含管理费和托管费")
                    with col_fee3:
                        st.metric("赎回费用", f"¥{redemption_fee:,.2f}")
                    with col_fee4:
                        st.metric("总费用", f"¥{total_fees:,.2f}")
                else:
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总投入本金", f"¥{total_investment:,.2f}")
                    with col2:
                        st.metric("期末总资产", f"¥{ideal_final_asset:,.2f}")
                    with col3:
                        st.metric("累计收益率", f"{ideal_total_return:.2f}%")
                    with col4:
                        st.metric("平均持仓成本", f"¥{ideal_avg_cost:,.2f}")
                    
                    col5, col6, col7, col8 = st.columns(4)
                    with col5:
                        st.metric("定投年化收益率", f"{ideal_dip_annualized:.2f}%", help="基于定投区间总时间计算的年化收益率")
                    with col6:
                        st.metric("一次性投入年化收益率", f"{lump_annualized:.2f}%", help="假设在开始日期一次性投入的年化收益率")
                    with col7:
                        st.metric("定投时长", f"{years:.2f}年")
                    with col8:
                        st.metric("定投次数", f"{len(investment_dates)}次")
                    
                    st.markdown("---")
                    st.subheader("投资风险")
                    col_risk1, col_risk2, col_risk3, col_risk4 = st.columns(4)
                    with col_risk1:
                        st.metric("最大亏损", f"{real_max_drawdown:.2f}%", help="相对于投入本金的最大亏损百分比")
                    with col_risk2:
                        st.metric("最大回撤", f"{real_max_pullback:.2f}%", help="从历史最高点到后续最低点的最大跌幅")
                    with col_risk3:
                        st.metric("累计亏损时长", f"{real_loss_days}天", help="累计收益率为负的总天数")
                    with col_risk4:
                        st.metric("亏损时长占比", f"{real_loss_ratio:.1f}%", help="亏损天数占总交易日的比例")
                    
                    col_risk5, col_risk6 = st.columns(2)
                    with col_risk5:
                        if real_recovery_days is not None:
                            st.metric("回本时间", f"{real_recovery_days}天", help="从开始投资到再也不亏损所用的时间")
                        else:
                            st.metric("回本时间", "未回本", help="整个投资期间未能回本")
                    with col_risk6:
                        if real_recovery_date is not None:
                            st.metric("回本日期", f"{real_recovery_date.date()}")
                        else:
                            st.metric("回本日期", "未回本")
                
                st.markdown("---")
                
                st.subheader("资产变动曲线")
                
                fig1 = go.Figure()
                
                fig1.add_trace(go.Scatter(
                    x=daily_assets_df['日期'],
                    y=daily_assets_df['累计投入'],
                    mode='lines',
                    name='累计投入本金',
                    line=dict(color='blue', width=2),
                    hovertemplate='日期: %{x}<br>累计投入: ¥%{y:,.2f}<extra></extra>'
                ))
                
                if realistic_params:
                    fig1.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['理想持仓市值'],
                        mode='lines',
                        name='理想持仓市值',
                        line=dict(color='green', width=2, dash='dash'),
                        hovertemplate='日期: %{x}<br>理想市值: ¥%{y:,.2f}<extra></extra>'
                    ))
                    
                    fig1.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['实际持仓市值'],
                        mode='lines',
                        name='实际持仓市值',
                        line=dict(color='red', width=2),
                        hovertemplate='日期: %{x}<br>实际市值: ¥%{y:,.2f}<extra></extra>'
                    ))
                else:
                    fig1.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['理想持仓市值'],
                        mode='lines',
                        name='持仓总资产',
                        line=dict(color='red', width=2),
                        hovertemplate='日期: %{x}<br>持仓市值: ¥%{y:,.2f}<extra></extra>'
                    ))
                
                fig1.update_layout(
                    xaxis_title='日期',
                    yaxis_title='金额（元）',
                    hovermode='x unified',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                
                st.plotly_chart(fig1, use_container_width=True)
                
                st.markdown("---")
                
                st.subheader("指数收盘价与持仓均价")

                first_price = daily_assets_df.iloc[0]['收盘价']

                fig2 = go.Figure()

                fig2.add_trace(go.Scatter(
                    x=daily_assets_df['日期'],
                    y=daily_assets_df['收盘价'],
                    mode='lines',
                    name='指数收盘价',
                    line=dict(color='green', width=2),
                    hovertemplate='日期: %{x}<br>收盘价: ¥%{y:,.2f}<extra></extra>'
                ))

                if realistic_params:
                    fig2.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['理想持仓均价'],
                        mode='lines',
                        name='理想持仓均价',
                        line=dict(color='orange', width=2, dash='dash'),
                        hovertemplate='日期: %{x}<br>理想均价: ¥%{y:,.2f}<extra></extra>'
                    ))
                    
                    fig2.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['实际持仓均价'],
                        mode='lines',
                        name='实际持仓均价',
                        line=dict(color='purple', width=2),
                        hovertemplate='日期: %{x}<br>实际均价: ¥%{y:,.2f}<extra></extra>'
                    ))
                else:
                    fig2.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['理想持仓均价'],
                        mode='lines',
                        name='持仓均价',
                        line=dict(color='orange', width=2, dash='dash'),
                        hovertemplate='日期: %{x}<br>持仓均价: ¥%{y:,.2f}<extra></extra>'
                    ))

                fig2.update_layout(
                    xaxis_title='日期',
                    yaxis_title='价格（元）',
                    hovermode='x unified',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                
                st.plotly_chart(fig2, use_container_width=True)
                
                st.markdown("---")
                
                st.subheader("累计收益率曲线")
                
                daily_assets_df['理想累计收益率'] = (daily_assets_df['理想持仓市值'] - daily_assets_df['累计投入']) / daily_assets_df['累计投入'] * 100
                daily_assets_df['理想累计收益率'] = daily_assets_df['理想累计收益率'].replace([np.inf, -np.inf], 0)
                
                if realistic_params:
                    daily_assets_df['实际累计收益率'] = (daily_assets_df['实际持仓市值'] - daily_assets_df['累计投入']) / daily_assets_df['累计投入'] * 100
                    daily_assets_df['实际累计收益率'] = daily_assets_df['实际累计收益率'].replace([np.inf, -np.inf], 0)
                    return_col = '实际累计收益率'
                else:
                    return_col = '理想累计收益率'
                
                fig3 = go.Figure()
                
                fig3.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                
                loss_periods = []
                in_loss = False
                loss_start = None
                
                for idx, row in daily_assets_df.iterrows():
                    if row[return_col] < 0:
                        if not in_loss:
                            in_loss = True
                            loss_start = row['日期']
                    else:
                        if in_loss:
                            loss_periods.append((loss_start, daily_assets_df.loc[idx - 1, '日期'] if idx > 0 else row['日期']))
                            in_loss = False
                
                if in_loss:
                    loss_periods.append((loss_start, daily_assets_df.iloc[-1]['日期']))
                
                for loss_start_date, loss_end_date in loss_periods:
                    fig3.add_vrect(
                        x0=loss_start_date, x1=loss_end_date,
                        fillcolor="red", opacity=0.1,
                        layer="below", line_width=0
                    )
                
                if realistic_params:
                    fig3.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['理想累计收益率'],
                        mode='lines',
                        name='理想累计收益率',
                        line=dict(color='green', width=2, dash='dash'),
                        hovertemplate='日期: %{x}<br>理想收益率: %{y:.2f}%<extra></extra>'
                    ))
                    
                    fig3.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['实际累计收益率'],
                        mode='lines',
                        name='实际累计收益率',
                        line=dict(color='red', width=2),
                        hovertemplate='日期: %{x}<br>实际收益率: %{y:.2f}%<extra></extra>'
                    ))
                else:
                    fig3.add_trace(go.Scatter(
                        x=daily_assets_df['日期'],
                        y=daily_assets_df['理想累计收益率'],
                        mode='lines',
                        name='累计收益率',
                        line=dict(color='red', width=2),
                        hovertemplate='日期: %{x}<br>累计收益率: %{y:.2f}%<extra></extra>'
                    ))
                
                if real_recovery_date is not None:
                    fig3.add_shape(
                        type="line",
                        x0=real_recovery_date, x1=real_recovery_date,
                        y0=0, y1=1,
                        yref="paper",
                        line=dict(color="blue", width=2, dash="dot"),
                    )
                    fig3.add_annotation(
                        x=real_recovery_date,
                        y=1,
                        yref="paper",
                        text="回本点",
                        showarrow=False,
                        xanchor="left",
                        yanchor="bottom"
                    )
                
                fig3.update_layout(
                    xaxis_title='日期',
                    yaxis_title='累计收益率（%）',
                    hovermode='x unified',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                
                st.plotly_chart(fig3, use_container_width=True)
                
                st.markdown("---")
                
                col_left, col_right = st.columns([1, 1])
                
                with col_left:
                    st.subheader("回测参数汇总")
                    st.write(f"- 定投区间: {start_date} ~ {end_date}")
                    st.write(f"- 定投频率: {freq_type}" + (f" ({freq_param})" if freq_param else ""))
                    st.write(f"- 每次定投金额: ¥{amount:,.2f}")
                    st.write(f"- 定投次数: {len(investment_dates)} 次")
                    st.write(f"- 累计份额: {real_shares:,.4f} 份")
                    st.write(f"- 期末收盘价: ¥{last_price:,.2f}")
                    st.write(f"- 期初收盘价: ¥{first_price:,.2f}")
                    
                    if realistic_params:
                        st.write("---")
                        st.write("**基金现实因素参数:**")
                        st.write(f"- 管理费率: {realistic_params['management_fee']*100:.2f}%")
                        st.write(f"- 托管费率: {realistic_params['custody_fee']*100:.2f}%")
                        st.write(f"- 申购费率: {realistic_params['purchase_fee']*100:.2f}%")
                        st.write(f"- 赎回费率: {realistic_params['redemption_fee']*100:.2f}%")
                        st.write(f"- 现金比例: {realistic_params['cash_ratio']*100:.1f}%")
                        st.write(f"- 跟踪误差: {realistic_params['tracking_error']*100:.2f}% ({realistic_params['tracking_error_mode']})")
                
                with col_right:
                    st.subheader("定投记录明细")
                    display_df = results_df.copy()
                    display_df['日期'] = display_df['日期'].astype(str)
                    display_df['收盘价'] = display_df['收盘价'].round(2)
                    display_df['买入份额'] = display_df['买入份额'].round(4)
                    display_df['累计份额'] = display_df['累计份额'].round(4)
                    display_df['投入金额'] = display_df['投入金额'].apply(lambda x: f"¥{x:,.2f}")
                    display_df['累计投入'] = display_df['累计投入'].apply(lambda x: f"¥{x:,.2f}")
                    
                    if realistic_params:
                        display_df['申购费用'] = display_df['申购费用'].apply(lambda x: f"¥{x:,.2f}")
                        st.dataframe(
                            display_df[['日期', '收盘价', '投入金额', '申购费用', '买入份额', '累计份额', '累计投入']],
                            use_container_width=True,
                            height=300
                        )
                    else:
                        st.dataframe(
                            display_df[['日期', '收盘价', '投入金额', '买入份额', '累计份额', '累计投入']],
                            use_container_width=True,
                            height=300
                        )

elif df is not None and not run_backtest:
    st.info("请在左侧设置参数后点击「开始回测」按钮")
