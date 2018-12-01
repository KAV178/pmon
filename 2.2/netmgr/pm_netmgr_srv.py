# -*- coding: utf-8 -*-
__author__ = 'Kostreno A.V.'

from multiprocessing.managers import BaseManager
from system.logger.pm_logger import PMonLogger
from os.path import join as os_pjoin, abspath
from time import sleep

COMMANDS = {'help': (('help', 'shows full help messgae'),
                     ('help <command>', 'shows help message for selected command')),
            'status': (('status', 'show status for all targets'),
                       ('status for <target_name>', 'show status for selected target')),
            'start': (('start all', 'starting monitring for all tagets'),
                      ('start <target_name>', 'staring monitoring for selected target')),
            'stop': (('stop all', 'stop monitoring for all targets'),
                     ('stop <target_name>', 'stop monitoring for selected target')),
            'list': (('list data_types', 'shows list of available data types for monitoring'),
                     ('list targets', 'shows list of available targets'),
                     ('list storages', 'shows list of available storages'),
                     ('list parameters for target <target_name|target list separated whitespaces>',
                      'shows list of parameters for selected target'),
                     ('list parameters for storage <storage_name>', 'shows list of parameters for selected storage'),
                     ),
            'set': (('set parameter <param_name>=<param_value> for target <target_name>',
                     'sets parameter values for selected target'),
                    ('set parameter <param_name>=<param_value> for storage <storage_name>',
                     'sets parameter values for selected storage'),
                    )}


