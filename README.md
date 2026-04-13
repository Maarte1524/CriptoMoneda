# CriptoMoneda Bot (Windows-first)

## 1) Resumen ejecutivo
Sistema modular para Binance orientado a **paper -> testnet -> live**, con gestión de riesgo estricta, backtesting y monitoreo. Pares soportados: `BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, LINKUSDT, TONUSDT`.

## 2) Arquitectura completa
- `bot/main.py`: orquestación async, lifecycle, kill switch.
- `bot/data_feed.py`: conexión Binance (ccxt), OHLCV, indicadores.
- `bot/risk_manager.py`: límites de DD, sizing, cooldown.
- `bot/order_manager.py`: normalización/validación por reglas exchange.
- `bot/portfolio.py`: estado de posiciones y equity.
- `bot/db.py`: auditoría SQLite.
- `bot/notifier.py`: alertas Telegram + consola.
- `bot/backtester.py`: simulador y métricas.
- `bot/dashboard/app.py`: Streamlit.
- `bot/strategies/*`: estrategias desacopladas.

## 3) Diseño de estrategias
- **Trend Following**: EMA20/50, EMA200, ADX, volumen.
- **Breakout/Momentum**: Donchian + ATR + volumen.
- **Mean Reversion**: Bollinger + RSI + VWAP.
- **Combined**: exige consenso ponderado (>=2 señales efectivas).

## 4) Modelo de riesgo
- 1% por trade evita ruina temprana.
- máximo 4 posiciones y 25% por activo limita concentración.
- DD diario -3% y semanal -7% corta colas de pérdida.
- cooldown 24h tras 3 pérdidas reduce sobreoperación.
- `--kill` para detener trading de emergencia.

## 5) Diseño técnico Python
- Python 3.11+, type hints, validación pydantic, logging estructurado.
- I/O async-first con reintentos exponenciales.
- Config dual `.env + config.yaml`.

## 6) Código base completo del bot
Ver carpeta `/bot`.

## 7) Backtesting
`python -m bot.main --backtest --symbol BTCUSDT` calcula retorno, CAGR, Sharpe, Sortino, MDD, win rate, profit factor y expectancy.

## 8) Dashboard
`streamlit run bot/dashboard/app.py`.

## 9) Guía Windows (PowerShell)
```powershell
# instalar Python 3.11+ desde python.org y marcar "Add python.exe to PATH"
python --version
py -3.11 --version

New-Item -ItemType Directory -Path C:\Trading\CriptoMoneda -Force
Set-Location C:\Trading\CriptoMoneda

# clonar/copiar proyecto
# git clone <repo_url> .

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

Copy-Item .env.example .env
notepad .env
notepad config.yaml

python -m bot.main --paper
streamlit run bot/dashboard/app.py
```

### Task Scheduler (24/7)
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -WindowStyle Hidden -Command \"Set-Location C:\\Trading\\CriptoMoneda; .\\.venv\\Scripts\\Activate.ps1; python -m bot.main --paper\""
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "CriptoMonedaBot" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
```

### Logs, stop y kill switch
```powershell
Get-Content .\logs\bot.log -Wait
Stop-ScheduledTask -TaskName "CriptoMonedaBot"
python -m bot.main --kill
```

## 10) VPS/Docker opcional
```bash
docker build -t criptomoneda-bot .
docker run --env-file .env -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs criptomoneda-bot
```

## 11) README
Este archivo cubre entregables funcionales y operativos.

## 12) requirements.txt
Dependencias fijadas en raíz.

## 13) Dockerfile
Incluido en raíz.

## 14) CI
Workflow `ci.yml` ejecuta `pytest`.

## 15) Pruebas unitarias base
`bot/tests/test_signals.py`, `test_risk.py`, `test_orders.py`.

---

## Riesgos críticos detectados antes de producción
1. Sesgo de backtest por OHLCV y sin orderbook: añadir simulación con latencia y partial fills.
2. Correlación entre alts: incorporar matriz rolling y límite de clúster de riesgo.
3. Slippage real > modelo: calibrar bps por activo/horario.
4. Fallos API/rate limit: incluir cola de órdenes y reconciliación de estado idempotente.
5. Sobreajuste: usar walk-forward estricto y mínimo 200+ trades por variante.
