import pandas as pd
import plotly.graph_objects as go
import numpy as np

from .config import CHART_HEIGHT, CHART_MARGIN


def create_asset_chart(daily_assets_df, realistic_params=None):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_assets_df['日期'],
        y=daily_assets_df['累计投入'],
        mode='lines',
        name='累计投入本金',
        line=dict(color='blue', width=2),
        hovertemplate='日期: %{x}<br>累计投入: ¥%{y:,.2f}<extra></extra>'
    ))
    
    if realistic_params:
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['理想持仓市值'],
            mode='lines',
            name='理想持仓市值',
            line=dict(color='green', width=2, dash='dash'),
            hovertemplate='日期: %{x}<br>理想市值: ¥%{y:,.2f}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['实际持仓市值'],
            mode='lines',
            name='实际持仓市值',
            line=dict(color='red', width=2),
            hovertemplate='日期: %{x}<br>实际市值: ¥%{y:,.2f}<extra></extra>'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['理想持仓市值'],
            mode='lines',
            name='持仓总资产',
            line=dict(color='red', width=2),
            hovertemplate='日期: %{x}<br>持仓市值: ¥%{y:,.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        xaxis_title='日期',
        yaxis_title='金额（元）',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=CHART_HEIGHT,
        margin=CHART_MARGIN
    )
    
    return fig


def create_price_chart(daily_assets_df, realistic_params=None):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_assets_df['日期'],
        y=daily_assets_df['收盘价'],
        mode='lines',
        name='指数收盘价',
        line=dict(color='green', width=2),
        hovertemplate='日期: %{x}<br>收盘价: ¥%{y:,.2f}<extra></extra>'
    ))
    
    if realistic_params:
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['理想持仓均价'],
            mode='lines',
            name='理想持仓均价',
            line=dict(color='orange', width=2, dash='dash'),
            hovertemplate='日期: %{x}<br>理想均价: ¥%{y:,.2f}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['实际持仓均价'],
            mode='lines',
            name='实际持仓均价',
            line=dict(color='purple', width=2),
            hovertemplate='日期: %{x}<br>实际均价: ¥%{y:,.2f}<extra></extra>'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['理想持仓均价'],
            mode='lines',
            name='持仓均价',
            line=dict(color='orange', width=2, dash='dash'),
            hovertemplate='日期: %{x}<br>持仓均价: ¥%{y:,.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        xaxis_title='日期',
        yaxis_title='价格（元）',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=CHART_HEIGHT,
        margin=CHART_MARGIN
    )
    
    return fig


def create_return_chart(daily_assets_df, realistic_params=None, recovery_date=None):
    daily_assets_df = daily_assets_df.copy()
    daily_assets_df['理想累计收益率'] = (daily_assets_df['理想持仓市值'] - daily_assets_df['累计投入']) / daily_assets_df['累计投入'] * 100
    daily_assets_df['理想累计收益率'] = daily_assets_df['理想累计收益率'].replace([np.inf, -np.inf], 0)
    
    if realistic_params:
        daily_assets_df['实际累计收益率'] = (daily_assets_df['实际持仓市值'] - daily_assets_df['累计投入']) / daily_assets_df['累计投入'] * 100
        daily_assets_df['实际累计收益率'] = daily_assets_df['实际累计收益率'].replace([np.inf, -np.inf], 0)
        return_col = '实际累计收益率'
    else:
        return_col = '理想累计收益率'
    
    fig = go.Figure()
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
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
        fig.add_vrect(
            x0=loss_start_date, x1=loss_end_date,
            fillcolor="red", opacity=0.1,
            layer="below", line_width=0
        )
    
    if realistic_params:
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['理想累计收益率'],
            mode='lines',
            name='理想累计收益率',
            line=dict(color='green', width=2, dash='dash'),
            hovertemplate='日期: %{x}<br>理想收益率: %{y:.2f}%<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['实际累计收益率'],
            mode='lines',
            name='实际累计收益率',
            line=dict(color='red', width=2),
            hovertemplate='日期: %{x}<br>实际收益率: %{y:.2f}%<extra></extra>'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=daily_assets_df['日期'],
            y=daily_assets_df['理想累计收益率'],
            mode='lines',
            name='累计收益率',
            line=dict(color='red', width=2),
            hovertemplate='日期: %{x}<br>累计收益率: %{y:.2f}%<extra></extra>'
        ))
    
    if recovery_date is not None:
        fig.add_shape(
            type="line",
            x0=recovery_date, x1=recovery_date,
            y0=0, y1=1,
            yref="paper",
            line=dict(color="blue", width=2, dash="dot"),
        )
        fig.add_annotation(
            x=recovery_date,
            y=1,
            yref="paper",
            text="回本点",
            showarrow=False,
            xanchor="left",
            yanchor="bottom"
        )
    
    fig.update_layout(
        xaxis_title='日期',
        yaxis_title='累计收益率（%）',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=CHART_HEIGHT,
        margin=CHART_MARGIN
    )
    
    return fig


