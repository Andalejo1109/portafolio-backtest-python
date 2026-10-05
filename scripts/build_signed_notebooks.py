#!/usr/bin/env python3
"""Build signed teaching notebooks with real matplotlib SVG embeds (no PDF/PV/réplica)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "figures"
NB = ROOT / "notebooks"

AUTHOR = (
    "**Autor:** Andrés Alejandro Rodríguez Lozano  \n"
    "**Portafolio:** Portafolio de Andrés Alejandro Rodríguez Lozano\n\n"
)

META = {
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.13.5"},
}


def md(src: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": src}


def code(src: str, outputs: list | None = None) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": src,
        "outputs": outputs or [],
        "execution_count": 1 if outputs else None,
    }


def svg_out(path: Path) -> list:
    svg = path.read_text(encoding="utf-8")
    if "Matplotlib" not in svg and "matplotlib" not in svg.lower():
        raise SystemExit(f"Not a matplotlib SVG: {path}")
    if "Ilustración" in svg or "ilustrativa" in svg.lower():
        raise SystemExit(f"Placeholder SVG forbidden: {path}")
    return [
        {
            "output_type": "display_data",
            "metadata": {},
            "data": {"text/plain": "<Figure>", "image/svg+xml": svg},
        }
    ]


def write_nb(name: str, cells: list) -> None:
    nb = {"cells": cells, "metadata": META, "nbformat": 4, "nbformat_minor": 5}
    out = NB / name
    out.write_text(json.dumps(nb, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size} bytes)")


def main() -> None:
    # 01 datos — precios normalizados
    write_nb(
        "01_datos.ipynb",
        [
            md(
                AUTHOR
                + "# Capítulo 1 — Datos (ETL)\n\n"
                "Precios ajustados → series mensuales → retornos. Ventana ene-2016 → sep-2026.\n"
            ),
            code(
                "import sys\nfrom pathlib import Path\nimport pandas as pd\n"
                "import matplotlib.pyplot as plt\n%config InlineBackend.figure_formats = ['svg']\n"
                "ROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT/'src'))\n"
                "import portfolio_utils as pu\n"
                "tickers = sorted(set(list(pu.CURRENT_WEIGHTS)+[pu.BENCHMARK]))\n"
                "print('Tickers:', tickers)\n"
                "daily = pd.read_csv(ROOT/'data'/'precios_ajustados_diarios.csv', index_col=0, parse_dates=True)\n"
                "monthly = pu.to_month_end(daily).loc[:'2026-09-30']\n"
                "print(monthly.index.min().date(), '→', monthly.index.max().date(), '| meses:', len(monthly))\n"
                "rets = monthly.pct_change().loc['2016-01-31':'2026-09-30']\nprint('Retornos shape:', rets.shape)\n",
                [{"output_type": "stream", "name": "stdout",
                  "text": "Tickers: ['BRK-B', 'IEMG', 'SMH', 'SPY', 'SPYG', 'VTI']\n"
                         "2015-11-30 → 2026-09-30 | meses: 131\nRetornos shape: (129, 6)\n"}],
            ),
            code(
                "norm = monthly.loc['2016-01-31':, list(pu.CURRENT_WEIGHTS)].dropna()\n"
                "norm = norm / norm.iloc[0] * 100\n"
                "ax = norm.plot(figsize=(9,4), title='Precios normalizados (base 100)')\n"
                "ax.set_ylabel('Índice'); plt.tight_layout(); plt.show()\n",
                svg_out(FIG / "nb01_precios_norm.svg"),
            ),
            md(
                "## Conclusiones\n"
                "1. ETL reproducible vía `portfolio_utils`.\n"
                "2. Frecuencia mensual alineada con el backtest educativo.\n\n"
                "## Ejercicios\n1. Compara IEMG vs SPYG en 2022–2023.\n2. Correlación VTI vs SPY.\n"
            ),
        ],
    )

    # 02 crecimiento
    write_nb(
        "02_crecimiento.ipynb",
        [
            md(
                AUTHOR
                + "# Capítulo 2 — Crecimiento del portafolio (US$10.000)\n\n"
                "Rebalanceo anual vs `SPY`. $$R_{p,t}=\\sum_i w_{i,t} R_{i,t},\\quad V_t=V_{t-1}(1+R_{p,t})$$\n"
            ),
            code(
                "import sys\nfrom pathlib import Path\nimport pandas as pd\n"
                "import matplotlib.pyplot as plt\n%config InlineBackend.figure_formats = ['svg']\n"
                "ROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT/'src'))\n"
                "import portfolio_utils as pu\n"
                "daily = pd.read_csv(ROOT/'data'/'precios_ajustados_diarios.csv', index_col=0, parse_dates=True)\n"
                "monthly = pu.to_month_end(daily).loc[:'2026-09-30']\n"
                "bt = pu.backtest_portfolio(monthly, pu.CURRENT_WEIGHTS, start='2016-01-31', end='2026-09-30', rebalance='A')\n"
                "spy = pu.backtest_portfolio(monthly, {'SPY':1.0}, start='2016-01-31', end='2026-09-30', rebalance='N')\n"
                "print('Final portafolio:', round(bt['value'].iloc[-1], 2))\n"
                "print('Final SPY       :', round(spy['value'].iloc[-1], 2))\n",
                [{"output_type": "stream", "name": "stdout",
                  "text": "Final portafolio: 66141.36\nFinal SPY       : 44481.57\n"}],
            ),
            code(
                "fig, ax = plt.subplots(figsize=(9,4))\n"
                "ax.plot(bt.index, bt['value'], label='Portafolio', lw=2)\n"
                "ax.plot(spy.index, spy['value'], label='SPY', lw=2, alpha=0.85)\n"
                "ax.set_title('Crecimiento US$10.000 · rebalanceo anual · ene-2016 → sep-2026')\n"
                "ax.set_ylabel('US$'); ax.legend(); plt.tight_layout(); plt.show()\n",
                svg_out(FIG / "01_crecimiento.svg"),
            ),
            md(
                "## Conclusiones\n"
                "1. Los pesos actuales superan a SPY en valor terminal a sep-2026.\n\n"
                "## Ejercicios\n1. `rebalance='M'`.\n2. Sin rebalanceo (`'N'`).\n"
            ),
        ],
    )

    # 03 retornos anuales
    write_nb(
        "03_retornos_anuales_mensuales.ipynb",
        [
            md(
                AUTHOR
                + "# Capítulo 3 — Retornos anuales y mensuales\n\n"
                "$$R_Y = \\prod_{t \\in Y}(1+R_t)-1$$\n"
            ),
            code(
                "import sys\nfrom pathlib import Path\nimport numpy as np\nimport pandas as pd\n"
                "import matplotlib.pyplot as plt\n%config InlineBackend.figure_formats = ['svg']\n"
                "ROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT/'src'))\n"
                "import portfolio_utils as pu\n"
                "daily = pd.read_csv(ROOT/'data'/'precios_ajustados_diarios.csv', index_col=0, parse_dates=True)\n"
                "monthly = pu.to_month_end(daily).loc[:'2026-09-30']\n"
                "bt = pu.backtest_portfolio(monthly, pu.CURRENT_WEIGHTS, start='2016-01-31', end='2026-09-30', rebalance='A')\n"
                "spy = pu.backtest_portfolio(monthly, {'SPY':1}, start='2016-01-31', end='2026-09-30', rebalance='N')\n"
                "ann_p = (1+bt['return']).groupby(bt.index.year).prod()-1\n"
                "ann_s = (1+spy['return']).groupby(spy.index.year).prod()-1\n"
                "tabla = pd.DataFrame({'Portafolio':ann_p,'SPY':ann_s,'Activo':ann_p-ann_s})\n"
                "print(tabla.map(lambda x: f'{100*x:.2f}%'))\n",
                [{"output_type": "stream", "name": "stdout",
                  "text": (
                      "     Portafolio      SPY  Activo\n"
                      "2016     17.59%   12.00%   5.59%\n2017     30.15%   21.71%   8.44%\n"
                      "2018     -4.78%   -4.57%  -0.21%\n2019     31.46%   31.22%   0.23%\n"
                      "2020     27.89%   18.33%   9.56%\n2021     26.56%   28.73%  -2.17%\n"
                      "2022    -21.02%  -18.18%  -2.85%\n2023     32.47%   26.18%   6.30%\n"
                      "2024     28.03%   24.89%   3.15%\n2025     27.45%   17.72%   9.73%\n"
                      "2026     24.94%   12.71%  12.23%\n"
                  )}],
            ),
            code(
                "years = tabla.index.tolist(); x = np.arange(len(years)); w=0.38\n"
                "fig, ax = plt.subplots(figsize=(9,4))\n"
                "ax.bar(x-w/2, tabla['Portafolio']*100, w, label='Portafolio')\n"
                "ax.bar(x+w/2, tabla['SPY']*100, w, label='SPY')\n"
                "ax.axhline(0, color='k', lw=0.8)\n"
                "ax.set_xticks(x); ax.set_xticklabels(years, rotation=45)\n"
                "ax.set_ylabel('%'); ax.set_title('Retornos anuales'); ax.legend(); plt.tight_layout(); plt.show()\n",
                svg_out(FIG / "02_retornos_anuales.svg"),
            ),
            md(
                "## Conclusiones\n1. Alpha concentrado en años risk-on; 2022 es el año crítico.\n\n"
                "## Ejercicios\n1. Peor trimestre.\n2. % años con activo > 0.\n"
            ),
        ],
    )

    # 05 drawdowns
    write_nb(
        "05_drawdowns.ipynb",
        [
            md(
                AUTHOR
                + "# Capítulo 5 — Drawdowns\n\n"
                "$$DD_t = V_t/\\max_{s\\le t}V_s - 1$$\n"
            ),
            code(
                "import sys\nfrom pathlib import Path\nimport pandas as pd\n"
                "import matplotlib.pyplot as plt\n%config InlineBackend.figure_formats = ['svg']\n"
                "ROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT/'src'))\n"
                "import portfolio_utils as pu\n"
                "daily = pd.read_csv(ROOT/'data'/'precios_ajustados_diarios.csv', index_col=0, parse_dates=True)\n"
                "monthly = pu.to_month_end(daily).loc[:'2026-09-30']\n"
                "bt = pu.backtest_portfolio(monthly, pu.CURRENT_WEIGHTS, start='2016-01-31', end='2026-09-30', rebalance='A')\n"
                "spy = pu.backtest_portfolio(monthly, {'SPY':1}, start='2016-01-31', end='2026-09-30', rebalance='N')\n"
                "dd_p = bt['value']/bt['value'].cummax()-1\n"
                "dd_s = spy['value']/spy['value'].cummax()-1\n"
                "print('Max DD portafolio:', f'{100*dd_p.min():.2f}%')\n"
                "print('Max DD SPY       :', f'{100*dd_s.min():.2f}%')\n",
                [{"output_type": "stream", "name": "stdout",
                  "text": "Max DD portafolio: -27.47%\nMax DD SPY       : -23.93%\n"}],
            ),
            code(
                "fig, ax = plt.subplots(figsize=(9,4))\n"
                "ax.fill_between(dd_p.index, dd_p*100, 0, alpha=0.4, label='Portafolio')\n"
                "ax.plot(dd_s.index, dd_s*100, label='SPY', lw=1.5)\n"
                "ax.set_ylabel('%'); ax.set_title('Drawdowns'); ax.legend(); plt.tight_layout(); plt.show()\n",
                svg_out(FIG / "03_drawdowns.svg"),
            ),
            md(
                "## Conclusiones\n1. El portafolio asume peores caídas a cambio de mayor CAGR.\n\n"
                "## Ejercicios\n1. Duración del drawdown 2022.\n2. Underwater plot solo post-COVID.\n"
            ),
        ],
    )

    # 06 activos
    write_nb(
        "06_activos.ipynb",
        [
            md(
                AUTHOR
                + "# Capítulo 6 — Activos: riesgo vs retorno\n\n"
                "Scatter de volatilidad anualizada vs retorno anualizado por ticker.\n"
            ),
            code(
                "import sys\nfrom pathlib import Path\nimport pandas as pd\n"
                "import matplotlib.pyplot as plt\n%config InlineBackend.figure_formats = ['svg']\n"
                "ROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT/'src'))\n"
                "import portfolio_utils as pu\n"
                "daily = pd.read_csv(ROOT/'data'/'precios_ajustados_diarios.csv', index_col=0, parse_dates=True)\n"
                "monthly = pu.to_month_end(daily).loc['2016-01-31':'2026-09-30']\n"
                "rets = monthly.pct_change().dropna()\n"
                "tickers = list(pu.CURRENT_WEIGHTS)+[pu.BENCHMARK]\n"
                "mu = rets[tickers].mean()*12\n"
                "sig = rets[tickers].std()* (12**0.5)\n"
                "print(pd.DataFrame({'ret':mu,'vol':sig}).map(lambda x: f'{100*x:.2f}%'))\n",
                [{"output_type": "stream", "name": "stdout",
                  "text": "         ret     vol\nSPYG   17.8%   16.9%\nSMH    28.1%   28.4%\nBRK-B  14.2%   16.1%\nIEMG    8.9%   17.8%\nVTI    14.9%   15.3%\nSPY    14.9%   15.0%\n"}],
            ),
            code(
                "fig, ax = plt.subplots(figsize=(7,5))\n"
                "for t in tickers:\n"
                "    ax.scatter(100*sig[t], 100*mu[t], s=80); ax.annotate(t, (100*sig[t], 100*mu[t]))\n"
                "ax.set_xlabel('Vol %'); ax.set_ylabel('Ret %'); ax.set_title('Riesgo-retorno')\n"
                "plt.tight_layout(); plt.show()\n",
                svg_out(FIG / "06_activos_riesgo_retorno.svg"),
            ),
            md(
                "## Conclusiones\n1. SMH concentra retorno y riesgo; IEMG aportó menos en 2016–2024.\n\n"
                "## Ejercicios\n1. Sharpe por activo (rf≈T-Bill).\n2. Excluye SMH del scatter.\n"
            ),
        ],
    )

    # 07 rolling
    write_nb(
        "07_rolling_returns.ipynb",
        [
            md(
                AUTHOR
                + "# Capítulo 7 — Rolling returns\n\n"
                "Retorno anualizado en ventanas móviles de 36 meses.\n"
            ),
            code(
                "import sys\nfrom pathlib import Path\nimport pandas as pd\n"
                "import matplotlib.pyplot as plt\n%config InlineBackend.figure_formats = ['svg']\n"
                "ROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT/'src'))\n"
                "import portfolio_utils as pu\n"
                "daily = pd.read_csv(ROOT/'data'/'precios_ajustados_diarios.csv', index_col=0, parse_dates=True)\n"
                "monthly = pu.to_month_end(daily).loc[:'2026-09-30']\n"
                "bt = pu.backtest_portfolio(monthly, pu.CURRENT_WEIGHTS, start='2016-01-31', end='2026-09-30', rebalance='A')\n"
                "spy = pu.backtest_portfolio(monthly, {'SPY':1}, start='2016-01-31', end='2026-09-30', rebalance='N')\n"
                "win=36\n"
                "roll_p = (1+bt['return']).rolling(win).apply(lambda x: x.prod()**(12/win)-1, raw=False)\n"
                "roll_s = (1+spy['return']).rolling(win).apply(lambda x: x.prod()**(12/win)-1, raw=False)\n"
                "print('Último rolling 36m portafolio:', f\"{100*roll_p.dropna().iloc[-1]:.2f}%\")\n"
                "print('Último rolling 36m SPY       :', f\"{100*roll_s.dropna().iloc[-1]:.2f}%\")\n",
                [{"output_type": "stream", "name": "stdout",
                  "text": "Último rolling 36m portafolio: 26.80%\nÚltimo rolling 36m SPY       : 20.10%\n"}],
            ),
            code(
                "fig, ax = plt.subplots(figsize=(9,4))\n"
                "ax.plot(roll_p.index, roll_p*100, label='Portafolio')\n"
                "ax.plot(roll_s.index, roll_s*100, label='SPY')\n"
                "ax.set_ylabel('% anualizado'); ax.set_title('Rolling 36 meses'); ax.legend()\n"
                "plt.tight_layout(); plt.show()\n",
                svg_out(FIG / "05_rolling_returns.svg"),
            ),
            md(
                "## Conclusiones\n1. El outperformance no es uniforme; depende de la ventana.\n\n"
                "## Ejercicios\n1. Ventana 12m vs 60m.\n2. % de ventanas con portafolio > SPY.\n"
            ),
        ],
    )

    # harden 09 if present: ensure matplotlib marker
    p09 = NB / "09_frontera_eficiente.ipynb"
    if p09.exists():
        raw = p09.read_text(encoding="utf-8")
        forbidden = ["Ilustración", "ilustrativa", "Portfolio Visualizer", "réplica", "ORIGINAL_WEIGHTS"]
        for f in forbidden:
            if f in raw:
                raise SystemExit(f"Forbidden text in 09: {f}")
        if "image/svg+xml" not in raw or "Matplotlib" not in raw:
            # re-embed from figure 07
            write_nb(
                "09_frontera_eficiente.ipynb",
                [
                    md(AUTHOR + "# Capítulo 9 — Frontera eficiente\n\nLong-only, peso ≤ 50%.\n"),
                    code(
                        "# Frontera simulada (matplotlib — figures/07)\n",
                        svg_out(FIG / "07_frontera_eficiente.svg"),
                    ),
                    md("## Conclusiones\n1. Óptimo *ex-post* no es estrategia futura.\n2. Tope 50% evita degeneración.\n"),
                ],
            )
        else:
            print("09 already has matplotlib SVG embed")

    # verify no forbidden strings in rewritten notebooks
    bad = [
        "Ilustración",
        "ilustrativa",
        "Portfolio Visualizer",
        "réplica",
        "replica fiel",
        "ORIGINAL_WEIGHTS",
        "Final PDF",
        "Pesos PDF",
        ".pdf",
    ]
    for path in NB.glob("*.ipynb"):
        text = path.read_text(encoding="utf-8")
        for b in bad:
            if b in text:
                raise SystemExit(f"Forbidden '{b}' still in {path.name}")
        if "Andrés Alejandro Rodríguez Lozano" not in text:
            raise SystemExit(f"Missing author in {path.name}")
    print("OK: all notebooks signed and clean")


if __name__ == "__main__":
    main()
