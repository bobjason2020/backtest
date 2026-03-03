import streamlit as st
import random
import os
from datetime import timedelta

from .config import (
    WEEKDAYS, MONTH_OPTIONS,
    DEFAULT_AMOUNT, MIN_AMOUNT, MAX_AMOUNT, AMOUNT_STEP,
    DEFAULT_MANAGEMENT_FEE, DEFAULT_CUSTODY_FEE,
    DEFAULT_PURCHASE_FEE, DEFAULT_REDEMPTION_FEE,
    DEFAULT_CASH_RATIO, DEFAULT_TRACKING_ERROR,
    DEFAULT_HOLDING_YEARS, MIN_HOLDING_YEARS, HOLDING_YEARS_STEP,
    DURATION_OPTIONS, DEFAULT_DURATION, MIN_DURATION, MAX_DURATION, DURATION_STEP,
    SAMPLING_OPTIONS, DEFAULT_SAMPLING,
    STRATEGY_TYPES, DEFAULT_STRATEGY,
    MA_PERIODS, DEFAULT_MA_PERIOD,
    DEFAULT_EXTREME_LOW_THRESHOLD, DEFAULT_LOW_THRESHOLD, DEFAULT_HIGH_THRESHOLD, DEFAULT_EXTREME_HIGH_THRESHOLD,
    VALUATION_COLUMNS, DEFAULT_VALUATION_COLUMN,
    DEFAULT_EXTREME_LOW_PERCENTILE, DEFAULT_LOW_PERCENTILE, DEFAULT_HIGH_PERCENTILE, DEFAULT_EXTREME_HIGH_PERCENTILE,
    DEFAULT_TREND_PERIOD, DEFAULT_TREND_EXTREME_LOW_THRESHOLD, DEFAULT_TREND_LOW_THRESHOLD, 
    DEFAULT_TREND_HIGH_THRESHOLD, DEFAULT_TREND_EXTREME_HIGH_THRESHOLD,
    DEFAULT_EXTREME_LOW_MULTIPLIER, DEFAULT_LOW_MULTIPLIER, DEFAULT_NORMAL_MULTIPLIER,
    DEFAULT_HIGH_MULTIPLIER, DEFAULT_EXTREME_HIGH_MULTIPLIER,
    MA_STRATEGY_PRESETS, MA_PRESETS_FILE, load_custom_presets, save_custom_preset, get_all_presets
)
from .data_loader import load_excel_file, get_date_range
from .chart_renderer import create_asset_chart, create_price_chart, create_return_chart
from .smart_strategy import SmartStrategyConfig


def render_sidebar():
    with st.sidebar:
        st.header("参数设置")
        
        data_source = st.radio("数据来源", ["上传数据文件", "使用示例数据"], horizontal=True)
        
        uploaded_file = None
        if data_source == "上传数据文件":
            uploaded_file = st.file_uploader("选择数据文件", type=["xlsx"])
        else:
            example_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "可用数据", "example_data.xlsx")
            if os.path.exists(example_data_path):
                st.success("✅ 已加载内置示例数据")
            else:
                st.warning("⚠️ 示例数据文件不存在，请上传数据文件")
                data_source = "上传数据文件"
                uploaded_file = st.file_uploader("选择数据文件", type=["xlsx"])
        
        params = {
            'uploaded_file': uploaded_file,
            'data_source': data_source,
            'df': None,
            'date_range': None,
            'start_date': None,
            'end_date': None,
            'freq_type': None,
            'freq_param': None,
            'amount': DEFAULT_AMOUNT,
            'realistic_params': None,
            'run_backtest': False,
            'mode': 'single',
            'analysis_start_date': None,
            'analysis_end_date': None,
            'investment_duration': DEFAULT_DURATION,
            'sampling': DEFAULT_SAMPLING,
            'strategy_mode': 'fixed',
            'strategy_config': None
        }
        
        df = None
        error = None
        
        if data_source == "使用示例数据":
            example_data_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "可用数据", "example_data.xlsx")
            if os.path.exists(example_data_path):
                df, error = load_excel_file(example_data_path)
        elif uploaded_file is not None:
            df, error = load_excel_file(uploaded_file)
        
        if df is not None and error is None:
            date_range = get_date_range(df)
            
            valuation_info = ""
            if date_range.get('has_valuation', False):
                valuation_info = f"\n包含估值数据: {', '.join(date_range['valuation_columns'])}"
            
            st.success(f"数据加载成功！\n共 {date_range['record_count']} 条记录\n日期范围: {date_range['min_date']} ~ {date_range['max_date']}{valuation_info}")
            
            st.subheader("分析模式")
            mode = st.radio("选择模式", ["单次回测", "概率分析"], horizontal=True)
            mode_map = {"单次回测": "single", "概率分析": "probability"}
            params['mode'] = mode_map.get(mode, "single")
            
            if params['mode'] == 'single':
                params.update(_render_single_backtest_ui(df, date_range))
            else:
                params.update(_render_probability_analysis_ui(df, date_range))
        else:
            st.info("请上传 Excel 数据文件")
        
        return params


def _render_single_backtest_ui(df, date_range):
    st.subheader("定投区间")
    date_mode = st.radio("日期选择方式", ["手动选择日期", "按持有年限", "随机持有年限"], horizontal=True, index=2)
    
    start_date = None
    end_date = None
    
    if date_mode == "手动选择日期":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=date_range['min_date'], min_value=date_range['min_date'], max_value=date_range['max_date'])
        with col2:
            end_date = st.date_input("结束日期", value=date_range['max_date'], min_value=date_range['min_date'], max_value=date_range['max_date'])
    
    elif date_mode == "按持有年限":
        start_date = st.date_input("开始日期", value=date_range['min_date'], min_value=date_range['min_date'], max_value=date_range['max_date'])
        holding_years = st.number_input("持有年限", min_value=MIN_HOLDING_YEARS, max_value=float(int(date_range['max_years'] * 10) / 10), value=DEFAULT_HOLDING_YEARS, step=HOLDING_YEARS_STEP)
        end_date = start_date + timedelta(days=int(holding_years * 365))
        if end_date > date_range['max_date']:
            end_date = date_range['max_date']
            st.warning(f"持有年限超出数据范围，结束日期已调整为 {end_date}")
        st.info(f"结束日期: {end_date}")
    
    elif date_mode == "随机持有年限":
        holding_years = st.number_input("持有年限", min_value=MIN_HOLDING_YEARS, max_value=float(int(date_range['max_years'] * 10) / 10), value=DEFAULT_HOLDING_YEARS, step=HOLDING_YEARS_STEP)
        random_seed = st.checkbox("固定随机种子", value=False)
        if random_seed:
            seed_value = st.number_input("随机种子", min_value=0, max_value=99999, value=42, step=1)
        else:
            seed_value = None
        
        max_start_date = date_range['max_date'] - timedelta(days=int(holding_years * 365))
        if max_start_date < date_range['min_date']:
            st.warning(f"持有年限 {holding_years} 年超出数据范围，请减小持有年限")
            start_date = date_range['min_date']
            end_date = date_range['max_date']
        else:
            if seed_value is not None:
                random.seed(seed_value)
            random_days = random.randint(0, (max_start_date - date_range['min_date']).days)
            start_date = date_range['min_date'] + timedelta(days=random_days)
            end_date = start_date + timedelta(days=int(holding_years * 365))
            if end_date > date_range['max_date']:
                end_date = date_range['max_date']
            st.info(f"随机选择的时间段:\n开始: {start_date}\n结束: {end_date}")
    
    st.subheader("定投频率")
    freq_type = st.radio("选择频率", ["按日", "按周", "按月", "一次性投入"], horizontal=True, index=1)
    
    freq_param = None
    if freq_type == "按周":
        freq_param = st.selectbox("选择定投日", WEEKDAYS, index=0)
    elif freq_type == "按月":
        freq_param = st.selectbox("选择定投日", MONTH_OPTIONS, index=0)
    
    st.subheader("定投策略")
    strategy_mode = st.radio("选择策略", ["固定定投", "智能定投", "策略对比"], horizontal=True, index=0)
    
    strategy_config = None
    if strategy_mode in ["智能定投", "策略对比"]:
        strategy_config = _render_strategy_config_ui(date_range)
    
    st.subheader("定投金额")
    amount = st.number_input("每次定投金额（元）", min_value=MIN_AMOUNT, max_value=MAX_AMOUNT, value=DEFAULT_AMOUNT, step=AMOUNT_STEP)
    
    if strategy_config:
        strategy_config.base_amount = amount
    
    realistic_params = _render_realistic_params()
    
    run_backtest = st.button("开始回测", type="primary", use_container_width=True)
    
    return {
        'df': df,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'freq_type': freq_type,
        'freq_param': freq_param,
        'amount': amount,
        'realistic_params': realistic_params,
        'run_backtest': run_backtest,
        'strategy_mode': strategy_mode,
        'strategy_config': strategy_config
    }


