# -*- coding: utf-8 -*-

from workers import *

S_CONF_FN = 'storages.ini'


class Storage(object):
    def __new__(cls, *args, **kwargs):
        sl = read_config(S_CONF_FN)
        if kwargs['name'] in sl.keys():
            return super(Storage, cls).__new__(cls)
        else:
            raise RuntimeError("Storage with name \"{0}\" is not found!".format(kwargs['name']))

    def __init__(self, name):
        self.name = name

    @property
    def type(self):
        return read_config(S_CONF_FN)[self.name]['type']

    @type.setter
    def type(self, value):
        av_types = {'file', 'http-grafana'}
        if value in av_types:
            update_value(S_CONF_FN, self.name, 'type', value)
        else:
            raise RuntimeError("Wrong type \"{0}\". Available types: {1}".format(value, ", ".join(av_types)))

    @property
    def path(self):
        s_data = read_config(S_CONF_FN)[self.name]
        if s_data['type'] == 'file':
            return s_data['path']
        elif s_data['type'] == 'http-grafana':
            return s_data['conn_str']
        else:
            return None

    @path.setter
    def path(self, value):
        update_value(S_CONF_FN, self.name, 'path', value)
