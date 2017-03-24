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
from xml.dom.minidom import parse, parseString

printer = None

app = Flask(__name__)

current_machine = FDM(state=State.Fault)


def parse_temperature(line):
    if 'ok' in line and 'T' in line and 'B' in line and 'T0' in line:
        current_machine.temp_nozzle = line.split(' ')[1].split(':')[1]
        current_machine.temp_bed = line.split(' ')[3].split(':')[1]


def init_printer(machine_config):
    global printer
    for index in range(0, 3):
        try:
            serial_to_usb = machine_config.getElementsByTagName("serialport")[0].firstChild.data
            baudrate = machine_config.getElementsByTagName("baudrate")[0].firstChild.data
            printer = printcore("{0}{1}".format(serial_to_usb, index), int(baudrate))
            print printer
            if printer.printer is not None:
                printer.tempcb = parse_temperature
                current_machine.state = State.Ready
                current_machine.x_size = int(machine_config.getElementsByTagName("x")[0].firstChild.data)
                current_machine.y_size = int(machine_config.getElementsByTagName("y")[0].firstChild.data)
                current_machine.z_size = int(machine_config.getElementsByTagName("z")[0].firstChild.data)
                current_machine.material = machine_config.getElementsByTagName("material")[0].firstChild.data
                current_machine.material_color = \
                    machine_config.getElementsByTagName("material_color")[0].firstChild.data
                current_machine.nozzle_size = float(machine_config.getElementsByTagName("nozzle_size")[0].firstChild.data)
                current_machine.worked_time = int(machine_config.getElementsByTagName("worked_time")[0].firstChild.data)
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
        init_printer(config_element)
        return jsonify()
    except Exception, e:
        return e


@app.route("/start-task", methods=['POST'])
def start_task():
    if current_machine.state is State.Ready:
        task_file = request.files.getlist('file')
        task_file[0].save(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'task.gcode'))
        print "get file" + str(task_file[0].filename)
        current_machine.state = State.Working
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
    dom = parse(os.path.abspath(os.path.dirname(__file__)) + '/config.xml')
    config_element = dom.getElementsByTagName("config")[0]
    init_printer(config_element)
    send_machine_state()
    app.run(host="0.0.0.0", port=5001, debug=False)