def _render_probability_analysis_ui(df, date_range):
    st.subheader("分析时间段")
    col1, col2 = st.columns(2)
    with col1:
        analysis_start_date = st.date_input("分析开始日期", value=date_range['min_date'], min_value=date_range['min_date'], max_value=date_range['max_date'], key="prob_start")
    with col2:
        analysis_end_date = st.date_input("分析结束日期", value=date_range['max_date'], min_value=date_range['min_date'], max_value=date_range['max_date'], key="prob_end")
    
    st.subheader("定投时长")
    duration_preset = st.selectbox("选择时长", [f"{y}年" for y in DURATION_OPTIONS] + ["自定义"], index=2)
    if duration_preset == "自定义":
        investment_duration = st.number_input("定投时长（年）", min_value=MIN_DURATION, max_value=MAX_DURATION, value=DEFAULT_DURATION, step=DURATION_STEP)
    else:
        investment_duration = float(duration_preset.replace("年", ""))
    
    max_possible_duration = (analysis_end_date - analysis_start_date).days / 365.0
    max_data_duration = (date_range['max_date'] - analysis_start_date).days / 365.0
    if investment_duration > max_data_duration:
        st.warning(f"定投时长超出数据范围，最大可用时长为 {max_data_duration:.1f} 年")
        investment_duration = max_data_duration
    
    st.subheader("定投频率")
    freq_type = st.radio("选择频率", ["按日", "按周", "按月", "一次性投入"], horizontal=True, index=2)
    
    freq_param = None
    if freq_type == "按周":
        freq_param = st.selectbox("选择定投日", WEEKDAYS, index=0, key="prob_freq_week")
    elif freq_type == "按月":
        freq_param = st.selectbox("选择定投日", MONTH_OPTIONS, index=0, key="prob_freq_month")
    
    st.subheader("定投金额")
    amount = st.number_input("每次定投金额（元）", min_value=MIN_AMOUNT, max_value=MAX_AMOUNT, value=DEFAULT_AMOUNT, step=AMOUNT_STEP, key="prob_amount")
    
    st.subheader("定投策略")
    strategy_mode = st.radio("选择策略", ["固定定投", "智能定投", "策略对比"], horizontal=True, index=0, key="prob_strategy")
    
    strategy_config = None
    if strategy_mode in ["智能定投", "策略对比"]:
        strategy_config = _render_strategy_config_ui(date_range)
        strategy_config.base_amount = amount
    
    st.subheader("采样设置")
    sampling = st.selectbox("起始日期采样方式", SAMPLING_OPTIONS, index=0, help="每月采样：每月取一个起始日期；每周采样：每周取一个起始日期；每日采样：每个交易日都作为起始日期（计算较慢）")
    
    realistic_params = _render_realistic_params()
    
    run_backtest = st.button("开始概率分析", type="primary", use_container_width=True)
    
    return {
        'df': df,
        'date_range': date_range,
        'analysis_start_date': analysis_start_date,
        'analysis_end_date': analysis_end_date,
        'investment_duration': investment_duration,
        'freq_type': freq_type,
        'freq_param': freq_param,
        'amount': amount,
        'sampling': sampling,
        'realistic_params': realistic_params,
        'run_backtest': run_backtest,
        'strategy_mode': strategy_mode,
        'strategy_config': strategy_config
    }


def _render_realistic_params():
    realistic_params = None
    
    with st.popover("⚙️ 基金现实因素", use_container_width=True):
        consider_realistic = st.checkbox("考虑基金现实因素", value=True)
        
        if consider_realistic:
            st.markdown("**费用参数**")
            col_fee1, col_fee2 = st.columns(2)
            with col_fee1:
                management_fee = st.number_input("管理费率（年化%）", min_value=0.0, max_value=10.0, value=DEFAULT_MANAGEMENT_FEE, step=0.01)
            with col_fee2:
                custody_fee = st.number_input("托管费率（年化%）", min_value=0.0, max_value=1.0, value=DEFAULT_CUSTODY_FEE, step=0.01)
            
            col_fee3, col_fee4 = st.columns(2)
            with col_fee3:
                purchase_fee = st.number_input("申购费率（%）", min_value=0.0, max_value=2.0, value=DEFAULT_PURCHASE_FEE, step=0.01)
            with col_fee4:
                redemption_fee = st.number_input("赎回费率（%）", min_value=0.0, max_value=2.0, value=DEFAULT_REDEMPTION_FEE, step=0.01)
            
            st.markdown("**跟踪因素**")
            cash_ratio = st.number_input("现金比例（%）", min_value=0.0, max_value=20.0, value=DEFAULT_CASH_RATIO, step=0.1)
            
            tracking_error_mode = st.radio("跟踪误差模式", ["固定折扣", "随机模拟"], horizontal=True)
            tracking_error = st.number_input("跟踪误差（年化%）", min_value=0.0, max_value=5.0, value=DEFAULT_TRACKING_ERROR, step=0.01)
            
            realistic_params = {
                'management_fee': management_fee / 100,
                'custody_fee': custody_fee / 100,
                'purchase_fee': purchase_fee / 100,
                'redemption_fee': redemption_fee / 100,
                'cash_ratio': cash_ratio / 100,
                'tracking_error': tracking_error / 100,
                'tracking_error_mode': tracking_error_mode
            }
    
    return realistic_params


def display_summary_metrics(total_investment, final_asset, total_return, avg_cost, 
                           dip_annualized, lump_annualized, years, investment_count):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总投入本金", f"¥{total_investment:,.2f}")
    with col2:
        st.metric("期末总资产", f"¥{final_asset:,.2f}")
    with col3:
        st.metric("累计收益率", f"{total_return:.2f}%")
    with col4:
        st.metric("平均持仓成本", f"¥{avg_cost:,.2f}")
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("定投年化收益率", f"{dip_annualized:.2f}%", help="基于定投区间总时间计算的年化收益率")
    with col6:
        st.metric("一次性投入年化收益率", f"{lump_annualized:.2f}%", help="假设在开始日期一次性投入的年化收益率")
    with col7:
        st.metric("定投时长", f"{years:.2f}年")
    with col8:
        st.metric("定投次数", f"{investment_count}次")


