# -*- coding: utf-8 -*-
from __future__ import print_function
from argparse import ArgumentParser
from atexit import register as atexit_reg
from multiprocessing import Process, Manager

from os import chdir, dup2, getpid, kill, remove, umask, _exit
from os.path import join as path_join, exists as path_exists, abspath, dirname
from platform import system
from signal import SIGTERM
from sys import argv as sys_argv, exit, stderr, stdout, stdin
from time import sleep
from siebel_collector.scollector import SiebelCollector
from siebel_collector.sender import Sender
from system.config_worker.target import Target
from system.config_worker.storage import Storage
from system.logger.pm_logger import PMonLogger
from system.pm_managers import PMConfManager
from netmgr.pm_netmgr_srv import PMonNetMgrSrv

if system() != 'Windows':
    from os import fork, setsid

__author__ = "Kostrenko A.V. <kostrenko.av@gmail.com>"
__status__ = "beta"
__version__ = "2.2"

sc_settings = None
mon_log = None
proc_pool = dict()


class ProcRunner(object):
    __slots__ = ['stend', 'settings', 'logger', 'main_settings', 'data_types', 'p_states']

    def __init__(self, stend_name, main_settings, data_types, p_states):
        self.data_types = data_types
        self.settings = main_settings
        self.stend = Target(name=stend_name)
        self.p_states = p_states
        self.logger = PMonLogger(name=stend_name,
                                 log_file=path_join(self.settings.wrk_dir, self.settings.log_dir,
                                                    "{0}_collector.log".format(stend_name)),
                                 max_log_size=self.settings.log_max_size,
                                 max_log_count=self.settings.log_max_count,
                                 debug=self.debug)

        self.run_sc()

    @property
    def debug(self):
        return self.settings.debug if 'debug' in [a for a in dir(self.settings) if not a.startswith('__')] else False

    @debug.setter
    def debug(self, value):
        if isinstance(value, bool):
            self.settings.__setattr__('debug', value)
        else:
            self.logger.warning('Wrong value type \'{0}\' must be boolean'.format(type(value)))

    def sc_worker(self):
        self.logger.info("Starting collection data from stend: {STEND}".format(STEND=self.stend.name))
        obj = SiebelCollector(target=self.stend, logger=self.logger, main_settings=self.settings,
                              data_types=self.data_types,
                              sender=Sender(storage=Storage(name=self.stend.storage),
                                            logger=PMonLogger(name=self.stend.name,
                                                              log_file=path_join(self.settings.wrk_dir,
                                                                                 self.settings.log_dir,
                                                                                 "{0}_sender.log".
                                                                                 format(self.stend.name)),
                                                              max_log_size=self.settings.log_max_size,
                                                              max_log_count=self.settings.log_max_count,
                                                              debug=self.debug)
                                            )
                              )
        obj.start_collect()

    def run_sc(self):
        while self.p_states['keep_running']:
            self.p_states['sleeping'] = False
            self.sc_worker()

            if self.p_states['keep_running']:
                if self.stend.request_timeout < 60:
                    self.logger.warning("Request timeout must be greather 60 sec. Current value {0} changed to 60 sec.".
                                        format(self.stend.request_timeout))
                    self.stend.request_timeout = 60

            self.logger.info("Waiting for next iteration {0} sec...".format(self.stend.request_timeout))
            self.p_states['sleeping'] = True
            sleep(float(self.stend.request_timeout))
        else:
            self.logger.info("Process stopped by request.")


