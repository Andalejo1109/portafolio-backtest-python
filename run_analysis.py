#!/usr/bin/env python3
"""Ejecuta el backtest del Portafolio de Andrés Alejandro Rodríguez Lozano: pesos eToro vs SPY + figuras.
Autor: Andrés Alejandro Rodríguez Lozano
"""
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
    CURRENT_WEIGHTS,
    LIVE_WEIGHTS_RAW,
    BENCHMARK,
    INITIAL,
    download_prices,
    to_month_end,
    load_risk_free_monthly,
    backtest_portfolio,
    series_metrics,
    drawdown_series,
    rolling_cagr,
    efficient_frontier,
    metrics_to_frame,
)

AUTHOR = "Andrés Alejandro Rodríguez Lozano"
PORTFOLIO_NAME = f"Portafolio de {AUTHOR}"

plt.rcParams.update({
    "svg.fonttype": "none",
    "path.simplify": True,
    "path.simplify_threshold": 0.1,
    "figure.dpi": 100,
    "savefig.dpi": 100,
    "font.size": 9,
})


def save_fig(fig, name: str) -> None:
    figs = ROOT / "figures"
    figs.mkdir(exist_ok=True)
    fig.savefig(figs / f"{name}.png", dpi=100, bbox_inches="tight")
    fig.savefig(figs / f"{name}.svg", format="svg", bbox_inches="tight")
    plt.close(fig)
    sz = (figs / f"{name}.svg").stat().st_size / 1024
    print(f"  figures/{name}.svg  {sz:.1f} KB")


