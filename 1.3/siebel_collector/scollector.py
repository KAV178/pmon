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
        if len(self.settings) > 0:
            self.logfile = self.settings['log']['log_file']
            self.mls = self.settings['log']['max_size']
        else:
            write_log('ERR: Error getting settings. The data collection is cancelled!', self.logfile, self.mls)

    def set_dbg_level(self, value):
        self.dbg_lvl = value

    def get_target_list(self):
        self.targets_params = read_config('siebel_collector/targets.ini')
        if len(self.targets_params) > 0:
            self.target_list = self.targets_params.keys()

    def reset_log_filename(self, target):
        if len(self.settings) > 0:
            import datetime
            self.logfile = self.settings['log']['log_dir']+'/'+target+'_'+self.settings['log']['log_file']
            if self.dbg_lvl in ('COL', 'ALL', 'SND'):
                self.debugfile = self.settings['log']['log_dir']+'/'+target+'_debug_'+self.dbg_lvl+'_' + \
                                 datetime.datetime.now().strftime("%Y%m%d%H%M")+'.log'
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
                write_log(self.logprefix+'DEBUG: clean_received_data: line = '+line.rstrip(), self.debugfile, self.mls)
            if line.find(b_mark) > -1 or (0 < step < header_height):
                step += 1
                continue
            if step == header_height and dirt_data.index(line) < len(dirt_data) - footer_height:
                line = line.rstrip()
                if self.dbg_lvl in ('COL', 'ALL'):
                    write_log(self.logprefix+'DEBUG: clean_received_data: line.rstrip() = '+line,
                              self.debugfile, self.mls)
                    write_log(self.logprefix+'DEBUG: clean_received_data: len(line) = '+str(len(line)),
                              self.debugfile, self.mls)
                if len(line) > 0:
                    for fix_word in ['Partially Offline', 'Not Online']:
                        line = line.replace(fix_word, fix_word.replace(' ', '_'))
                    line = re.sub(r'\s+', ';', line).rstrip().split(';')

                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix+'DEBUG: clean_received_data: result.append('+str(line)+')',
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
            write_log(self.logprefix+'DEBUG: get_data_from_srvrmgr: platform = \''+platform.system() +
                      '\' using \''+key_sym+'\' as key_sym', self.debugfile, self.mls)
        procs = ''
        try:
            do_cmd = self.settings['srvrmgr_'+self.targets_params[target_name]['sieb_ver']][
                         'cmd']+' '+key_sym+'g ' + \
                     self.targets_params[target_name]['gw_name'] + \
                     ' '+key_sym+'e '+self.targets_params[target_name]['ent_name'] + \
                     ' '+key_sym+'u '+self.targets_params[target_name]['crd'].decode('base64').split()[0] + \
                     ' '+key_sym+'p '+self.targets_params[target_name]['crd'].decode('base64').split()[1] + \
                     ' '+key_sym+'c "'+srvr_cmd+'"'
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: get_data_from_srvrmgr: do_cmd = ' +
                          do_cmd.replace(self.targets_params[target_name]['crd'].decode('base64').split()[1], '*****'),
                          self.debugfile, self.mls)
            procs = subprocess.Popen(do_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE, shell=True, cwd=os.getcwd())
        except StandardError, e:
            write_log(self.logprefix+'Fail - ERR: Error on receive data over srvrmgr! [' + str(e) + ']',
                      self.logfile, self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: get_data_from_srvrmgr: Fail - ERR: Error on receive data over '
                                         'srvrmgr! [' + str(e) + ']', self.debugfile, self.mls)
        result = procs.stdout.readlines()
        err_res = procs.stderr.readlines()
        if len(err_res) > 0:
            write_log(self.logprefix + 'Fail - ERR: Error on receive data over srvrmgr! [' +
                      ':|: '.join(err_res).rstrip() + ']', self.logfile, self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: get_data_from_srvrmgr: ' + ':|: '.join(err_res).rstrip(),
                          self.debugfile, self.mls)
            sys.exit()

        if self.dbg_lvl in ('COL', 'ALL'):
            write_log(self.logprefix+'DEBUG: get_data_from_srvrmgr: result has '+str(len(result))+' lines.',
                      self.debugfile, self.mls)
        return result

    def get_servers(self, target):
        result = []
        servers_cmd_fields = ['SBLSRVR_NAME', 'SBLSRVR_STATE']
        servers_cmd = 'list servers show '+",".join(servers_cmd_fields)
        if self.dbg_lvl in ('COL', 'ALL'):
            write_log(
                self.logprefix+'DEBUG: get_servers: req_out = self.get_data_from_srvrmgr(\''+target+'\', \'' +
                servers_cmd+'\')', self.debugfile, self.mls)
        req_out = self.get_data_from_srvrmgr(target, servers_cmd)

        if self.dbg_lvl in ('COL', 'ALL'):
            write_log(self.logprefix+'DEBUG: get_servers: OK', self.debugfile, self.mls)
        if len(req_out) > 0:
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: get_servers: crd = self.clean_received_data(\''+servers_cmd+'\', {' +
                          str(len(req_out[0]))+' lines}', self.debugfile, self.mls)
            crd = self.clean_received_data(servers_cmd, req_out)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: get_servers: OK', self.debugfile, self.mls)
            for line in crd:
                if self.dbg_lvl in ('COL', 'ALL'):
                    write_log(self.logprefix+'DEBUG: get_servers: line = ['+';'.join(line)+']', self.debugfile,
                              self.mls)
                if len(line) > 1:
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix+'DEBUG: get_servers: result.append('+line[0]+')',
                                  self.debugfile, self.mls)
                    result.append(line[0])
        else:
            write_log(self.logprefix+'ERR: No data for load.', self.logfile, self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: get_servers: ERR: No data for load.',
                          self.debugfile, self.mls)
        return result

    def collect_data(self, target_name):
        self.logprefix = 'Collect data for '+target_name+': '
        write_log(self.logprefix+'begin', self.logfile, self.mls)
        if self.targets_params[target_name]['active'] in ['Yes', 'yes', 'true', 'True', '1']:
            active_servers = self.get_servers(target_name)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: collect_data: active_servers = ['+'; '.join(active_servers)+']',
                          self.debugfile, self.mls)
            if len(active_servers) > 0:
                comps_cmd_fields = ['SV_NAME', 'CC_ALIAS', 'CP_DISP_RUN_STATE', 'CP_STARTMODE', 'CP_NUM_RUN_TASKS',
                                    'CP_MAX_TASKS', 'CP_ACTV_MTS_PROCS', 'CP_MAX_MTS_PROCS']
                comps_cmd = 'list comp show '+','.join(comps_cmd_fields)
                c_data = []
                try:
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: req_out = self.get_data_from_srvrmgr(' +
                                  target_name + ', ' + comps_cmd + ')', self.debugfile, self.mls)
                    req_out = self.get_data_from_srvrmgr(target_name, comps_cmd)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: OK', self.debugfile, self.mls)
                        write_log(self.logprefix + 'DEBUG: collect_data: len(req_out) = ' + str(len(req_out)),
                                  self.debugfile, self.mls)
                    if len(req_out) > 0:
                        write_log(
                            self.logprefix + 'Received ' + str(len(req_out)) + ' lines. Preparing received data...',
                            self.logfile, self.mls)
                        if self.dbg_lvl in ('COL', 'ALL'):
                            write_log(
                                self.logprefix + 'DEBUG: collect_data: crd = self.clean_received_data(' + comps_cmd +
                                ', {req_out(' + str(len(req_out)) + ' lines)})', self.debugfile, self.mls)
                        crd = self.clean_received_data(comps_cmd, req_out)
                        if self.dbg_lvl in ('COL', 'ALL'):
                            write_log(self.logprefix + 'DEBUG: collect_data: OK', self.debugfile, self.mls)
                        for cl_line in crd:
                            if self.dbg_lvl in ('COL', 'ALL'):
                                write_log(self.logprefix + 'DEBUG: collect_data: cl_line = [' + ';'.join(cl_line) + ']',
                                          self.debugfile, self.mls)
                                write_log(self.logprefix + 'DEBUG: collect_data: ' + cl_line[0] + ' in [' +
                                          ', '.join(active_servers) + ']', self.debugfile, self.mls)
                            if cl_line[0] in active_servers:
                                if self.dbg_lvl in ('COL', 'ALL'):
                                    write_log(self.logprefix + 'DEBUG: collect_data: OK ', self.debugfile, self.mls)
                                    write_log(self.logprefix + 'DEBUG: collect_data: len(cl_line)-1 <= '
                                                               'len(comps_cmd_fields) : ' + str(len(cl_line) - 1) +
                                              ' <= ' + str(len(comps_cmd_fields)), self.debugfile, self.mls)
                                if len(cl_line) - 1 <= len(comps_cmd_fields):
                                    if self.dbg_lvl in ('COL', 'ALL'):
                                        write_log(self.logprefix + 'DEBUG: collect_data: OK ', self.debugfile, self.mls)
                                    res_line = {}
                                    for field in comps_cmd_fields:
                                        if self.dbg_lvl in ('COL', 'ALL'):
                                            write_log(self.logprefix + 'DEBUG: collect_data: comps_cmd_fields.index'
                                                                       '(' + field + ') = ' +
                                                      str(comps_cmd_fields.index(field)), self.debugfile, self.mls)
                                        try:
                                            if self.dbg_lvl in ('COL', 'ALL'):
                                                write_log(
                                                    self.logprefix + 'DEBUG: collect_data: res_line[' + field + '] = ' +
                                                    cl_line[comps_cmd_fields.index(field)], self.debugfile, self.mls)
                                            res_line[field] = cl_line[comps_cmd_fields.index(field)]
                                        except IndexError, e:
                                            if self.dbg_lvl in ('COL', 'ALL'):
                                                write_log(self.logprefix + 'DEBUG: collect_data: res_line[' + field +
                                                          '] = \'\' err: [' + str(e) + ']', self.debugfile, self.mls)
                                            res_line[field] = ''
                                        except StandardError, e:
                                            write_log(self.logprefix + 'ERR: collect_data: res_line[' + field + ']' +
                                                      str(e), self.logfile, self.mls)
                                            if self.dbg_lvl in ('COL', 'ALL'):
                                                write_log(self.logprefix + 'DEBUG: collect_data: res_line[' + field +
                                                          '] err: [' + str(e) + ']', self.debugfile, self.mls)
                                        if self.dbg_lvl in ('COL', 'ALL'):
                                            write_log(self.logprefix + 'DEBUG: collect_data: c_data.append(' +
                                                      str(res_line) + ')', self.debugfile, self.mls)
                                    c_data.append(res_line)
                                else:
                                    write_log(self.logprefix + 'Fail - ERR: Exceeded the number of fields in line "' +
                                              " ".join(cl_line) + '" Line Skipped!', self.logfile, self.mls)
                                    if self.dbg_lvl in ('COL', 'ALL'):
                                        write_log(self.logprefix + 'DEBUG: collect_data: Fail - ERR: Exceeded the '
                                                                   'number of fields in line "' + " ".join(cl_line) +
                                                  '" Line Skipped!', self.debugfile, self.mls)
                    else:
                        write_log(self.logprefix + 'ERR: No data for load.', self.logfile, self.mls)
                        if self.dbg_lvl in ('COL', 'ALL'):
                            write_log(self.logprefix + 'DEBUG: collect_data: ERR: No data for load.', self.debugfile,
                                      self.mls)
                except StandardError, e:
                    write_log(self.logprefix + 'Fail - ERR: Error on get data over srvrmgr. [' + str(e) + ']',
                              self.logfile, self.mls)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: Fail - ERR: Error on get data over srvrmgr.',
                                  self.debugfile, self.mls)
                if len(c_data) == 0:
                    write_log(self.logprefix + 'Fail - ERR: No data except headers.', self.logfile, self.mls)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: Fail - ERR: No data except headers.',
                                  self.debugfile, self.mls)
                else:
                    write_log(self.logprefix + 'Preparing received data... Success.', self.logfile, self.mls)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(
                            self.logprefix + 'DEBUG: collect_data: self.send_data_to_store(' + target_name +
                            ', {' + str(len(c_data)) + ' lines}', self.debugfile, self.mls)
                    self.send_data_to_store(target_name, c_data)
                    if self.dbg_lvl in ('COL', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: collect_data: OK', self.debugfile, self.mls)
            else:
                write_log(self.logprefix+'ERR: No active servers.', self.logfile)
                if self.dbg_lvl in ('COL', 'ALL'):
                    write_log(self.logprefix+'DEBUG: collect_data: ERR: No active servers.', self.debugfile, self.mls)
        else:
            write_log(self.logprefix+'WARN: Target "'+target_name+'" marked as inactive. Skipped!', self.logfile,
                      self.mls)
            if self.dbg_lvl in ('COL', 'ALL'):
                write_log(self.logprefix+'DEBUG: collect_data: WARN: Target "'+target_name +
                          '" marked as inactive. Skipped!', self.debugfile, self.mls)

    def percentage(self, cur_value, max_value):
        if self.dbg_lvl in ('SND', 'ALL'):
            write_log(self.logprefix + 'DEBUG: percentage: cur_value = ' + str(cur_value) + ' ' + str(type(cur_value)) +
                      ' max_value = ' + str(max_value) + ' ' + str(type(max_value)), self.debugfile, self.mls)
        if len(cur_value) > 0:
            if type(cur_value) == str:
                if self.dbg_lvl in ('SND', 'ALL'):
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: percentage: convert value = ' + str(cur_value) +
                                  ' from string to integer type ', self.debugfile, self.mls)
                try:
                    v1 = int(cur_value)
                except ValueError:
                    v1 = 0
            else:
                v1 = cur_value
        else:
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: percentage:  cur_value = ' + cur_value + ' ' + str(type(cur_value)) +
                          '[ cur_value is empty, set default value = 0]', self.debugfile, self.mls)
            v1 = 0

        if len(max_value) > 0:
            if type(max_value) == str:
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix + 'DEBUG: percentage: convert max_value = ' + str(max_value) +
                              ' from string to integer type ', self.debugfile, self.mls)
                try:
                    v2 = int(max_value)
                except ValueError:
                    v2 = 0
            else:
                v2 = max_value
        else:
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: percentage:  max_value = ' + max_value + ' ' + str(type(max_value)) +
                          '[ max_value is empty, set default value = 0]', self.debugfile, self.mls)
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
                write_log(self.logprefix + 'DEBUG: abs_value: value = ' + value + ' ' + str(type(value)),
                          self.debugfile, self.mls)
            if type(value) == str:
                try:
                    result = int(value)
                except ValueError:
                    result = 0
        else:
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix + 'DEBUG: abs_value:  value = ' + value + ' ' + str(type(value)) +
                          '[ value is empty, set default value = 0]', self.debugfile, self.mls)
        return result

    def send_data_to_store(self, target_name, data):
        store_params = read_config('siebel_collector/storages.ini')
        self.logprefix = 'Sending data '+target_name+' in storage '+self.targets_params[target_name][
            'store_name']+': '
        store_type = store_params[self.targets_params[target_name]['store_name']]['type']
        if self.dbg_lvl in ('SND', 'ALL'):
            write_log(self.logprefix+'DEBUG: send_data_to_store: store_type = ' + store_type, self.debugfile, self.mls)
        if store_type == 'http-grafana':
            url = store_params[self.targets_params[target_name]['store_name']]['conn_str']
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix+'DEBUG: send_data_to_store: url = '+url,
                          self.debugfile, self.mls)
            if len(url) > 0:
                try:
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix+'DEBUG: send_data_to_store: import module \'requests\'',
                                  self.debugfile, self.mls)
                    import requests
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix+'DEBUG: send_data_to_store: OK', self.debugfile, self.mls)
                except ImportError(requests), e:
                    write_log(
                        self.logprefix+'ERR: '+str(e), self.logfile, self.mls)
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix+'DEBUG: send_data_to_store: ERR: ' + str(e),
                                  self.debugfile, self.mls)
                    sys.exit('Error on import requests module')

                write_log(self.logprefix+'INF: begin sending data to storage', self.logfile, self.mls)
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix+'DEBUG: send_data_to_store: begin sending data to storage',
                              self.debugfile, self.mls)
                for data_str in data:
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix+'DEBUG: send_data_to_store: line ' + str(data.index(data_str)),
                                  self.debugfile, self.mls)
                        write_log(self.logprefix+'DEBUG: >>>>>>>>>>>>>>> BEGIN >>>>>>>>>>>>>>>', self.debugfile,
                                  self.mls)
                        write_log(self.logprefix + 'DEBUG: send_data_to_store: data_str = '+str(data_str),
                                  self.debugfile, self.mls)
                    if data_str['CP_DISP_RUN_STATE'] not in ['Shutdown', 'shutdown', 'Not_Online', 'Not Online']:
                        req = 'ObjManagersTasks,host='+data_str['SV_NAME']+',obj='+data_str['CC_ALIAS']+' value=' + \
                              str(self.abs_value(data_str['CP_NUM_RUN_TASKS']))+'\n' + \
                              'ObjManagersTasksPercent,host='+data_str['SV_NAME']+',obj='+data_str['CC_ALIAS'] + \
                              ' value='+str(self.percentage(data_str['CP_NUM_RUN_TASKS'], data_str['CP_MAX_TASKS'])) + \
                              '\n'+'ObjManagersProcesses,host='+data_str['SV_NAME']+',obj='+data_str['CC_ALIAS'] + \
                              ' value='+str(self.abs_value(data_str['CP_ACTV_MTS_PROCS']))+'\n' + \
                              'ObjManagersProcessesPercent,host='+data_str['SV_NAME']+',obj=' + data_str['CC_ALIAS'] + \
                              ' value='+str(self.percentage(data_str['CP_ACTV_MTS_PROCS'],
                                                            data_str['CP_MAX_MTS_PROCS']))
                        if self.dbg_lvl in ('SND', 'ALL'):
                            write_log(self.logprefix + 'DEBUG: send_data_to_store: \n---------- req begin ----------\n'
                                      + req + '\n----------- req end -----------', self.debugfile,
                                      self.mls)
                        try:
                            response = requests.post(url, data=req)
                            if self.dbg_lvl in ('SND', 'ALL'):
                                write_log(self.logprefix+'DEBUG: send_data_to_store: Sending request - ' +
                                          str(response.ok).replace('True', 'OK'), self.debugfile, self.mls)
                            if not response.ok:
                                write_log(
                                    self.logprefix+'ERR: on sending data [Reason: '+response.reason+'; Text: ' +
                                    response.text.rstrip('\t\n')+']', self.logfile, self.mls)
                                if self.dbg_lvl in ('SND', 'ALL'):
                                    write_log(self.logprefix+'DEBUG: send_data_to_store: ERR: on sending data '
                                                             '[Reason: '+response.reason+'; Text: ' +
                                              response.text.rstrip('\t\n')+']', self.debugfile, self.mls)
                        except requests.RequestException, e:
                            write_log(self.logprefix + 'ERR: Can\'t send request to "' + url + '". [' +
                                      str(e) + ']', self.logfile, self.mls)
                            if self.dbg_lvl in ('SND', 'ALL'):
                                write_log(self.logprefix + 'DEBUG: send_data_to_store: ERR: Can\'t send request to "' +
                                          url + '". [' + str(e) + ']', self.debugfile, self.mls)
                    else:
                        write_log(self.logprefix+'INF: Component '+data_str['CC_ALIAS']+' on server ' +
                                  data_str['SV_NAME']+' state is "'+data_str['CP_DISP_RUN_STATE']+'". Skipped!',
                                  self.logfile, self.mls)
                        if self.dbg_lvl in ('SND', 'ALL'):
                            write_log(
                                self.logprefix+'DEBUG: send_data_to_store: INF: Component '+data_str['CC_ALIAS'] +
                                ' on server '+data_str['SV_NAME']+' state is "'+data_str['CP_DISP_RUN_STATE'] +
                                '". Skipped!', self.debugfile, self.mls)
                    if self.dbg_lvl in ('SND', 'ALL'):
                        write_log(self.logprefix + 'DEBUG: <<<<<<<<<<<<<<< END <<<<<<<<<<<<<<<',
                                  self.debugfile, self.mls)
            else:
                write_log(self.logprefix+'ERR: Error connection string in storage settings for "' +
                          self.targets_params[target_name]['store_name']+'"', self.logfile, self.mls)
                if self.dbg_lvl in ('SND', 'ALL'):
                    write_log(self.logprefix+'DEBUG: send_data_to_store: ERR: Error connection string in '
                                             'storage settings for "' +
                              self.targets_params[target_name]['store_name'] + '"', self.debugfile, self.mls)
            write_log(self.logprefix+'INF: finish sending data to storage', self.logfile, self.mls)
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix+'DEBUG: send_data_to_store: INF: finish sending data to storage',
                          self.debugfile, self.mls)
        else:
            write_log(self.logprefix+'INF: sending to storage type "'+store_type+'" is under construction!',
                      self.logfile, self.mls)
            if self.dbg_lvl in ('SND', 'ALL'):
                write_log(self.logprefix+'DEBUG: send_data_to_store: INF: sending to storage type "'+store_type +
                          '" is under construction!', self.debugfile, self.mls)
