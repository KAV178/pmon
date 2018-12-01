# -*- coding: utf-8 -*-
from sys import argv
from netmgr.pm_netmgr_cli import PMonNetMgrCli

__author__ = 'Kostreno A.V.'

if __name__ == '__main__':
    cli = PMonNetMgrCli(argv[1:])
    cli.run()
