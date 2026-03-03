import streamlit as st

from modules.config import PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE
from modules.ui_components import render_sidebar, display_results, display_probability_analysis_results, display_comparison_results
from modules.investment import (
    get_investment_dates,
    run_backtest_calculation,
    calculate_daily_assets,
    calculate_lump_sum_return,
    run_comparison_backtest
)
from modules.risk_analyzer import analyze_risk_metrics
from modules.probability_analyzer import run_probability_analysis, calculate_probability_statistics

st.set_page_config(page_title=PAGE_TITLE, layout=PAGE_LAYOUT, initial_sidebar_state=SIDEBAR_STATE)

st.title(PAGE_TITLE)
st.markdown("---")

params = render_sidebar()

if params['df'] is not None and params['run_backtest']:
    if params['mode'] == 'single':
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
                    if params.get('strategy_mode', 'fixed') == 'smart':
                        results_df, total_shares_ideal, total_investment, total_purchase_fee = run_backtest_calculation(
                            params['df'], 
                            investment_dates, 
                            params['amount'], 
                            params['realistic_params']
                        )
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
    
    elif params['mode'] == 'probability':
        if params['analysis_start_date'] >= params['analysis_end_date']:
            st.error("分析开始日期必须早于分析结束日期！")
        else:
            sampling_map = {
                "每月采样": "monthly",
                "每周采样": "weekly", 
                "每日采样": "daily"
            }
            sampling = sampling_map.get(params['sampling'], "monthly")
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(current, total):
                progress = int(current / total * 100)
                progress_bar.progress(progress)
                status_text.text(f"正在计算... {current}/{total} ({progress}%)")
            
            with st.spinner("正在进行概率分析..."):
                results = run_probability_analysis(
                    params['df'],
                    params['analysis_start_date'],
                    params['analysis_end_date'],
                    params['investment_duration'],
                    params['freq_type'],
                    params['freq_param'],
                    params['amount'],
                    params['realistic_params'],
                    sampling=sampling,
                    progress_callback=update_progress
                )
                
                if len(results) == 0:
                    st.warning("没有找到有效的分析结果！请检查参数设置。")
                else:
                    stats = calculate_probability_statistics(results, params['realistic_params'])
                    
                    progress_bar.progress(100)
                    status_text.text(f"分析完成！共 {len(results)} 次模拟")
                    
                    display_probability_analysis_results(
                        stats,
                        results,
                        params['investment_duration'],
                        params['freq_type'],
                        params['freq_param'],
                        params['amount'],
                        params['sampling'],
                        params['realistic_params']
                    )
    
    elif params['mode'] == 'comparison':
        if params['start_date'] >= params['end_date']:
            st.error("开始日期必须早于结束日期！")
        else:
            with st.spinner("正在进行策略对比分析..."):
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
                    comparison_data = run_comparison_backtest(
                        params['df'],
                        investment_dates,
                        params['amount'],
                        params['strategy_config'],
                        params['realistic_params']
                    )
                    
                    fixed_daily_df = comparison_data['fixed']['daily_df']
                    fixed_daily_df = fixed_daily_df[
                        (fixed_daily_df['日期'].dt.date >= params['start_date']) & 
                        (fixed_daily_df['日期'].dt.date <= params['end_date'])
                    ]
                    comparison_data['fixed']['daily_df'] = fixed_daily_df
                    
                    smart_daily_df = comparison_data['smart']['daily_df']
                    smart_daily_df = smart_daily_df[
                        (smart_daily_df['日期'].dt.date >= params['start_date']) & 
                        (smart_daily_df['日期'].dt.date <= params['end_date'])
                    ]
                    comparison_data['smart']['daily_df'] = smart_daily_df
                    
                    display_comparison_results(
                        comparison_data,
                        params['start_date'],
                        params['end_date'],
                        params['freq_type'],
                        params['freq_param'],
                        params['amount'],
                        params['strategy_config'],
                        params['realistic_params']
                    )

elif params['df'] is not None and not params['run_backtest']:
    if params['mode'] == 'single':
        st.info("请在左侧设置参数后点击「开始回测」按钮")
    elif params['mode'] == 'probability':
        st.info("请在左侧设置参数后点击「开始概率分析」按钮")
    else:
        st.info("请在左侧设置参数后点击「开始对比分析」按钮")
