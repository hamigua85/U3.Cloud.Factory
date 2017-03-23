import sys, requests, time, json, os
from threading import Timer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Common.machine import FDM, State
from flask import Flask, request, jsonify
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Common", "Printrun-master")))
for item in sys.path:
    print item
from printrun.printcore import printcore
from printrun import gcoder

serial_to_usb = '/dev/ttyUSB'
baudrate = 115200
printer = None

app = Flask(__name__)

current_machine = FDM()

def parse_temperature(line):
    if 'ok' in line and 'T' in line and 'B' in line and 'T0' in line:
        current_machine.temp_nozzle = line.split(' ')[1].split(':')[1]
        current_machine.temp_bed = line.split(' ')[3].split(':')[1]


def init_printer():
    global printer
    for index in range(0, 3):
        try:
            printer = printcore("{0}{1}".format(serial_to_usb, index), baudrate)
            print printer
            if printer.printer is not None:
                printer.tempcb = parse_temperature
                break
        except Exception, e:
            print e


@app.route("/reboot")
def reboot():
    return "reboot..."


@app.route("/init", methods=['POST'])
def init():
    global printer
    try:
        printer.disconnect()
        init_printer()
        return jsonify()
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
    global printer
    cmd = request.args.get('cmd')
    result = printer.send_now(cmd)
    print result
    return jsonify(result)


def get_machine_state():
    global printer
    printer.send_now('M105')
    current_machine.x_size = 100
    current_machine.y_size = 100
    current_machine.z_size = 100
    current_machine.online = printer.online
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
    init_printer()
    send_machine_state()
    app.run(host="0.0.0.0", port=5001, debug=False)
