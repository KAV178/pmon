# -*- coding: utf-8 -*-
from __future__ import print_function
from sys import argv, exit
from argparse import ArgumentParser
from multiprocessing.managers import BaseManager
from multiprocessing.pool import ThreadPool
from re import match, findall
from socket import error as socket_err
from time import sleep

from pm_netmgr_srv import COMMANDS
from system.config_worker.main import PMonConfig

__author__ = 'Kostreno A.V.'


class PMonNetMgrCli(object):
    def __init__(self, args):
        p_args = self.__parse_args(args)
        cfg_data = PMonConfig()
        if not any((v for k, v in vars(p_args).items() if k.startswith('netmgr_'))):
            for a in ((k for k in vars(p_args).keys() if k.startswith('netmgr_'))):
                if not vars(p_args)[a]:
                    p_args.__setattr__(a, cfg_data.__getattribute__(a))
        self.conn = BaseManager(address=(p_args.netmgr_host, p_args.netmgr_port), authkey='2.2')
        for c in COMMANDS.keys():
            self.conn.register(typeid=c)
        print('Trying to connect with {hp.netmgr_host}:{hp.netmgr_port} ... '.format(hp=p_args), end='')
        try:
            self.conn.connect()
            print("OK")
        except socket_err as e:
            print("Fail\n\n{0}\n".format(e))
            exit(0)

    def __parse_args(self, args):
        parser = ArgumentParser(add_help=True, version='Client for PMon version 2.2')
        parser.add_argument('-s', '--srv', type=str, default=None, dest='netmgr_host',
                            help='hostname or ip address with running pmon service')
        parser.add_argument('-p', '--port', type=int, default=None, dest='netmgr_port',
                            help='port for connecting to pmon service')

        return parser.parse_args(args)

    def run(self):
        def req_processing():
            return self.conn.__getattribute__(parsed_req[0])(parsed_req[1:])

        while True:
            in_cmd = raw_input('pmon_mgr> ').strip()
            if len(in_cmd):
                if in_cmd.lower() not in ('exit', 'quit'):
                    t_pool = ThreadPool(processes=1)
                    req_res = None
                    parsed_req = tuple(in_cmd.split())
                    if parsed_req[0] in self.conn._registry.keys():
                        try:
                            _tr = t_pool.apply_async(func=req_processing, args=())
                            while not _tr.ready():
                                sleep(0.5)
                                print(".", end="")
                            req_res = _tr.get().decode('utf-8')
                        except Exception as e:
                            print(e)
                        print("\n{0}\n".format(req_res))
                    else:
                        print("Unknown command \"{0}\". Use help for get list of available commands.".format(parsed_req[0]))
                        continue
                    if len(findall(r'no active monitoring processes left\.', req_res)):
                        print("Exiting...")
                        break
                else:
                    print("Exiting...")
                    break
        exit(0)


if __name__ == '__main__':
    cli = PMonNetMgrCli(argv[1:])
    cli.run()
