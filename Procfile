web: gunicorn app:app --log-file=-
main_worker: celery -A app.celery worker --beat --loglevel=INFO
