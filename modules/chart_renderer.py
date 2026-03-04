import pandas as pd
import plotly.graph_objects as go
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from .config import CHART_HEIGHT, CHART_MARGIN
from .utils import CacheManager, hash_dataframe


class ChartRenderer:
    _COLOR_SCHEME = {
        'primary': '#3498db',
        'secondary': '#e74c3c',
        'success': '#27ae60',
        'warning': '#f39c12',
        'info': '#9b59b6',
        'dark': '#2c3e50',
        'gray': '#7f8c8d',
        'blue': '#2980b9',
        'green': '#16a085',
        'red': '#c0392b',
        'orange': '#e67e22',
        'purple': '#8e44ad',
        'teal': '#1abc9c',
        'steelblue': '#4682b4'
    }
    
    _FONT_SIZE = {
        'title': 16,
        'axis': 12,
        'legend': 11,
        'annotation': 11
    }
    
    _LEGEND_CONFIG = dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=_FONT_SIZE['legend'])
    )
    
    _MAX_POINTS_BEFORE_SAMPLING = 1000
    
    _chart_cache = CacheManager(default_ttl=300)
    
    def __init__(self, height: int = 400, margin: Optional[Dict[str, int]] = None):
        self.height = height
        self.margin = margin if margin is not None else CHART_MARGIN
    
    def _get_common_layout(self, title: str, x_title: str, y_title: str) -> Dict[str, Any]:
        return dict(
            title=dict(text=title, font=dict(size=self._FONT_SIZE['title'])),
            xaxis=dict(
                title=dict(text=x_title, font=dict(size=self._FONT_SIZE['axis'])),
                tickfont=dict(size=10)
            ),
            yaxis=dict(
                title=dict(text=y_title, font=dict(size=self._FONT_SIZE['axis'])),
                tickfont=dict(size=10)
            ),
            hovermode='x unified',
            height=self.height,
            margin=self.margin
        )
    
    def _apply_common_style(self, fig: go.Figure) -> go.Figure:
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='rgba(128,128,128,0.4)',
            linecolor='rgba(128,128,128,0.6)',
            tickcolor='rgba(128,128,128,0.6)'
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128,128,128,0.2)',
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='rgba(128,128,128,0.4)',
            linecolor='rgba(128,128,128,0.6)',
            tickcolor='rgba(128,128,128,0.6)'
        )
        fig.update_layout(
            font=dict(color='rgba(50,50,50,0.9)')
        )
        return fig
    
    def _sample_data_if_needed(self, x: pd.Series, y: pd.Series) -> Tuple[pd.Series, pd.Series]:
        if len(x) <= self._MAX_POINTS_BEFORE_SAMPLING:
            return x, y
        
        step = len(x) // self._MAX_POINTS_BEFORE_SAMPLING
        indices = np.arange(0, len(x), step)
        return x.iloc[indices], y.iloc[indices]
    
    def _create_scatter_trace(
        self,
        x: pd.Series,
        y: pd.Series,
        name: str,
        color: str,
        mode: str = 'lines',
        dash: Optional[str] = None,
        hover_template: Optional[str] = None,
        use_scattergl: bool = False
    ) -> go.Scatter:
        x_sampled, y_sampled = self._sample_data_if_needed(x, y)
        
        line_config = dict(color=color, width=2)
        if dash:
            line_config['dash'] = dash
        
        scatter_class = go.Scattergl if use_scattergl or len(x) > self._MAX_POINTS_BEFORE_SAMPLING else go.Scatter
        
        return scatter_class(
            x=x_sampled,
            y=y_sampled,
            mode=mode,
            name=name,
            line=line_config,
            hovertemplate=hover_template if hover_template else f'{name}: %{{y:.2f}}<extra></extra>'
        )
    
    def _get_cache_key(self, *args, **kwargs) -> str:
        key_parts = []
        for arg in args:
            if isinstance(arg, pd.DataFrame):
                key_parts.append(hash_dataframe(arg))
            elif isinstance(arg, dict):
                key_parts.append(str(sorted(arg.items())))
            else:
                key_parts.append(str(arg))
        
        for k, v in sorted(kwargs.items()):
            if isinstance(v, pd.DataFrame):
                key_parts.append(f"{k}:{hash_dataframe(v)}")
            else:
                key_parts.append(f"{k}:{v}")
        
        return "|".join(key_parts)
    
    def _get_cached_chart(self, cache_key: str) -> Optional[go.Figure]:
        return self._chart_cache.get(cache_key)
    
    def _cache_chart(self, cache_key: str, fig: go.Figure) -> None:
        self._chart_cache.set(cache_key, fig)
    
    def create_asset_chart(self, daily_assets_df: pd.DataFrame, realistic_params: Optional[Dict] = None) -> go.Figure:
        cache_key = self._get_cache_key('asset_chart', daily_assets_df, realistic_params=realistic_params)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
        fig = go.Figure()
        
        fig.add_trace(self._create_scatter_trace(
            daily_assets_df['日期'],
            daily_assets_df['累计投入'],
            '累计投入本金',
            self._COLOR_SCHEME['blue'],
            hover_template='日期: %{x}<br>累计投入: ¥%{y:,.2f}<extra></extra>'
        ))
        
        if realistic_params:
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['理想持仓市值'],
                '理想持仓市值',
                self._COLOR_SCHEME['success'],
                dash='dash',
                hover_template='日期: %{x}<br>理想市值: ¥%{y:,.2f}<extra></extra>'
            ))
            
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['实际持仓市值'],
                '实际持仓市值',
                self._COLOR_SCHEME['secondary'],
                hover_template='日期: %{x}<br>实际市值: ¥%{y:,.2f}<extra></extra>'
            ))
        else:
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['理想持仓市值'],
                '持仓总资产',
                self._COLOR_SCHEME['secondary'],
                hover_template='日期: %{x}<br>持仓市值: ¥%{y:,.2f}<extra></extra>'
            ))
        
        fig.update_layout(**self._get_common_layout('', '日期', '金额（元）'))
        fig.update_layout(legend=self._LEGEND_CONFIG)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_price_chart(self, daily_assets_df: pd.DataFrame, realistic_params: Optional[Dict] = None) -> go.Figure:
        cache_key = self._get_cache_key('price_chart', daily_assets_df, realistic_params=realistic_params)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
        fig = go.Figure()
        
        fig.add_trace(self._create_scatter_trace(
            daily_assets_df['日期'],
            daily_assets_df['收盘价'],
            '指数收盘价',
            self._COLOR_SCHEME['success'],
            hover_template='日期: %{x}<br>收盘价: ¥%{y:,.2f}<extra></extra>'
        ))
        
        if realistic_params:
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['理想持仓均价'],
                '理想持仓均价',
                self._COLOR_SCHEME['orange'],
                dash='dash',
                hover_template='日期: %{x}<br>理想均价: ¥%{y:,.2f}<extra></extra>'
            ))
            
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['实际持仓均价'],
                '实际持仓均价',
                self._COLOR_SCHEME['purple'],
                hover_template='日期: %{x}<br>实际均价: ¥%{y:,.2f}<extra></extra>'
            ))
        else:
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['理想持仓均价'],
                '持仓均价',
                self._COLOR_SCHEME['orange'],
                dash='dash',
                hover_template='日期: %{x}<br>持仓均价: ¥%{y:,.2f}<extra></extra>'
            ))
        
        fig.update_layout(**self._get_common_layout('', '日期', '价格（元）'))
        fig.update_layout(legend=self._LEGEND_CONFIG)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_return_chart(
        self,
        daily_assets_df: pd.DataFrame,
        realistic_params: Optional[Dict] = None,
        recovery_date: Optional[Any] = None
    ) -> go.Figure:
        cache_key = self._get_cache_key('return_chart', daily_assets_df, realistic_params=realistic_params, recovery_date=recovery_date)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
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
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['理想累计收益率'],
                '理想累计收益率',
                self._COLOR_SCHEME['success'],
                dash='dash',
                hover_template='日期: %{x}<br>理想收益率: %{y:.2f}%<extra></extra>'
            ))
            
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['实际累计收益率'],
                '实际累计收益率',
                self._COLOR_SCHEME['secondary'],
                hover_template='日期: %{x}<br>实际收益率: %{y:.2f}%<extra></extra>'
            ))
        else:
            fig.add_trace(self._create_scatter_trace(
                daily_assets_df['日期'],
                daily_assets_df['理想累计收益率'],
                '累计收益率',
                self._COLOR_SCHEME['secondary'],
                hover_template='日期: %{x}<br>累计收益率: %{y:.2f}%<extra></extra>'
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
                yanchor="bottom",
                font=dict(size=self._FONT_SIZE['annotation'])
            )
        
        fig.update_layout(**self._get_common_layout('', '日期', '累计收益率（%）'))
        fig.update_layout(legend=self._LEGEND_CONFIG)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_return_distribution_chart(
        self,
        stats: Dict[str, Any],
        realistic_params: Optional[Dict] = None,
        use_cash_flow: bool = False
    ) -> go.Figure:
        cache_key = self._get_cache_key('return_dist_chart', stats['results_df'], realistic_params=realistic_params, use_cash_flow=use_cash_flow)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
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
            marker_color=self._COLOR_SCHEME['steelblue'],
            opacity=0.75,
            hovertemplate='收益率区间: %{x}<br>频次: %{y}<extra></extra>'
        ))
        
        fig.add_vline(x=0, line_dash="dash", line_color="red", opacity=0.7)
        
        fig.add_vline(x=stats['avg_return'], line_dash="dot", line_color="#2ecc71", opacity=0.9,
                      annotation_text=f"平均: {stats['avg_return']:.1f}%",
                      annotation_position="top right",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color='#2ecc71'))
        
        fig.add_vline(x=stats['median_return'], line_dash="dot", line_color="#e67e22", opacity=0.9,
                      annotation_text=f"中位数: {stats['median_return']:.1f}%",
                      annotation_position="top left",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color='#e67e22'))
        
        fig.update_layout(**self._get_common_layout('', '累计收益率（%）', '频次'))
        fig.update_layout(hovermode='x', bargap=0.05)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_return_timeline_chart(
        self,
        results: List[Dict],
        realistic_params: Optional[Dict] = None,
        use_cash_flow: bool = False
    ) -> go.Figure:
        df = pd.DataFrame(results)
        cache_key = self._get_cache_key('return_timeline_chart', df, realistic_params=realistic_params, use_cash_flow=use_cash_flow)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
        fig = go.Figure()
        
        if use_cash_flow and 'total_return_with_cash' in df.columns:
            return_col = 'total_return_with_cash'
        elif realistic_params:
            return_col = 'real_total_return'
        else:
            return_col = 'ideal_total_return'
        
        colors = [self._COLOR_SCHEME['success'] if r > 0 else self._COLOR_SCHEME['secondary'] for r in df[return_col]]
        
        fig.add_trace(go.Bar(
            x=df['start_date'],
            y=df[return_col],
            name='累计收益率',
            marker_color=colors,
            opacity=0.7,
            hovertemplate='起始日期: %{x}<br>累计收益率: %{y:.2f}%<extra></extra>'
        ))
        
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(**self._get_common_layout('', '起始日期', '累计收益率（%）'))
        fig.update_layout(hovermode='x', showlegend=False)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_cumulative_probability_chart(
        self,
        stats: Dict[str, Any],
        realistic_params: Optional[Dict] = None,
        use_cash_flow: bool = False
    ) -> go.Figure:
        cache_key = self._get_cache_key('cum_prob_chart', stats['results_df'], realistic_params=realistic_params, use_cash_flow=use_cash_flow)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
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
            line=dict(color=self._COLOR_SCHEME['steelblue'], width=2),
            marker=dict(size=6),
            hovertemplate='收益率≥%{x}%<br>概率: %{y:.1f}%<extra></extra>'
        ))
        
        fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(**self._get_common_layout('', '收益率阈值（%）', '达到该收益率的概率（%）'))
        fig.update_layout(hovermode='x')
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_annualized_distribution_chart(
        self,
        stats: Dict[str, Any],
        realistic_params: Optional[Dict] = None,
        use_cash_flow: bool = False
    ) -> go.Figure:
        cache_key = self._get_cache_key('annualized_dist_chart', stats['results_df'], realistic_params=realistic_params, use_cash_flow=use_cash_flow)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
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
            marker_color=self._COLOR_SCHEME['teal'],
            opacity=0.75,
            hovertemplate='年化收益率区间: %{x}<br>频次: %{y}<extra></extra>'
        ))
        
        fig.add_vline(x=0, line_dash="dash", line_color="red", opacity=0.7)
        
        fig.add_vline(x=stats['avg_annualized'], line_dash="dot", line_color="#2ecc71", opacity=0.9,
                      annotation_text=f"平均: {stats['avg_annualized']:.1f}%",
                      annotation_position="top right",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color='#2ecc71'))
        
        fig.add_vline(x=stats['median_annualized'], line_dash="dot", line_color="#e67e22", opacity=0.9,
                      annotation_text=f"中位数: {stats['median_annualized']:.1f}%",
                      annotation_position="top left",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color='#e67e22'))
        
        fig.update_layout(**self._get_common_layout('', '年化收益率（%）', '频次'))
        fig.update_layout(hovermode='x', bargap=0.05)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_comparison_chart(
        self,
        fixed_df: pd.DataFrame,
        smart_df: pd.DataFrame,
        realistic_params: Optional[Dict] = None
    ) -> go.Figure:
        cache_key = self._get_cache_key('comparison_chart', fixed_df, smart_df, realistic_params=realistic_params)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
        fig = go.Figure()
        
        fig.add_trace(self._create_scatter_trace(
            fixed_df['日期'],
            fixed_df['累计投入'],
            '固定定投-累计投入',
            self._COLOR_SCHEME['blue'],
            dash='dash',
            hover_template='日期: %{x}<br>固定投入: ¥%{y:,.2f}<extra></extra>'
        ))
        
        fig.add_trace(self._create_scatter_trace(
            smart_df['日期'],
            smart_df['累计投入'],
            '智能定投-累计投入',
            self._COLOR_SCHEME['blue'],
            hover_template='日期: %{x}<br>智能投入: ¥%{y:,.2f}<extra></extra>'
        ))
        
        smart_asset_col = '总资产' if '总资产' in smart_df.columns else ('实际持仓市值' if realistic_params else '理想持仓市值')
        
        if realistic_params:
            fig.add_trace(self._create_scatter_trace(
                fixed_df['日期'],
                fixed_df['实际持仓市值'],
                '固定定投-总资产',
                self._COLOR_SCHEME['success'],
                dash='dash',
                hover_template='日期: %{x}<br>固定总资产: ¥%{y:,.2f}<extra></extra>'
            ))
            
            fig.add_trace(self._create_scatter_trace(
                smart_df['日期'],
                smart_df[smart_asset_col],
                '智能定投-总资产',
                self._COLOR_SCHEME['secondary'],
                hover_template='日期: %{x}<br>智能总资产: ¥%{y:,.2f}<extra></extra>'
            ))
        else:
            fig.add_trace(self._create_scatter_trace(
                fixed_df['日期'],
                fixed_df['理想持仓市值'],
                '固定定投-总资产',
                self._COLOR_SCHEME['success'],
                dash='dash',
                hover_template='日期: %{x}<br>固定总资产: ¥%{y:,.2f}<extra></extra>'
            ))
            
            fig.add_trace(self._create_scatter_trace(
                smart_df['日期'],
                smart_df[smart_asset_col],
                '智能定投-总资产',
                self._COLOR_SCHEME['secondary'],
                hover_template='日期: %{x}<br>智能总资产: ¥%{y:,.2f}<extra></extra>'
            ))
        
        fig.update_layout(**self._get_common_layout('', '日期', '金额（元）'))
        fig.update_layout(legend=self._LEGEND_CONFIG)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_strategy_signal_chart(self, results_df: pd.DataFrame) -> go.Figure:
        cache_key = self._get_cache_key('strategy_signal_chart', results_df)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
        fig = go.Figure()
        
        signal_colors = {
            'extreme_low': self._COLOR_SCHEME['dark'],
            'low': self._COLOR_SCHEME['success'],
            'normal': self._COLOR_SCHEME['gray'],
            'high': self._COLOR_SCHEME['orange'],
            'extreme_high': self._COLOR_SCHEME['secondary']
        }
        
        colors = [signal_colors.get(s, self._COLOR_SCHEME['gray']) for s in results_df['信号']]
        
        fig.add_trace(go.Bar(
            x=results_df['日期'],
            y=results_df['倍数'],
            name='定投倍数',
            marker_color=colors,
            opacity=0.8,
            hovertemplate='日期: %{x}<br>倍数: %{y:.2f}x<extra></extra>'
        ))
        
        fig.add_hline(y=1.0, line_dash="dash", line_color="black", opacity=0.5)
        
        fig.update_layout(**self._get_common_layout('', '日期', '定投倍数'))
        fig.update_layout(hovermode='x', showlegend=False)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_amount_distribution_chart(self, results_df: pd.DataFrame, base_amount: float) -> go.Figure:
        cache_key = self._get_cache_key('amount_dist_chart', results_df, base_amount=base_amount)
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=results_df['投入金额'],
            nbinsx=20,
            name='金额分布',
            marker_color=self._COLOR_SCHEME['steelblue'],
            opacity=0.75,
            hovertemplate='金额区间: ¥%{x:,.0f}<br>频次: %{y}<extra></extra>'
        ))
        
        fig.add_vline(x=base_amount, line_dash="dash", line_color="#e74c3c", opacity=0.8,
                      annotation_text=f"基础金额: ¥{base_amount:,.0f}",
                      annotation_position="top right",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color='#e74c3c'))
        
        avg_amount = results_df['投入金额'].mean()
        fig.add_vline(x=avg_amount, line_dash="dot", line_color="#2ecc71", opacity=0.8,
                      annotation_text=f"平均金额: ¥{avg_amount:,.0f}",
                      annotation_position="top left",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color='#2ecc71'))
        
        fig.update_layout(**self._get_common_layout('', '定投金额（元）', '频次'))
        fig.update_layout(hovermode='x', bargap=0.05)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_comparison_probability_chart(
        self,
        comparison_stats: Dict[str, Any],
        realistic_params: Optional[Dict] = None,
        use_cash_flow: bool = True
    ) -> go.Figure:
        cache_key = self._get_cache_key(
            'comparison_prob_chart',
            comparison_stats['fixed_results_df'],
            comparison_stats['smart_results_df'],
            realistic_params=realistic_params,
            use_cash_flow=use_cash_flow
        )
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
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
            marker_color=self._COLOR_SCHEME['primary'],
            opacity=0.8,
            hovertemplate='固定定投<br>收益区间: %{customdata:.0f}%~%{customdata:.0f}+5%<br>频次: %{y}<extra></extra>',
            customdata=bin_edges[:-1]
        ))
        
        fig.add_trace(go.Bar(
            x=bin_centers + bar_width/2,
            y=smart_counts,
            width=bar_width,
            name='智能定投',
            marker_color=self._COLOR_SCHEME['secondary'],
            opacity=0.8,
            hovertemplate='智能定投<br>收益区间: %{customdata:.0f}%~%{customdata:.0f}+5%<br>频次: %{y}<extra></extra>',
            customdata=bin_edges[:-1]
        ))
        
        fig.add_vline(x=comparison_stats['fixed_avg_return'], line_dash="dash", line_color=self._COLOR_SCHEME['blue'], opacity=0.8,
                      annotation_text=f"固定平均: {comparison_stats['fixed_avg_return']:.1f}%",
                      annotation_position="top right",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color=self._COLOR_SCHEME['blue']))
        
        fig.add_vline(x=comparison_stats['smart_avg_return'], line_dash="dash", line_color=self._COLOR_SCHEME['secondary'], opacity=0.8,
                      annotation_text=f"智能平均: {comparison_stats['smart_avg_return']:.1f}%",
                      annotation_position="top left",
                      annotation_font=dict(size=self._FONT_SIZE['annotation'], color=self._COLOR_SCHEME['secondary']))
        
        fig.update_layout(**self._get_common_layout('', '累计收益率（%）', '频次'))
        fig.update_layout(hovermode='x unified', bargap=0.05, barmode='group')
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    def create_comparison_timeline_chart(
        self,
        comparison_stats: Dict[str, Any],
        realistic_params: Optional[Dict] = None,
        use_cash_flow: bool = True
    ) -> go.Figure:
        cache_key = self._get_cache_key(
            'comparison_timeline_chart',
            comparison_stats['fixed_results_df'],
            comparison_stats['smart_results_df'],
            realistic_params=realistic_params,
            use_cash_flow=use_cash_flow
        )
        cached = self._get_cached_chart(cache_key)
        if cached is not None:
            return cached
        
        fig = go.Figure()
        
        fixed_df = comparison_stats['fixed_results_df'].sort_values('start_date').reset_index(drop=True)
        smart_df = comparison_stats['smart_results_df'].sort_values('start_date').reset_index(drop=True)
        
        if realistic_params:
            return_col = 'real_total_return'
        else:
            return_col = 'ideal_total_return'
        
        fig.add_trace(self._create_scatter_trace(
            fixed_df['start_date'],
            fixed_df[return_col],
            '固定定投',
            self._COLOR_SCHEME['primary'],
            mode='lines+markers',
            hover_template='日期: %{x}<br>固定定投收益: %{y:.2f}%<extra></extra>'
        ))
        
        if use_cash_flow and 'total_return_with_cash' in smart_df.columns:
            smart_return_col = 'total_return_with_cash'
        else:
            smart_return_col = return_col
        
        fig.add_trace(self._create_scatter_trace(
            smart_df['start_date'],
            smart_df[smart_return_col],
            '智能定投',
            self._COLOR_SCHEME['secondary'],
            mode='lines+markers',
            hover_template='日期: %{x}<br>智能定投收益: %{y:.2f}%<extra></extra>'
        ))
        
        return_diff = comparison_stats['return_diff']
        
        fig.add_trace(go.Bar(
            x=fixed_df['start_date'],
            y=return_diff,
            name='收益差异',
            marker_color=[self._COLOR_SCHEME['success'] if d > 0 else self._COLOR_SCHEME['secondary'] for d in return_diff],
            opacity=0.3,
            hovertemplate='日期: %{x}<br>收益差异: %{y:.2f}%<extra></extra>'
        ))
        
        fig.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
        
        fig.update_layout(**self._get_common_layout('', '起始日期', '累计收益率（%）'))
        fig.update_layout(legend=self._LEGEND_CONFIG)
        self._apply_common_style(fig)
        
        self._cache_chart(cache_key, fig)
        return fig
    
    @classmethod
    def clear_cache(cls) -> None:
        cls._chart_cache.clear()


