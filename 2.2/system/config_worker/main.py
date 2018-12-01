# -*- coding: utf-8 -*-
__author__ = 'Kostreno A.V.'

from workers import read_config, update_value
from socket import socket, AF_INET, SOCK_STREAM


class PMonConfig(object):
    def __init__(self):
        self.siebel_data_types = ('comp', 'session')
        self.srvrmgr_cmd = None

    @property
    def log_dir(self):
        ms = read_config('settings.ini')
        return ms['log']['log_dir']

    @property
    def log_max_count(self):
        ms = read_config('settings.ini')
        return ms['log']['max_log_count']

    @property
    def log_max_size(self):
        ms = read_config('settings.ini')
        return ms['log']['max_size']

    @property
    def netmgr_host(self):
        ms = read_config('settings.ini')
        return ms['netmgr']['host']

    @property
    def netmgr_port(self):
        ms = read_config('settings.ini')
        port = int(ms['netmgr']['port'])
        if port == 0:
            sock = socket(AF_INET, SOCK_STREAM)
            sock.bind((self.netmgr_host, port))
            port = sock.getsockname()[1]
            sock.close()
            self.netmgr_port = port
        return port

    @netmgr_port.setter
    def netmgr_port(self, value):
        update_value('settings.ini', 'netmgr', 'port', value)

    def get_srvrmgr_cmd(self, target=None):
        targets_settings = read_config('targets.ini')
        ms = read_config('settings.ini')
        if target:
            return ms['srvrmgr_' + targets_settings[target]['sieb_ver']]['cmd']
        else:
            return {k: ms['srvrmgr_' + v['sieb_ver']]['cmd'] for (k, v) in targets_settings.items()}

    #   Targets settings
    @property
    def target_list(self):
        tl = read_config('targets.ini')
        return tl.keys() if tl else None

    @property
    def asm_target_list(self):
        return tuple([t for t, v in read_config('targets.ini').items() if v['start_mode'].lower() == 'auto'])

    @property
    def asm_target_count(self):
        return len(self.asm_target_list)

    #   Storages settings
    @property
    def storage_list(self):
        sl = read_config('storages.ini')
        return sl.keys() if sl else None

    # def get_storage(self, storage_name):
    #     _storage_mgr = StorageManager()
    #     _storage_mgr.start()
    #     return _storage_mgr.Storage(storage_name)
