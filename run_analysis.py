#!/usr/bin/env python3
"""Ejecuta el backtest completo: validación PDF + portafolio actual + figuras."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from portfolio_utils import (
    CURRENT_WEIGHTS, ORIGINAL_WEIGHTS, BENCHMARK, INITIAL, DATA, FIGS, RESULTS,
    download_prices, to_month_end, monthly_returns, load_risk_free_monthly,
    backtest_portfolio, series_metrics, drawdown_series, rolling_cagr,
    efficient_frontier, metrics_to_frame,
)

sns.set_theme(style="whitegrid", context="talk")
plt.rcParams["figure.figsize"] = (12, 6)
ALL_TICKERS = sorted(set(list(ORIGINAL_WEIGHTS) + list(CURRENT_WEIGHTS) + [BENCHMARK]))

def fmt_pct(x, digits=2):
    if x is None or (isinstance(x, float) and (np.isnan(x))):
        return "—"
    return f"{100*x:.{digits}f}%"

def main():
    print("=== Descargando precios ===")
    daily = download_prices(ALL_TICKERS, start="2015-11-01", end="2026-10-05")
    monthly_all = to_month_end(daily)
    monthly_all = monthly_all.loc[monthly_all.index <= "2026-09-30"]
    monthly = monthly_all.loc[monthly_all.index >= "2016-01-31"]
    monthly.to_csv(DATA / "precios_mensuales.csv")
    rets = monthly_returns(monthly_all).loc["2016-01-31":]
    rets.to_csv(DATA / "retornos_mensuales.csv")
    monthly = monthly_all
    rf = load_risk_free_monthly("2016-01-01", "2026-10-01")
    print("Meses:", len(monthly), monthly.index.min().date(), "→", monthly.index.max().date())

    print("=== Validación PDF ===")
    bt_orig = backtest_portfolio(monthly, ORIGINAL_WEIGHTS, start="2016-01-31", end="2025-05-31", rebalance="A")
    bt_bench_val = backtest_portfolio(monthly, {BENCHMARK: 1.0}, start="2016-01-31", end="2025-05-31", rebalance="N")
    m_val = series_metrics(bt_orig["value"], bt_bench_val["value"], rf, "Portafolio PDF (réplica)")
    m_bval = series_metrics(bt_bench_val["value"], None, rf, "SPY (validación)")
    print("Réplica CAGR:", fmt_pct(m_val["cagr"]), "PDF: 17.60%")

    print("=== Actualizado ===")
    bt_cur = backtest_portfolio(monthly, CURRENT_WEIGHTS, start="2016-01-31", end="2026-09-30", rebalance="A")
    bt_bench = backtest_portfolio(monthly, {BENCHMARK: 1.0}, start="2016-01-31", end="2026-09-30", rebalance="N")
    bt_orig_ext = backtest_portfolio(monthly, ORIGINAL_WEIGHTS, start="2016-01-31", end="2026-09-30", rebalance="A")
    m_cur = series_metrics(bt_cur["value"], bt_bench["value"], rf, "Portafolio actual")
    m_bench = series_metrics(bt_bench["value"], None, rf, "SPY")
    m_orig_ext = series_metrics(bt_orig_ext["value"], bt_bench["value"], rf, "Pesos PDF (periodo extendido)")
    metrics_df = metrics_to_frame([m_val, m_bval, m_cur, m_bench, m_orig_ext])
    metrics_df.to_csv(RESULTS / "metricas.csv")
    print(metrics_df[["cagr", "stdev", "max_drawdown", "sharpe", "sortino", "end_balance"]].to_string())

    growth = pd.DataFrame({"portafolio_actual": bt_cur["value"], "pesos_pdf": bt_orig_ext["value"], "spy": bt_bench["value"]})
    growth.to_csv(RESULTS / "crecimiento.csv")

    # Figuras (PNG)
    fig, ax = plt.subplots()
    ax.plot(bt_cur.index, bt_cur["value"], label="Portafolio actual", lw=2)
    ax.plot(bt_bench.index, bt_bench["value"], label="SPY", lw=2, alpha=0.85)
    ax.plot(bt_orig_ext.index, bt_orig_ext["value"], label="Pesos PDF", lw=1.5, ls="--", alpha=0.7)
    ax.set_title("Crecimiento US$10.000"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGS / "01_crecimiento.png", dpi=120); plt.close()

    def annual_rets(values):
        r = values.pct_change().dropna()
        return (1 + r).groupby(r.index.year).prod() - 1
    a_cur, a_spy = annual_rets(bt_cur["value"]), annual_rets(bt_bench["value"])
    years = sorted(set(a_cur.index) | set(a_spy.index))
    fig, ax = plt.subplots(); x = np.arange(len(years)); w = 0.38
    ax.bar(x - w/2, [a_cur.get(y, np.nan) * 100 for y in years], w, label="Portafolio")
    ax.bar(x + w/2, [a_spy.get(y, np.nan) * 100 for y in years], w, label="SPY")
    ax.axhline(0, color="k", lw=0.8); ax.set_xticks(x); ax.set_xticklabels(years, rotation=45)
    ax.legend(); fig.tight_layout(); fig.savefig(FIGS / "02_retornos_anuales.png", dpi=120); plt.close()
    pd.DataFrame({"portafolio": a_cur, "spy": a_spy}).to_csv(RESULTS / "retornos_anuales.csv")

    dd_p, dd_b = drawdown_series(bt_cur["value"]), drawdown_series(bt_bench["value"])
    fig, ax = plt.subplots()
    ax.fill_between(dd_p.index, dd_p.values * 100, 0, alpha=0.5, label="Portafolio")
    ax.plot(dd_b.index, dd_b.values * 100, label="SPY", color="C1")
    ax.legend(); fig.tight_layout(); fig.savefig(FIGS / "03_drawdowns.png", dpi=120); plt.close()

    cur_tickers = list(CURRENT_WEIGHTS.keys())
    corr = rets[cur_tickers].corr(); corr.to_csv(RESULTS / "correlacion.csv")
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdYlGn", vmin=-1, vmax=1, ax=ax, square=True)
    fig.tight_layout(); fig.savefig(FIGS / "04_correlacion.png", dpi=120); plt.close()

    roll3 = rolling_cagr(bt_cur["value"], 36); roll5 = rolling_cagr(bt_cur["value"], 60)
    roll3b = rolling_cagr(bt_bench["value"], 36)
    fig, ax = plt.subplots()
    ax.plot(roll3.index, roll3 * 100, label="Portafolio 3a"); ax.plot(roll3b.index, roll3b * 100, label="SPY 3a")
    ax.plot(roll5.index, roll5 * 100, label="Portafolio 5a", ls="--"); ax.legend()
    fig.tight_layout(); fig.savefig(FIGS / "05_rolling_returns.png", dpi=120); plt.close()

    asset_stats = []
    for t in cur_tickers:
        s = monthly[t].dropna(); s = s.loc[(s.index >= "2016-01-31") & (s.index <= "2026-09-30")]
        r = s.pct_change().dropna(); years = len(r) / 12
        cagr = (s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1
        vol = r.std(ddof=1) * np.sqrt(12)
        asset_stats.append({"ticker": t, "cagr": cagr, "vol": vol, "weight": CURRENT_WEIGHTS[t]})
    adf = pd.DataFrame(asset_stats); adf.to_csv(RESULTS / "activos_riesgo_retorno.csv", index=False)
    fig, ax = plt.subplots()
    ax.scatter(adf["vol"] * 100, adf["cagr"] * 100, s=adf["weight"] * 2000, alpha=0.7)
    for _, row in adf.iterrows():
        ax.annotate(row["ticker"], (row["vol"] * 100, row["cagr"] * 100), textcoords="offset points", xytext=(6, 4))
    fig.tight_layout(); fig.savefig(FIGS / "06_activos_riesgo_retorno.png", dpi=120); plt.close()

    fr, special = efficient_frontier(rets[cur_tickers].dropna(), n_portfolios=8000, max_weight=0.5)
    fig, ax = plt.subplots()
    ax.scatter(fr["vol"] * 100, fr["ret"] * 100, c=fr["sharpe"], cmap="viridis", s=8, alpha=0.4)
    mu = rets[cur_tickers].mean().values * 12; cov = rets[cur_tickers].cov().values * 12
    w_cur = np.array([CURRENT_WEIGHTS[t] for t in cur_tickers])
    ret_c, vol_c = float(w_cur @ mu), float(np.sqrt(w_cur @ cov @ w_cur))
    ax.scatter([vol_c * 100], [ret_c * 100], c="red", s=120, marker="*", label="Actual", zorder=5)
    ax.scatter([special["max_sharpe_stats"]["vol"] * 100], [special["max_sharpe_stats"]["ret"] * 100], c="orange", s=100, marker="D", label="Máx Sharpe", zorder=5)
    ax.scatter([special["min_vol_stats"]["vol"] * 100], [special["min_vol_stats"]["ret"] * 100], c="cyan", s=100, marker="s", label="Mín vol", zorder=5)
    ax.legend(); fig.tight_layout(); fig.savefig(FIGS / "07_frontera_eficiente.png", dpi=120); plt.close()

    ms, mv = special["max_sharpe"], special["min_vol"]
    opt = {"tickers": list(cur_tickers),
           "current_weights": {t: float(CURRENT_WEIGHTS[t]) for t in cur_tickers},
           "max_sharpe_weights": {t: float(w) for t, w in zip(cur_tickers, ms)},
           "min_vol_weights": {t: float(w) for t, w in zip(cur_tickers, mv)},
           "max_sharpe_stats": {k: float(v) for k, v in special["max_sharpe_stats"].items()},
           "min_vol_stats": {k: float(v) for k, v in special["min_vol_stats"].items()},
           "current_stats": {"ret": ret_c, "vol": vol_c, "sharpe": ret_c / vol_c}}
    with open(RESULTS / "optimizacion.json", "w") as f:
        json.dump(opt, f, indent=2)

    summary = {"as_of_weights": "2026-10-05T16:45:09Z", "source": "eToro get-my-portfolio-summary",
               "current_weights": {k: round(v, 4) for k, v in CURRENT_WEIGHTS.items()},
               "period_updated": "2016-01 → 2026-09", "period_validation": "2016-01 → 2025-05",
               "rebalance": "annual", "benchmark": "SPY", "initial_usd": INITIAL,
               "validation_vs_pdf": {"pdf_cagr": 0.1760, "replica_cagr": m_val["cagr"],
                 "pdf_maxdd": -0.2559, "replica_maxdd": m_val["max_drawdown"],
                 "pdf_sharpe": 0.96, "replica_sharpe": m_val["sharpe"],
                 "pdf_end": 46016, "replica_end": m_val["end_balance"],
                 "pdf_stdev": 0.1631, "replica_stdev": m_val["stdev"]},
               "updated_portfolio": {k: m_cur[k] for k in ["cagr","stdev","max_drawdown","sharpe","sortino","beta","alpha","best_year","worst_year","end_balance","upside_capture","downside_capture","tracking_error","information_ratio","corr_bench"] if k in m_cur},
               "updated_spy": {k: m_bench[k] for k in ["cagr","stdev","max_drawdown","sharpe","sortino","best_year","worst_year","end_balance"] if k in m_bench}}
    with open(RESULTS / "summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=float)
    print("=== Listo ===", FIGS, RESULTS)
    return summary

if __name__ == "__main__":
    main()
