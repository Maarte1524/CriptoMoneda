# CriptoMoneda - Binance Trading Bot (Windows-first)

## 1) Resumen ejecutivo
Este proyecto implementa un bot profesional para Binance con arquitectura modular, priorizando **paper trading**, control de riesgo estricto y operación estable en **Windows 10/11**. Está diseñado para evolucionar de simulación a testnet/live con auditoría completa (SQLite/logs/CSV/JSON), dashboard de monitoreo y pruebas automatizadas.

## 2) Arquitectura completa del sistema
```text
bot/
  main.py
  config.py
  data_feed.py
  risk_manager.py
  order_manager.py
  portfolio.py
  notifier.py
  backtester.py
  db.py
  utils.py
  strategies/
    base.py
    trend_following.py
    mean_reversion.py
    breakout.py
    combined_signal.py
  dashboard/
    app.py
  tests/
    test_signals.py
    test_risk.py
    test_orders.py
```

## 3) Diseño detallado de estrategias
- **Trend Following**: EMA20/50 + EMA200 + ADX + volumen + confirmación 1H/4H.
- **Breakout/Momentum**: ruptura de rango reciente con confirmación de ATR y volumen.
- **Mean Reversion**: Bollinger + RSI + VWAP solo en rango (ADX bajo).
- **Combined Signal**: exige al menos 2 señales alineadas.

## 4) Modelo de gestión de riesgo
Reglas por defecto:
- Riesgo por trade: 1%
- Máx. posiciones abiertas: 4
- Exposición máxima por activo: 25%
- Límite DD diario: -3%
- Límite DD semanal: -7%
- Cooldown de 24h tras 3 pérdidas por par
- Kill switch de emergencia

**Por qué son razonables:** limitan riesgo de ruina, reducen sobreoperación y desacoplan errores temporales del mercado/sistema. Ajustar de forma gradual (0.25%-0.5% por iteración), nunca varias palancas a la vez.

## 5) Diseño técnico Python
- Python 3.11+ con `asyncio` para I/O.
- `ccxt` async para integración Binance Spot/Futures/Testnet.
- Config robusta vía `.env` + `config.yaml` con validación `pydantic`.
- Persistencia en SQLite por defecto (Windows friendly).

## 6) Código base completo del bot
Ver carpeta `bot/` (archivos incluidos en este repositorio).

## 7) Módulo de backtesting
`bot/backtester.py` incluye métricas: total return, CAGR, Sharpe, Sortino, max drawdown, win rate, avg win/loss, profit factor, expectancy.

## 8) Dashboard de monitoreo
`streamlit run bot/dashboard/app.py`.

## 9) Guía instalación Windows (PowerShell)
### 9.1 Instalar Python 3.11+
```powershell
winget install Python.Python.3.11
```

### 9.2 Verificación en PowerShell
```powershell
python --version
pip --version
```

### 9.3 Crear carpeta de proyecto
```powershell
New-Item -ItemType Directory -Path C:\Trading\CriptoMoneda -Force
cd C:\Trading\CriptoMoneda
```

### 9.4 Crear entorno virtual
```powershell
python -m venv .venv
```

### 9.5 Activar entorno virtual
```powershell
.\.venv\Scripts\Activate.ps1
```

### 9.6 Instalar dependencias
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 9.7 Crear archivo .env
```powershell
Copy-Item .env.example .env
notepad .env
```

### 9.8 Crear/editar config.yaml
```powershell
notepad config.yaml
```

### 9.9 Ejecutar en modo paper
```powershell
python -m bot.main --paper
```

### 9.10 Ejecutar dashboard
```powershell
streamlit run bot\dashboard\app.py
```

### 9.11 Dejar corriendo con Task Scheduler
```powershell
$action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "-NoProfile -WindowStyle Hidden -Command \"cd C:\Trading\CriptoMoneda; .\\.venv\\Scripts\\Activate.ps1; python -m bot.main --paper\""
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "CriptoMonedaBot" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest
Start-ScheduledTask -TaskName "CriptoMonedaBot"
```

### 9.12 Revisar logs
```powershell
Get-Content .\logs\bot.log -Wait
```

### 9.13 Detener bot
```powershell
Stop-ScheduledTask -TaskName "CriptoMonedaBot"
```

### 9.14 Usar kill switch
```powershell
python -m bot.main --kill
```

## 10) VPS/Docker (opcional)
```bash
docker build -t criptomoneda-bot .
docker run --env-file .env -v $(pwd)/data:/app/data -v $(pwd)/logs:/app/logs criptomoneda-bot
```

## 11) README completo
Este archivo cumple ese entregable.

## 12) requirements.txt
Incluido con versiones fijadas.

## 13) Dockerfile
Incluido.

## 14) CI workflow
`.github/workflows/ci.yml` con pytest.

## 15) Pruebas unitarias base
`bot/tests/`.

---

## Crítica técnica (debilidades actuales y mitigaciones)
1. **Latencia/slippage real**: backtest simplifica ejecución. Mitigar con replay de order book y fill model.
2. **Sesgo de régimen**: estrategias pueden degradarse en cambios bruscos de estructura. Mitigar con walk-forward estricto.
3. **Riesgo de correlación sistémica**: implementar matriz rolling y límites por clúster (macro vs alt agresivas).
4. **Operativa live**: requiere endurecer idempotencia con clientOrderId y reconciliación periódica de estado.
5. **Seguridad operativa**: usar key sin retiros, IP whitelist, y rotación de credenciales.
