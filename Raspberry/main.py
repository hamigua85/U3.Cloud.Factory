import sys, requests, time, json
from threading import Timer
sys.path.append("../../Common")
from Common.machine import FDM


current_machine = FDM()


def get_machine_state():
    current_machine.x_size = 100
    current_machine.y_size = 100
    current_machine.z_size = 100
    return current_machine.__dict__


def send_machine_state():
    info = get_machine_state()
    try:
        print str(time.time())
        print info
        r = requests.post("http://192.168.0.99:5000/online_machine_state", data=json.dumps(info), timeout=5)
    except Exception, e:
        print e
    finally:
        t = Timer(5, send_machine_state)
        t.start()

if __name__ == "__main__":
    send_machine_state()
