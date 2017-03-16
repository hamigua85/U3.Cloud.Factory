import sys, requests, time, json, os
from threading import Timer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Common.machine import FDM, State
from flask import Flask, request
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Common", "Printrun-master")))
for item in sys.path:
    print item
from printrun.printcore import printcore


printer = printcore('/dev/ttyUSB0', 115200)
app = Flask(__name__)

current_machine = FDM()


@app.route("/reboot")
def reboot():
    return "reboot..."


@app.route("/init")
def init():
    global printer
    print "init..."
    try:
        printer.disconnect()
        printer = printcore('/dev/tty.usbserial-AL00YO7M', 115200)
        return printer
    except Exception, e:
        return e


@app.route("/start-task", methods=['POST'])
def start_task():
    if current_machine.state is State.Ready:
        upload_files = request.files.getlist('file')
        print "get file"
    else:
        print "busy..."


@app.route("/pause-task")
def pause_task():
    if current_machine.state is not State.Working:
        print "pause task..."
    else:
        print "not working..."


@app.route("/cancel-task")
def cancel_task():
    if current_machine.state is not State.Working:
        print "cancel task..."
        init()
    else:
        print "not working..."


@app.route("/state")
def state():
    return get_machine_state()


@app.route("/send-cmd", methods=['POST'])
def send_cmd():
    cmd = request.args.get('cmd')
    result = printer.send_now(cmd)
    return result


def get_machine_state():
    current_machine.x_size = 100
    current_machine.y_size = 100
    current_machine.z_size = 100
    return current_machine.__dict__


def send_machine_state():
    info = get_machine_state()
    try:
        print str(time.time())
        r = requests.post("http://192.168.0.99:5000/online_machine_state", data=json.dumps(info), timeout=5)
    except Exception, e:
        print e
    finally:
        t = Timer(5, send_machine_state)
        t.start()

if __name__ == "__main__":
    # init()
    app.run(host="0.0.0.0", port=5001, debug=False)
