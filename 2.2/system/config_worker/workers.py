# -*- coding: utf-8 -*-

from os import path as os_path, walk as os_walk
from sys import argv
import ConfigParser

__all__ = ['read_config', 'update_value', ]

FOUND_PATHS = dict()


def __get_file_path(f_name, dir_name):
    res_path = None

    for root, dirs, files in os_walk(dir_name):
        if res_path:
            break
        if f_name in files:
            res_path = os_path.abspath(os_path.join(root, f_name))
        else:
            if len(dirs) > 0:
                for d in dirs:
                    res_path = __get_file_path(f_name, os_path.join(root, d))
                    if res_path:
                        break
            else:
                return None
    return res_path


def read_config(file_name, dir_name=os_path.dirname(os_path.abspath(argv[0]))):
    global FOUND_PATHS
    if file_name not in FOUND_PATHS.keys():
        FOUND_PATHS[file_name] = __get_file_path(file_name, dir_name)
    file_path = FOUND_PATHS.get(file_name, None)

    result = {}
    if file_path and os_path.isfile(file_path):
        parser = ConfigParser.ConfigParser()
        try:
            parser.read(file_path)
        except ConfigParser.ParsingError as e:
            print('ERR: {0}'.format(e))
        except ConfigParser.Error as e:
            print('ERR: {0}'.format(e))
        for el in parser.sections():
            conf_params = {}
            for el_param in parser.options(el):
                conf_params[el_param] = parser.get(el, el_param)
            result[el] = conf_params
    else:
        print('ERR: File %s is not exists!' % file_name)
    return result if len(result) > 0 else None


def update_value(file_name, section, parameter, value, dir_name=os_path.dirname(os_path.abspath(argv[0]))):
    global FOUND_PATHS
    if file_name not in FOUND_PATHS.keys():
        FOUND_PATHS[file_name] = __get_file_path(file_name, dir_name)

    file_path = FOUND_PATHS.get(file_name, None)
    cfg = ConfigParser.ConfigParser()
    try:
        cfg.read(file_path)
        cfg.set(section, parameter, value)
    except ConfigParser.Error as e:
        print('ERR: {0}'.format(e))

    try:
        with open(file_path, 'w') as cf:
            cfg.write(cf)
    except IOError as e:
        print('ERR: {0}'.format(e))