class Monitor(object):
    __slots__ = ['pidfile_name', 'stdin', 'stdout', 'stderr', 'args', 'proc_start_func']
    global WORK_DIR
    global sc_settings
    global mon_log

    def __init__(self, args, proc_start_func, stdin_=None, stdout_=None, stderr_=None):
        self.pidfile_name = "%s.pid" % abspath(sys_argv[0]).partition(".py")[0]

        self.stdin = stdin_ if stdin_ else '/dev/null'
        if args.daemon:
            self.stdout = path_join(sc_settings.wrk_dir, sc_settings.log_dir, 'dstdout.log')
            self.stderr = path_join(sc_settings.wrk_dir, sc_settings.log_dir, 'dstderr.log')
        else:
            self.stdout = stdout_ if stdout_ else '/dev/null'
            self.stderr = stderr_ if stderr_ else '/dev/null'

        self.args = args
        sc_settings.__setattr__('debug', args.debug)
        self.proc_start_func = proc_start_func

    @property
    def pid_file(self):
        try:
            with open(self.pidfile_name, 'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None
        return pid

    @pid_file.setter
    def pid_file(self, new_pid):
        with open(self.pidfile_name, 'w+') as pf:
            pf.write("{0}\n".format(new_pid))

    def del_pid(self):
        remove(self.pidfile_name)

    def daemonize(self):
        try:
            pid = fork()
            if pid > 0:
                _exit(0)
        except OSError as e:
            stderr.write("fork #1 failed: %d (%s)\n" % (e.errno, e.strerror))
            _exit(1)

        chdir("/")
        setsid()
        umask(0)

        # делаем второй fork
        try:
            pid = fork()
            if pid > 0:
                _exit(0)
        except OSError as e:
            stderr.write("fork #2 failed: %d (%s)\n" % (e.errno, e.strerror))
            _exit(1)

        # перенаправление стдн ввода/вывода
        stdout.flush()
        stderr.flush()
        si = open(self.stdin, 'r')
        so = open(self.stdout, 'a+')
        se = open(self.stderr, 'a+')
        dup2(si.fileno(), stdin.fileno())
        dup2(so.fileno(), stdout.fileno())
        dup2(se.fileno(), stderr.fileno())

        atexit_reg(self.del_pid)
        self.pid_file = getpid()

    def mon_start(self):
        # Checking pidfile, for existing process
        if self.pid_file:
            stderr.write("pidfile {0} already exist. Daemon already running?\n".format(self.pidfile_name))
            exit(1)

        if self.args.daemon:
            if system() != 'Windows':
                mon_log.info("Run as daemon.")
                self.daemonize()
            else:
                msg = "Running in daemon mode is not allowed on Windows!"
                mon_log.warning(msg)
                print(msg)
        self.run()

    def mon_stop(self):
        # Getting pid from pidfile
        pid = self.pid_file
        if not pid:
            stderr.write("pidfile {0} does not exist. Daemon not running?\n".format(self.pidfile_name))
            return  # not error on restart

        # Kill daemon process
        try:
            while 1:
                kill(pid, SIGTERM)
                sleep(0.1)
        except OSError as err:
            err = str(err)
            if err.find("No such process") > 0:
                if path_exists(self.pidfile_name):
                    remove(self.pidfile_name)
            else:
                print(str(err))
                exit(1)

    def mon_restart(self):
        self.mon_stop()
        self.mon_start()

    def mon_status(self):
        if self.pid_file:
            try:
                with open(path_join('/proc', str(self.pid_file), 'cmdline'), 'r') as pf:
                    cmd = " ".join(filter(len, pf.read().split("\x00")))
            except IOError:
                cmd = "UNKNOWN"
            t_msg = "\nState: Script is running.\n\n{sep}\nPID: {pid}\nCMD: {cmd}\n"
            print(t_msg.format(sep="-" * 15, pid=self.pid_file, cmd=cmd))

        else:
            print("\nState: Script is stopped!\n")

    def run(self):
        global proc_pool
        target = None
        net_mgr_busy = None
        siebel_data_types = set()
        cmd_pool = Manager().dict()

        if any(vars(self.args)):
            if self.args.trg_list:
                show_target_list()
                self.mon_stop()
            elif self.args.dt_list:
                show_siebel_data_types()
                self.mon_stop()
            else:
                if self.args.target:
                    if self.args.target in sc_settings.target_list:
                        target = self.args.target
                    else:
                        print("!!! ERROR !!! Invalid name of target = \"{0}\"".format(sys_argv.target))
                        show_target_list()
                        self.mon_stop()

                if self.args.dtype:
                    dt_set = set(self.args.dtype.split(','))
                    err_dt = dt_set - set(sc_settings.siebel_data_types)
                    if len(err_dt):
                        print(
                            "!!! ERROR !!! Invalid value for siebel data type flag = \"{0}\"".format(",".join(err_dt)))
                        show_siebel_data_types()
                        self.mon_stop()
                    else:
                        siebel_data_types |= dt_set

                print("Preparing and starting threads...")
                print("Starting netmgr... ", end='')
                net_mgr_busy = Manager().Event()
                net_mgr_proc = Process(target=PMonNetMgrSrv, kwargs={'settings': sc_settings, 'cmd_pool': cmd_pool,
                                                                     'busy_flag': net_mgr_busy})

                net_mgr_proc.daemon = True
                net_mgr_proc.start()
                print("OK")

                if target:
                    mon_log.info("Selected target \"{0}\"".format(target))
                else:
                    mon_log.info("No target spesified. Run for all with auto start mode {0}".
                                 format(sc_settings.asm_target_list))
                for stend_name in (target,) if target else sc_settings.asm_target_list:
                    self.proc_start_func(stend_name, siebel_data_types)

            while len(proc_pool) > 0:
                check_procs()
                sleep(1)
                netmgr_reqs = [k for k in cmd_pool.keys() if k.startswith('netmgr_')]
                for r in netmgr_reqs:
                    mark = r.rpartition('_req')[0]
                    func = globals().get('__{0}'.format(mark.partition('netmgr_')[2]), None)
                    args = cmd_pool.pop(r)
                    if func:
                        if args:
                            cmd_pool[mark + '_resp'] = func(*args)
                        else:
                            cmd_pool[mark + '_resp'] = func()
                    else:
                        cmd_pool[r] = "FAIL on processing request \'{0}\'.\nFunction not found!".format(r)
            mon_log.info("All processes finished. Monitoring stopped.")
            while net_mgr_busy.is_set():
                sleep(1)
            self.mon_stop()


def __status(args=()):
    """
    :param args: tuple of target names fo processing, or nothing
    :return: tuple(PID this process, max length of target name, data aboun targets states)
    """

    def get_target_data(t_name):
        t_proc, t_sf = proc_pool.get(t_name, dict.fromkeys((range(2)))).values()
        if t_proc:
            return 'running', t_proc.pid, Target(name=t_name).start_mode,
        else:
            return 'stopped', None, Target(name=t_name).start_mode,

    t_data = dict()
    t_name_len = 0
    for t in set(args) - {'for'} if len(args) > 1 else sc_settings.target_list:
        if len(t) > t_name_len:
            t_name_len = len(t)
        t_data[t] = get_target_data(t)
    return getpid(), t_name_len, t_data


def __start(target, data_types=None):
    p_states = Manager().dict(keep_running=True, sleeping=False)
    proc_pool[target] = {'p': Process(target=ProcRunner, name="{0}_proc".format(target),
                                      kwargs={'stend_name': target,
                                              'data_types': data_types,
                                              'main_settings': sc_settings,
                                              'p_states': p_states}
                                      ),
                         'p_states': p_states}
    proc_pool[target]['p'].start()
    msg = "\"{0}\" started with PID {1}".format(target, proc_pool[target]['p'].pid)
    mon_log.info(msg)
    return msg


def __stop(target):
    t_proc, t_states = proc_pool.get(target, dict.fromkeys((range(2)))).values()
    if t_proc:
        mon_log.info("Stop the process \"{0}\" is initialized...".format(t_proc.pid))
        t_states['keep_running'] = False
        if t_states['sleeping']:
            t_proc.terminate()
        while t_proc.is_alive():
            sleep(1)
            mon_log.info("Stop the process \"{0}\": waiting for stop".format(t_proc.pid))
        msg = "\"{0}\" sucessfully stopped.".format(target)
    else:
        msg = "\"{0}\" already stopped.".format(target)

    check_procs()
    mon_log.info(msg)

    return msg, len(proc_pool)


def __list_targets():
    return sc_settings.target_list


def __list_storages():
    return sc_settings.storage_list


def __list_data_types():
    return sc_settings.siebel_data_types


def __list_obj_parameters(obj_type, obj_name):
    """
    :param obj_type: target or storage
    :param obj_name:
    :return: dictionary with target parameters or None
    """
    try:
        obj_c = globals().get(obj_type.capitalize())(name=obj_name)
    except RuntimeError as e:
        return e.message
    lp = dict()
    for p in dir(obj_c):
        if all([not p.startswith('__'), p not in ('crd', 'name')]):
            lp[p] = obj_c.__getattribute__(p)
    return lp if len(lp) else None


def __set_obj_parameter(obj_type, obj_name, pv):
    """
    :param obj_type: object type, must be target or storage
    :param obj_name: object name
    :param pv: string of parameter name and value, f.e. request_timeout=4
    :return: string with result of execution
    """
    s_result = '{0}: '.format(obj_name)
    p, v = pv.split('=')
    try:
        obj_c = globals().get(obj_type.capitalize())(name=obj_name)
    except (RuntimeError, TypeError) as e:
        return s_result + 'FAIL -> {0}'.format(e.message)
    if p in dir(obj_c):
        old_v = obj_c.__getattribute__(p)
        try:
            obj_c.__setattr__(p, v)
        except RuntimeError as e:
            return s_result + 'FAIL -> {0}'.format(e)
        return s_result + 'SUCCESS {0} -> {1}'.format(old_v, v)
    else:
        return s_result + 'FAIL -> Target \"{0}\" has not parameter \"{1}\" '.format(obj_name, p)


def show_target_list():
    print("Available target names:\n - {0}".format("\n - ".join(__list_targets())))


def show_siebel_data_types():
    print("Available siebel data types:\n - {0}".format("\n - ".join(__list_data_types())))


def check_procs():
    for pn, pv in proc_pool.items():
        if not pv['p'].is_alive():
            mon_log.info("\"{0}\" PID: {1} finished.".format(pn, pv['p'].pid))
            del proc_pool[pn]


def __parse_args(args):
    parser = ArgumentParser(add_help=True, version='PMon version 2.2 (c) created by Andrey Kostrenko')
    parser.add_argument('-b, --daemon', dest='daemon', help='run as daemon', action='store_true')
    parser.add_argument('-d, --debug', dest='debug', help='enable debug mode', action='store_true')
    parser.add_argument('-t, --target', type=str, dest='target', metavar='<TARGET>',
                        help='processing a specific target. The name is taken from the file \"targets.ini\"')
    parser.add_argument('-s, --data_type', type=str, dest='dtype', nargs="+", metavar='<DTYPE>,<DTYPE>...',
                        help='processing of specific siebel data types ('
                             'comma-separated)')
    parser.add_argument('-T', '--list_targets', dest='trg_list', action='store_true',
                        help='print avalable target names')
    parser.add_argument('-S', '--data_types', dest='dt_list', action='store_true',
                        help='print avalable siebel data types')

    return parser.parse_args(args)


def main(argv):
    global sc_settings
    global mon_log
    cfg_mgr = PMConfManager()
    cfg_mgr.start()
    sc_settings = cfg_mgr.PMonConfig()
    sc_settings.__setattr__('wrk_dir', dirname(abspath(sys_argv[0])))

    mon_log = PMonLogger(name='main', log_file=path_join(sc_settings.wrk_dir, sc_settings.log_dir, 'monitor.log'),
                         max_log_size=sc_settings.log_max_size, max_log_count=sc_settings.log_max_count,
                         debug=False if set(dir(sc_settings)).isdisjoint(set('debug')) else sc_settings.debug)

    m = Monitor(args=argv, proc_start_func=__start)
    m.mon_start()


if __name__ == "__main__":
    main(__parse_args(sys_argv[1:]))
