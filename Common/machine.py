class State:
    def __init__(self):
        pass

    Ready = 'ready'
    Preoperation = 'preoperation'
    Working = 'working'
    Done = 'done'
    Fault = 'fault'
    SerialErr = 'SerialErr'


class Type:
    def __init__(self):
        pass

    FDM = 'FDM'
    SLM = 'SLM'


class Color:
    def __init__(self):
        pass

    White = 'white'
    Black = 'black'
    Yellow = 'yellow'
    Blue = 'blue'


class Material:
    def __init__(self):
        pass

    ABS = 'ABS'
    PLA = 'PLA'


class NozzleSize:
    def __init__(self):
        pass

    Size_40 = 0.4
    Size_20 = 0.2


class Machine:
    def __init__(self):
        self.address = None
        self.type = None
        self.material = None
        self.material_color = None
        self.x_size = None
        self.y_size = None
        self.z_size = None
        self.state = None
        self.worked_time = None
        self.task_info = None
        self.task_id = None
        pass

    def machine_base_info_to_bootstrap_table(self):
        return 'address : {0}<br>' \
               'type : {1}<br>' \
               'material : {2}<br>' \
               'material_color : {3}<br>'' \
               ''x*y*z(mm) : {4}*{5}*{6}<br>'.format(self.address, self.type, self.material,
                                                     self.material_color, self.x_size,
                                                     self.y_size, self.z_size)


class FDM(Machine):
    def __init__(self, index=None, address=None, x_size=None, y_size=None, z_size=None, material=None, state=None,
                 temp_nozzle=None, temp_bed=None, worked_time=None, material_color=None, nozzle_size=None,
                 task_info=None, online=None):
        self.address = address
        self.index = index
        self.type = Type.FDM
        self.x_size = x_size
        self.y_size = y_size
        self.z_size = z_size
        self.material = material
        self.material_color = material_color
        self.state = state
        self.temp_nozzle = temp_nozzle
        self.temp_bed = temp_bed
        self.worked_time = worked_time
        self.nozzle_size = nozzle_size
        self.task_info = task_info
        self.online = online

    def parse_data(self, data):
        state = dict()
        self.state = data[1]

    def parse_data_to_bootstrap_table(self, addr, data):
        for item in self.__dict__:
            if hasattr(self, item):
                setattr(self, item, data[item])
        self.address = addr
        return self.__dict__