class PMonNetMgrSrv(BaseManager):
    _server_object = None

    def __init__(self, settings, cmd_pool, busy_flag):
        BaseManager.__init__(self, address=(settings.netmgr_host, settings.netmgr_port), authkey='2.2')
        self.busy_flag = busy_flag

        self.logger = PMonLogger(name='netmgr', log_file=os_pjoin(settings.wrk_dir, settings.log_dir, 'netmgr.log'),
                                 max_log_size=settings.log_max_size, max_log_count=settings.log_max_count,
                                 debug=False if set(dir(settings)).isdisjoint(set('debug')) else settings.debug)

        self.stop_valve = False
        self.cmd_pool = cmd_pool

        for c in COMMANDS.keys():
            cf = None
            try:
                cf = self.__getattribute__('__pm_{0}__'.format(c))
            except AttributeError:
                self.logger.warning("The function for command \"{0}\" is not found!")
            if cf:
                self.register(typeid=c, callable=cf)

        self.start_server()

    def __del__(self):
        self.stop_valve = True

    def stop_server(self):
        self._server_object.stop_event.set()

    def start_server(self):
        self.logger.info('PMon net manager listening at {sd[0]}:{sd[1]}'.format(sd=self.address))
        self._server_object = self.get_server()
        self._server_object.serve_forever()

    def get_format_errmsg(self, command, args):
        return "[ERR] Wrong command format: {0}\n\n{1}".format("%s %s" % (command, " ".join(args)),
                                                               self.__pm_help__((command,)))

    @staticmethod
    def __pm_help__(args):
        max_cmd = max_msg = 0
        c_lst = COMMANDS.keys() if not len(args) else [c for c in COMMANDS.keys() if c == args[0]]
        for c in c_lst:
            for hc, hm in COMMANDS[c]:
                max_cmd = len(hc) if len(hc) > max_cmd else max_cmd
                max_msg = len(hm) if len(hm) > max_msg else max_msg
        max_cmd += 2
        max_msg += 2
        help_template = '{cmd:<' + str(max_cmd) + '} - {msg:<' + str(max_msg) + '}\n'
        help_msg = ""
        for c in c_lst:
            help_msg += 'Command \"{0}\":\n{1}\n'.format(c, "-" * 20)
            for hc, hm in COMMANDS[c]:
                help_msg += help_template.format(cmd=hc, msg=hm)
            help_msg += '\n'

        return help_msg

    def req(self, req_data, *args):
        mark = 'netmgr_{0}'.format(req_data)
        self.cmd_pool[mark + '_req'] = args if len(args) else None
        resp = None
        while not resp:
            sleep(0.2)
            resp = self.cmd_pool.pop(mark + '_resp', None)
        return resp

    def __pm_status__(self, args):
        recv_data = self.req('status', args)

        f_len = {'name': recv_data[1] + 4, 'state': 11, 'pid': 8, 'sm': 12}
        f_lst = ('name', 'state', 'pid', 'sm')
        h_line = '+'.join('{line:-^' + str(f_len[i]) + '}' for i in f_lst).format(line='-') + '\n'
        d_line_template = '|'.join(
            '{name:<' + str(f_len[i]) + '}' if i == 'name' else '{data[' + str(f_lst.index(i) - 1) +
                                                                ']:^' + str(f_len[i]) + '}'
            for i in f_lst) + '\n'

        res_data = ('PMon is running with PID: {pmon_pid}\nTargets:\n{line}'
                    '{ht_name:^' + str(f_len['name']) + '}|{ht_state:^' + str(f_len['state']) + '}|{ht_pid:^' +
                    str(f_len['pid']) + '}|{ht_sm:^' + str(f_len['sm']) + '}\n{line}'). \
            format(pmon_pid=recv_data[0], ht_name='Name', ht_state='State', ht_pid='PID', ht_sm='Start mode',
                   line=h_line)

        for t, d in recv_data[2].items():
            res_data += d_line_template.format(name=t, data=d)
        return res_data + h_line

    def __pm_list__(self, args):
        list_result = ''
        if len(args) > 0:
            if args[0] in ('param', 'params', 'parameters'):
                # validating
                err_str = ''
                try:
                    if 'for' not in args:
                        err_str += ' ?<for>'
                    if args[2] not in ('target', 'storage'):
                        err_str += ' ?<target or storage>'
                    if not len(args[3:]):
                        err_str += ' ?<target list separated whitespaces>'
                except IndexError:
                    return self.get_format_errmsg('list', args)

                if len(err_str):
                    list_result = "[ERR] Wrong command format: list {0}{1}{2}". \
                        format(args[0], '' if err_str.__contains__('<for>') else ' for', err_str)
                else:
                    for obj in args[3:]:
                        recv_data = self.req('list_obj_parameters', args[2], obj)
                        if not isinstance(recv_data, dict):
                            list_result = recv_data
                            break
                        else:
                            tmp = '{obj_type}: {obj_name}\n{pn_line}+{pv_line}\n'
                            pn_width = pv_width = 0
                            for k, v in recv_data.items():
                                if len(str(k)) > pn_width:
                                    pn_width = len(str(k))
                                v_len = len(str(v)) + str(v).count('\\')
                                if v_len > pv_width:
                                    pv_width = v_len
                            else:
                                pn_width += 3
                                pv_width += 3
                                p_template = '{p[0]:<' + str(pn_width) + 's}| {p[1]:<' + str(pv_width) + '}\n'

                            for p in sorted(recv_data.items()):
                                tmp += p_template.format(p=p)
                            tmp += '{pn_line}+{pv_line}\n'

                            list_result += tmp.format(obj_type=args[2].capitalize(),
                                                      obj_name=obj, pn_line="-" * pn_width,
                                                      pv_line='-' * pv_width) + '\n'

            elif args[0] in ('targets', 'storages', 'data_types'):
                list_result = "\n - ".join(self.req('list_{0}'.format(args[0])))
                if 'FAIL ' not in list_result:
                    list_result = "Available {0}:\n - {1}".format(args[0][:-1], list_result)
            else:
                list_result = self.get_format_errmsg('list', args)
        else:
            list_result = self.__pm_help__(('list',))
        return list_result

    def __pm_set__(self, args):
        set_result = None
        if len(args) > 0:
            if args[0] in ('param', 'parameter'):
                set_result = 'Setting {0} parameter \"{1}\":\n'.format(args[3], args[1].partition('=')[0])
                for obj in args[4:]:
                    if '=' in args[1]:
                        recv_data = self.req('set_obj_parameter', args[3], obj, args[1])
                        set_result += '\t{0}\n'.format(recv_data)
                    else:
                        return self.get_format_errmsg('set', args)
            else:
                return self.get_format_errmsg('set', args)
        else:
            set_result = self.__pm_help__(('set',))
        return set_result

    def __target_name_valid(self, names, trg_set):
        a_set = set(names)
        if a_set <= trg_set:
            return True, None
        else:
            unknown_names = a_set - trg_set
            return False, "Unknown target name{0}: {1}\nTry \"list targets\" for receiving actual list". \
                format('s' if len(unknown_names) > 1 else '', ', '.join(unknown_names))

    def __pm_start__(self, args):
        a_count = len(args)
        if a_count:
            if a_count == 1 and args[0].lower() == 'all':
                args = tuple(self.req('list_targets'))
            t_state = self.req('status', args)[2]
            t_valid = self.__target_name_valid(args, set(t_state.keys()))
            if t_valid[0]:
                res_lst = []
                for t in args:
                    if not t_state[t][1]:
                        res_lst.append(self.req('start', t))
                    else:
                        res_lst.append("{0} already running with PID {1}.".format(t, t_state[t][1]))
                return "\n".join(res_lst)
            else:
                return t_valid[1]
        else:
            return self.__pm_help__(('start',))

    def __pm_stop__(self, args):
        a_count = len(args)
        if a_count:
            if a_count == 1 and args[0].lower() == 'all':
                args = tuple(self.req('list_targets'))
            t_state = self.req('status', args)[2]
            t_valid = self.__target_name_valid(args, set(t_state.keys()))
            if t_valid[0]:
                self.busy_flag.set()
                res_lst = []
                for t in args:
                    if t_state[t][1]:
                        res_lst.append(self.req('stop', t))
                    else:
                        res_lst.append(("\"{0}\" already stopped.".format(t), None))
                # FIXME: Already stopped
                if not all({s[1] for s in res_lst}):
                    res_lst.append(("\n[!] PMon is stopped because there are no active monitoring processes left.",))
                self.busy_flag.clear()
                return "\n".join((m[0] for m in res_lst))
            else:
                return t_valid[1]
        else:
            return self.__pm_help__(('stop',))
