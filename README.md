# CriptoMoneda Binance Trading Bot (Windows-first)

Bot algorítmico profesional para Binance con enfoque en robustez operativa, seguridad, gestión de riesgo estricta y trazabilidad completa.

## Riesgos críticos detectados y mitigaciones de diseño

1. **Sobreajuste y sesgo de selección**: se fuerza walk-forward, split train/validation/test y umbral mínimo de 200 trades antes de confiar una estrategia.
2. **Riesgo de ejecución**: retries con backoff, validación previa de riesgo y modo `paper` por defecto.
3. **Riesgo de correlación**: limitación de posiciones correlacionadas y reducción de tamaño para clústeres de riesgo.
4. **Riesgo operacional 24/7**: kill switch, circuit breakers diario/semanal, cooldown por pérdidas y logging estructurado.
5. **Riesgo de seguridad**: credenciales por `.env`, sin hardcodeo, recomendación de API sin retiros y whitelist IP.

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

## Docker (opcional)

```powershell
docker build -t criptomoneda-bot .
docker run --env-file .env -v ${PWD}/data:/app/data -v ${PWD}/logs:/app/logs criptomoneda-bot
```

## Seguridad mínima recomendada

- API key con **retiros desactivados**.
- Activar **IP whitelist**.
- Rotación periódica de credenciales.
- Revisar logs JSON para auditoría.
