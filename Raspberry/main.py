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
import fcntl
import struct


def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

try:
    myaddr = get_ip_address('eth0')
except Exception, e:
    myaddr = None
    print e

printer = None
tree = ET.parse(os.path.abspath(os.path.dirname(__file__)) + '/config.xml')
root = tree.getroot()

app = Flask(__name__)

current_machine = FDM(state=State.Initing)
server_addr = ""

def parse_temperature(line):
    if 'ok' in line and 'T' in line and 'B' in line and 'T0' in line:
        current_machine.temp_nozzle = line.split(' ')[1].split(':')[1]
        current_machine.temp_bed = line.split(' ')[3].split(':')[1]


def updata_config(name, value):
    tree.getroot().find(name).text = value
    tree.write(os.path.abspath(os.path.dirname(__file__)) + '/config.xml')


def init_printer(machine_config):
    global printer
    global server_addr
    for index in range(0, 3):
        try:
            # read config file init serialport
            serial_to_usb = machine_config.find('serialport').text
            baudrate = machine_config.find('baudrate').text
            server_addr = machine_config.find('server').text

            # read config file init machine state
            if machine_config.find('state').text is not None:
                current_machine.state = machine_config.find('state').text
            else:
                current_machine.state = State.Ready

            # init printcore
            printer = printcore("{0}{1}".format(serial_to_usb, index), int(baudrate))

            if printer.printer is not None:
                # set callback func
                printer.tempcb = parse_temperature

                # read config file init current_machine
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
        current_machine.state = State.Ready
        printer.disconnect()
        init_printer(root)
        time.sleep(1)
        printer.send_now("G28")
        return jsonify()
    except Exception, e:
        return jsonify(e)


@app.route("/start-task", methods=['POST'])
def start_task():
    global printer

    task_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'task.gcode')

    if current_machine.state is State.Ready:
        # receive gcode file which send from Server, and save to task_path
        task_file = request.files.getlist('file')
        task_file[0].save(task_path)

        print "get file" + str(task_file[0].filename)

        # read task_path file
        totallines = len(open(task_path).readlines())

        # write task_id, currentline and totalline into config file
        updata_config('currentline', '0')
        updata_config('totalline', str(totallines))
        updata_config('task_id', request.args['task_id'])

        # update current_machine info
        current_machine.task_info = 'task_id : {0}<br>' \
                                    'task_state : {1}%'.format(request.args['task_id'], '00.00')

        current_machine.task_id = request.args['task_id']

        # start print gcode file
        gcode = [i.strip() for i in open(task_path)]
        gcode = gcoder.LightGCode(gcode)
        printer.startprint(gcode)

        # update machine state to working
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

    progress = 0
    try:
        if float(printer.priqueue.qsize()) != 0:
            progress = round((float(printer.lineno)/float(printer.priqueue.qsize())) * 100.0, 2)
        current_machine.task_info = 'task_id : {0}<br>' \
                                    'task_state : {1}%'.format(current_machine.task_id, progress)
    except Exception, e:
        print e
    current_machine.online = printer.online
    current_machine.address = myaddr
    if printer.lineno != 0 and printer.lineno >= printer.priqueue.qsize():
        current_machine.state = State.Done
        current_machine.task_info = 'task_id : {0}<br>' \
                                    'task_state : {1}%'.format(current_machine.task_id, '100')
    return current_machine.__dict__


def send_machine_state():
    with app.app_context():
        global server_addr
        info = get_machine_state()
        try:
            print str(time.time())
            print info
            r = requests.post("http://{0}/online_machine_state".format(server_addr), data=json.dumps(info), timeout=5)
        except Exception, e:
            print e
        finally:
            pass
    t = Timer(5, send_machine_state)
    t.start()


if __name__ == "__main__":
    init_printer(root)
    send_machine_state()
    app.run(host="0.0.0.0", port=5001, debug=False)
