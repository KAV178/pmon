################################################################
# version 2.1
################################################################
import sys

from system.config_worker import *
from system.logger import *


class SiebelCollector:
    def __init__(self):
        self.target_list = []
        self.targets_params = {}
        self.get_target_list()
        self.settings = read_config('siebel_collector/settings.ini')
        self.logfile = ''
        self.debugfile = ''
        self.logprefix = ''
        self.mls = ''
        self.dbg_lvl = ''
        self.sdata_cmd_list = {}
        self.set_data_req_cmd()
        if len(self.settings) > 0:
            self.logfile = self.settings['log']['log_file']
            self.mls = self.settings['log']['max_size']
        else:
            write_log('ERR: Error getting settings. The data collection is cancelled!', self.logfile, self.mls)

    def set_dbg_level(self, value):
        self.dbg_lvl = value

    def set_data_req_cmd(self, sdata_type=()):
        self.sdata_cmd_list = {}
        if ('comp' in sdata_type) or (len(sdata_type) == 0):
            self.sdata_cmd_list['comp'] = {'get_fields': ['SV_NAME', 'CC_ALIAS', 'CC_RUNMODE','CP_DISP_RUN_STATE', 'CP_STARTMODE',
                                                          'CP_NUM_RUN_TASKS', 'CP_MAX_TASKS', 'CP_ACTV_MTS_PROCS',
                                                          'CP_MAX_MTS_PROCS']}
            self.sdata_cmd_list['comp']['get_cmd'] = 'list comp show {0}'.format(
                ','.join(self.sdata_cmd_list['comp']['get_fields']))

        if ('session' in sdata_type) or (len(sdata_type) == 0):
            self.sdata_cmd_list['session'] = {'get_fields': ['SV_NAME', 'CC_ALIAS', 'TK_DISP_RUNSTATE']}
            self.sdata_cmd_list['session']['get_cmd'] = 'list session show {0}'.format(
                ','.join(self.sdata_cmd_list['session']['get_fields']))

    def get_target_list(self):
        self.targets_params = read_config('siebel_collector/targets.ini')
        if len(self.targets_params) > 0:
            self.target_list = self.targets_params.keys()

    def reset_log_filename(self, target):
        if len(self.settings) > 0:
            import datetime
            self.logfile = self.settings['log']['log_dir'] + '/' + target + '_' + self.settings['log']['log_file']
            if self.dbg_lvl in ('COL', 'ALL', 'SND'):
                self.debugfile = self.settings['log']['log_dir'] + '/' + target + '_debug_' + self.dbg_lvl + '_' + \
                                 datetime.datetime.now().strftime("%Y%m%d%H%M") + '.log'
        else:
            write_log('ERR: Error getting settings. The data collection is cancelled!', self.logfile, self.mls)

    def clean_received_data(self, b_mark, dirt_data):
        import re
        result = []
        step = 0
        header_height = 4
        footer_height = 4
        for line in dirt_data:
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: clean_received_data: line = {0}'.format(line.rstrip()),
                          self.debugfile, self.mls)
            if line.find(b_mark) > -1 or (0 < step < header_height):
                step += 1
                continue
            if step == header_height and dirt_data.index(line) < len(dirt_data) - footer_height:
                line = line.rstrip()
                if self.dbg_lvl in ('COL', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: clean_received_data: line.rstrip() = {0}'.format(line),
                              self.debugfile, self.mls)
                    write_log(self.logprefix + 'DEBUG: clean_received_data: len(line) = {0}'.format(len(line)),
                              self.debugfile, self.mls)
                if len(line) > 0:
                    for fix_word in ['Partially Offline', 'Not Online']:
                        line = line.replace(fix_word, fix_word.replace(' ', '_'))
                    line = re.sub(r'\s+', ';', line).rstrip().split(';')

                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: clean_received_data: result.append({0})'.format(line),
                                  self.debugfile, self.mls)
                    result.append(line)
        return result

    def get_data_from_srvrmgr(self, target_name, srvr_cmd):
        import os
        import subprocess
        import platform
        key_sym = '-'
        if platform.system() == 'Windows':
            key_sym = '/'
        if self.dbg_lvl in ('COL', 'ALL'):
            write_log(self.logprefix + 'DEBUG: get_data_from_srvrmgr: platform = \'{OS_NAME}\' using \'{KS}\' as '
                                       'key_sym'.format(OS_NAME=platform.system(), KS=key_sym), self.debugfile,
                      self.mls)
        procs = ''
        try:
            # TODO Modify composition do_cmd string for usinf "".format()
            do_cmd = self.settings['srvrmgr_' + self.targets_params[target_name]['sieb_ver']][
                         'cmd'] + ' ' + key_sym + 'g ' + \
                     self.targets_params[target_name]['gw_name'] + \
                     ' ' + key_sym + 'e ' + self.targets_params[target_name]['ent_name'] + \
                     ' ' + key_sym + 'u ' + self.targets_params[target_name]['crd'].decode('base64').split()[0] + \
                     ' ' + key_sym + 'p ' + self.targets_params[target_name]['crd'].decode('base64').split()[1] + \
                     ' ' + key_sym + 'c "' + srvr_cmd + '"'
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: get_data_from_srvrmgr: do_cmd = {0}'.format(
                    do_cmd.replace(self.targets_params[target_name]['crd'].decode('base64').split()[1], '*****')),
                          self.debugfile, self.mls)
            procs = subprocess.Popen(do_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=True, cwd=os.getcwd())
        except StandardError, e:
            write_log(self.logprefix + 'Fail - ERR: Error on receive data over srvrmgr! [{0}]'.format(str(e)),
                      self.logfile, self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: get_data_from_srvrmgr: Fail - ERR: Error on receive data over '
                                           'srvrmgr! [{0}]'.format(str(e)), self.debugfile, self.mls)
        result = procs.stdout.readlines()
        err_res = procs.stderr.readlines()
        if len(err_res) > 0:
            write_log(self.logprefix + 'Fail - ERR: Error on receive data over srvrmgr! [{0}]'.format(
                ':|: '.join(err_res).rstrip()), self.logfile, self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: get_data_from_srvrmgr: {0}'.format(':|: '.join(err_res).rstrip()),
                          self.debugfile, self.mls)
            sys.exit()

        if self.dbg_lvl in ('COL', 'ALL'):
            write_log(self.logprefix + 'DEBUG: get_data_from_srvrmgr: result has {0} lines.'.format(str(len(result))),
                      self.debugfile, self.mls)
        return result

    def get_servers(self, target):
        result = []
        servers_cmd_fields = ['SBLSRVR_NAME', 'SBLSRVR_STATE']
        servers_cmd = 'list servers show ' + ",".join(servers_cmd_fields)
        if self.dbg_lvl in ('COL', 'ALL'):
            write_log(
                self.logprefix + 'DEBUG: get_servers: req_out = self.get_data_from_srvrmgr(\'{TRG}\', \'{S_CMD}\')'
                                 ''.format(TRG=target, S_CMD=servers_cmd), self.debugfile, self.mls)
        req_out = self.get_data_from_srvrmgr(target, servers_cmd)
        if self.dbg_lvl in ('COL', 'ALL'):
            write_log(self.logprefix + 'DEBUG: get_servers: OK', self.debugfile, self.mls)
        if len(req_out) > 0:
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(
                    self.logprefix + 'DEBUG: get_servers: crd = self.clean_received_data(\'{S_CMD}\', {{{L_CNT} lines}}'
                                     ''.format(S_CMD=servers_cmd, L_CNT=len(req_out[0])), self.debugfile, self.mls)
            crd = self.clean_received_data(servers_cmd, req_out)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: get_servers: OK', self.debugfile, self.mls)
            for line in crd:
                if self.dbg_lvl in ('COL', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: get_servers: line = [{0}]'.format(';'.join(line)),
                              self.debugfile, self.mls)
                if len(line) > 1:
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: get_servers: result.append(' + line[0] + ')',
                                  self.debugfile, self.mls)
                    result.append(line[0])
        else:
            write_log(self.logprefix + 'ERR: No data for load.', self.logfile, self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: get_servers: ERR: No data for load.', self.debugfile, self.mls)
        return result

    def collect_data(self, target_name):
        self.logprefix = 'Collect data for {0}: '.format(target_name)
        write_log(self.logprefix + 'begin', self.logfile, self.mls)
        if self.targets_params[target_name]['active'] in ['Yes', 'yes', 'true', 'True', '1']:
            active_servers = self.get_servers(target_name)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: collect_data: active_servers = [{0}]'.format(
                    '; '.join(active_servers)), self.debugfile, self.mls)
            if len(active_servers) > 0:
                from re import findall, sub
                res_data = {}
                for sdt in self.sdata_cmd_list.keys():
                    if len(findall('\[[a-zA-Z0-9]+]', self.logprefix)) == 0:
                        self.logprefix += '[{0}] '.format(sdt)
                    else:
                        self.logprefix = sub('\[[a-zA-Z0-9]+]', '[{0}]'.format(sdt), self.logprefix)
                    c_data = []
                    comps_cmd = self.sdata_cmd_list[sdt]['get_cmd']
                    comps_cmd_fields = self.sdata_cmd_list[sdt]['get_fields']

                    try:
                        if self.dbg_lvl in ('COL', 'ALL'):
                            write_log(self.logprefix + 'DEBUG: collect_data: req_out = self.get_data_from_srvrmgr({TRG}'
                                                       ', {C_CMD})'.format(TRG=target_name, C_CMD=comps_cmd),
                                      self.debugfile, self.mls)
                        req_out = self.get_data_from_srvrmgr(target_name, comps_cmd)
                        if self.dbg_lvl in ('COL', 'ALL'):
                            write_log(self.logprefix + 'DEBUG: collect_data: OK', self.debugfile, self.mls)
                            write_log(self.logprefix + 'DEBUG: collect_data: len(req_out) = {0}'.format(len(req_out)),
                                      self.debugfile, self.mls)
                        if len(req_out) > 0:
                            write_log(
                                self.logprefix + 'Received {0} lines. Preparing received data...'.format(len(req_out)),
                                self.logfile, self.mls)
                            if self.dbg_lvl in ('COL', 'ALL'):
                                write_log(
                                    self.logprefix + 'DEBUG: collect_data: crd = self.clean_received_data({C_CMD}, '
                                                     '{{req_out({REQ_LEN} lines)}})'.format(C_CMD=comps_cmd,
                                                                                          REQ_LEN=len(req_out)),
                                    self.debugfile, self.mls)
                            crd = self.clean_received_data(comps_cmd, req_out)
                            if self.dbg_lvl in ('COL', 'ALL'):
                                write_log(self.logprefix + 'DEBUG: collect_data: OK', self.debugfile, self.mls)
                            for cl_line in crd:
                                if self.dbg_lvl in ('COL', 'ALL'):
                                    write_log(self.logprefix + 'DEBUG: collect_data: cl_line = [{0}]'.format(
                                        ';'.join(cl_line)), self.debugfile, self.mls)
                                    write_log(self.logprefix + 'DEBUG: collect_data: {CL} in [{A_SRVS}]'.format(
                                        CL=cl_line[0], A_SRVS=', '.join(active_servers)), self.debugfile, self.mls)
                                if cl_line[0] in active_servers:
                                    if self.dbg_lvl in ('COL', 'ALL'):
                                        write_log(self.logprefix + 'DEBUG: collect_data: OK ', self.debugfile, self.mls)
                                        write_log(self.logprefix + 'DEBUG: collect_data: len(cl_line)-1 <= '
                                                                   'len(comps_cmd_fields) : {L_CL} <= {L_CF}'.format(
                                            L_CL=(len(cl_line) - 1), L_CF=len(comps_cmd_fields)), self.debugfile,
                                                  self.mls)
                                    if len(cl_line) - 1 <= len(comps_cmd_fields):
                                        if self.dbg_lvl in ('COL', 'ALL'):
                                            write_log(self.logprefix + 'DEBUG: collect_data: OK ', self.debugfile,
                                                      self.mls)
                                        res_line = {}
                                        for field in comps_cmd_fields:
                                            if self.dbg_lvl in ('COL', 'ALL'):
                                                write_log(self.logprefix + 'DEBUG: collect_data: comps_cmd_fields.index'
                                                                           '({F}) = {FD}'.format(
                                                    F=field, FD=comps_cmd_fields.index(field)), self.debugfile,
                                                          self.mls)
                                            try:
                                                if self.dbg_lvl in ('COL', 'ALL'):
                                                    write_log(
                                                        self.logprefix + 'DEBUG: collect_data: res_line[{F}] = '
                                                                         '{FD}'.format(F=field,
                                                                                       FD=cl_line[comps_cmd_fields.
                                                                                       index(field)]),
                                                        self.debugfile, self.mls)
                                                res_line[field] = cl_line[comps_cmd_fields.index(field)]
                                            except IndexError, e:
                                                if self.dbg_lvl in ('COL', 'ALL'):
                                                    write_log(self.logprefix + 'DEBUG: collect_data: res_line[{F}] '
                                                                               '= \'\' err: [{E}]'.format(F=field,
                                                                                                          E=e),
                                                              self.debugfile, self.mls)
                                                res_line[field] = ''
                                            except StandardError, e:
                                                write_log(self.logprefix + 'ERR: collect_data: res_line[{F}] err: {E}'.
                                                          format(F=field, E=e), self.logfile, self.mls)
                                                if self.dbg_lvl in ('COL', 'ALL'):
                                                    write_log(self.logprefix + 'DEBUG: collect_data: res_line[{F}] '
                                                                               'err: [{E}]'.format(F=field, E=e),
                                                              self.debugfile, self.mls)
                                            if self.dbg_lvl in ('COL', 'ALL'):
                                                write_log(self.logprefix + 'DEBUG: collect_data: c_data.append({0})'.
                                                          format(res_line), self.debugfile, self.mls)
                                        c_data.append(res_line)
                                    else:
                                        write_log(self.logprefix + 'Fail - ERR: Exceeded the number of fields in '
                                                                   'line "' + " ".join(cl_line) + '" Line Skipped!',
                                                  self.logfile, self.mls)
                                        if self.dbg_lvl in ('COL', 'ALL'):
                                            write_log(self.logprefix + 'DEBUG: collect_data: Fail - ERR: Exceeded the '
                                                                       'number of fields in line \"{0}\". Line '
                                                                       'Skipped!'.format(" ".join(cl_line)),
                                                      self.debugfile, self.mls)
                        else:
                            write_log(self.logprefix + 'ERR: No data for load.', self.logfile, self.mls)
                            if self.dbg_lvl in ('COL', 'ALL'):
                                write_log(self.logprefix + 'DEBUG: collect_data: ERR: No data for load.',
                                          self.debugfile, self.mls)
                        if len(c_data) > 0:
                            res_data[sdt] = c_data

                    # end try
                    except StandardError, e:
                        write_log(self.logprefix + 'Fail - ERR: Error on get data over srvrmgr. [{0}]'.format(e),
                                  self.logfile, self.mls)
                        if self.dbg_lvl in ('COL', 'ALL'):
                            write_log(self.logprefix + 'DEBUG: collect_data: Fail - ERR: Error on get data over '
                                                       'srvrmgr.', self.debugfile, self.mls)
                        #  sending data
                if len(res_data) == 0:
                    write_log(self.logprefix + 'Fail - ERR: No data except headers.', self.logfile, self.mls)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: Fail - ERR: No data except headers.',
                                  self.debugfile, self.mls)
                else:
                    self.logprefix = sub('\[[a-zA-Z0-9]+]\s', '', self.logprefix)
                    write_log(self.logprefix + 'Preparing received data... Success.', self.logfile, self.mls)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: self.send_data_to_store({TN}, {{{RD_LEN} '
                                                   'lines}}'.format(TN=target_name, RD_LEN=len(res_data)),
                                  self.debugfile, self.mls)
                    self.send_data_to_store(target_name, res_data)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: OK', self.debugfile, self.mls)
            else:
                write_log(self.logprefix + 'ERR: No active servers.', self.logfile)
                if self.dbg_lvl in ('COL', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: collect_data: ERR: No active servers.', self.debugfile, self.mls)
        else:
            write_log(self.logprefix + 'WARN: Target \"{0}\" marked as inactive. Skipped!'.format(target_name),
                      self.logfile, self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix + 'DEBUG: collect_data: WARN: Target \"{0}\" marked as inactive. '
                                           'Skipped!'.format(target_name), self.debugfile, self.mls)

    def send_data_to_store(self, target_name, data):
        store_params = read_config('siebel_collector/storages.ini')
        self.logprefix = 'Sending data {TN} in storage {ST}: '.format(TN=target_name,
                                                                      ST=self.targets_params[target_name]['store_name'])
        store_type = store_params[self.targets_params[target_name]['store_name']]['type']
        if self.dbg_lvl in ('SND', 'ALL'):
            write_log(self.logprefix + 'DEBUG: send_data_to_store: store_type = {0}'.format(store_type), self.debugfile,
                      self.mls)
        if store_type == 'http-grafana':
            url = store_params[self.targets_params[target_name]['store_name']]['conn_str']
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: send_data_to_store: url = {0}'.format(url), self.debugfile, self.mls)
            if len(url) > 0:
                try:
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: send_data_to_store: import module \'requests\'',
                                  self.debugfile, self.mls)
                    import requests
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: send_data_to_store: OK', self.debugfile, self.mls)
                except ImportError(requests), e:
                    write_log(
                        self.logprefix + 'ERR: ' + str(e), self.logfile, self.mls)
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: send_data_to_store: ERR: {0}'.format(e), self.debugfile,
                                  self.mls)
                    sys.exit('Error on import requests module')

                for sdt in data.keys():
                    write_log(self.logprefix + 'INF: [{0}] begin generate requests for sending data to '
                                               'storage'.format(sdt), self.logfile, self.mls)
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: [{0}] send_data_to_store: begin generate requests'
                                                   ' for sending data to storage'.format(sdt), self.debugfile,
                                  self.mls)
                    req_pool = self.gen_grafana_reqs(sdt, data[sdt])
                    write_log(self.logprefix + 'INF: [{0}] Generation requests for sending data to storage - '
                                               'complete.'.format(sdt), self.logfile, self.mls)
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: [{S}] send_data_to_store: generate requests for sending '
                                                   'data to storage complete. Generated {RC} reqests.'.format(
                            S=sdt, RC=len(req_pool)), self.debugfile, self.mls)
                    write_log(self.logprefix + 'INF: [{0}] Begin sending data to storage'.format(sdt), self.logfile,
                              self.mls)
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: [{0}] send_data_to_store: begin sending '
                                                   'requests'.format(sdt), self.debugfile, self.mls)
                    for req in req_pool:
                        if self.dbg_lvl in ('SND', 'ALL'):
                            write_log(
                                self.logprefix + 'DEBUG: [{S}] send_data_to_store request[{RN}]:'
                                                 '\n>>>----------- request [{RN}] body begin ---------->>>\n{RB}\n'
                                                 '<<<----------- request [{RN}] body end -------------<<<'.format(
                                    S=sdt, RN=req_pool.index(req), RB=req), self.debugfile, self.mls)
                        try:
                            response = requests.post(url, data=req)
                            if self.dbg_lvl in ('SND', 'ALL'):
                                write_log(self.logprefix + 'DEBUG: [{S}] send_data_to_store: Sending request[{R}] '
                                                           '- {RES}'.format(S=sdt, R=req_pool.index(req),
                                                                            RES=str(response.ok).replace('True', 'OK')),
                                          self.debugfile, self.mls)
                            if not response.ok:
                                write_log(self.logprefix + 'ERR: [{S}] on sending data [Reason: {R}; Text: '
                                                           '{T}]'.format(S=sdt, R=response.reason,
                                                                         T=response.text.rstrip('\t\n')),
                                          self.logfile, self.mls)
                                if self.dbg_lvl in ('SND', 'ALL'):
                                    write_log(self.logprefix + 'DEBUG: [{S}] send_data_to_store: ERR: on sending data '
                                                               '[Reason: {R}; Text: {T}]'.format(
                                        S=sdt, R=response.reason, T=response.text.rstrip('\t\n')),
                                              self.debugfile, self.mls)
                        except requests.RequestException, e:
                            write_log(self.logprefix + 'ERR: [{S}] Can\'t send request to \"{U}\". [{E}]'.format(
                                S=sdt, U=url, E=e), self.logfile, self.mls)
                            if self.dbg_lvl in ('SND', 'ALL'):
                                write_log(
                                    self.logprefix + 'DEBUG: [{S}] send_data_to_store: ERR: Can\'t send '
                                                     'request to \"{U}\". [{E}]'.format(S=sdt, U=url, E=e),
                                    self.debugfile, self.mls)
                    write_log(self.logprefix + 'INF: [{0}] finish sending data to storage'.format(sdt), self.logfile,
                              self.mls)
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: [{0}] send_data_to_store: INF: finish sending data to '
                                                   'storage'.format(sdt), self.debugfile, self.mls)
                        # end "for sdt in data.keys()"
            else:
                write_log(self.logprefix + 'ERR: Error connection string in storage settings for \"{0}\"'.format(
                    self.targets_params[target_name]['store_name']), self.logfile, self.mls)
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: send_data_to_store: ERR: Error connection string in '
                                               'storage settings for \"{0}\"'.format(
                        self.targets_params[target_name]['store_name']), self.debugfile, self.mls)
        else:
            write_log(self.logprefix + 'INF: sending to storage type \"{0}\" is under construction!'.format(store_type),
                      self.logfile, self.mls)
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: send_data_to_store: INF: sending to storage type \"{0}\" is under '
                                           'construction!'.format(store_type), self.debugfile, self.mls)

    def percentage(self, cur_value, max_value):
        if self.dbg_lvl in ('SND', 'ALL'):
            write_log(self.logprefix + 'DEBUG: percentage: cur_value = {CV} {CVT} max_value = {MV} {MVT}'.format(
                CV=cur_value, CVT=type(cur_value), MV=max_value, MVT=type(max_value)), self.debugfile, self.mls)
        if len(cur_value) > 0:
            if type(cur_value) == str:
                if self.dbg_lvl in ('SND', 'ALL'):
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: percentage: convert value = {0} from string to integer '
                                                   'type '.format(cur_value), self.debugfile, self.mls)
                try:
                    v1 = int(cur_value)
                except ValueError:
                    v1 = 0
            else:
                v1 = cur_value
        else:
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: percentage:  cur_value = {CV} {CVT} [cur_value is empty,'
                                           'set default value = 0]'.format(CV=cur_value, CVT=type(cur_value)),
                          self.debugfile, self.mls)
            v1 = 0

        if len(max_value) > 0:
            if type(max_value) == str:
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: percentage: convert max_value = {0} from string to integer '
                                               'type'.format(max_value), self.debugfile, self.mls)
                try:
                    v2 = int(max_value)
                except ValueError:
                    v2 = 0
            else:
                v2 = max_value
        else:
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: percentage:  max_value = {MV} {MVT} [max_value is empty, '
                                           'set default value = 0]'.format(MV=max_value, MVT=type(max_value)),
                          self.debugfile, self.mls)
            v2 = 0

        if v2 > 0:
            calc_res = v1 * 100 / v2
        else:
            calc_res = 0
        return calc_res

    def abs_value(self, value):
        result = 0
        if len(value) > 0:
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: abs_value: value = {V} {VT}'.format(V=value, VT=type(value)),
                          self.debugfile, self.mls)
            if type(value) == str:
                try:
                    result = int(value)
                except ValueError:
                    result = 0
        else:
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: abs_value:  value = {V} {VT} [value is empty, set default '
                                           'value = 0]'.format(V=value, VT=type(value)), self.debugfile, self.mls)
        return result

    def gen_grafana_reqs(self, sdt, data):
        result = []
        if self.dbg_lvl in ('SND', 'ALL'):
            write_log(self.logprefix + 'DEBUG: [{0}] gen_grafana_reqs: begin generate requests'.format(sdt),
                      self.debugfile, self.mls)
        if sdt == 'comp':
            for data_str in data:
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: [{S}] gen_grafana_reqs: line {L}'.format(S=sdt,
                                                                                                L=data.index(data_str)),
                              self.debugfile, self.mls)
                    write_log(self.logprefix + 'DEBUG: [{0}] >>>>>>>>>>>>>>> BEGIN >>>>>>>>>>>>>>>'.format(sdt),
                              self.debugfile, self.mls)
                    write_log(self.logprefix + 'DEBUG: [{S}] gen_grafana_reqs: data_str = {D}'.format(
                        S=sdt, D=data_str), self.debugfile, self.mls)
                # if data_str['CP_DISP_RUN_STATE'] not in ['Shutdown', 'shutdown', 'Not_Online', 'Not Online']:
                req = 'ObjManagersTasks,host={SV_NAME},obj={CC_ALIAS},runmode={RUN_MODE},state={RUN_STATE},startmode={START_MODE} value={ABS_TASKS},maxtask={ABS_MAXTASKS}\n' \
                      'ObjManagersTasksPercent,host={SV_NAME},obj={CC_ALIAS} value={PERC_TASKS}\n' \
                      'ObjManagersProcesses,host={SV_NAME},obj={CC_ALIAS} value={ABS_PROCS}\n' \
                      'ObjManagersProcessesPercent,host={SV_NAME},obj={CC_ALIAS} value={PERC_PROCS}'.format(
                    SV_NAME=data_str['SV_NAME'], 
                    CC_ALIAS=data_str['CC_ALIAS'],
                    RUN_MODE=data_str['CC_RUNMODE'],
                    RUN_STATE=data_str['CP_DISP_RUN_STATE'],
                    START_MODE=data_str['CP_STARTMODE'],
                    ABS_TASKS=self.abs_value(data_str['CP_NUM_RUN_TASKS']),
                    ABS_MAXTASKS=self.abs_value(data_str['CP_MAX_TASKS']),
                    PERC_TASKS=self.percentage(data_str['CP_NUM_RUN_TASKS'], data_str['CP_MAX_TASKS']),
                    ABS_PROCS=self.abs_value(data_str['CP_ACTV_MTS_PROCS']),
                    PERC_PROCS=self.percentage(data_str['CP_ACTV_MTS_PROCS'], data_str['CP_MAX_MTS_PROCS']))
                result.append(req)
                # else:
                #     write_log(self.logprefix + 'INF: [{S}] Component {C} on server {SRV} state is \"{ST}\". '
                #                                'Skipped!'.format(S=sdt, C=data_str['CC_ALIAS'],
                #                                                  SRV=data_str['SV_NAME'],
                #                                                  ST=data_str['CP_DISP_RUN_STATE']),
                #               self.logfile, self.mls)
                #     if self.dbg_lvl in ('SND', 'ALL'):
                #         write_log(
                #             self.logprefix + 'DEBUG: [{S}] gen_grafana_reqs: INF: Component {C} on server {SRV} state is \"{ST}\". '
                #                              'Skipped!'.format(S=sdt, C=data_str['CC_ALIAS'],
                #                                                SRV=data_str['SV_NAME'],
                #                                                ST=data_str['CP_DISP_RUN_STATE']),
                #            self.debugfile, self.mls)
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: [{0}] <<<<<<<<<<<<<<< END <<<<<<<<<<<<<<<'.format(sdt),
                              self.debugfile, self.mls)
        elif sdt == 'session':
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: [{0}] gen_grafana_reqs: start sorting and counting '
                                           'records'.format(sdt), self.debugfile, self.mls)
            calc_data = []
            for dl in data:
                nrec = True
                for cdl in calc_data:
                    if cdl['SV_NAME'] == dl['SV_NAME'] and cdl['CC_ALIAS'] == dl['CC_ALIAS']:
                        if dl['TK_DISP_RUNSTATE'] in cdl['STATES_CNT']:
                            cdl['STATES_CNT'][dl['TK_DISP_RUNSTATE']] += 1
                        else:
                            cdl['STATES_CNT'][dl['TK_DISP_RUNSTATE']] = 1
                        nrec = False
                        break
                if nrec:
                    nl = {'SV_NAME': dl['SV_NAME'], 'CC_ALIAS': dl['CC_ALIAS'],
                          'STATES_CNT': {dl['TK_DISP_RUNSTATE']: 1}}
                    calc_data.append(nl)
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: [{S}] gen_grafana_reqs: found {D} records'.format(
                    S=sdt, D=len(calc_data)), self.debugfile, self.mls)

            for data_str in calc_data:
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: [{S}] gen_grafana_reqs: generation request for line {L}'.format(
                        S=sdt, L=calc_data.index(data_str)), self.debugfile, self.mls)
                    write_log(self.logprefix + 'DEBUG: [{0}] >>>>>>>>>>>>>>> BEGIN >>>>>>>>>>>>>>>'.format(sdt),
                              self.debugfile, self.mls)
                    write_log(self.logprefix + 'DEBUG: [{S}] gen_grafana_reqs: data_str = {D}'.format(
                        S=sdt, D=data_str), self.debugfile, self.mls)
                req = ''
                for state in data_str['STATES_CNT']:
                    if len(req) > 0:
                        req += '\n'
                    req += 'SiebelSession,host={SV_NAME},component={CC_ALIAS},status={STATE} value={CNT}'.format(
                        SV_NAME=data_str['SV_NAME'], CC_ALIAS=data_str['CC_ALIAS'], STATE=state,
                        CNT=data_str['STATES_CNT'][state])
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: [{0}] <<<<<<<<<<<<<<< END <<<<<<<<<<<<<<<'.format(sdt),
                              self.debugfile, self.mls)
                result.append(req)
        else:
            result = []
        return result
