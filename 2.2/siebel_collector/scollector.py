# -*- coding: utf-8 -*-
from collections import Counter
from srvrmgr import Srvrmgr
from threading import Thread, ThreadError
from thread import get_ident as th_id
from multiprocessing.dummy import Pool as ThPool
from time import sleep

__author__ = "Kostrenko A.V. <kostrenko.av@gmail.com>"
__status__ = "beta"
__version__ = "2.2"


class SiebelCollector(object):
    def __init__(self, target, main_settings, logger, sender, data_types=None):
        self.logger = logger
        self.sender = sender
        self.target = target
        self.data_types = data_types if data_types else main_settings.siebel_data_types
        self.srvrmgr = Srvrmgr(settings=self.target, logger=self.logger)

    def _get_data_from_srvrmgr(self, data_type):
        if self.srvrmgr.owner:
            srvrmgr = Srvrmgr(settings=self.target, logger=self.logger)
        else:
            srvrmgr = self.srvrmgr
        srvrmgr.owner = th_id()

        if data_type == 'comp':
            return srvrmgr.get_components_data(fields_filter=['SV_NAME', 'CC_ALIAS', 'CC_RUNMODE',
                                                              'CP_DISP_RUN_STATE', 'CP_STARTMODE',
                                                              'CP_NUM_RUN_TASKS', 'CP_MAX_TASKS',
                                                              'CP_ACTV_MTS_PROCS', 'CP_MAX_MTS_PROCS'])
        elif data_type == 'session':
            result = []
            raw_data = srvrmgr.get_sessions_data(fields_filter=['SV_NAME', 'CC_ALIAS', 'TK_DISP_RUNSTATE'])
            c = Counter([(v['SV_NAME'], v['CC_ALIAS'], v['TK_DISP_RUNSTATE']) for v in raw_data['out']])

            for serv, comp in set(z[:2] for z in c.keys()):
                state_data = tuple()
                for s in filter(lambda x: x[0][0] == serv and x[0][1] == comp, c.items()):
                    state_data += (s[0][2], s[1])
                data_for_send = {'SV_NAME': serv, 'CC_ALIAS': comp, 'STATES': state_data}
                result.append(data_for_send)
            del srvrmgr
            return {'out': result, 'err': raw_data['err']}
        else:
            self.logger.error("Unknown type of data -> {0}".format(data_type))
            del srvrmgr
            return None

    def collect_worker(self, data_type):
        self.logger.debug("Starting collection data type \"{0}\"".format(data_type))
        res = self._get_data_from_srvrmgr(data_type)
        self.logger.info("[{DT}] Received {CNT} lines of data type.".format(DT=data_type,
                                                                            CNT=len(res['out'])))
        if len(res['out']):
            self.logger.info("[{DT}] Sending received data to storage \"{STORAGE}\".".
                             format(DT=data_type, STORAGE=self.target.storage))
            for i in res['out']:
                self.sender.queue.put((data_type, i))

    def start_collect(self):
        si = self.srvrmgr.servers_info
        if si['running'] and len(si['running']) > 0:
            if len(si['offline']) > 0:
                self.logger.warning("Some servers is offile -> {0}".format(self.srvrmgr.servers_info['offline']))
            try:
                # Create sender thread
                sender_th = Thread(target=self.sender.sending_worker, name="sender")
                sender_th.start()
                # Create other threads
                pool = ThPool(len(self.data_types))
                pool.map_async(func=self.collect_worker, iterable=self.data_types)
                pool.close()
                pool.join()

                while self.sender.queue.unfinished_tasks:
                    self.logger.info("Waiting for finish sending.... ({0} tasks remain)".format(self.sender.queue.
                                                                                                unfinished_tasks))
                    sleep(1)
            except ThreadError:
                self.logger.exception("Fail on collecting data")
            except TypeError:
                self.logger.exception("")

        elif si['running']:
            self.logger.error("No active servers.")
