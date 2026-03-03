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
