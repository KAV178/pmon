
def write_log(message, log_file='monitor.log', max_log_size='10MB'):
    import datetime
    try:
        if len(message) > 0:
            import os.path
            import re
            uom_err = ''
            zf_err = ''
            if os.path.exists(log_file):
                uom = max_log_size[-2:].upper()
                if re.match('KB|MB', uom):
                    import os
                    mls_bytes = {
                        'KB': lambda val: val * 1024,
                        'MB': lambda val: val * 1024 * 1024
                    }[uom](int(max_log_size[:len(max_log_size) - 2]))
                    if os.path.getsize(log_file) >= mls_bytes:
                        arc_name = log_file[:-4] + '_' + datetime.datetime.now().strftime("%Y%m%d%H%M") + '.log'
                        os.rename(log_file, arc_name)
                        import zipfile
                        try:
                            import zlib
                            compr_type = zipfile.ZIP_DEFLATED
                        except:
                            compr_type = zipfile.ZIP_STORED
                        zf = zipfile.ZipFile(arc_name + '.zip', mode='w', compression=compr_type)
                        try:
                            zf.write(arc_name)
                        finally:
                            zf.close()
                        if os.path.getsize(arc_name + '.zip') > 0:
                            os.remove(arc_name)
                        else:
                            try:
                                os.remove(arc_name + '.zip')
                            except IOError as e:
                                zf_err = "Logger: ERR: I/O error[code %s]: %s  - %s" % (e.errno, e.strerror, e.filename)
                                print zf_err
                else:
                    uom_err = 'Logger: ERR: Invalid format value maximum size of log file [max_size = %s]' % \
                              max_log_size

            cur_ts = datetime.datetime.now().strftime("[%Y.%m.%d %H:%M:%S]")
            lf = open(log_file, 'a')
            if len(uom_err) > 0:
                lf.write(cur_ts + ' ' + uom_err + "\n")
            if len(zf_err) > 0:
                lf.write(cur_ts + ' ' + zf_err + "\n")
            lf.write(cur_ts + ' ' + message + "\n")
            lf.close()
    except IOError as e:
        print "Logger: ERR: I/O error[code %s]: %s  - %s" % (e.errno, e.strerror, e.filename)
