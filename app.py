import os
import sys
import json
import time
from datetime import datetime

import requests
from flask import Flask, request
from celery import Celery


app = Flask(__name__)

# Celery configuration
app.config['CELERY_BROKER_URL'] = os.environ['REDIS_URL']

# Initialize Celery
celery = Celery(app.name, broker=app.config[os.environ['REDIS_URL']])
celery.conf.update(app.config)


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


ACCESS_TOKEN = os.environ['ACCESS_TOKEN']
VERIFY_TOKEN = os.environ['VERIFY_TOKEN']

@app.route('/', methods=['GET'])
def verify():
    # when the endpoint is registered as a webhook, it must echo back
    # the 'hub.challenge' value it receives in the query arguments
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200
    return "Hello world", 200


@app.route('/', methods=['POST'])
def webhook():
    # endpoint for processing incoming messaging events
    data = request.get_json()
    log(data)  # you may not want to log every incoming message in production, but it's good for testing
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):  # someone sent us a message
                    sender_id = messaging_event["sender"]["id"]        # the facebook ID of the person sending you the message
                    recipient_id = messaging_event["recipient"]["id"]  # the recipient's ID, which should be your page's facebook ID
                    message_text = messaging_event["message"]["text"]  # the message's text
                    if message_text == "Send":
                        message_creative_id = set_broadcast()   #Send the message to fb
                        send_broadcast(message_creative_id)     #Distribute the message from fb to users
                    elif message_text == "Thank you":
                        send_message(sender_id, "You're welcome!")
                    else:
                        send_message(sender_id, 'If you want to setup & send a BTC/USD price report type "Send"')
                if messaging_event.get("delivery"):  # delivery confirmation
                    pass
                if messaging_event.get("optin"):  # optin confirmation
                    pass
                if messaging_event.get("postback"):  # user clicked/tapped "postback" button in earlier message
                    pass
    return "ok", 200

#Sendin a message to a single user
def send_message(recipient_id, message_text):
    log("sending message to {recipient}: {text}".format(recipient=recipient_id, text=message_text))
    params = {
        "access_token": ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

#Sending the broadcast message to be saved at Facebook node
def set_broadcast():
    price_btc, change_btc = get_btc()
    #construct message
    price_btc = "Current BTC price: " + str(price_btc) + " USD"
    change_btc = "Change in price over the past 24h: " + str(change_btc) + " %"
    params = {
        "access_token": ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
          "messages": [{
              "attachment":{
                "type":"template",
                "payload":{
                  "template_type":"generic",
                  "elements":[
                     {
                      "title":price_btc,
                      "image_url":"https://s2.coinmarketcap.com/static/img/coins/200x200/1.png",
                      "subtitle":change_btc,
                      "buttons":[
                        {
                          "type":"web_url",
                          "url":"https://coinmarketcap.com/currencies/bitcoin/",
                          "title":"View at CMC"
                        }
                      ]
                    }
                  ]
                }
              }
            }
          ]
        })
    r = requests.post('https://graph.facebook.com/v2.11/me/message_creatives', params=params, headers=headers, data=data)
    response = r.json()
    message_creative_id = response["message_creative_id"]
    return (message_creative_id)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

#Sending a request to Facebook to send saved broadcast message to users
def send_broadcast(message_creative_id):
    params = {
        "access_token": ACCESS_TOKEN
    }
    headers = {
        "Content-Type": "application/json"
    }
    data = json.dumps({
        "message_creative_id": message_creative_id,
        "notification_type": "REGULAR",
        "messaging_type": "MESSAGE_TAG",
        "tag": "NON_PROMOTIONAL_SUBSCRIPTION"
    })
    r = requests.post("https://graph.facebook.com/v2.11/me/broadcast_messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

#GET BTC/USD rate from CoinMarketCap
def get_btc ():
    r = requests.get("https://api.coinmarketcap.com/v2/ticker/1/")
    data = r.json()
    price_btc = data["data"]["quotes"]["USD"]["price"]
    change_btc = data["data"]["quotes"]["USD"]["percent_change_24h"]
    return(price_btc, change_btc)
    if r.status_code != 200:
        log(r.status_code)
        log(r.text)

def log(msg, *args, **kwargs):  # simple wrapper for logging to stdout on heroku
    try:
        if type(msg) is dict:
            msg = json.dumps(msg)
        else:
            msg = msg.format(*args, **kwargs)
        print (u"{}: {}".format(datetime.now(), msg))
    except UnicodeEncodeError:
        pass  # squash logging errors in case of non-ascii text
    sys.stdout.flush()

if __name__ == '__main__':
    app.run(debug=True)
