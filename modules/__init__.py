"""
红利定投回测工具模块

本模块提供完整的定投回测功能，包括：
- 数据加载与验证
- 投资策略计算
- 费用计算与管理
- 风险分析
- 概率分析
- 图表渲染

主要类:
    CacheManager: 缓存管理器
    TradingCalendar: 交易日历
    DataLoader: 数据加载器
    FeeCalculator: 费用计算器
    FeeParams: 费用参数
    RiskAnalyzer: 风险分析器
    ProbabilityAnalyzer: 概率分析器
    ChartRenderer: 图表渲染器
    ConfigManager: 配置管理器
    SmartStrategyConfig: 智能策略配置
    StrategySignal: 策略信号
    BaseStrategy: 策略基类
    CashFlowAccount: 现金流账户

异常类:
    BacktestError: 回测基础异常
    DataValidationError: 数据验证异常
    ConfigError: 配置异常
    CalculationError: 计算异常
    StrategyError: 策略异常
"""

__version__ = "2.0.0"
__author__ = "Your Name"

from .exceptions import (
    BacktestError,
    DataValidationError,
    ConfigError,
    CalculationError,
    StrategyError
)

from .utils import (
    CacheManager,
    TradingCalendar,
    hash_params,
    hash_dataframe,
    hash_file,
    calculate_total_return,
    calculate_annualized_return,
    calculate_years_between,
    get_date_range_info,
    filter_df_by_date_range
)

from .config import (
    ConfigManager,
    get_config_manager,
    load_custom_presets,
    save_custom_preset,
    delete_custom_preset,
    get_all_presets
)

from .data_loader import (
    DataLoader,
    load_excel_file,
    validate_data,
    get_date_range,
    check_valuation_data
)

from .fee_calculator import (
    FeeCalculator,
    FeeParams,
    calculate_purchase_fee,
    calculate_daily_management_fee,
    calculate_redemption_fee,
    apply_tracking_error
)

from .risk_analyzer import (
    RiskAnalyzer,
    analyze_risk_metrics,
    calculate_max_drawdown,
    calculate_max_pullback,
    calculate_loss_statistics,
    find_recovery_date
)

from .chart_renderer import (
    ChartRenderer,
    create_asset_chart,
    create_price_chart,
    create_return_chart,
    create_return_distribution_chart,
    create_return_timeline_chart,
    create_cumulative_probability_chart,
    create_annualized_distribution_chart,
    create_comparison_chart,
    create_strategy_signal_chart,
    create_amount_distribution_chart,
    create_comparison_probability_chart,
    create_comparison_timeline_chart
)

from .investment import (
    get_investment_dates,
    find_next_trading_day,
    run_backtest_calculation,
    calculate_daily_assets,
    calculate_lump_sum_return,
    run_smart_backtest_calculation,
    calculate_smart_daily_assets,
    run_comparison_backtest
)

from .smart_strategy import (
    SmartStrategyConfig,
    StrategySignal,
    BaseStrategy,
    create_strategy,
    get_investment_amount,
    generate_strategy_signals,
    calculate_smart_investment_amounts
)

from .cash_flow import CashFlowAccount

from .probability_analyzer import (
    ProbabilityAnalyzer,
    get_all_possible_start_dates,
    run_single_backtest,
    run_probability_analysis,
    calculate_probability_statistics,
    run_single_smart_backtest,
    run_smart_probability_analysis,
    run_comparison_probability_analysis,
    calculate_comparison_statistics
)

from .ui_components import render_sidebar, display_results

__all__ = [
    '__version__',
    '__author__',
    'BacktestError',
    'DataValidationError',
    'ConfigError',
    'CalculationError',
    'StrategyError',
    'CacheManager',
    'TradingCalendar',
    'hash_params',
    'hash_dataframe',
    'hash_file',
    'calculate_total_return',
    'calculate_annualized_return',
    'calculate_years_between',
    'get_date_range_info',
    'filter_df_by_date_range',
    'ConfigManager',
    'get_config_manager',
    'load_custom_presets',
    'save_custom_preset',
    'delete_custom_preset',
    'get_all_presets',
    'DataLoader',
    'load_excel_file',
    'validate_data',
    'get_date_range',
    'check_valuation_data',
    'FeeCalculator',
    'FeeParams',
    'calculate_purchase_fee',
    'calculate_daily_management_fee',
    'calculate_redemption_fee',
    'apply_tracking_error',
    'RiskAnalyzer',
    'analyze_risk_metrics',
    'calculate_max_drawdown',
    'calculate_max_pullback',
    'calculate_loss_statistics',
    'find_recovery_date',
    'ChartRenderer',
    'create_asset_chart',
    'create_price_chart',
    'create_return_chart',
    'create_return_distribution_chart',
    'create_return_timeline_chart',
    'create_cumulative_probability_chart',
    'create_annualized_distribution_chart',
    'create_comparison_chart',
    'create_strategy_signal_chart',
    'create_amount_distribution_chart',
    'create_comparison_probability_chart',
    'create_comparison_timeline_chart',
    'get_investment_dates',
    'find_next_trading_day',
    'run_backtest_calculation',
    'calculate_daily_assets',
    'calculate_lump_sum_return',
    'run_smart_backtest_calculation',
    'calculate_smart_daily_assets',
    'run_comparison_backtest',
    'SmartStrategyConfig',
    'StrategySignal',
    'BaseStrategy',
    'create_strategy',
    'get_investment_amount',
    'generate_strategy_signals',
    'calculate_smart_investment_amounts',
    'CashFlowAccount',
    'ProbabilityAnalyzer',
    'get_all_possible_start_dates',
    'run_single_backtest',
    'run_probability_analysis',
    'calculate_probability_statistics',
    'run_single_smart_backtest',
    'run_smart_probability_analysis',
    'run_comparison_probability_analysis',
    'calculate_comparison_statistics',
    'render_sidebar',
    'display_results'
]
