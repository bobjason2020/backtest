import streamlit as st
import random
from datetime import timedelta

from .config import (
    WEEKDAYS, MONTH_OPTIONS,
    DEFAULT_AMOUNT, MIN_AMOUNT, MAX_AMOUNT, AMOUNT_STEP,
    DEFAULT_MANAGEMENT_FEE, DEFAULT_CUSTODY_FEE,
    DEFAULT_PURCHASE_FEE, DEFAULT_REDEMPTION_FEE,
    DEFAULT_CASH_RATIO, DEFAULT_TRACKING_ERROR,
    DEFAULT_HOLDING_YEARS, MIN_HOLDING_YEARS, HOLDING_YEARS_STEP
)
from .data_loader import load_excel_file, get_date_range
from .chart_renderer import create_asset_chart, create_price_chart, create_return_chart


def render_sidebar():
    with st.sidebar:
        st.header("参数设置")
        
        uploaded_file = st.file_uploader("选择数据文件", type=["xlsx"])
        
        params = {
            'uploaded_file': uploaded_file,
            'df': None,
            'date_range': None,
            'start_date': None,
            'end_date': None,
            'freq_type': None,
            'freq_param': None,
            'amount': DEFAULT_AMOUNT,
            'realistic_params': None,
            'run_backtest': False
        }
        
        if uploaded_file is not None:
            df, error = load_excel_file(uploaded_file)
            
            if error:
                st.error(f"文件读取错误: {error}")
                return params
            
            date_range = get_date_range(df)
            
            st.success(f"数据加载成功！\n共 {date_range['record_count']} 条记录\n日期范围: {date_range['min_date']} ~ {date_range['max_date']}")
            
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
            
            st.subheader("定投金额")
            amount = st.number_input("每次定投金额（元）", min_value=MIN_AMOUNT, max_value=MAX_AMOUNT, value=DEFAULT_AMOUNT, step=AMOUNT_STEP)
            
            st.subheader("基金现实因素")
            consider_realistic = st.checkbox("考虑基金现实因素", value=True)
            
            realistic_params = None
            if consider_realistic:
                st.markdown("**费用参数**")
                col_fee1, col_fee2 = st.columns(2)
                with col_fee1:
                    management_fee = st.number_input("管理费率（年化%）", min_value=0.0, max_value=3.0, value=DEFAULT_MANAGEMENT_FEE, step=0.01)
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
            
            run_backtest = st.button("开始回测", type="primary", use_container_width=True)
            
            params.update({
                'df': df,
                'date_range': date_range,
                'start_date': start_date,
                'end_date': end_date,
                'freq_type': freq_type,
                'freq_param': freq_param,
                'amount': amount,
                'realistic_params': realistic_params,
                'run_backtest': run_backtest
            })
        else:
            st.info("请上传 Excel 数据文件")
        
        return params


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
