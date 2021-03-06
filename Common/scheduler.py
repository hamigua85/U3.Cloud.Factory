from threading import Timer
import requests, time
import json
from Common.models import User, Role, Post, Task
from Common.machine import FDM, State, Type
from app import db
from redis import Redis

online_machines_redis = Redis()


def update_online_machine_state(request):
    data = json.loads(request.data)
    online_machines_redis.set(data["address"], request.data, 7)


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
                time.sleep(5)
                online_machines = get_online_machines(State.Ready)
            waiting_task.state = 'preoperation'
            db.session.commit()
            files = {'file': open(waiting_task.file.path, 'rb')}
            r = requests.post('http://{0}:{1}/{2}?task_id={3}'.format(online_machines[0]['address'], 5001, 'start-task',
                                                                      waiting_task.id),
                              files=files, timeout=60)
            if r.status_code == 200:
                r = requests.get('http://{0}:{1}/{2}'.format(online_machines[0]['address'], 5001, 'state'), timeout=60)
                if r.status_code == 200 and json.loads(eval(r.content))['state'] == State.Working:
                    waiting_task.state = 'assigned'
                    waiting_task.machine_info = \
                        str(waiting_task.machine_info).replace('address : None',
                                                               'address : {0}'.format(online_machines[0]['address']))
                else:
                    print 'fail to confirm remote machine state'
                    # waiting_task.state = 'waiting'
            else:
                print 'fail to upload task file'
            db.session.commit()
    t = Timer(5, algorithm_one, args=(app,))
    t.start()
