"""API pública del backtest educativo (reexporta core + métricas)."""
from portfolio_utils_core import *  # noqa: F401,F403
from portfolio_utils_metrics import (  # noqa: F401
    series_metrics,
    drawdown_series,
    rolling_cagr,
    efficient_frontier,
    metrics_to_frame,
)
