from threading import Timer
import requests, time


def post_scheduler_request():
    try:
        print str(time.time())
        r = requests.post("http://192.168.0.99:5000/scheduler-tasks")
    except Exception, e:
        print e
    finally:
        t = Timer(2, post_scheduler_request)
        t.start()

if __name__ == "__main__":
    post_scheduler_request()
