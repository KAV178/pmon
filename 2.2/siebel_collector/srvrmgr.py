# -*- coding: utf-8 -*-
from os import environ, path as os_path, _exit
from multiprocessing.dummy import Pool as ThPool
from re import findall as re_findall
from subprocess import Popen, PIPE, check_output
from sys import exit as sys_exit
from tempfile import SpooledTemporaryFile as STF
from time import sleep
import platform

__author__ = "Kostrenko A.V. <kostrenko.av@gmail.com>"
__status__ = "beta"
__version__ = "1.0"



class Srvrmgr(object):
    def __init__(self, settings, logger, owner=None):
        self._owner = owner
        self.srvrmgr_path = settings.srvrmgr_cmd
        self.sieb_gateway = settings.gw_name
        self.sieb_enterprise = settings.ent_name
        self.sieb_crd = settings.crd
        self.logger = logger
        self.srvrmgr_proc = None
        self.ready = False
        self._key_sym = '/' if platform.system() == 'Windows' else '-'
        self._headshift = 1090 if platform.system() != 'Windows' else 87
        self._threads = None
        self._get_srvrmgr_session()

    def __del__(self):
        if self.srvrmgr_proc:
            try:
                self.send_request("quit")
            except Exception as e:
                self.logger.error(e)
            self.srvrmgr_proc.kill()
        for f in self._threads.values():
            if not f.closed:
                f.close()

    @property
    def owner(self):
        return self._owner

    @owner.setter
    def owner(self, value):
        self._owner = value

    def _hide_pass(self, data):
        return data.replace(self.sieb_crd.decode('base64').split()[1], "*" * 6)

    def _prepare_env(self, add_env=None):
        res_env = environ.copy()
        res_env['SIEBEL_DEBUG_FLAGS'] = "16"
        if platform.system() != 'Windows':
            self.logger.debug("Type OS is \"{0}\", applying \"siebenv.sh\" environment.".format(platform.system()))
            res_env['NLS_LANG'] = "AMERICAN_AMERICA.AL32UTF8"
            siebenv_sh = check_output('. ' + os_path.join(os_path.dirname(self.srvrmgr_path),
                                                          '..', 'siebenv.sh') + '; set',
                                      bufsize=-1, shell=True)
            for env_var in siebenv_sh.split('\n'):
                if '=' in env_var:
                    var_name, var_value = env_var.split('=')
                    if var_name not in ['_', 'EDITOR', 'ENV', 'FCEDIT', 'HISTCMD', 'HOME', 'IFS', 'JOBMAX',
                                        'KSH_VERSION',
                                        'LINENO', 'LOGNAME', 'MAIL', 'MAILCHECK', 'OLDPWD', 'OPTIND', 'PPID', 'PWD',
                                        'RANDOM',
                                        'SECONDS', 'SHELL', 'SHLVL', 'TERM', 'TMOUT', 'TZ', 'USER'] \
                            and var_name[:4] != 'SSH_' \
                            and len(re_findall(r'PS\d', var_name)) == 0:
                        res_env[var_name] = var_value

            if add_env:
                res_env.update({k: unicode(v) for k, v in add_env.items()})
        self.logger.debug(
            "SRVRMGR environment: \n\t{0}".format("\n\t".join(["=".join([k, v]) for k, v in res_env.items()])))
        return res_env

    def _get_srvrmgr_session(self):
        self.logger.debug("Opening srvrmgr session...")
        if not self._threads:
            self._threads = dict(stdout=STF(max_size=5242880, mode='w+b'),
                                 stderr=STF(max_size=5242880, mode='w+b'))
        srvrmgr_cmd = [self.srvrmgr_path, self._key_sym + 'g', self.sieb_gateway, self._key_sym + 'e',
                       self.sieb_enterprise, self._key_sym + 'u', self.sieb_crd.decode('base64').split()[0],
                       self._key_sym + 'k', '^$^']
        if platform.system() == 'Windows':
            srvrmgr_cmd += [self._key_sym + 'p', self.sieb_crd.decode('base64').split()[1], self._key_sym + 'q']

        try:
            self.srvrmgr_proc = Popen(args=srvrmgr_cmd,
                                      stdin=PIPE, stdout=self._threads['stdout'], stderr=self._threads['stderr'],
                                      bufsize=-1, shell=False,
                                      env=self._prepare_env())

            if platform.system() != 'Windows':
                self.srvrmgr_proc.stdin.write(self.sieb_crd.decode('base64').split()[1] + '\n')
                self.srvrmgr_proc.stdin.flush()
        except Exception as e:
            self.logger.exception(self._hide_pass(e.message))
            sys_exit()
            # _exit()

    def _parse_data(self, data):
        if len(data) > 0:
            self.logger.debug("Parsing data: \n{0}".format(data.replace('^$^', ' ')))
            result = tuple()
            if len(data.strip()) > 0:
                if '^$^' in data:
                    ud = filter(len, map(str.strip, data.split('\n')))
                    fields = tuple(filter(len, map(str.strip, ud[0].split('^$^'))))
                    for line_ndx in range(2, len(ud) - 2):
                        result += (dict(zip(fields, map(str.strip, ud[line_ndx].split("^$^")))),)
                else:
                    result = tuple(filter(len, data.split('\n')))
                return result
            else:
                return None
        else:
            return None

    @property
    def servers_info(self):
        """
        :return:
        data    - tuple with data about servers
        running - tuple names of active servers
        """
        _data = self.send_request('list servers')
        if _data['err']:
            si = {'data': _data['err'],
                  'running': None,
                  'offline': None
                  }
        else:
            try:
                si = {'data': _data['out'],
                      'running': tuple(v['SBLSRVR_NAME'] for v in _data['out'] if v['SBLSRVR_STATE'] == 'Running'),
                      'offline': tuple(v['SBLSRVR_NAME'] for v in _data['out'] if v['SBLSRVR_STATE'] != 'Running')
                      }
            except TypeError:
                self.logger.exception(u"Fail on \"list servers\': {0}".format(_data))

        return si

    def send_request(self, cmd):
        def read_output(args):
            args['data'].seek(args.get('shift', 0))
            return self._parse_data(args['data'].read())

        if self.srvrmgr_proc.stdin.closed:
            if cmd != "quit":
                self._get_srvrmgr_session()
            else:
                return None
        self.logger.debug("Executing srvrmgr command -> {0}".format(self._hide_pass(cmd)))

        self.srvrmgr_proc.stdin.write(cmd + '\n')
        self.srvrmgr_proc.stdin.flush()

        while not any(map(STF.tell, self._threads.values())):
            self.logger.debug("Waiting data...")
            sleep(1)

        pool = ThPool(2)
        cmd_res = pool.map(read_output, [dict(data=self._threads['stdout'], shift=self._headshift),
                                         dict(data=self._threads['stderr'])])
        pool.close()
        pool.join()

        self.logger.debug("parced data: \n\n{0}\n".format(cmd_res))
        if self._threads['stderr'].tell() > 0:
            self._threads['stderr'].seek(0)
            self.logger.error(self._threads['stderr'].read())

        for f in self._threads.values():
            f.seek(0)
            f.truncate()
        self._headshift = 0

        return dict(out=cmd_res[0], err=cmd_res[1])

    def get_components_data(self, server=None, fields_filter=None):
        req_text = "list comp"
        if server:
            if server not in self.servers_info['running']:
                self.logger.error("Server \"{0}\" is not available.".format(server))
                return None
            else:
                req_text += " for server {0}".format(server)

        if fields_filter:
            if not isinstance(fields_filter, list):
                self.logger.error("Filter parameter must be a list type, but this is {0}".format(type(fields_filter)))
                return None
            else:
                req_text += " show {0}".format(",".join(fields_filter))

        self.logger.debug("Request string for fetching components data: \"{0}\"".format(req_text))
        return self.send_request(req_text)

    def get_sessions_data(self, server=None, fields_filter=None):
        req_text = "list session"
        if server:
            if server not in self.servers_info['running']:
                self.logger.error("Server \"{0}\" is not available.".format(server))
                return None
            else:
                req_text += " for server {0}".format(server)

        if fields_filter:
            if not isinstance(fields_filter, list):
                self.logger.error("Filter parameter must be a list type, but this is {0}".format(type(fields_filter)))
                return None
            else:
                req_text += " show {0}".format(",".join(fields_filter))

        self.logger.debug("Request string for fetching session data: \"{0}\"".format(req_text))
        return self.send_request(req_text)
