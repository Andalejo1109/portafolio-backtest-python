"""Métricas, drawdowns, rolling y frontera (parte 2)."""
from __future__ import annotations

from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

from portfolio_utils_core import INITIAL

def series_metrics(
    values: pd.Series,
    bench_values: Optional[pd.Series] = None,
    rf_monthly: Optional[pd.Series] = None,
    label: str = "Portafolio",
) -> Dict[str, float]:
    values = values.dropna()
    n = len(values)
    if n < 2:
        return {}
    first_ret = values.iloc[0] / INITIAL - 1.0
    rets = pd.concat([pd.Series([first_ret], index=[values.index[0]]), values.pct_change().iloc[1:]]).dropna()
    n = len(rets)
    if rf_monthly is not None and len(rf_monthly):
        rf = rf_monthly.reindex(rets.index).ffill().fillna(0.0)
    else:
        rf = pd.Series(0.0, index=rets.index)
    years = n / 12.0
    cagr = (values.iloc[-1] / INITIAL) ** (1 / years) - 1
    vol = float(rets.std(ddof=1) * np.sqrt(12))
    excess = rets - rf
    sharpe = float((excess.mean() * 12) / (rets.std(ddof=1) * np.sqrt(12))) if rets.std(ddof=1) > 0 else np.nan
    neg = excess[excess < 0]
    down_std = float(np.sqrt((neg ** 2).mean()) * np.sqrt(12)) if len(neg) else np.nan
    sortino = float((excess.mean() * 12) / down_std) if down_std and down_std > 0 else np.nan
    path = pd.concat([pd.Series([INITIAL], index=[values.index[0] - pd.offsets.MonthEnd(1)]), values])
    max_dd = float((path / path.cummax() - 1.0).min())
    yearly = (1 + rets).groupby(rets.index.year).prod() - 1
    out = {
        "label": label, "start_balance": float(INITIAL), "end_balance": float(values.iloc[-1]),
        "months": int(n), "cagr": float(cagr), "stdev": vol, "best_year": float(yearly.max()),
        "worst_year": float(yearly.min()), "max_drawdown": max_dd, "sharpe": sharpe, "sortino": sortino,
        "positive_months": int((rets > 0).sum()), "positive_months_pct": float((rets > 0).mean()),
        "arith_mean_m": float(rets.mean()), "arith_mean_a": float(rets.mean() * 12),
        "geom_mean_m": float((1 + cagr) ** (1 / 12) - 1), "skew": float(rets.skew()),
        "kurtosis_excess": float(rets.kurtosis()),
        "calmar": float(cagr / abs(max_dd)) if max_dd < 0 else np.nan, "_returns": rets,
    }
    if bench_values is not None:
        b = bench_values.reindex(values.index).dropna()
        br_first = b.iloc[0] / INITIAL - 1.0
        br = pd.concat([pd.Series([br_first], index=[b.index[0]]), b.pct_change().iloc[1:]]).dropna()
        pr = out["_returns"]
        idx = pr.index.intersection(br.index)
        pr, br = pr.loc[idx], br.loc[idx]
        if len(pr) > 2 and br.std(ddof=1) > 0:
            cov = np.cov(pr, br, ddof=1)
            beta = float(cov[0, 1] / cov[1, 1])
            rf_a = rf.reindex(idx).fillna(0.0)
            alpha_m = (pr - rf_a) - beta * (br - rf_a)
            alpha_a = float((1 + alpha_m.mean()) ** 12 - 1)
            corr = float(pr.corr(br))
            te = float((pr - br).std(ddof=1) * np.sqrt(12))
            b_cagr = (b.iloc[-1] / INITIAL) ** (12 / len(br)) - 1
            active_cagr = float(cagr - b_cagr)
            ir = float(active_cagr / te) if te > 0 else np.nan
            up, down = br > 0, br < 0
            up_cap = float(pr[up].mean() / br[up].mean()) if up.any() and br[up].mean() != 0 else np.nan
            down_cap = float(pr[down].mean() / br[down].mean()) if down.any() and br[down].mean() != 0 else np.nan
            out.update({"beta": beta, "alpha": alpha_a, "corr_bench": corr, "r2": corr ** 2,
                        "tracking_error": te, "information_ratio": ir,
                        "upside_capture": up_cap * 100 if up_cap == up_cap else np.nan,
                        "downside_capture": down_cap * 100 if down_cap == down_cap else np.nan,
                        "active_return": active_cagr})
    out.pop("_returns", None)
    return out

def drawdown_series(values: pd.Series, initial: float = INITIAL) -> pd.Series:
    path = pd.concat([pd.Series([initial], index=[values.index[0] - pd.offsets.MonthEnd(1)]), values])
    return path / path.cummax() - 1.0

def rolling_cagr(values: pd.Series, window_months: int = 36) -> pd.Series:
    arr = values.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)
    for i in range(window_months - 1, len(arr)):
        a, b = arr[i - window_months + 1], arr[i]
        if a > 0:
            out[i] = (b / a) ** (12 / (window_months - 1)) - 1
    return pd.Series(out, index=values.index, name=f"roll_{window_months}m")

def efficient_frontier(month_rets: pd.DataFrame, n_portfolios: int = 5000, max_weight: float = 0.50, seed: int = 42):
    rng = np.random.default_rng(seed)
    cols = list(month_rets.columns)
    k = len(cols)
    mu = month_rets.mean().values * 12
    cov = month_rets.cov().values * 12
    rows, weights_list = [], []
    for _ in range(n_portfolios * 3):
        if len(rows) >= n_portfolios:
            break
        w = rng.random(k); w /= w.sum()
        if (w > max_weight + 1e-9).any():
            continue
        ret = float(w @ mu); vol = float(np.sqrt(w @ cov @ w))
        rows.append({"ret": ret, "vol": vol, "sharpe": ret / vol if vol > 0 else np.nan})
        weights_list.append(w)
    df = pd.DataFrame(rows); W = np.array(weights_list)
    i_ms, i_mv = int(df["sharpe"].idxmax()), int(df["vol"].idxmin())
    return df, {"max_sharpe": W[i_ms], "min_vol": W[i_mv], "tickers": np.array(cols),
                "max_sharpe_stats": df.loc[i_ms].to_dict(), "min_vol_stats": df.loc[i_mv].to_dict()}

def metrics_to_frame(metrics_list):
    return pd.DataFrame(metrics_list).set_index("label")