_default_renderer = ChartRenderer(height=CHART_HEIGHT, margin=CHART_MARGIN)


def create_asset_chart(daily_assets_df: pd.DataFrame, realistic_params: Optional[Dict] = None) -> go.Figure:
    return _default_renderer.create_asset_chart(daily_assets_df, realistic_params)


def create_price_chart(daily_assets_df: pd.DataFrame, realistic_params: Optional[Dict] = None) -> go.Figure:
    return _default_renderer.create_price_chart(daily_assets_df, realistic_params)


def create_return_chart(
    daily_assets_df: pd.DataFrame,
    realistic_params: Optional[Dict] = None,
    recovery_date: Optional[Any] = None
) -> go.Figure:
    return _default_renderer.create_return_chart(daily_assets_df, realistic_params, recovery_date)


def create_return_distribution_chart(
    stats: Dict[str, Any],
    realistic_params: Optional[Dict] = None,
    use_cash_flow: bool = False
) -> go.Figure:
    return _default_renderer.create_return_distribution_chart(stats, realistic_params, use_cash_flow)


def create_return_timeline_chart(
    results: List[Dict],
    realistic_params: Optional[Dict] = None,
    use_cash_flow: bool = False
) -> go.Figure:
    return _default_renderer.create_return_timeline_chart(results, realistic_params, use_cash_flow)


