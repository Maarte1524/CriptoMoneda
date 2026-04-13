# CriptoMoneda Binance Trading Bot (Windows-first)

Bot algorítmico profesional para Binance con enfoque en robustez operativa, seguridad, gestión de riesgo estricta y trazabilidad completa.

## Riesgos críticos mitigados

1. **TA-Lib en Windows**: uso de `pandas-ta` (pure Python).
2. **Compatibilidad asyncio Windows**: `WindowsSelectorEventLoopPolicy` automático.
3. **Lookahead bias/data leakage**: señales y backtest con datos cerrados (`shift(1)`).
4. **SQLite bloqueante**: toda persistencia crítica con `aiosqlite`.
5. **Kill switch**: cierre ordenado con `asyncio.Event` (detiene entradas, cierra posiciones, persiste estado final, cierra conexiones).
6. **WebSocket ciego**: heartbeat + watchdog con reconexión automática.
7. **Órdenes inválidas**: normalización con filtros de mercado (precision/minQty/minNotional).
8. **Correlación costosa**: cálculo en background cada 5 minutos (configurable).
9. **Dashboard aislado**: Streamlit se ejecuta en proceso separado.
10. **Fuga de secretos**: sanitización de logs y mensajes.

## Estructura

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
.github/workflows/ci.yml
config.yaml
.env.example
requirements.txt
Dockerfile
```

## Instalación rápida (Windows PowerShell)

```powershell
py -3.11 --version
mkdir C:\trading\CriptoMoneda
cd C:\trading\CriptoMoneda
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
notepad config.yaml
python -m bot.main --paper
```

## Dashboard (proceso separado)

```powershell
streamlit run bot/dashboard/app.py
```

## Task Scheduler

1. Crear script `run_bot.ps1`:

```powershell
Set-Location C:\trading\CriptoMoneda
.\.venv\Scripts\Activate.ps1
python -m bot.main --paper
```

2. Crear tarea:

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\trading\CriptoMoneda\run_bot.ps1"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "CriptoMonedaBot" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -User $env:USERNAME
```

## Kill switch

```powershell
python -m bot.main --kill
```
