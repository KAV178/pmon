# -*- coding: utf-8 -*-

import platform
import gzip
from logging.handlers import RotatingFileHandler
from re import findall as re_fall, match as re_match
from os import path as os_path, remove as rm, rename as ren

__author__ = 'Kostreno A.V.'


__all__ = ['ZipRotatingFileHandler']


def conv_to_bytes(src_data):
    d = re_fall(r'^(\d+)', src_data)
    if len(d) > 0:
        suf = src_data[len(d[0])::]
        if len(suf) > 0:
            if re_match('KB|MB', suf):
                return {'KB': lambda val: val * 1024, 'MB': lambda val: val * 1024 * 1024}[suf](int(d[0]))
            else:
                return "Wrong format of size siffix!"
        else:
            if not isinstance(src_data, int):
                try:
                    src_data = int(src_data)
                except ValueError:
                    return 'Wrong value!'
            return src_data
    else:
        return 'Wrong value!'


class ZipRotatingFileHandler(RotatingFileHandler):
    def __init__(self, filename, **kws):
        self.backupCount = int(kws.get('backupCount', 0))
        if 'maxBytes' in kws.keys():
            kws['maxBytes'] = conv_to_bytes(kws['maxBytes'])

        for a in ('maxBytes', 'backupCount'):
            if a in kws.keys() and not isinstance(kws[a], int):
                kws[a] = int(kws[a])
        RotatingFileHandler.__init__(self, filename, **kws)

    def compress_log(self, old_log):
        with open(old_log) as log:
            with gzip.open(old_log + '.gz', 'wb') as zf:
                zf.writelines(log)
        rm(old_log)

    def doRollover(self):
        if self.stream:
            self.stream.close()
            self.stream = None
        if int(self.backupCount) > 0:
            for i in range(int(self.backupCount) - 1, 0, -1):
                sfn = "%s.%d.gz" % (self.baseFilename, i)
                dfn = "%s.%d.gz" % (self.baseFilename, i + 1)
                if os_path.exists(sfn):
                    if os_path.exists(dfn):
                        rm(dfn)
                    ren(sfn, dfn)
            dfn = self.baseFilename + ".1"
            if os_path.exists(dfn):
                rm(dfn)
            if os_path.exists(self.baseFilename):
                try:
                    ren(self.baseFilename, dfn)
                except Exception as e:
                    msg = e.strerror if platform.system() != 'Windows' else e.strerror.decode('cp1251')
                    print(u"ERR: on rename {0} -> {1} - {2}".format(self.baseFilename, dfn, msg))
                self.compress_log(dfn)
        if not self.delay:
            self.stream = self._open()