def create_return_distribution_chart(stats, realistic_params=None, use_cash_flow=False):
    fig = go.Figure()
    
    if use_cash_flow and 'total_return_with_cash' in stats['results_df'].columns:
        return_col = 'total_return_with_cash'
    elif realistic_params:
        return_col = 'real_total_return'
    else:
        return_col = 'ideal_total_return'
    
    df = stats['results_df']
    
    returns = df[return_col].values
    
    fig.add_trace(go.Histogram(
        x=returns,
        nbinsx=30,
        name='收益分布',
        marker_color='steelblue',
        opacity=0.75,
        hovertemplate='收益率区间: %{x}<br>频次: %{y}<extra></extra>'
    ))
    
    fig.add_vline(x=0, line_dash="dash", line_color="red", opacity=0.7)
    
    fig.add_vline(x=stats['avg_return'], line_dash="dot", line_color="green", opacity=0.7,
                  annotation_text=f"平均: {stats['avg_return']:.1f}%",
                  annotation_position="top right")
    
    fig.add_vline(x=stats['median_return'], line_dash="dot", line_color="orange", opacity=0.7,
                  annotation_text=f"中位数: {stats['median_return']:.1f}%",
                  annotation_position="top left")
    
    fig.update_layout(
        xaxis_title='累计收益率（%）',
        yaxis_title='频次',
        hovermode='x',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        bargap=0.05
    )
    
    return fig


def create_return_timeline_chart(results, realistic_params=None, use_cash_flow=False):
    fig = go.Figure()
    
    df = pd.DataFrame(results)
    
    if use_cash_flow and 'total_return_with_cash' in df.columns:
        return_col = 'total_return_with_cash'
    elif realistic_params:
        return_col = 'real_total_return'
    else:
        return_col = 'ideal_total_return'
    
    annualized_col = 'real_annualized' if realistic_params else 'ideal_annualized'
    
    colors = ['green' if r > 0 else 'red' for r in df[return_col]]
    
    fig.add_trace(go.Bar(
        x=df['start_date'],
        y=df[return_col],
        name='累计收益率',
        marker_color=colors,
        opacity=0.7,
        hovertemplate='起始日期: %{x}<br>累计收益率: %{y:.2f}%<extra></extra>'
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        xaxis_title='起始日期',
        yaxis_title='累计收益率（%）',
        hovermode='x',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        showlegend=False
    )
    
    return fig


def create_cumulative_probability_chart(stats, realistic_params=None, use_cash_flow=False):
    fig = go.Figure()
    
    df = stats['results_df']
    
    if use_cash_flow and 'total_return_with_cash' in df.columns:
        return_col = 'total_return_with_cash'
    elif realistic_params:
        return_col = 'real_total_return'
    else:
        return_col = 'ideal_total_return'
    
    returns = sorted(df[return_col].values)
    total = len(returns)
    
    thresholds = list(range(-50, 51, 5))
    actual_thresholds = [t for t in thresholds if t >= min(returns) - 5 and t <= max(returns) + 5]
    
    probs = []
    for t in actual_thresholds:
        prob = sum(1 for r in returns if r >= t) / total * 100
        probs.append(prob)
    
    fig.add_trace(go.Scatter(
        x=actual_thresholds,
        y=probs,
        mode='lines+markers',
        name='累计概率',
        line=dict(color='steelblue', width=2),
        marker=dict(size=6),
        hovertemplate='收益率≥%{x}%<br>概率: %{y:.1f}%<extra></extra>'
    ))
    
    fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        xaxis_title='收益率阈值（%）',
        yaxis_title='达到该收益率的概率（%）',
        hovermode='x',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN
    )
    
    return fig


def create_annualized_distribution_chart(stats, realistic_params=None, use_cash_flow=False):
    fig = go.Figure()
    
    if use_cash_flow and 'annualized_with_cash' in stats['results_df'].columns:
        annualized_col = 'annualized_with_cash'
    elif realistic_params:
        annualized_col = 'real_annualized'
    else:
        annualized_col = 'ideal_annualized'
    
    df = stats['results_df']
    
    annualized_returns = df[annualized_col].values
    
    fig.add_trace(go.Histogram(
        x=annualized_returns,
        nbinsx=30,
        name='年化收益分布',
        marker_color='teal',
        opacity=0.75,
        hovertemplate='年化收益率区间: %{x}<br>频次: %{y}<extra></extra>'
    ))
    
    fig.add_vline(x=0, line_dash="dash", line_color="red", opacity=0.7)
    
    fig.add_vline(x=stats['avg_annualized'], line_dash="dot", line_color="green", opacity=0.7,
                  annotation_text=f"平均: {stats['avg_annualized']:.1f}%",
                  annotation_position="top right")
    
    fig.add_vline(x=stats['median_annualized'], line_dash="dot", line_color="orange", opacity=0.7,
                  annotation_text=f"中位数: {stats['median_annualized']:.1f}%",
                  annotation_position="top left")
    
    fig.update_layout(
        xaxis_title='年化收益率（%）',
        yaxis_title='频次',
        hovermode='x',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        bargap=0.05
    )
    
    return fig