def display_risk_metrics(risk_metrics):
    col_risk1, col_risk2, col_risk3, col_risk4 = st.columns(4)
    with col_risk1:
        st.metric("最大亏损", f"{risk_metrics['max_drawdown']:.2f}%", help="相对于投入本金的最大亏损百分比")
    with col_risk2:
        st.metric("最大回撤", f"{risk_metrics['max_pullback']:.2f}%", help="从历史最高点到后续最低点的最大跌幅")
    with col_risk3:
        st.metric("累计亏损时长", f"{risk_metrics['loss_days']}天", help="累计收益率为负的总天数")
    with col_risk4:
        st.metric("亏损时长占比", f"{risk_metrics['loss_ratio']:.1f}%", help="亏损天数占总交易日的比例")
    
    col_risk5, col_risk6 = st.columns(2)
    with col_risk5:
        if risk_metrics['recovery_days'] is not None:
            st.metric("回本时间", f"{risk_metrics['recovery_days']}天", help="从开始投资到再也不亏损所用的时间")
        else:
            st.metric("回本时间", "未回本", help="整个投资期间未能回本")
    with col_risk6:
        if risk_metrics['recovery_date'] is not None:
            st.metric("回本日期", f"{risk_metrics['recovery_date'].date()}")
        else:
            st.metric("回本日期", "未回本")


def display_comparison_metrics(ideal_final_asset, ideal_total_return, ideal_annualized,
                               real_final_asset, real_total_return, real_annualized):
    st.markdown("---")
    st.subheader("理想收益 vs 实际收益")
    col9, col10, col11, col12 = st.columns(4)
    with col9:
        st.metric("理想期末资产", f"¥{ideal_final_asset:,.2f}")
    with col10:
        st.metric("理想累计收益率", f"{ideal_total_return:.2f}%")
    with col11:
        st.metric("理想年化收益率", f"{ideal_annualized:.2f}%")
    with col12:
        st.empty()
    
    col13, col14, col15, col16 = st.columns(4)
    with col13:
        st.metric("实际期末资产", f"¥{real_final_asset:,.2f}", f"-{ideal_final_asset - real_final_asset:,.2f}")
    with col14:
        st.metric("实际累计收益率", f"{real_total_return:.2f}%", f"-{ideal_total_return - real_total_return:.2f}%")
    with col15:
        st.metric("实际年化收益率", f"{real_annualized:.2f}%", f"-{ideal_annualized - real_annualized:.2f}%")
    with col16:
        st.empty()


def display_fee_details(total_purchase_fee, total_management_fee, redemption_fee, total_fees):
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


def display_parameters_summary(start_date, end_date, freq_type, freq_param, amount, 
                               investment_dates, real_shares, last_price, first_price, 
                               realistic_params=None):
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


def display_investment_records(results_df, realistic_params=None):
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


