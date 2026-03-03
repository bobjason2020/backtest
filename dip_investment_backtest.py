import streamlit as st

from modules.config import PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE
from modules.ui_components import render_sidebar, display_results
from modules.investment import (
    get_investment_dates,
    run_backtest_calculation,
    calculate_daily_assets,
    calculate_lump_sum_return
)
from modules.risk_analyzer import analyze_risk_metrics

st.set_page_config(page_title=PAGE_TITLE, layout=PAGE_LAYOUT, initial_sidebar_state=SIDEBAR_STATE)

st.title(PAGE_TITLE)
st.markdown("---")

params = render_sidebar()

if params['run_backtest'] and params['df'] is not None:
    if params['start_date'] >= params['end_date']:
        st.error("开始日期必须早于结束日期！")
    else:
        with st.spinner("正在计算回测结果..."):
            investment_dates = get_investment_dates(
                params['df'], 
                params['start_date'], 
                params['end_date'], 
                params['freq_type'], 
                params['freq_param']
            )
            
            if len(investment_dates) == 0:
                st.warning("在选定的时间范围内没有找到有效的定投日期！")
            else:
                results_df, total_shares_ideal, total_investment, total_purchase_fee = run_backtest_calculation(
                    params['df'], 
                    investment_dates, 
                    params['amount'], 
                    params['realistic_params']
                )
                
                daily_assets_df = calculate_daily_assets(
                    params['df'], 
                    investment_dates, 
                    params['amount'], 
                    params['realistic_params']
                )
                daily_assets_df = daily_assets_df[
                    (daily_assets_df['日期'].dt.date >= params['start_date']) & 
                    (daily_assets_df['日期'].dt.date <= params['end_date'])
                ]
                
                risk_metrics = analyze_risk_metrics(
                    daily_assets_df, 
                    params['realistic_params'], 
                    params['start_date']
                )
                
                lump_total_return, lump_annualized = calculate_lump_sum_return(
                    params['df'], 
                    params['start_date'], 
                    params['end_date']
                )
                
                display_results(
                    params['start_date'],
                    params['end_date'],
                    params['freq_type'],
                    params['freq_param'],
                    params['amount'],
                    investment_dates,
                    results_df,
                    daily_assets_df,
                    total_shares_ideal,
                    total_investment,
                    total_purchase_fee,
                    params['realistic_params'],
                    risk_metrics,
                    lump_total_return,
                    lump_annualized
                )

elif params['df'] is not None and not params['run_backtest']:
    st.info("请在左侧设置参数后点击「开始回测」按钮")
