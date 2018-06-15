
#________________Job sheduling part__________________________________

def job():
    message_creative_id = set_broadcast()   #Send the message to fb
    send_broadcast(message_creative_id)

schedule.every(1).minutes.do(job)
#schedule.every().wednesday.at("13:15").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