def display_results(start_date, end_date, freq_type, freq_param, amount, investment_dates,
                   results_df, daily_assets_df, total_shares_ideal, total_investment, 
                   total_purchase_fee, realistic_params, risk_metrics, lump_total_return, 
                   lump_annualized):
    
    st.header(f"回测结果（{start_date} ~ {end_date}）")
    
    last_row = daily_assets_df.iloc[-1]
    last_price = last_row['收盘价']
    first_price = daily_assets_df.iloc[0]['收盘价']
    
    ideal_final_asset = last_row['理想持仓市值']
    ideal_total_return = (ideal_final_asset - total_investment) / total_investment * 100
    ideal_avg_cost = total_investment / total_shares_ideal if total_shares_ideal > 0 else 0
    
    days = (end_date - start_date).days
    years = days / 365.0 if days > 0 else 0
    ideal_dip_annualized = ((1 + ideal_total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    
    if realistic_params:
        real_final_asset = last_row['实际持仓市值']
        real_shares = last_row['实际持仓份额']
        total_management_fee = last_row['累计管理费']
        
        redemption_fee = real_final_asset * realistic_params.get('redemption_fee', 0)
        final_asset_after_redemption = real_final_asset - redemption_fee
        
        real_total_return = (final_asset_after_redemption - total_investment) / total_investment * 100
        real_avg_cost = total_investment / real_shares if real_shares > 0 else 0
        
        total_fees = total_purchase_fee + total_management_fee + redemption_fee
        
        real_dip_annualized = ((1 + real_total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        display_summary_metrics(
            total_investment, final_asset_after_redemption, real_total_return, real_avg_cost,
            real_dip_annualized, lump_annualized, years, len(investment_dates)
        )
        
        st.markdown("---")
        st.subheader("投资风险")
        display_risk_metrics(risk_metrics)
        
        display_comparison_metrics(
            ideal_final_asset, ideal_total_return, ideal_dip_annualized,
            final_asset_after_redemption, real_total_return, real_dip_annualized
        )
        
        display_fee_details(total_purchase_fee, total_management_fee, redemption_fee, total_fees)
    else:
        real_shares = total_shares_ideal
        
        display_summary_metrics(
            total_investment, ideal_final_asset, ideal_total_return, ideal_avg_cost,
            ideal_dip_annualized, lump_annualized, years, len(investment_dates)
        )
        
        st.markdown("---")
        st.subheader("投资风险")
        display_risk_metrics(risk_metrics)
    
    st.markdown("---")
    
    st.subheader("资产变动曲线")
    fig1 = create_asset_chart(daily_assets_df, realistic_params)
    st.plotly_chart(fig1, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("指数收盘价与持仓均价")
    fig2 = create_price_chart(daily_assets_df, realistic_params)
    st.plotly_chart(fig2, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("累计收益率曲线")
    fig3 = create_return_chart(daily_assets_df, realistic_params, risk_metrics['recovery_date'])
    st.plotly_chart(fig3, use_container_width=True)
    
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        display_parameters_summary(
            start_date, end_date, freq_type, freq_param, amount,
            investment_dates, real_shares, last_price, first_price, realistic_params
        )
    
    with col_right:
        display_investment_records(results_df, realistic_params)


def display_probability_summary(stats, investment_duration, realistic_params=None):
    st.subheader("核心概率指标")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        profit_color = "normal" if stats['profit_probability'] >= 50 else "inverse"
        st.metric("盈利概率", f"{stats['profit_probability']:.1f}%", 
                  help=f"在 {stats['total_count']} 次模拟中，有 {stats['profit_count']} 次盈利")
    with col2:
        st.metric("平均年化收益", f"{stats['avg_annualized']:.2f}%")
    with col3:
        st.metric("中位数年化收益", f"{stats['median_annualized']:.2f}%")
    with col4:
        st.metric("收益标准差", f"{stats['std_return']:.2f}%")
    
    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.metric("最大累计收益", f"{stats['max_return']:.2f}%")
    with col6:
        st.metric("最小累计收益", f"{stats['min_return']:.2f}%")
    with col7:
        st.metric("平均定投次数", f"{stats['avg_investment_count']:.0f}次")
    with col8:
        st.metric("平均定投时长", f"{stats['avg_years']:.1f}年")


def display_cumulative_probability(cumulative_prob):
    st.subheader("收益概率分布")
    
    cols = st.columns(len(cumulative_prob))
    for i, (threshold, prob) in enumerate(cumulative_prob.items()):
        with cols[i]:
            st.metric(threshold, f"{prob:.1f}%")


def display_annualized_cumulative_probability(annualized_cumulative_prob):
    st.subheader("年化收益概率分布")
    
    cols = st.columns(len(annualized_cumulative_prob))
    for i, (threshold, prob) in enumerate(annualized_cumulative_prob.items()):
        with cols[i]:
            st.metric(threshold, f"{prob:.1f}%")


def display_probability_details(results_df, realistic_params=None):
    st.subheader("详细数据")
    
    display_df = results_df.copy()
    
    if realistic_params:
        display_df = display_df[['start_date', 'end_date', 'investment_count', 'total_investment', 
                                  'real_final_asset', 'real_total_return', 'real_annualized', 'total_fees']]
        display_df.columns = ['起始日期', '结束日期', '定投次数', '累计投入', '期末资产', 
                              '累计收益率(%)', '年化收益率(%)', '总费用']
    else:
        display_df = display_df[['start_date', 'end_date', 'investment_count', 'total_investment', 
                                  'ideal_final_asset', 'ideal_total_return', 'ideal_annualized']]
        display_df.columns = ['起始日期', '结束日期', '定投次数', '累计投入', '期末资产', 
                              '累计收益率(%)', '年化收益率(%)']
    
    display_df['起始日期'] = display_df['起始日期'].astype(str)
    display_df['结束日期'] = display_df['结束日期'].astype(str)
    display_df['累计投入'] = display_df['累计投入'].apply(lambda x: f"¥{x:,.0f}")
    display_df['期末资产'] = display_df['期末资产'].apply(lambda x: f"¥{x:,.0f}")
    display_df['累计收益率(%)'] = display_df['累计收益率(%)'].round(2)
    display_df['年化收益率(%)'] = display_df['年化收益率(%)'].round(2)
    
    st.dataframe(display_df, use_container_width=True, height=400)


def display_probability_analysis_results(stats, results, investment_duration, freq_type, freq_param, 
                                         amount, sampling, realistic_params=None):
    from .chart_renderer import create_return_distribution_chart, create_return_timeline_chart, create_cumulative_probability_chart, create_annualized_distribution_chart
    
    st.header(f"概率分析结果（定投时长: {investment_duration}年）")
    
    display_probability_summary(stats, investment_duration, realistic_params)
    
    st.markdown("---")
    display_cumulative_probability(stats['cumulative_prob'])
    
    st.markdown("---")
    display_annualized_cumulative_probability(stats['annualized_cumulative_prob'])
    
    st.markdown("---")
    st.subheader("累计收益分布直方图")
    fig_hist = create_return_distribution_chart(stats, realistic_params)
    st.plotly_chart(fig_hist, use_container_width=True)
    
    st.markdown("---")
    st.subheader("年化收益分布直方图")
    fig_ann_hist = create_annualized_distribution_chart(stats, realistic_params)
    st.plotly_chart(fig_ann_hist, use_container_width=True)
    
    st.markdown("---")
    st.subheader("收益随起始日期变化")
    fig_timeline = create_return_timeline_chart(results, realistic_params)
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    st.markdown("---")
    st.subheader("累计概率曲线")
    fig_cum = create_cumulative_probability_chart(stats, realistic_params)
    st.plotly_chart(fig_cum, use_container_width=True)
    
    st.markdown("---")
    
    with st.expander("查看详细数据"):
        display_probability_details(stats['results_df'], realistic_params)
    
    st.markdown("---")
    st.subheader("分析参数")
    st.write(f"- 定投时长: {investment_duration}年")
    st.write(f"- 定投频率: {freq_type}" + (f" ({freq_param})" if freq_param else ""))
    st.write(f"- 每次定投金额: ¥{amount:,.0f}")
    st.write(f"- 采样方式: {sampling}")
    st.write(f"- 模拟次数: {stats['total_count']}次")


def _render_strategy_config_ui(date_range):
    strategy_type = st.selectbox("策略类型", STRATEGY_TYPES, index=0, help="选择智能定投策略类型")
    
    config_params = {
        'strategy_type': strategy_type,
        'base_amount': DEFAULT_AMOUNT
    }
    
    with st.popover("⚙️ 智能策略参数设置", use_container_width=True):
        if strategy_type == "均线偏离":
            st.markdown("**均线偏离策略参数**")
            
            all_presets = get_all_presets()
            preset_options = list(all_presets.keys()) + ["自定义", "保存当前参数..."]
            
            def on_preset_change():
                selected = st.session_state.ma_preset_select
                if selected in all_presets:
                    preset = all_presets[selected]
                    st.session_state.ma_period_val = preset.get("ma_period", DEFAULT_MA_PERIOD)
                    st.session_state.extreme_high_val = preset.get("extreme_high_threshold", DEFAULT_EXTREME_HIGH_THRESHOLD)
                    st.session_state.extreme_high_m_val = preset.get("extreme_high_multiplier", DEFAULT_EXTREME_HIGH_MULTIPLIER)
                    st.session_state.high_val = preset.get("high_threshold", DEFAULT_HIGH_THRESHOLD)
                    st.session_state.high_m_val = preset.get("high_multiplier", DEFAULT_HIGH_MULTIPLIER)
                    st.session_state.normal_m_val = preset.get("normal_multiplier", DEFAULT_NORMAL_MULTIPLIER)
                    st.session_state.low_val = preset.get("low_threshold", DEFAULT_LOW_THRESHOLD)
                    st.session_state.low_m_val = preset.get("low_multiplier", DEFAULT_LOW_MULTIPLIER)
                    st.session_state.extreme_low_val = preset.get("extreme_low_threshold", DEFAULT_EXTREME_LOW_THRESHOLD)
                    st.session_state.extreme_low_m_val = preset.get("extreme_low_multiplier", DEFAULT_EXTREME_LOW_MULTIPLIER)
            
            selected_preset = st.selectbox("预设参数", preset_options, key="ma_preset_select", help="选择预设参数或自定义", on_change=on_preset_change)
            
            if selected_preset == "保存当前参数...":
                preset_name = st.text_input("参数名称", key="preset_name_input", placeholder="输入参数名称")
                if st.button("保存参数", key="save_preset_btn") and preset_name:
                    current_params = {
                        "ma_period": st.session_state.get("ma_period_val", DEFAULT_MA_PERIOD),
                        "extreme_high_threshold": st.session_state.get("extreme_high_val", DEFAULT_EXTREME_HIGH_THRESHOLD),
                        "extreme_high_multiplier": st.session_state.get("extreme_high_m_val", DEFAULT_EXTREME_HIGH_MULTIPLIER),
                        "high_threshold": st.session_state.get("high_val", DEFAULT_HIGH_THRESHOLD),
                        "high_multiplier": st.session_state.get("high_m_val", DEFAULT_HIGH_MULTIPLIER),
                        "normal_multiplier": st.session_state.get("normal_m_val", DEFAULT_NORMAL_MULTIPLIER),
                        "low_threshold": st.session_state.get("low_val", DEFAULT_LOW_THRESHOLD),
                        "low_multiplier": st.session_state.get("low_m_val", DEFAULT_LOW_MULTIPLIER),
                        "extreme_low_threshold": st.session_state.get("extreme_low_val", DEFAULT_EXTREME_LOW_THRESHOLD),
                        "extreme_low_multiplier": st.session_state.get("extreme_low_m_val", DEFAULT_EXTREME_LOW_MULTIPLIER)
                    }
                    save_custom_preset(preset_name, current_params)
                    st.success(f"已保存参数: {preset_name}")
                    st.rerun()
            
            default_ma = st.session_state.get("ma_period_val", DEFAULT_MA_PERIOD)
            default_extreme_high = st.session_state.get("extreme_high_val", DEFAULT_EXTREME_HIGH_THRESHOLD)
            default_extreme_high_m = st.session_state.get("extreme_high_m_val", DEFAULT_EXTREME_HIGH_MULTIPLIER)
            default_high = st.session_state.get("high_val", DEFAULT_HIGH_THRESHOLD)
            default_high_m = st.session_state.get("high_m_val", DEFAULT_HIGH_MULTIPLIER)
            default_normal_m = st.session_state.get("normal_m_val", DEFAULT_NORMAL_MULTIPLIER)
            default_low = st.session_state.get("low_val", DEFAULT_LOW_THRESHOLD)
            default_low_m = st.session_state.get("low_m_val", DEFAULT_LOW_MULTIPLIER)
            default_extreme_low = st.session_state.get("extreme_low_val", DEFAULT_EXTREME_LOW_THRESHOLD)
            default_extreme_low_m = st.session_state.get("extreme_low_m_val", DEFAULT_EXTREME_LOW_MULTIPLIER)
            
            col1, col2 = st.columns(2)
            with col1:
                ma_period = st.selectbox("均线周期", MA_PERIODS, index=MA_PERIODS.index(default_ma) if default_ma in MA_PERIODS else 0, help="选择移动平均线周期", key="ma_period_val")
            with col2:
                st.info("当价格低于均线时增加定投，高于均线时减少定投")
            
            config_params['ma_period'] = ma_period
            
            st.markdown("**阈值与倍数设置**")
            st.markdown("*偏离度 = (当前价格 - 均线价格) / 均线价格 × 100%*")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**极度高估**")
            with col2:
                extreme_high_threshold = st.number_input("偏离≥", min_value=0.0, max_value=50.0, value=default_extreme_high, step=1.0, key="extreme_high_val", help="价格高于均线该比例时暂停定投")
            with col3:
                extreme_high_multiplier = st.number_input("倍数", min_value=0.0, max_value=1.0, value=default_extreme_high_m, step=0.1, key="extreme_high_m_val", help="0表示暂停定投")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**高估**")
            with col2:
                high_threshold = st.number_input("偏离≥", min_value=0.0, max_value=50.0, value=default_high, step=1.0, key="high_val", help="价格高于均线该比例时减少定投")
            with col3:
                high_multiplier = st.number_input("倍数", min_value=0.0, max_value=1.5, value=default_high_m, step=0.1, key="high_m_val", help="高估时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**正常**")
            with col2:
                st.markdown("—")
            with col3:
                normal_multiplier = st.number_input("倍数", min_value=0.5, max_value=2.0, value=default_normal_m, step=0.1, key="normal_m_val", help="正常时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**低估**")
            with col2:
                low_threshold = st.number_input("偏离≤", min_value=-50.0, max_value=0.0, value=default_low, step=1.0, key="low_val", help="价格低于均线该比例时增加定投")
            with col3:
                low_multiplier = st.number_input("倍数", min_value=1.0, max_value=3.0, value=default_low_m, step=0.1, key="low_m_val", help="低估时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**极度低估**")
            with col2:
                extreme_low_threshold = st.number_input("偏离≤", min_value=-50.0, max_value=0.0, value=default_extreme_low, step=1.0, key="extreme_low_val", help="价格低于均线该比例时加倍定投")
            with col3:
                extreme_low_multiplier = st.number_input("倍数", min_value=1.0, max_value=5.0, value=default_extreme_low_m, step=0.5, key="extreme_low_m_val", help="极度低估时的定投倍数")
            
            config_params['extreme_high_threshold'] = extreme_high_threshold / 100
            config_params['high_threshold'] = high_threshold / 100
            config_params['low_threshold'] = low_threshold / 100
            config_params['extreme_low_threshold'] = extreme_low_threshold / 100
        
        elif strategy_type == "趋势动量":
            st.markdown("**趋势动量策略参数**")
            col1, col2 = st.columns(2)
            with col1:
                trend_period = st.number_input("判断周期（天）", min_value=5, max_value=120, value=DEFAULT_TREND_PERIOD, step=5, help="计算过去N天的涨跌幅")
            with col2:
                st.info("根据过去一段时间的涨跌幅判断市场状态")
            
            config_params['trend_period'] = trend_period
            
            st.markdown("**阈值与倍数设置**")
            st.markdown("*涨跌幅 = (当前价格 - N天前价格) / N天前价格 × 100%*")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**极度高估**")
            with col2:
                trend_extreme_high_threshold = st.number_input("涨幅≥", min_value=0.0, max_value=100.0, value=DEFAULT_TREND_EXTREME_HIGH_THRESHOLD, step=1.0, key="trend_extreme_high", help="涨幅超过该值时暂停定投")
            with col3:
                extreme_high_multiplier = st.number_input("倍数", min_value=0.0, max_value=1.0, value=DEFAULT_EXTREME_HIGH_MULTIPLIER, step=0.1, key="trend_extreme_high_m", help="0表示暂停定投")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**高估**")
            with col2:
                trend_high_threshold = st.number_input("涨幅≥", min_value=0.0, max_value=100.0, value=DEFAULT_TREND_HIGH_THRESHOLD, step=1.0, key="trend_high", help="涨幅超过该值时减少定投")
            with col3:
                high_multiplier = st.number_input("倍数", min_value=0.0, max_value=1.5, value=DEFAULT_HIGH_MULTIPLIER, step=0.1, key="trend_high_m", help="高估时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**正常**")
            with col2:
                st.markdown("—")
            with col3:
                normal_multiplier = st.number_input("倍数", min_value=0.5, max_value=2.0, value=DEFAULT_NORMAL_MULTIPLIER, step=0.1, key="trend_normal_m", help="正常时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**低估**")
            with col2:
                trend_low_threshold = st.number_input("跌幅≤", min_value=-100.0, max_value=0.0, value=DEFAULT_TREND_LOW_THRESHOLD, step=1.0, key="trend_low", help="跌幅超过该值时增加定投")
            with col3:
                low_multiplier = st.number_input("倍数", min_value=1.0, max_value=3.0, value=DEFAULT_LOW_MULTIPLIER, step=0.1, key="trend_low_m", help="低估时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**极度低估**")
            with col2:
                trend_extreme_low_threshold = st.number_input("跌幅≤", min_value=-100.0, max_value=0.0, value=DEFAULT_TREND_EXTREME_LOW_THRESHOLD, step=1.0, key="trend_extreme_low", help="跌幅超过该值时加倍定投")
            with col3:
                extreme_low_multiplier = st.number_input("倍数", min_value=1.0, max_value=5.0, value=DEFAULT_EXTREME_LOW_MULTIPLIER, step=0.5, key="trend_extreme_low_m", help="极度低估时的定投倍数")
            
            config_params['trend_extreme_high_threshold'] = trend_extreme_high_threshold / 100
            config_params['trend_high_threshold'] = trend_high_threshold / 100
            config_params['trend_low_threshold'] = trend_low_threshold / 100
            config_params['trend_extreme_low_threshold'] = trend_extreme_low_threshold / 100
        
        elif strategy_type == "估值分位":
            st.markdown("**估值分位策略参数**")
            
            if not date_range.get('has_valuation', False):
                st.warning("当前数据不包含估值信息（PE/PB），将无法使用估值策略")
            
            col1, col2 = st.columns(2)
            with col1:
                valuation_options = VALUATION_COLUMNS if date_range.get('has_valuation', False) else VALUATION_COLUMNS
                valuation_column = st.selectbox("估值指标", valuation_options, index=0, help="选择估值指标")
            with col2:
                st.info("根据估值历史分位数调整定投金额")
            
            config_params['valuation_column'] = valuation_column
            
            st.markdown("**阈值与倍数设置**")
            st.markdown("*分位数 = 当前估值在历史估值中的排名位置*")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**极度高估**")
            with col2:
                extreme_high_percentile = st.number_input("分位≥", min_value=50.0, max_value=100.0, value=DEFAULT_EXTREME_HIGH_PERCENTILE, step=5.0, key="val_extreme_high", help="估值高于该分位时暂停定投")
            with col3:
                extreme_high_multiplier = st.number_input("倍数", min_value=0.0, max_value=1.0, value=DEFAULT_EXTREME_HIGH_MULTIPLIER, step=0.1, key="val_extreme_high_m", help="0表示暂停定投")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**高估**")
            with col2:
                high_percentile = st.number_input("分位≥", min_value=50.0, max_value=100.0, value=DEFAULT_HIGH_PERCENTILE, step=5.0, key="val_high", help="估值高于该分位时减少定投")
            with col3:
                high_multiplier = st.number_input("倍数", min_value=0.0, max_value=1.5, value=DEFAULT_HIGH_MULTIPLIER, step=0.1, key="val_high_m", help="高估时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**正常**")
            with col2:
                st.markdown("—")
            with col3:
                normal_multiplier = st.number_input("倍数", min_value=0.5, max_value=2.0, value=DEFAULT_NORMAL_MULTIPLIER, step=0.1, key="val_normal_m", help="正常时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**低估**")
            with col2:
                low_percentile = st.number_input("分位≤", min_value=0.0, max_value=50.0, value=DEFAULT_LOW_PERCENTILE, step=5.0, key="val_low", help="估值低于该分位时增加定投")
            with col3:
                low_multiplier = st.number_input("倍数", min_value=1.0, max_value=3.0, value=DEFAULT_LOW_MULTIPLIER, step=0.1, key="val_low_m", help="低估时的定投倍数")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([2, 1, 3])
            with col1:
                st.markdown("**极度低估**")
            with col2:
                extreme_low_percentile = st.number_input("分位≤", min_value=0.0, max_value=50.0, value=DEFAULT_EXTREME_LOW_PERCENTILE, step=5.0, key="val_extreme_low", help="估值低于该分位时加倍定投")
            with col3:
                extreme_low_multiplier = st.number_input("倍数", min_value=1.0, max_value=5.0, value=DEFAULT_EXTREME_LOW_MULTIPLIER, step=0.5, key="val_extreme_low_m", help="极度低估时的定投倍数")
            
            config_params['extreme_high_percentile'] = extreme_high_percentile
            config_params['high_percentile'] = high_percentile
            config_params['low_percentile'] = low_percentile
            config_params['extreme_low_percentile'] = extreme_low_percentile
        
        elif strategy_type == "组合策略":
            st.markdown("**组合策略参数**")
            st.info("组合策略将同时使用均线偏离和趋势动量策略，取平均信号")
            
            col1, col2 = st.columns(2)
            with col1:
                ma_period = st.selectbox("均线周期", MA_PERIODS, index=MA_PERIODS.index(DEFAULT_MA_PERIOD), key="combo_ma")
            with col2:
                trend_period = st.number_input("趋势周期（天）", min_value=5, max_value=120, value=DEFAULT_TREND_PERIOD, step=5, key="combo_trend")
            
            config_params['ma_period'] = ma_period
            config_params['trend_period'] = trend_period
            config_params['extreme_high_threshold'] = DEFAULT_EXTREME_HIGH_THRESHOLD / 100
            config_params['high_threshold'] = DEFAULT_HIGH_THRESHOLD / 100
            config_params['low_threshold'] = DEFAULT_LOW_THRESHOLD / 100
            config_params['extreme_low_threshold'] = DEFAULT_EXTREME_LOW_THRESHOLD / 100
            config_params['trend_extreme_high_threshold'] = DEFAULT_TREND_EXTREME_HIGH_THRESHOLD / 100
            config_params['trend_high_threshold'] = DEFAULT_TREND_HIGH_THRESHOLD / 100
            config_params['trend_low_threshold'] = DEFAULT_TREND_LOW_THRESHOLD / 100
            config_params['trend_extreme_low_threshold'] = DEFAULT_TREND_EXTREME_LOW_THRESHOLD / 100
            
            st.markdown("**金额调整倍数**")
            col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
            with col_m1:
                extreme_high_multiplier = st.number_input("极度高估", min_value=0.0, max_value=1.0, value=DEFAULT_EXTREME_HIGH_MULTIPLIER, step=0.1, key="combo_extreme_high_m")
            with col_m2:
                high_multiplier = st.number_input("高估", min_value=0.0, max_value=1.5, value=DEFAULT_HIGH_MULTIPLIER, step=0.1, key="combo_high_m")
            with col_m3:
                normal_multiplier = st.number_input("正常", min_value=0.5, max_value=2.0, value=DEFAULT_NORMAL_MULTIPLIER, step=0.1, key="combo_normal_m")
            with col_m4:
                low_multiplier = st.number_input("低估", min_value=1.0, max_value=3.0, value=DEFAULT_LOW_MULTIPLIER, step=0.1, key="combo_low_m")
            with col_m5:
                extreme_low_multiplier = st.number_input("极度低估", min_value=1.0, max_value=5.0, value=DEFAULT_EXTREME_LOW_MULTIPLIER, step=0.5, key="combo_extreme_low_m")
    
    config_params['extreme_low_multiplier'] = extreme_low_multiplier
    config_params['low_multiplier'] = low_multiplier
    config_params['normal_multiplier'] = normal_multiplier
    config_params['high_multiplier'] = high_multiplier
    config_params['extreme_high_multiplier'] = extreme_high_multiplier
    
    return SmartStrategyConfig(**config_params)


def _render_comparison_ui(df, date_range):
    st.subheader("定投区间")
    date_mode = st.radio("日期选择方式", ["手动选择日期", "按持有年限", "随机持有年限"], horizontal=True, index=2, key="comp_date_mode")
    
    start_date = None
    end_date = None
    
    if date_mode == "手动选择日期":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=date_range['min_date'], min_value=date_range['min_date'], max_value=date_range['max_date'], key="comp_start")
        with col2:
            end_date = st.date_input("结束日期", value=date_range['max_date'], min_value=date_range['min_date'], max_value=date_range['max_date'], key="comp_end")
    
    elif date_mode == "按持有年限":
        start_date = st.date_input("开始日期", value=date_range['min_date'], min_value=date_range['min_date'], max_value=date_range['max_date'], key="comp_start_hold")
        holding_years = st.number_input("持有年限", min_value=MIN_HOLDING_YEARS, max_value=float(int(date_range['max_years'] * 10) / 10), value=DEFAULT_HOLDING_YEARS, step=HOLDING_YEARS_STEP, key="comp_hold_years")
        end_date = start_date + timedelta(days=int(holding_years * 365))
        if end_date > date_range['max_date']:
            end_date = date_range['max_date']
            st.warning(f"持有年限超出数据范围，结束日期已调整为 {end_date}")
        st.info(f"结束日期: {end_date}")
    
    elif date_mode == "随机持有年限":
        holding_years = st.number_input("持有年限", min_value=MIN_HOLDING_YEARS, max_value=float(int(date_range['max_years'] * 10) / 10), value=DEFAULT_HOLDING_YEARS, step=HOLDING_YEARS_STEP, key="comp_rand_years")
        random_seed = st.checkbox("固定随机种子", value=False, key="comp_rand_seed")
        if random_seed:
            seed_value = st.number_input("随机种子", min_value=0, max_value=99999, value=42, step=1, key="comp_seed_val")
        else:
            seed_value = None
        
        max_start_date = date_range['max_date'] - timedelta(days=int(holding_years * 365))
        if max_start_date < date_range['min_date']:
            st.warning(f"持有年限 {holding_years} 年超出数据范围，请减小持有年限")
            start_date = date_range['min_date']
            end_date = date_range['max_date']
        else:
            if seed_value is not None:
                random.seed(seed_value)
            random_days = random.randint(0, (max_start_date - date_range['min_date']).days)
            start_date = date_range['min_date'] + timedelta(days=random_days)
            end_date = start_date + timedelta(days=int(holding_years * 365))
            if end_date > date_range['max_date']:
                end_date = date_range['max_date']
            st.info(f"随机选择的时间段:\n开始: {start_date}\n结束: {end_date}")
    
    st.subheader("定投频率")
    freq_type = st.radio("选择频率", ["按日", "按周", "按月", "一次性投入"], horizontal=True, index=1, key="comp_freq")
    
    freq_param = None
    if freq_type == "按周":
        freq_param = st.selectbox("选择定投日", WEEKDAYS, index=0, key="comp_freq_week")
    elif freq_type == "按月":
        freq_param = st.selectbox("选择定投日", MONTH_OPTIONS, index=0, key="comp_freq_month")
    
    st.subheader("基础定投金额")
    amount = st.number_input("每次定投金额（元）", min_value=MIN_AMOUNT, max_value=MAX_AMOUNT, value=DEFAULT_AMOUNT, step=AMOUNT_STEP, key="comp_amount", help="智能策略将以此金额为基础进行调整")
    
    strategy_config = _render_strategy_config_ui(date_range)
    strategy_config.base_amount = amount
    
    realistic_params = _render_realistic_params()
    
    run_backtest = st.button("开始对比分析", type="primary", use_container_width=True)
    
    return {
        'df': df,
        'date_range': date_range,
        'start_date': start_date,
        'end_date': end_date,
        'freq_type': freq_type,
        'freq_param': freq_param,
        'amount': amount,
        'realistic_params': realistic_params,
        'run_backtest': run_backtest,
        'strategy_mode': 'smart',
        'strategy_config': strategy_config
    }


def display_comparison_results(comparison_data, start_date, end_date, freq_type, freq_param, 
                               base_amount, strategy_config, realistic_params, use_cash_flow=True):
    from .chart_renderer import create_comparison_chart, create_strategy_signal_chart, create_amount_distribution_chart
    from .risk_analyzer import analyze_risk_metrics
    
    fixed = comparison_data['fixed']
    smart = comparison_data['smart']
    
    st.header(f"策略对比结果（{start_date} ~ {end_date}）")
    
    st.subheader("核心指标对比")
    
    fixed_last_row = fixed['daily_df'].iloc[-1]
    smart_last_row = smart['daily_df'].iloc[-1]
    
    fixed_final_asset = fixed_last_row['理想持仓市值']
    fixed_total_investment = fixed['total_investment']
    fixed_total_deposited = fixed.get('total_deposited', fixed_total_investment)
    fixed_total_return = (fixed_final_asset - fixed_total_deposited) / fixed_total_deposited * 100
    
    smart_final_asset = smart_last_row['理想持仓市值']
    smart_total_investment = smart['total_investment']
    smart_total_deposited = smart.get('total_deposited', smart_total_investment)
    smart_cash_balance = smart.get('cash_balance', 0)
    smart_total_asset = smart_final_asset + smart_cash_balance
    smart_total_return = (smart_total_asset - smart_total_deposited) / smart_total_deposited * 100 if smart_total_deposited > 0 else 0
    
    days = (end_date - start_date).days
    years = days / 365.0 if days > 0 else 0
    
    fixed_annualized = ((1 + fixed_total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    smart_annualized = ((1 + smart_total_return / 100) ** (1 / years) - 1) * 100 if years > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("固定定投累计存入", f"¥{fixed_total_deposited:,.2f}")
    with col2:
        st.metric("智能定投累计存入", f"¥{smart_total_deposited:,.2f}")
    with col3:
        if use_cash_flow:
            st.metric("存入金额一致", "✓", help="启用现金流账户后，两种策略存入金额相同")
        else:
            diff_investment = smart_total_investment - fixed_total_investment
            st.metric("投入差异", f"¥{diff_investment:,.2f}", 
                      f"{'多投入' if diff_investment > 0 else '少投入'} {abs(diff_investment/fixed_total_investment*100):.1f}%")
    
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("固定定投期末资产", f"¥{fixed_final_asset:,.2f}")
    with col5:
        st.metric("智能定投期末资产", f"¥{smart_final_asset:,.2f}")
    with col6:
        diff_asset = smart_final_asset - fixed_final_asset
        st.metric("资产差异", f"¥{diff_asset:,.2f}",
                  f"{'+' if diff_asset > 0 else ''}{diff_asset/fixed_final_asset*100:.2f}%")
    
    if use_cash_flow and smart_cash_balance > 0:
        col_cash1, col_cash2, col_cash3 = st.columns(3)
        with col_cash1:
            st.metric("智能定投现金余额", f"¥{smart_cash_balance:,.2f}", help="未投入的现金")
        with col_cash2:
            st.metric("智能定投总资产", f"¥{smart_total_asset:,.2f}", help="持仓市值 + 现金余额")
        with col_cash3:
            cash_utilization = (smart_total_investment / smart_total_deposited * 100) if smart_total_deposited > 0 else 0
            st.metric("现金利用率", f"{cash_utilization:.1f}%", help="实际投入/累计存入")
    
    col7, col8, col9 = st.columns(3)
    with col7:
        st.metric("固定定投累计收益率", f"{fixed_total_return:.2f}%")
    with col8:
        st.metric("智能定投累计收益率", f"{smart_total_return:.2f}%")
    with col9:
        diff_return = smart_total_return - fixed_total_return
        st.metric("收益率差异", f"{diff_return:+.2f}%")
    
    col10, col11, col12 = st.columns(3)
    with col10:
        st.metric("固定定投年化收益率", f"{fixed_annualized:.2f}%")
    with col11:
        st.metric("智能定投年化收益率", f"{smart_annualized:.2f}%")
    with col12:
        diff_ann = smart_annualized - fixed_annualized
        st.metric("年化差异", f"{diff_ann:+.2f}%")
    
    st.markdown("---")
    st.subheader("资产对比曲线")
    fig_comparison = create_comparison_chart(fixed['daily_df'], smart['daily_df'], realistic_params)
    st.plotly_chart(fig_comparison, use_container_width=True)
    
    st.markdown("---")
    st.subheader("策略信号分析")
    
    smart_results = smart['results_df']
    signal_counts = smart_results['信号'].value_counts()
    
    col_sig1, col_sig2, col_sig3, col_sig4, col_sig5 = st.columns(5)
    with col_sig1:
        st.metric("加倍定投", f"{signal_counts.get('extreme_low', 0)}次")
    with col_sig2:
        st.metric("增加定投", f"{signal_counts.get('low', 0)}次")
    with col_sig3:
        st.metric("正常定投", f"{signal_counts.get('normal', 0)}次")
    with col_sig4:
        st.metric("减少定投", f"{signal_counts.get('high', 0)}次")
    with col_sig5:
        st.metric("暂停定投", f"{signal_counts.get('extreme_high', 0)}次")
    
    fig_signal = create_strategy_signal_chart(smart_results)
    st.plotly_chart(fig_signal, use_container_width=True)
    
    st.markdown("---")
    st.subheader("定投金额分布")
    fig_amount = create_amount_distribution_chart(smart_results, base_amount)
    st.plotly_chart(fig_amount, use_container_width=True)
    
    st.markdown("---")
    st.subheader("策略参数")
    st.write(f"- 策略类型: {strategy_config.strategy_type}")
    st.write(f"- 基础定投金额: ¥{base_amount:,.2f}")
    if use_cash_flow:
        st.write(f"- 现金流账户: 已启用")
    if hasattr(strategy_config, 'ma_period'):
        st.write(f"- 均线周期: {strategy_config.ma_period}天")
    if hasattr(strategy_config, 'trend_period'):
        st.write(f"- 趋势周期: {strategy_config.trend_period}天")
    
    st.markdown("---")
    with st.expander("查看智能定投明细"):
        display_smart_investment_records(smart_results)


def display_smart_investment_records(results_df):
    display_df = results_df.copy()
    display_df['日期'] = display_df['日期'].astype(str)
    display_df['收盘价'] = display_df['收盘价'].round(2)
    display_df['买入份额'] = display_df['买入份额'].round(4)
    display_df['累计份额'] = display_df['累计份额'].round(4)
    display_df['投入金额'] = display_df['投入金额'].apply(lambda x: f"¥{x:,.2f}")
    display_df['累计投入'] = display_df['累计投入'].apply(lambda x: f"¥{x:,.2f}")
    
    st.dataframe(
        display_df[['日期', '收盘价', '信号', '倍数', '投入金额', '买入份额', '累计份额', '累计投入', '原因']],
        use_container_width=True,
        height=400
    )


def display_comparison_probability_results(comparison_stats, investment_duration, freq_type, freq_param, 
                                            base_amount, sampling, strategy_config, realistic_params=None, use_cash_flow=True):
    from .chart_renderer import create_comparison_probability_chart, create_comparison_timeline_chart
    
    st.header(f"策略对比概率分析结果（定投时长: {investment_duration}年）")
    
    st.subheader("核心指标对比")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("固定定投盈利概率", f"{comparison_stats['fixed_profit_probability']:.1f}%")
    with col2:
        st.metric("智能定投盈利概率", f"{comparison_stats['smart_profit_probability']:.1f}%")
    with col3:
        diff = comparison_stats['smart_profit_probability'] - comparison_stats['fixed_profit_probability']
        st.metric("盈利概率差异", f"{diff:+.1f}%")
    
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("固定定投平均收益", f"{comparison_stats['fixed_avg_return']:.2f}%")
    with col5:
        st.metric("智能定投平均收益", f"{comparison_stats['smart_avg_return']:.2f}%")
    with col6:
        diff = comparison_stats['smart_avg_return'] - comparison_stats['fixed_avg_return']
        st.metric("平均收益差异", f"{diff:+.2f}%")
    
    col7, col8, col9 = st.columns(3)
    with col7:
        st.metric("固定定投中位数收益", f"{comparison_stats['fixed_median_return']:.2f}%")
    with col8:
        st.metric("智能定投中位数收益", f"{comparison_stats['smart_median_return']:.2f}%")
    with col9:
        diff = comparison_stats['smart_median_return'] - comparison_stats['fixed_median_return']
        st.metric("中位数差异", f"{diff:+.2f}%")
    
    col10, col11, col12 = st.columns(3)
    with col10:
        st.metric("固定定投平均年化", f"{comparison_stats['fixed_avg_annualized']:.2f}%")
    with col11:
        st.metric("智能定投平均年化", f"{comparison_stats['smart_avg_annualized']:.2f}%")
    with col12:
        diff = comparison_stats['smart_avg_annualized'] - comparison_stats['fixed_avg_annualized']
        st.metric("年化差异", f"{diff:+.2f}%")
    
    st.markdown("---")
    st.subheader("智能策略胜率分析")
    
    col13, col14, col15 = st.columns(3)
    with col13:
        st.metric("智能策略胜率", f"{comparison_stats['smart_win_rate']:.1f}%", 
                  help=f"在 {comparison_stats['total_count']} 次模拟中，智能定投收益超过固定定投的次数为 {comparison_stats['smart_win_count']} 次")
    with col14:
        st.metric("平均收益提升", f"{comparison_stats['avg_return_diff']:+.2f}%")
    with col15:
        st.metric("平均年化提升", f"{comparison_stats['avg_annualized_diff']:+.2f}%")
    
    st.markdown("---")
    st.subheader("投入金额对比")
    
    smart_avg_deposited = comparison_stats.get('smart_avg_deposited', comparison_stats['smart_avg_investment'])
    smart_avg_cash_balance = comparison_stats.get('smart_avg_cash_balance', 0)
    
    col16, col17, col18 = st.columns(3)
    with col16:
        st.metric("固定定投平均存入", f"¥{comparison_stats['fixed_avg_investment']:,.0f}")
    with col17:
        st.metric("智能定投平均存入", f"¥{smart_avg_deposited:,.0f}")
    with col18:
        if use_cash_flow:
            st.metric("存入金额一致", "✓", help="启用现金流账户后，两种策略存入金额相同")
        else:
            diff = comparison_stats['smart_avg_investment'] - comparison_stats['fixed_avg_investment']
            pct = diff / comparison_stats['fixed_avg_investment'] * 100 if comparison_stats['fixed_avg_investment'] > 0 else 0
            st.metric("投入差异", f"¥{diff:,.0f}", f"{pct:+.1f}%")
    
    if use_cash_flow and smart_avg_cash_balance > 0:
        col_cash1, col_cash2 = st.columns(2)
        with col_cash1:
            st.metric("智能定投平均现金余额", f"¥{smart_avg_cash_balance:,.0f}", help="期末未投入的现金")
        with col_cash2:
            cash_utilization = ((comparison_stats['smart_avg_investment'] / smart_avg_deposited) * 100) if smart_avg_deposited > 0 else 0
            st.metric("平均现金利用率", f"{cash_utilization:.1f}%", help="实际投入/累计存入")
    
    st.markdown("---")
    st.subheader("收益分布对比")
    fig_dist = create_comparison_probability_chart(comparison_stats, realistic_params)
    st.plotly_chart(fig_dist, use_container_width=True)
    
    st.markdown("---")
    st.subheader("收益差异随起始日期变化")
    fig_timeline = create_comparison_timeline_chart(comparison_stats, realistic_params)
    st.plotly_chart(fig_timeline, use_container_width=True)
    
    st.markdown("---")
    st.subheader("分析参数")
    st.write(f"- 定投时长: {investment_duration}年")
    st.write(f"- 定投频率: {freq_type}" + (f" ({freq_param})" if freq_param else ""))
    st.write(f"- 基础定投金额: ¥{base_amount:,.0f}")
    st.write(f"- 采样方式: {sampling}")
    st.write(f"- 模拟次数: {comparison_stats['total_count']}次")
    st.write(f"- 策略类型: {strategy_config.strategy_type}")
    if use_cash_flow:
        st.write(f"- 现金流账户: 已启用")
    
    st.markdown("---")
    with st.expander("查看详细数据"):
        col_detail1, col_detail2 = st.columns(2)
        with col_detail1:
            st.markdown("**固定定投结果**")
            fixed_df = comparison_stats['fixed_results_df'].copy()
            fixed_df['起始日期'] = fixed_df['start_date'].astype(str)
            fixed_df['结束日期'] = fixed_df['end_date'].astype(str)
            if realistic_params:
                display_cols = ['起始日期', '结束日期', 'investment_count', 'total_investment', 
                               'real_total_return', 'real_annualized']
                fixed_df['累计收益率(%)'] = fixed_df['real_total_return'].round(2)
                fixed_df['年化收益率(%)'] = fixed_df['real_annualized'].round(2)
            else:
                display_cols = ['起始日期', '结束日期', 'investment_count', 'total_investment', 
                               'ideal_total_return', 'ideal_annualized']
                fixed_df['累计收益率(%)'] = fixed_df['ideal_total_return'].round(2)
                fixed_df['年化收益率(%)'] = fixed_df['ideal_annualized'].round(2)
            fixed_df['累计投入'] = fixed_df['total_investment'].apply(lambda x: f"¥{x:,.0f}")
            st.dataframe(fixed_df[['起始日期', '结束日期', 'investment_count', '累计投入', '累计收益率(%)', '年化收益率(%)']], 
                        use_container_width=True, height=300)
        
        with col_detail2:
            st.markdown("**智能定投结果**")
            smart_df = comparison_stats['smart_results_df'].copy()
            smart_df['起始日期'] = smart_df['start_date'].astype(str)
            smart_df['结束日期'] = smart_df['end_date'].astype(str)
            if 'total_return_with_cash' in smart_df.columns:
                smart_df['累计收益率(%)'] = smart_df['total_return_with_cash'].round(2)
                smart_df['年化收益率(%)'] = smart_df['annualized_with_cash'].round(2)
            elif realistic_params:
                smart_df['累计收益率(%)'] = smart_df['real_total_return'].round(2)
                smart_df['年化收益率(%)'] = smart_df['real_annualized'].round(2)
            else:
                smart_df['累计收益率(%)'] = smart_df['ideal_total_return'].round(2)
                smart_df['年化收益率(%)'] = smart_df['ideal_annualized'].round(2)
            smart_df['累计投入'] = smart_df['total_investment'].apply(lambda x: f"¥{x:,.0f}")
            st.dataframe(smart_df[['起始日期', '结束日期', 'investment_count', '累计投入', '累计收益率(%)', '年化收益率(%)']], 
                        use_container_width=True, height=300)
