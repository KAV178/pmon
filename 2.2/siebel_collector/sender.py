# -*- coding: utf-8 -*-
from Queue import Queue
import requests

__author__ = "Kostrenko A.V. <kostrenko.av@gmail.com>"
__status__ = "beta"
__version__ = "1.0"



class Sender(object):
    def __init__(self, storage, logger):
        self.storage = storage
        self.logger = logger
        self._queue = Queue()

        if storage.type == 'file':
            from os import path as os_path, getpid as cur_pid
            self.store_fname = os_path.join(os_path.dirname(self.storage.path), str(cur_pid()) + '_' +
                                            os_path.basename(self.storage.path))

    @property
    def queue(self):
        return self._queue

    def _prepare_data(self, data_type, data):
        """
        :rtype: str
        """

        def get_int(v):
            return int(v) if len(v.strip()) > 0 else 0

        def get_percent(cv, mv):
            return 0 if mv == 0 else (cv * 100) // mv

        if data_type == 'comp':
            if self.storage.type in ('file', 'http-grafana'):
                try:
                    req = 'ObjManagersTasks,host={SV_NAME},obj={CC_ALIAS},runmode={RUN_MODE},state={RUN_STATE},' \
                          'startmode={START_MODE} value={ABS_TASKS},maxtask={ABS_MAXTASKS}\n' \
                          'ObjManagersTasksPercent,host={SV_NAME},obj={CC_ALIAS} value={PERC_TASKS}\n' \
                          'ObjManagersProcesses,host={SV_NAME},obj={CC_ALIAS} value={ABS_PROCS}\n' \
                          'ObjManagersProcessesPercent,host={SV_NAME},obj={CC_ALIAS} value={PERC_PROCS}'.format(
                        SV_NAME=data['SV_NAME'],
                        CC_ALIAS=data['CC_ALIAS'],
                        RUN_MODE=data['CC_RUNMODE'],
                        RUN_STATE=data['CP_DISP_RUN_STATE'],
                        START_MODE=data['CP_STARTMODE'],
                        ABS_TASKS=get_int(data.get('CP_NUM_RUN_TASKS', 0)),
                        ABS_MAXTASKS=get_int(data.get('CP_MAX_TASKS', 0)),
                        PERC_TASKS=get_percent(get_int(data.get('CP_NUM_RUN_TASKS', 0)),
                                               get_int(data.get('CP_MAX_TASKS', 0))),
                        ABS_PROCS=get_int(data.get('CP_ACTV_MTS_PROCS', 0)),
                        PERC_PROCS=get_percent(get_int(data.get('CP_ACTV_MTS_PROCS', 0)),
                                               get_int(data.get('CP_MAX_MTS_PROCS', 0)))
                    )
                except ValueError:
                    self.logger.exception("Error on preparation data for sending")
                else:
                    return req
        elif data_type == 'session':
            if self.storage.type in ('http-grafana', 'file'):
                return "\n".join(["SiebelSession,host={SV_NAME},component={CC_ALIAS},status={STATE} value={CNT}".
                                 format(SV_NAME=data['SV_NAME'], CC_ALIAS=data['CC_ALIAS'], STATE=data['STATES'][si],
                                        CNT=data['STATES'][si + 1]) for si in range(0, len(data['STATES']), 2)])

    def _send_data(self, data_for_sending):
        req = self._prepare_data(data_for_sending[0], data_for_sending[1])
        self.logger.debug("Request for send: {0}".format(req))
        # Local file
        if self.storage.type == 'file':
            self.logger.debug("Write request to file {0}".format(self.storage.path))
            try:
                with open(self.store_fname, 'a') as f:
                    f.write(req)
                return True
            except IOError:
                self.logger.exception("Exception on sending request")
                return False
        # Grafana
        elif self.storage.type == 'http-grafana':
            self.logger.debug("Sending request {0} to {1}".format(req, self.storage.path))
            try:
                response = requests.post(self.storage.path, data=req)
                return response.ok
            except requests.RequestException:
                self.logger.exception("Can\'t send request {0} to {1}".format(req, self.storage.path))

    def sending_worker(self):
        while True:
            self.logger.debug(u"Sender queue size = {0}".format(self.queue.qsize()))
            item = self.queue.get()
            self.logger.debug(u"[{0}] preparation for send data: {1}".format(item[0].capitalize(), item[1]))
            if self._send_data(item):
                self.logger.info(u"Sending {DT} data for server: {SV_NAME} comp: {CC_ALIAS} - SUCCESS".
                                 format(DT=item[0], SV_NAME=item[1]['SV_NAME'], CC_ALIAS=item[1]['CC_ALIAS']))
                self.queue.task_done()
            else:
                self.logger.critical(u"Sending {DT} data for server: {SV_NAME} comp: {CC_ALIAS} - FAILED".
                                     format(DT=item[0], SV_NAME=item[1]['SV_NAME'], CC_ALIAS=item[1]['CC_ALIAS']))
