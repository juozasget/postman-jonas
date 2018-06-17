from celery import Celery
from celery.schedules import crontab

BROKER_URL = os.environ['REDIS_URL']

celery = Celery(app.name, broker=app.config['BROKER_URL'])
celery.conf.update(app.config)

app = Celery()

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every Monday morning at 7:30 a.m.
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1),
        test.s('Happy Mondays!'),
    )

@app.task
def test(arg):
    print(arg)
