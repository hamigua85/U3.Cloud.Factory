from threading import Timer
import requests, time
import json
from Common.models import User, Role, Post, Task
from Common.machine import FDM, State, Type
from app import db
from redis import Redis

online_machines_redis = Redis()


def update_online_machine_state(request):
    online_machines_redis.set('{0}'.format(request.headers.environ['REMOTE_ADDR']), request.data, 7)


def get_online_machines(state=None):
    machines_info = []
    for machine_addr in online_machines_redis.keys():
        data = online_machines_redis.get(machine_addr)
        online_machine = FDM()
        temp = online_machine.parse_data_to_bootstrap_table(machine_addr, json.loads(data))
        if state is None:
            machines_info.append(temp)
        elif temp['state'] == state and temp['online'] is True:
            machines_info.append(temp)
    return machines_info


def algorithm_one(app):
    with app.app_context():
        waiting_task = Task.query.filter_by(state='waiting').first()
        if waiting_task is not None:
            online_machines = get_online_machines(State.Ready)
            while len(online_machines) == 0:
                online_machines = get_online_machines(State.Ready)
            waiting_task.state = 'preoperation'
            db.session.commit()
            files = {'file': open(waiting_task.file.path, 'rb')}
            r = requests.post('http://{0}:{1}/{2}'.format(online_machines[0]['address'], 5001, 'start-task'),
                              files=files, timeout=10)
            print r
    t = Timer(5, algorithm_one, args=(app,))
    t.start()