def create_comparison_chart(fixed_df, smart_df, realistic_params=None):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=fixed_df['日期'],
        y=fixed_df['累计投入'],
        mode='lines',
        name='固定定投-累计投入',
        line=dict(color='blue', width=2, dash='dash'),
        hovertemplate='日期: %{x}<br>固定投入: ¥%{y:,.2f}<extra></extra>'
    ))
    
    fig.add_trace(go.Scatter(
        x=smart_df['日期'],
        y=smart_df['累计投入'],
        mode='lines',
        name='智能定投-累计投入',
        line=dict(color='blue', width=2),
        hovertemplate='日期: %{x}<br>智能投入: ¥%{y:,.2f}<extra></extra>'
    ))
    
    smart_asset_col = '总资产' if '总资产' in smart_df.columns else ('实际持仓市值' if realistic_params else '理想持仓市值')
    
    if realistic_params:
        fig.add_trace(go.Scatter(
            x=fixed_df['日期'],
            y=fixed_df['实际持仓市值'],
            mode='lines',
            name='固定定投-总资产',
            line=dict(color='green', width=2, dash='dash'),
            hovertemplate='日期: %{x}<br>固定总资产: ¥%{y:,.2f}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=smart_df['日期'],
            y=smart_df[smart_asset_col],
            mode='lines',
            name='智能定投-总资产',
            line=dict(color='red', width=2),
            hovertemplate='日期: %{x}<br>智能总资产: ¥%{y:,.2f}<extra></extra>'
        ))
    else:
        fig.add_trace(go.Scatter(
            x=fixed_df['日期'],
            y=fixed_df['理想持仓市值'],
            mode='lines',
            name='固定定投-总资产',
            line=dict(color='green', width=2, dash='dash'),
            hovertemplate='日期: %{x}<br>固定总资产: ¥%{y:,.2f}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=smart_df['日期'],
            y=smart_df[smart_asset_col],
            mode='lines',
            name='智能定投-总资产',
            line=dict(color='red', width=2),
            hovertemplate='日期: %{x}<br>智能总资产: ¥%{y:,.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        xaxis_title='日期',
        yaxis_title='金额（元）',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=CHART_HEIGHT,
        margin=CHART_MARGIN
    )
    
    return fig


def create_strategy_signal_chart(results_df):
    fig = go.Figure()
    
    signal_colors = {
        'extreme_low': 'darkgreen',
        'low': 'green',
        'normal': 'gray',
        'high': 'orange',
        'extreme_high': 'red'
    }
    
    colors = [signal_colors.get(s, 'gray') for s in results_df['信号']]
    
    fig.add_trace(go.Bar(
        x=results_df['日期'],
        y=results_df['倍数'],
        name='定投倍数',
        marker_color=colors,
        opacity=0.8,
        hovertemplate='日期: %{x}<br>倍数: %{y:.2f}x<extra></extra>'
    ))
    
    fig.add_hline(y=1.0, line_dash="dash", line_color="black", opacity=0.5)
    
    fig.update_layout(
        xaxis_title='日期',
        yaxis_title='定投倍数',
        hovermode='x',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        showlegend=False
    )
    
    return fig


def create_amount_distribution_chart(results_df, base_amount):
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=results_df['投入金额'],
        nbinsx=20,
        name='金额分布',
        marker_color='steelblue',
        opacity=0.75,
        hovertemplate='金额区间: ¥%{x:,.0f}<br>频次: %{y}<extra></extra>'
    ))
    
    fig.add_vline(x=base_amount, line_dash="dash", line_color="red", opacity=0.7,
                  annotation_text=f"基础金额: ¥{base_amount:,.0f}",
                  annotation_position="top right")
    
    avg_amount = results_df['投入金额'].mean()
    fig.add_vline(x=avg_amount, line_dash="dot", line_color="green", opacity=0.7,
                  annotation_text=f"平均金额: ¥{avg_amount:,.0f}",
                  annotation_position="top left")
    
    fig.update_layout(
        xaxis_title='定投金额（元）',
        yaxis_title='频次',
        hovermode='x',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        bargap=0.05
    )
    
    return fig


