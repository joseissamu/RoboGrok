cls
docker compose up --build -d
set N_BOTS=3
celery -A task worker -Q bot_queue --loglevel=info --pool=solo