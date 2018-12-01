from system.logger import *

def read_config(file_name):
    import os.path
    import ConfigParser
    result = {}
    if os.path.isfile(file_name):
        parser = ConfigParser.ConfigParser()
        parser.read(file_name)
        for el in parser.sections():
            conf_params = {}
            for el_param in parser.options(el):
                conf_params[el_param] = parser.get(el, el_param)
            result[el] = conf_params
    else:
        write_log('ERR: File '+file_name+' is not exists!')
    return result

