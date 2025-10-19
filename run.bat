@echo off

cls

echo running nginx...
start "Nginx" /MIN cmd /k "startNginx"

echo running main...
start "Main" /MIN cmd /k "call venv\Scripts\activate &&  python -m main"

echo running celery...
start "Celery" /MIN cmd /k "call venv\Scripts\activate &&  startCelery"

:: echo running beat celery...
:: start "beat celery" /MIN cmd /k "call venv\Scripts\activate &&  celery -A task beat --loglevel=info"

echo running webhook...
start "Webhook" /MIN cmd /k "python -m webhook_receiver"