def create_comparison_probability_chart(comparison_stats, realistic_params=None, use_cash_flow=True):
    import numpy as np
    
    fig = go.Figure()
    
    if realistic_params:
        return_col = 'real_total_return'
    else:
        return_col = 'ideal_total_return'
    
    fixed_df = comparison_stats['fixed_results_df']
    smart_df = comparison_stats['smart_results_df']
    
    fixed_returns = fixed_df[return_col].values
    
    if use_cash_flow and 'total_return_with_cash' in smart_df.columns:
        smart_returns = smart_df['total_return_with_cash'].values
    else:
        smart_returns = smart_df[return_col].values
    
    all_returns = np.concatenate([fixed_returns, smart_returns])
    min_return = np.floor(all_returns.min() / 5) * 5
    max_return = np.ceil(all_returns.max() / 5) * 5
    
    bin_width = 5
    bin_edges = np.arange(min_return, max_return + bin_width, bin_width)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bar_width = bin_width * 0.4
    
    fixed_counts, _ = np.histogram(fixed_returns, bins=bin_edges)
    smart_counts, _ = np.histogram(smart_returns, bins=bin_edges)
    
    fig.add_trace(go.Bar(
        x=bin_centers - bar_width/2,
        y=fixed_counts,
        width=bar_width,
        name='固定定投',
        marker_color='#3498db',
        opacity=0.8,
        hovertemplate='固定定投<br>收益区间: %{customdata:.0f}%~%{customdata:.0f}+5%<br>频次: %{y}<extra></extra>',
        customdata=bin_edges[:-1]
    ))
    
    fig.add_trace(go.Bar(
        x=bin_centers + bar_width/2,
        y=smart_counts,
        width=bar_width,
        name='智能定投',
        marker_color='#e74c3c',
        opacity=0.8,
        hovertemplate='智能定投<br>收益区间: %{customdata:.0f}%~%{customdata:.0f}+5%<br>频次: %{y}<extra></extra>',
        customdata=bin_edges[:-1]
    ))
    
    fig.add_vline(x=comparison_stats['fixed_avg_return'], line_dash="dash", line_color="#2980b9", opacity=0.8,
                  annotation_text=f"固定平均: {comparison_stats['fixed_avg_return']:.1f}%",
                  annotation_position="top right")
    
    fig.add_vline(x=comparison_stats['smart_avg_return'], line_dash="dash", line_color="#c0392b", opacity=0.8,
                  annotation_text=f"智能平均: {comparison_stats['smart_avg_return']:.1f}%",
                  annotation_position="top left")
    
    fig.update_layout(
        xaxis_title='累计收益率（%）',
        yaxis_title='频次',
        hovermode='x unified',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        bargap=0.05,
        barmode='group'
    )
    
    return fig


def create_comparison_timeline_chart(comparison_stats, realistic_params=None, use_cash_flow=True):
    fig = go.Figure()
    
    fixed_df = comparison_stats['fixed_results_df'].sort_values('start_date').reset_index(drop=True)
    smart_df = comparison_stats['smart_results_df'].sort_values('start_date').reset_index(drop=True)
    
    if realistic_params:
        return_col = 'real_total_return'
    else:
        return_col = 'ideal_total_return'
    
    fig.add_trace(go.Scatter(
        x=fixed_df['start_date'],
        y=fixed_df[return_col],
        mode='lines+markers',
        name='固定定投',
        line=dict(color='#3498db', width=1.5),
        marker=dict(size=4),
        hovertemplate='日期: %{x}<br>固定定投收益: %{y:.2f}%<extra></extra>'
    ))
    
    if use_cash_flow and 'total_return_with_cash' in smart_df.columns:
        smart_return_col = 'total_return_with_cash'
    else:
        smart_return_col = return_col
    
    fig.add_trace(go.Scatter(
        x=smart_df['start_date'],
        y=smart_df[smart_return_col],
        mode='lines+markers',
        name='智能定投',
        line=dict(color='#e74c3c', width=1.5),
        marker=dict(size=4),
        hovertemplate='日期: %{x}<br>智能定投收益: %{y:.2f}%<extra></extra>'
    ))
    
    return_diff = comparison_stats['return_diff']
    smart_win = [1 if d > 0 else 0 for d in return_diff]
    
    fig.add_trace(go.Bar(
        x=fixed_df['start_date'],
        y=return_diff,
        name='收益差异',
        marker_color=['#27ae60' if d > 0 else '#e74c3c' for d in return_diff],
        opacity=0.3,
        hovertemplate='日期: %{x}<br>收益差异: %{y:.2f}%<extra></extra>'
    ))
    
    fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    
    fig.update_layout(
        xaxis_title='起始日期',
        yaxis_title='累计收益率（%）',
        hovermode='x unified',
        height=CHART_HEIGHT,
        margin=CHART_MARGIN,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig
