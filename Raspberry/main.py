import sys, requests, time, json, os
from threading import Timer
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from Common.machine import FDM, State, Material, Color, NozzleSize
from flask import Flask, request, jsonify
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Common", "Printrun-master")))
for item in sys.path:
    print item
from printrun.printcore import printcore
from printrun import gcoder
import xml.etree.ElementTree as ET
import socket

myname = socket.getfqdn(socket.gethostname())
myaddr = socket.gethostbyname(myname)

printer = None
tree = ET.parse(os.path.abspath(os.path.dirname(__file__)) + '/config.xml')
root = tree.getroot()

app = Flask(__name__)

current_machine = FDM(state=State.Fault)


def parse_temperature(line):
    if 'ok' in line and 'T' in line and 'B' in line and 'T0' in line:
        current_machine.temp_nozzle = line.split(' ')[1].split(':')[1]
        current_machine.temp_bed = line.split(' ')[3].split(':')[1]


def updata_config(name, value):
    tree.getroot().find(name).text = value
    tree.write(os.path.abspath(os.path.dirname(__file__)) + '/config.xml')


def init_printer(machine_config):
    global printer
    for index in range(0, 3):
        try:
            serial_to_usb = machine_config.find('serialport').text
            baudrate = machine_config.find('baudrate').text
            printer = printcore("{0}{1}".format(serial_to_usb, index), int(baudrate))
            print printer
            if printer.printer is not None:
                printer.tempcb = parse_temperature
                current_machine.state = State.Ready
                current_machine.x_size = int(machine_config.find('x').text)
                current_machine.y_size = int(machine_config.find('y').text)
                current_machine.z_size = int(machine_config.find('z').text)
                current_machine.material = machine_config.find('material').text
                current_machine.material_color = machine_config.find('material_color').text
                current_machine.nozzle_size = float(machine_config.find('nozzle_size').text)
                current_machine.worked_time = int(machine_config.find('worked_time').text)
                break
        except Exception, e:
            current_machine.state = str(e)
            print str(e)


@app.route("/reboot")
def reboot():
    return "reboot..."


@app.route("/init", methods=['POST'])
def init():
    global printer
    try:
        printer.disconnect()
        init_printer(root)
        return jsonify()
    except Exception, e:
        return e


@app.route("/start-task", methods=['POST'])
def start_task():
    global printer
    task_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'task.gcode')
    if current_machine.state is State.Ready:
        task_file = request.files.getlist('file')
        task_file[0].save(task_path)
        print "get file" + str(task_file[0].filename)
        current_machine.state = State.Working
        current_machine.task_info = request.args['task_id']
        updata_config('task_id', request.args['task_id'])
        totallines = len(open(task_path).readlines())
        updata_config('currentline', '0')
        updata_config('totalline', str(totallines))
        gcode = [i.strip() for i in open(task_path)]
        gcode = gcoder.LightGCode(gcode)
        printer.startprint(gcode)
        return jsonify()
    else:
        print "busy..."
        return jsonify('busy...')


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


@app.route("/state", methods=['GET'])
def state():
    return jsonify(json.dumps(get_machine_state()))


@app.route("/send-cmd", methods=['POST'])
def send_cmd():
    global printer
    cmd = request.args.get('cmd')
    result = printer.send_now(cmd)
    print result
    return jsonify(result)


def get_machine_state():
    global printer
    printer.send('M105')
    current_machine.online = printer.online
    current_machine.address = myaddr
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
        pass


if __name__ == "__main__":
    init_printer(root)
    send_machine_state()
    app.run(host="0.0.0.0", port=5001, debug=False)
