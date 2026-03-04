import logging
import streamlit as st

from modules.config import PAGE_TITLE, PAGE_LAYOUT, SIDEBAR_STATE
from modules.ui_components import render_sidebar, display_results, display_probability_analysis_results, display_comparison_results, display_comparison_probability_results
from modules.utils import CacheManager
from modules.data_loader import DataLoader
from modules.investment import (
    get_investment_dates,
    run_backtest_calculation,
    calculate_daily_assets,
    calculate_lump_sum_return,
    run_comparison_backtest
)
from modules.risk_analyzer import analyze_risk_metrics
from modules.probability_analyzer import (
    run_probability_analysis, 
    calculate_probability_statistics,
    run_smart_probability_analysis,
    run_comparison_probability_analysis,
    calculate_comparison_statistics
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BacktestService:
    def __init__(self):
        self.cache_manager = CacheManager()
        self.data_loader = DataLoader()
        logger.info("BacktestService initialized")
    
    def load_data(self, file_source) -> tuple:
        logger.info(f"Loading data from source: {file_source}")
        try:
            df = self.data_loader.load_data(file_source)
            if df is not None:
                logger.info(f"Data loaded successfully, shape: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            return None
    
    def get_date_range_info(self, df) -> dict:
        if df is None or len(df) == 0:
            return {}
        
        info = {
            'min_date': df['日期'].min().date(),
            'max_date': df['日期'].max().date(),
            'total_days': len(df)
        }
        logger.info(f"Date range: {info['min_date']} to {info['max_date']}, total days: {info['total_days']}")
        return info
    
    def run_single_backtest(self, params: dict) -> dict:
        logger.info(f"Running single backtest with params: start={params.get('start_date')}, end={params.get('end_date')}")
        
        if params['start_date'] >= params['end_date']:
            logger.warning("Invalid date range: start_date >= end_date")
            return {'error': "开始日期必须早于结束日期！"}
        
        strategy_mode = params.get('strategy_mode', '固定定投')
        
        if strategy_mode == '策略对比':
            return self._run_comparison_backtest(params)
        else:
            return self._run_fixed_backtest(params)
    
    def _run_fixed_backtest(self, params: dict) -> dict:
        logger.info("Running fixed investment backtest")
        
        investment_dates = get_investment_dates(
            params['df'], 
            params['start_date'], 
            params['end_date'], 
            params['freq_type'], 
            params['freq_param']
        )
        
        if len(investment_dates) == 0:
            logger.warning("No valid investment dates found")
            return {'warning': "在选定的时间范围内没有找到有效的定投日期！"}
        
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
        
        logger.info(f"Fixed backtest completed: {len(investment_dates)} investment dates")
        
        return {
            'investment_dates': investment_dates,
            'results_df': results_df,
            'daily_assets_df': daily_assets_df,
            'total_shares_ideal': total_shares_ideal,
            'total_investment': total_investment,
            'total_purchase_fee': total_purchase_fee,
            'risk_metrics': risk_metrics,
            'lump_total_return': lump_total_return,
            'lump_annualized': lump_annualized
        }
    
    def _run_comparison_backtest(self, params: dict) -> dict:
        logger.info("Running comparison backtest")
        
        investment_dates = get_investment_dates(
            params['df'], 
            params['start_date'], 
            params['end_date'], 
            params['freq_type'], 
            params['freq_param']
        )
        
        if len(investment_dates) == 0:
            logger.warning("No valid investment dates found")
            return {'warning': "在选定的时间范围内没有找到有效的定投日期！"}
        
        comparison_data = run_comparison_backtest(
            params['df'],
            investment_dates,
            params['amount'],
            params['strategy_config'],
            params['realistic_params'],
            use_cash_flow=True
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
        
        logger.info(f"Comparison backtest completed: {len(investment_dates)} investment dates")
        
        return {
            'comparison_data': comparison_data,
            'investment_dates': investment_dates
        }
    
    def run_probability_analysis(self, params: dict) -> dict:
        logger.info(f"Running probability analysis with params: start={params.get('analysis_start_date')}, end={params.get('analysis_end_date')}")
        
        if params['analysis_start_date'] >= params['analysis_end_date']:
            logger.warning("Invalid date range: analysis_start_date >= analysis_end_date")
            return {'error': "分析开始日期必须早于分析结束日期！"}
        
        sampling_map = {
            "每月采样": "monthly",
            "每周采样": "weekly", 
            "每日采样": "daily"
        }
        sampling = sampling_map.get(params['sampling'], "monthly")
        
        strategy_mode = params.get('strategy_mode', '固定定投')
        
        if strategy_mode == '固定定投':
            return self._run_fixed_probability(params, sampling)
        elif strategy_mode == '智能定投':
            return self._run_smart_probability(params, sampling)
        elif strategy_mode == '策略对比':
            return self._run_comparison_probability(params, sampling)
        
        return {'error': f"未知的策略模式: {strategy_mode}"}
    
    def _run_fixed_probability(self, params: dict, sampling: str) -> dict:
        logger.info("Running fixed investment probability analysis")
        
        results, elapsed_time = run_probability_analysis(
            params['df'],
            params['analysis_start_date'],
            params['analysis_end_date'],
            params['investment_duration'],
            params['freq_type'],
            params['freq_param'],
            params['amount'],
            params['realistic_params'],
            sampling=sampling,
            progress_callback=params.get('progress_callback')
        )
        
        if len(results) == 0:
            logger.warning("No valid probability analysis results")
            return {'warning': "没有找到有效的分析结果！请检查参数设置。"}
        
        stats = calculate_probability_statistics(results, params['realistic_params'])
        
        logger.info(f"Fixed probability analysis completed: {len(results)} simulations, {elapsed_time:.1f}s")
        
        return {
            'results': results,
            'stats': stats,
            'elapsed_time': elapsed_time,
            'strategy_mode': '固定定投',
            'use_cash_flow': False
        }
    
    def _run_smart_probability(self, params: dict, sampling: str) -> dict:
        logger.info("Running smart investment probability analysis")
        
        results, elapsed_time = run_smart_probability_analysis(
            params['df'],
            params['analysis_start_date'],
            params['analysis_end_date'],
            params['investment_duration'],
            params['freq_type'],
            params['freq_param'],
            params['amount'],
            params['strategy_config'],
            params['realistic_params'],
            sampling=sampling,
            progress_callback=params.get('progress_callback'),
            use_cash_flow=True
        )
        
        if len(results) == 0:
            logger.warning("No valid probability analysis results")
            return {'warning': "没有找到有效的分析结果！请检查参数设置。"}
        
        stats = calculate_probability_statistics(results, params['realistic_params'], use_cash_flow=True)
        
        logger.info(f"Smart probability analysis completed: {len(results)} simulations, {elapsed_time:.1f}s")
        
        return {
            'results': results,
            'stats': stats,
            'elapsed_time': elapsed_time,
            'strategy_mode': '智能定投',
            'use_cash_flow': True
        }
    
    def _run_comparison_probability(self, params: dict, sampling: str) -> dict:
        logger.info("Running comparison probability analysis")
        
        fixed_results, smart_results, elapsed_time = run_comparison_probability_analysis(
            params['df'],
            params['analysis_start_date'],
            params['analysis_end_date'],
            params['investment_duration'],
            params['freq_type'],
            params['freq_param'],
            params['amount'],
            params['strategy_config'],
            params['realistic_params'],
            sampling=sampling,
            progress_callback=params.get('progress_callback'),
            use_cash_flow=True
        )
        
        if len(fixed_results) == 0:
            logger.warning("No valid probability analysis results")
            return {'warning': "没有找到有效的分析结果！请检查参数设置。"}
        
        comparison_stats = calculate_comparison_statistics(fixed_results, smart_results, params['realistic_params'], use_cash_flow=True)
        
        logger.info(f"Comparison probability analysis completed: {len(fixed_results)} simulations, {elapsed_time:.1f}s")
        
        return {
            'fixed_results': fixed_results,
            'smart_results': smart_results,
            'comparison_stats': comparison_stats,
            'elapsed_time': elapsed_time,
            'strategy_mode': '策略对比'
        }


st.set_page_config(page_title=PAGE_TITLE, layout=PAGE_LAYOUT, initial_sidebar_state=SIDEBAR_STATE)

st.title(PAGE_TITLE)
st.markdown("---")

params = render_sidebar()
service = BacktestService()

if params['df'] is not None and params['run_backtest']:
    if params['mode'] == 'single':
        result = service.run_single_backtest(params)
        
        if 'error' in result:
            st.error(result['error'])
        elif 'warning' in result:
            st.warning(result['warning'])
        elif 'comparison_data' in result:
            with st.spinner("正在进行策略对比分析..."):
                display_comparison_results(
                    result['comparison_data'],
                    params['start_date'],
                    params['end_date'],
                    params['freq_type'],
                    params['freq_param'],
                    params['amount'],
                    params['strategy_config'],
                    params['realistic_params'],
                    use_cash_flow=True
                )
        else:
            with st.spinner("正在计算回测结果..."):
                display_results(
                    params['start_date'],
                    params['end_date'],
                    params['freq_type'],
                    params['freq_param'],
                    params['amount'],
                    result['investment_dates'],
                    result['results_df'],
                    result['daily_assets_df'],
                    result['total_shares_ideal'],
                    result['total_investment'],
                    result['total_purchase_fee'],
                    params['realistic_params'],
                    result['risk_metrics'],
                    result['lump_total_return'],
                    result['lump_annualized']
                )
    
    elif params['mode'] == 'probability':
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total):
            progress = int(current / total * 100)
            progress_bar.progress(progress)
            status_text.text(f"正在计算... {current}/{total} ({progress}%)")
        
        params['progress_callback'] = update_progress
        
        with st.spinner("正在进行概率分析..."):
            result = service.run_probability_analysis(params)
        
        if 'error' in result:
            st.error(result['error'])
        elif 'warning' in result:
            st.warning(result['warning'])
        else:
            progress_bar.progress(100)
            status_text.text(f"分析完成！共 {len(result.get('results', result.get('fixed_results', [])))} 次模拟，耗时 {result['elapsed_time']:.1f} 秒")
            
            if result['strategy_mode'] == '策略对比':
                display_comparison_probability_results(
                    result['comparison_stats'],
                    params['investment_duration'],
                    params['freq_type'],
                    params['freq_param'],
                    params['amount'],
                    params['sampling'],
                    params['strategy_config'],
                    params['realistic_params'],
                    use_cash_flow=True
                )
            else:
                display_probability_analysis_results(
                    result['stats'],
                    result['results'],
                    params['investment_duration'],
                    params['freq_type'],
                    params['freq_param'],
                    params['amount'],
                    params['sampling'],
                    params['realistic_params'],
                    use_cash_flow=result.get('use_cash_flow', False)
                )

elif params['df'] is not None and not params['run_backtest']:
    if params['mode'] == 'single':
        st.info("请在左侧设置参数后点击「开始回测」按钮")
    else:
        st.info("请在左侧设置参数后点击「开始概率分析」按钮")