def main() -> None:
    print(f"=== Backtest — {PORTFOLIO_NAME} ===")
    print(f"Autor: {AUTHOR}")
    tickers = sorted(set(list(CURRENT_WEIGHTS) + [BENCHMARK]))
    csv = ROOT / "data" / "precios_ajustados_diarios.csv"
    if csv.exists():
        daily = pd.read_csv(csv, index_col=0, parse_dates=True)
        print("Precios desde cache:", csv)
    else:
        daily = download_prices(tickers)
    monthly = to_month_end(daily).loc[: "2026-09-30"]
    monthly.to_csv(ROOT / "data" / "precios_mensuales.csv", float_format="%.4f")
    rets = monthly.pct_change()
    rets.loc["2016-01-31":"2026-09-30"].to_csv(
        ROOT / "data" / "retornos_mensuales.csv", float_format="%.6f"
    )
    rf_path = ROOT / "data" / "rf_mensual.csv"
    if rf_path.exists():
        rf = pd.read_csv(rf_path, index_col=0, parse_dates=True).squeeze()
    else:
        rf = load_risk_free_monthly()

    bt = backtest_portfolio(
        monthly, CURRENT_WEIGHTS, start="2016-01-31", end="2026-09-30", rebalance="A"
    )
    spy = backtest_portfolio(
        monthly, {BENCHMARK: 1.0}, start="2016-01-31", end="2026-09-30", rebalance="N"
    )
    m_p = series_metrics(bt["value"], spy["value"], rf, label="Portafolio")
    m_s = series_metrics(spy["value"], None, rf, label="SPY")

    dfm = metrics_to_frame([m_p, m_s])
    dfm.to_csv(ROOT / "results" / "metricas.csv")
    print(dfm.to_string())

    ann_p = (1 + bt["return"]).groupby(bt.index.year).prod() - 1
    ann_s = (1 + spy["return"]).groupby(spy.index.year).prod() - 1
    pd.DataFrame({"Portafolio": ann_p, "SPY": ann_s, "Activo": ann_p - ann_s}).to_csv(
        ROOT / "results" / "retornos_anuales.csv"
    )

    cols = list(CURRENT_WEIGHTS)
    corr = rets.loc["2016-01-31":"2026-09-30", cols].corr()
    corr.to_csv(ROOT / "results" / "correlacion.csv")

    rows = []
    px = monthly.loc["2015-12-31":"2026-09-30"]
    for t, w in CURRENT_WEIGHTS.items():
        s = px[t].dropna()
        r = s.pct_change().loc["2016-01-31":].dropna()
        years = len(r) / 12
        v0 = s.loc[: "2015-12-31"].iloc[-1]
        vT = s.loc["2016-01-31":"2026-09-30"].iloc[-1]
        rows.append({
            "ticker": t, "peso": w,
            "cagr": (vT / v0) ** (1 / years) - 1,
            "vol": float(r.std(ddof=1) * np.sqrt(12)),
        })
    adf = pd.DataFrame(rows)
    adf.to_csv(ROOT / "results" / "activos_riesgo_retorno.csv", index=False)

    fr, special = efficient_frontier(
        rets.loc["2016-01-31":"2026-09-30", cols].dropna(),
        n_portfolios=1500, max_weight=0.5,
    )
    opt = {
        "max_sharpe": {t: float(w) for t, w in zip(cols, special["max_sharpe"])},
        "min_vol": {t: float(w) for t, w in zip(cols, special["min_vol"])},
        "max_sharpe_stats": special["max_sharpe_stats"],
        "min_vol_stats": special["min_vol_stats"],
    }
    (ROOT / "results" / "optimizacion.json").write_text(
        json.dumps(opt, indent=2, default=float)
    )

    summary = {
        "author": AUTHOR,
        "portfolio_name": PORTFOLIO_NAME,
        "as_of_weights": "2026-10-05T16:45:09Z",
        "source": "eToro get-my-portfolio-summary (read-only)",
        "current_weights": CURRENT_WEIGHTS,
        "current_values_usd": LIVE_WEIGHTS_RAW,
        "period": {"start": "2016-01", "end": "2026-09"},
        "rebalance": "annual",
        "benchmark": BENCHMARK,
        "initial_usd": INITIAL,
        "portfolio_metrics": {k: v for k, v in m_p.items() if k != "label"},
        "spy_metrics": {k: v for k, v in m_s.items() if k != "label"},
    }
    (ROOT / "results" / "summary.json").write_text(
        json.dumps(summary, indent=2, default=float)
    )

    print("Generando figuras…")
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(bt.index, bt["value"], label="Portafolio", lw=1.6)
    ax.plot(spy.index, spy["value"], label="SPY", lw=1.6, alpha=0.85)
    ax.set_title(f"Crecimiento US$10.000 — {PORTFOLIO_NAME}\nene-2016 → sep-2026")
    ax.set_ylabel("US$")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    fig.tight_layout()
    save_fig(fig, "01_crecimiento")

    years = ann_p.index.tolist()
    x = np.arange(len(years))
    wbar = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x - wbar / 2, ann_p * 100, wbar, label="Portafolio")
    ax.bar(x + wbar / 2, ann_s * 100, wbar, label="SPY")
    ax.axhline(0, color="k", lw=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(years, rotation=45, ha="right")
    ax.set_ylabel("%")
    ax.set_title("Retornos anuales")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "02_retornos_anuales")

    dd_p = drawdown_series(bt["value"])
    dd_s = drawdown_series(spy["value"])
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.fill_between(dd_p.index, dd_p.values * 100, 0, alpha=0.45, label="Portafolio")
    ax.plot(dd_s.index, dd_s.values * 100, label="SPY", color="C1", lw=1.2)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdowns — portafolio vs SPY")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "03_drawdowns")

    fig, ax = plt.subplots(figsize=(5.5, 4.8))
    sns.heatmap(
        corr, annot=True, fmt=".2f", cmap="RdYlGn", vmin=-1, vmax=1,
        square=True, ax=ax, annot_kws={"size": 8},
    )
    ax.set_title("Correlación mensual")
    fig.tight_layout()
    save_fig(fig, "04_correlacion")

    roll3 = rolling_cagr(bt["value"], 36)
    roll5 = rolling_cagr(bt["value"], 60)
    roll3s = rolling_cagr(spy["value"], 36)
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(roll3.index, roll3 * 100, label="Portafolio 3a", lw=1.4)
    ax.plot(roll3s.index, roll3s * 100, label="SPY 3a", lw=1.4, alpha=0.85)
    ax.plot(roll5.index, roll5 * 100, label="Portafolio 5a", ls="--", lw=1.2)
    ax.set_ylabel("CAGR rodante (%)")
    ax.set_title("Retornos rodantes anualizados")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "05_rolling_returns")

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(adf.vol * 100, adf.cagr * 100, s=adf.peso * 2500, alpha=0.7)
    for _, row in adf.iterrows():
        ax.annotate(
            row.ticker, (row.vol * 100, row.cagr * 100),
            xytext=(6, 4), textcoords="offset points", fontsize=8,
        )
    ax.set_xlabel("Volatilidad anualizada (%)")
    ax.set_ylabel("CAGR (%)")
    ax.set_title("Riesgo–retorno por activo (tamaño = peso eToro)")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "06_activos_riesgo_retorno")

    mu = rets.loc["2016-01-31":"2026-09-30", cols].mean().values * 12
    cov = rets.loc["2016-01-31":"2026-09-30", cols].cov().values * 12
    w_cur = np.array([CURRENT_WEIGHTS[t] for t in cols])
    ret_c = float(w_cur @ mu)
    vol_c = float(np.sqrt(w_cur @ cov @ w_cur))
    fig, ax = plt.subplots(figsize=(7.5, 5))
    sc = ax.scatter(
        fr.vol * 100, fr.ret * 100, c=fr.sharpe, cmap="viridis",
        s=6, alpha=0.35, rasterized=True,
    )
    plt.colorbar(sc, ax=ax, label="Sharpe (aprox.)", fraction=0.046)
    ax.scatter([vol_c * 100], [ret_c * 100], c="red", s=120, marker="*", label="Pesos actuales", zorder=5)
    ax.scatter(
        [special["max_sharpe_stats"]["vol"] * 100],
        [special["max_sharpe_stats"]["ret"] * 100],
        c="orange", s=80, marker="D", label="Máx Sharpe", zorder=5,
    )
    ax.scatter(
        [special["min_vol_stats"]["vol"] * 100],
        [special["min_vol_stats"]["ret"] * 100],
        c="cyan", s=80, marker="s", label="Mín vol", zorder=5,
    )
    ax.set_xlabel("Volatilidad (%)")
    ax.set_ylabel("Retorno esp. (%)")
    ax.set_title("Frontera simulada (long-only, peso ≤ 50%, n=1500)")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "07_frontera_eficiente")

    norm = monthly.loc["2016-01-31":, cols].dropna()
    norm = norm / norm.iloc[0] * 100
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for c in cols:
        ax.plot(norm.index, norm[c], label=c, lw=1.3)
    ax.set_title("Precios normalizados (base 100 en ene-2016)")
    ax.set_ylabel("Índice")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    save_fig(fig, "nb01_precios_norm")

    (ROOT / "figures" / "README.md").write_text(
        "# Figuras\n\n"
        "SVG/PNG generados con matplotlib a partir del backtest real "
        f"(`run_analysis.py` / notebooks).\n\nAutor: {AUTHOR}\n"
    )
    print("Listo.")


if __name__ == "__main__":
    main()
