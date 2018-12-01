# -*- coding: utf-8 -*-
import logging
from datetime import datetime as dtime
from os import path as os_path
from log_handlers import ZipRotatingFileHandler


class PMonLogger(logging.Logger):
    def __init__(self, name, log_file='monitor.log', max_log_size='10MB', max_log_count=1000, debug=None):
        logging.Logger.__init__(self, name=name)

        self.setLevel(logging.INFO)
        file_handler = ZipRotatingFileHandler(filename=log_file, maxBytes=max_log_size, backupCount=max_log_count)

        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(name)-10s (PID: %(process)-6d %('
                                                    'processName)-10s) %(levelname)-10s: %(message)s'))
        self.addHandler(file_handler)

        if debug:
            dfmt = logging.Formatter('[%(asctime)s] %(name)-10s (PID: %(process)-6d %(processName)-10s) (TID: %('
                                     'thread)-6d %(threadName)-10s) %(funcName)-17s %(levelname)-10s: %(message)s')

            self.setLevel(logging.DEBUG)

            con_handler = logging.StreamHandler()
            con_handler.setLevel(logging.DEBUG)
            con_handler.setFormatter(dfmt)
            self.addHandler(con_handler)

            dfile_handler = ZipRotatingFileHandler(filename=os_path.join(os_path.dirname(log_file),
                                                                         "{0}_debug_{1}.log".format(
                                                                             os_path.splitext(os_path.basename
                                                                                              (log_file))[0],
                                                                             dtime.now().strftime("%Y%m%d%H%M"))),
                                                   maxBytes=max_log_size, backupCount=max_log_count)
            dfile_handler.setLevel(logging.DEBUG)
            dfile_handler.setFormatter(dfmt)
            self.addHandler(dfile_handler)
