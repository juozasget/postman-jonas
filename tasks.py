import os
import sys
import json
from celery import Celery
from celery.schedules import crontab

from app import set_broadcast, send_broadcast

BROKER_URL = os.environ['REDIS_URL']

celery = Celery(app.name, broker=app.config['BROKER_URL'])
celery.conf.update(app.config)

app = Celery()

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('world') every 30 seconds
    sender.add_periodic_task(30.0, send.s(), expires=10)
    # Executes every Monday morning at 7:30 a.m.
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1),
        send.s(),
    )

@app.task
def send():
    message_creative_id = set_broadcast()   #Send the message to fb
    send_broadcast(message_creative_id)