def create_cumulative_probability_chart(
    stats: Dict[str, Any],
    realistic_params: Optional[Dict] = None,
    use_cash_flow: bool = False
) -> go.Figure:
    return _default_renderer.create_cumulative_probability_chart(stats, realistic_params, use_cash_flow)


def create_annualized_distribution_chart(
    stats: Dict[str, Any],
    realistic_params: Optional[Dict] = None,
    use_cash_flow: bool = False
) -> go.Figure:
    return _default_renderer.create_annualized_distribution_chart(stats, realistic_params, use_cash_flow)


def create_comparison_chart(
    fixed_df: pd.DataFrame,
    smart_df: pd.DataFrame,
    realistic_params: Optional[Dict] = None
) -> go.Figure:
    return _default_renderer.create_comparison_chart(fixed_df, smart_df, realistic_params)


def create_strategy_signal_chart(results_df: pd.DataFrame) -> go.Figure:
    return _default_renderer.create_strategy_signal_chart(results_df)


def create_amount_distribution_chart(results_df: pd.DataFrame, base_amount: float) -> go.Figure:
    return _default_renderer.create_amount_distribution_chart(results_df, base_amount)


def create_comparison_probability_chart(
    comparison_stats: Dict[str, Any],
    realistic_params: Optional[Dict] = None,
    use_cash_flow: bool = True
) -> go.Figure:
    return _default_renderer.create_comparison_probability_chart(comparison_stats, realistic_params, use_cash_flow)


def create_comparison_timeline_chart(
    comparison_stats: Dict[str, Any],
    realistic_params: Optional[Dict] = None,
    use_cash_flow: bool = True
) -> go.Figure:
    return _default_renderer.create_comparison_timeline_chart(comparison_stats, realistic_params, use_cash_flow)
