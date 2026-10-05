"""
Utilidades de backtest de portafolio (estilo Portfolio Visualizer).
Educativo — no constituye asesoría de inversión.
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIGS = ROOT / "figures"
RESULTS = ROOT / "results"
for _d in (DATA, FIGS, RESULTS):
    _d.mkdir(parents=True, exist_ok=True)

ORIGINAL_WEIGHTS = {
    "SPYG": 0.42,
    "BRK-B": 0.27,
    "SMH": 0.15,
    "VTI": 0.11,
    "SPY": 0.05,
}

LIVE_WEIGHTS_RAW = {
    "SPYG": 14970.29,
    "SMH": 10676.04,
    "BRK-B": 10008.96,
    "IEMG": 9887.05,
    "VTI": 3520.96,
}
_live_total = sum(LIVE_WEIGHTS_RAW.values())
CURRENT_WEIGHTS = {k: v / _live_total for k, v in LIVE_WEIGHTS_RAW.items()}

BENCHMARK = "SPY"
INITIAL = 10_000.0


def normalize_ticker(t: str) -> str:
    return t.replace(".", "-")


def download_prices(
    tickers: Iterable[str],
    start: str = "2015-11-01",
    end: str = "2026-10-05",
) -> pd.DataFrame:
    tickers = [normalize_ticker(t) for t in tickers]
    uniq = sorted(set(tickers))
    raw = yf.download(
        uniq, start=start, end=end, auto_adjust=True, progress=False, threads=True
    )
    if isinstance(raw.columns, pd.MultiIndex):
        px = raw["Close"].copy()
    else:
        px = raw[["Close"]].copy()
        px.columns = uniq
    px = px.dropna(how="all").sort_index()
    px.to_csv(DATA / "precios_ajustados_diarios.csv")
    return px


def to_month_end(prices: pd.DataFrame) -> pd.DataFrame:
    return prices.resample("ME").last().dropna(how="all")


def monthly_returns(month_prices: pd.DataFrame) -> pd.DataFrame:
    return month_prices.pct_change()


def load_risk_free_monthly(
    start: str = "2016-01-01",
    end: str = "2026-10-01",
) -> pd.Series:
    try:
        irx = yf.download("^IRX", start=start, end=end, auto_adjust=True, progress=False)
        if isinstance(irx.columns, pd.MultiIndex):
            s = irx["Close"].iloc[:, 0]
        else:
            s = irx["Close"]
        s = s.resample("ME").last().dropna()
        rf = (s / 100.0) / 12.0
        rf.name = "rf"
        rf.to_csv(DATA / "rf_mensual.csv")
        return rf
    except Exception as e:
        print(f"Advertencia: no se pudo descargar ^IRX ({e}); rf=0")
        return pd.Series(dtype=float, name="rf")


def backtest_portfolio(
    month_prices: pd.DataFrame,
    weights: Dict[str, float],
    start: Optional[str] = None,
    end: Optional[str] = None,
    initial: float = INITIAL,
    rebalance: str = "A",
) -> pd.DataFrame:
    """
    Backtest por retornos mensuales (estilo Portfolio Visualizer).

    - Precios mensuales deben incluir el mes ANTERIOR al inicio (p. ej. dic-2015)
      para que el primer retorno del periodo (ene-2016) esté disponible.
    - Rebalanceo 'A': al cierre de cada año calendario (tras el retorno de diciembre).
    - Rebalanceo 'M': cada mes. 'N': buy & hold sin rebalanceo.
    """
    w0 = {normalize_ticker(k): float(v) for k, v in weights.items()}
    cols = list(w0.keys())
    s = sum(w0.values())
    w0 = {k: v / s for k, v in w0.items()}

    px = month_prices[cols].dropna().sort_index()
    rets_all = px.pct_change()

    r = rets_all.copy()
    if start:
        r = r.loc[r.index >= pd.Timestamp(start)]
    if end:
        r = r.loc[r.index <= pd.Timestamp(end)]
    r = r.dropna(how="any")
    if r.empty:
        raise ValueError("Sin retornos tras el filtro")

    w = np.array([w0[c] for c in cols], dtype=float)
    values = []
    port_rets = []
    value = float(initial)
    dates = []

    for i, dt in enumerate(r.index):
        rw = r.loc[dt, cols].values.astype(float)
        pr = float(np.dot(w, rw))
        value = value * (1.0 + pr)
        port_rets.append(pr)
        values.append(value)
        dates.append(dt)

        w = w * (1.0 + rw)
        w = w / w.sum()

        do_reb = False
        if rebalance == "M":
            do_reb = True
        elif rebalance == "A":
            if dt.month == 12:
                do_reb = True
            elif i + 1 < len(r.index) and r.index[i + 1].year != dt.year:
                do_reb = True
        if do_reb:
            w = np.array([w0[c] for c in cols], dtype=float)

    out = pd.DataFrame({"value": values, "return": port_rets}, index=pd.DatetimeIndex(dates, name="date"))
    return out
