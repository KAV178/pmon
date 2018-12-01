# -*- coding: utf-8 -*-
from workers import *

T_CONF_FN = 'targets.ini'
S_CONF_FN = 'storages.ini'


class Target(object):
    def __new__(cls, *args, **kwargs):
        tl = read_config(T_CONF_FN)

        if tl and kwargs['name'] in tl.keys():
            return super(Target, cls).__new__(cls, *args, **kwargs)
        else:
            raise RuntimeError("Target with name \"{0}\" is not found!".format(kwargs['name']))

    def __init__(self, name):
        self.name = name


    @property
    def start_mode(self):
        return read_config(T_CONF_FN)[self.name]['start_mode']

    @start_mode.setter
    def start_mode(self, value):
        values = ('auto', 'manual')
        if value.lower() in values:
            update_value(T_CONF_FN, self.name, 'start_mode', value)
        else:
            raise RuntimeError('Wrong value \"{0}\"! Can be any from: {1}'.format(value, ', '.join(values)))

    @property
    def ent_name(self):
        return read_config(T_CONF_FN)[self.name]['ent_name']

    @ent_name.setter
    def ent_name(self, value):
        update_value(T_CONF_FN, self.name, 'ent_name', value)

    @property
    def gw_name(self):
        return read_config(T_CONF_FN)[self.name]['gw_name']

    @gw_name.setter
    def gw_name(self, value):
        update_value(T_CONF_FN, self.name, 'gw_name', value)

    @property
    def storage(self):
        return read_config(T_CONF_FN)[self.name]['store_name']

    @storage.setter
    def storage(self, value):
        #  FIXme: check available storages
        sl = read_config('storages.ini')
        if value in sl.keys():
            update_value(T_CONF_FN, self.name, 'storage', value)
        else:
            raise RuntimeError('Wrong storage name \"{0}\".Available names: {1}'.format(value,
                                                                                        ', '.join(sl.keys())))

    @property
    def sieb_ver(self):
        return read_config(T_CONF_FN)[self.name]['sieb_ver']

    @sieb_ver.setter
    def sieb_ver(self, value):
        update_value(T_CONF_FN, self.name, 'sieb_ver', value)

    @property
    def srvrmgr_cmd(self):
        return read_config('settings.ini')['srvrmgr_' + self.sieb_ver]['cmd']

    @srvrmgr_cmd.setter
    def srvrmgr_cmd(self, value):
        update_value(T_CONF_FN, self.name, 'srvrmgr_cmd', value)

    @property
    def request_timeout(self):
        return int(read_config(T_CONF_FN)[self.name]['request_timeout'])

    @request_timeout.setter
    def request_timeout(self, value):
        update_value(T_CONF_FN, self.name, 'request_timeout', value)

    @property
    def crd(self):
        return read_config(T_CONF_FN)[self.name]['crd']

    @crd.setter
    def crd(self, value):
        update_value(T_CONF_FN, self.name, 'crd', value)
