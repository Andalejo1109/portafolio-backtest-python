# Backtest de portafolio en Python

**Portafolio de Andrés Alejandro Rodríguez Lozano**  
**Autor:** Andrés Alejandro Rodríguez Lozano

Backtest educativo de la asignación de activos actual (snapshot eToro del **5 oct 2026**) frente al S&P 500 (`SPY`), periodo **ene-2016 → sep-2026**. Inspirado en un ejercicio de backtest del año pasado.

> **No es asesoría de inversión.** Material para clase universitaria: juicio previo, ETL, código, métricas y conclusiones.

**Repo:** https://github.com/Andalejo1109/portafolio-backtest-python

---

## Índice de capítulos (notebooks)

| # | Notebook | Contenido |
|---|---|---|
| 0 | [`notebooks/00_introduccion.ipynb`](notebooks/00_introduccion.ipynb) | Juicio previo, tesis, mapa del curso |
| 1 | [`notebooks/01_datos.ipynb`](notebooks/01_datos.ipynb) | ETL con `yfinance`, precios mensuales, RF |
| 2 | [`notebooks/02_crecimiento.ipynb`](notebooks/02_crecimiento.ipynb) | US$10.000, rebalanceo anual, vs SPY |
| 3 | [`notebooks/03_retornos_anuales_mensuales.ipynb`](notebooks/03_retornos_anuales_mensuales.ipynb) | Calendario anual + histograma |
| 4 | [`notebooks/04_metricas.ipynb`](notebooks/04_metricas.ipynb) | CAGR, σ, Max DD, Sharpe, Sortino, β, α, capture, TE, IR |
| 5 | [`notebooks/05_drawdowns.ipynb`](notebooks/05_drawdowns.ipynb) | Underwater chart |
| 6 | [`notebooks/06_activos.ipynb`](notebooks/06_activos.ipynb) | Riesgo–retorno por ticker |
| 7 | [`notebooks/07_rolling_returns.ipynb`](notebooks/07_rolling_returns.ipynb) | CAGR rodante 3y/5y |
| 8 | [`notebooks/08_correlacion.ipynb`](notebooks/08_correlacion.ipynb) | Matriz de correlación |
| 9 | [`notebooks/09_frontera_eficiente.ipynb`](notebooks/09_frontera_eficiente.ipynb) | Monte Carlo, máx Sharpe / mín vol |

Código compartido: [`src/portfolio_utils.py`](src/portfolio_utils.py) · script batch: [`run_analysis.py`](run_analysis.py)

---

## Juicio previo

Antes de mirar resultados:

1. Un núcleo **growth + semiconductores** debería **superar a SPY en CAGR** en 2016–2026, a costa de mayor volatilidad y peores caídas en 2022.
2. Incluir **~20% IEMG** debería **bajar un poco la correlación** con EE.UU., pero puede diluir retorno si emergentes rezagan.
3. `SMH`–`SPYG` serán altamente correlacionados (>0.8).
4. El Max DD del portafolio será **peor** que el de SPY.

---

## Metodología

| Parámetro | Valor |
|---|---|
| Datos | `yfinance` precios ajustados (total return) |
| Frecuencia | Mensual (último precio del mes) |
| Periodo | ene-2016 → **sep-2026** |
| Capital inicial | US$10.000 |
| Aportes | Ninguno |
| Rebalanceo | **Anual** (cierre de año) |
| Benchmark | `SPY` |
| Libre de riesgo | `^IRX` (T-Bill 13s) / 12 |
| Restricciones frontera | long-only, sin apalancamiento, peso ≤ 50% |

---

## Pesos actuales (eToro, valor de mercado, sin efectivo)

Fuente: conector eToro `get-my-portfolio-summary` (solo lectura), snapshot `2026-10-05T16:45:09Z`.

| Ticker | Valor US$ | Peso |
|---|---:|---:|
| SPYG | 14.970 | 30.51% |
| SMH | 10.676 | 21.76% |
| BRK-B | 10.009 | 20.40% |
| IEMG | 9.887 | 20.15% |
| VTI | 3.521 | 7.18% |
| **Total** | **49.063** | **100%** |

---

## Resultados (ene-2016 → sep-2026)

| Métrica | Portafolio | SPY |
|---|---:|---:|
| Valor final (de US$10k) | **66,141** | 44,482 |
| CAGR | **19.21%** | 14.89% |
| Volatilidad | 16.54% | 15.04% |
| Max Drawdown | -27.47% | -23.93% |
| Sharpe | **1.02** | 0.85 |
| Sortino | 0.93 | 0.77 |
| Mejor año | 32.47% | 31.22% |
| Peor año | -21.02% | -18.18% |
| Beta vs SPY | 1.03 | 1.00 |
| Alpha anualizado | 3.62% | — |
| Upside capture | 108.8% | 100% |
| Downside capture | 89.6% | 100% |
| Tracking error | 5.73% | — |
| Information ratio | 0.75 | — |

### Correlación mensual (hallazgos)

| Par | ρ |
|---|---:|
| SPYG–VTI | 0.94 (máx.) |
| SPYG–SMH | 0.81 |
| SMH–BRK-B | 0.30 (mín. del núcleo) |
| IEMG–BRK-B | 0.38 |

### Frontera (ex-post, solo diagnóstico)

Óptimo máx. Sharpe histórico (peso ≤50%): ≈ SMH 46% + BRK-B 45% (sobreajuste; **no** usar como señal de trading).

---

## Figuras principales

Generadas con matplotlib a partir de los precios reales del repositorio:

### Crecimiento
![Crecimiento](figures/01_crecimiento.svg)

### Retornos anuales
![Retornos anuales](figures/02_retornos_anuales.svg)

### Drawdowns
![Drawdowns](figures/03_drawdowns.svg)

### Correlación
![Correlación](figures/04_correlacion.svg)

### Rolling returns
![Rolling](figures/05_rolling_returns.svg)

### Frontera eficiente
![Frontera](figures/07_frontera_eficiente.svg)

---

## Conclusiones

1. **Con pesos vivos (SMH + IEMG), el portafolio bate a SPY** en CAGR (~19.2% vs ~14.9%) y Sharpe (~1.02 vs ~0.85) hasta sep-2026, con Max DD algo peor (~−27.5% vs ~−23.9%).
2. **IEMG aporta diversificación** pero históricamente diluye el motor EE.UU. growth.
3. **El alpha no es uniforme**: se concentra en años risk-on tech; 2022 es el régimen crítico.
4. **La frontera eficiente ex-post favorece SMH+BRK-B** — útil para discutir sobreajuste, no para rebalancear a ciegas.

---

## Cómo ejecutar

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python run_analysis.py
cd notebooks && jupyter notebook
```

---

## Limitaciones

- Precios Yahoo Finance; resultados pueden diferir de otros vendors.
- Sharpe/Sortino dependen de `^IRX`.
- Optimización media-varianza es **in-sample**.
- Sin impuestos/spreads/costos de rebalanceo.

---

**Autor:** Andrés Alejandro Rodríguez Lozano  
**Portafolio:** Portafolio de Andrés Alejandro Rodríguez Lozano
