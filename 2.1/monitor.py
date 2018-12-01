import sys
import getopt
from siebel_collector.scollector import SiebelCollector
from system.info import *

def show_tl(sc):
    print("Available target names:")
    for t_name in sc.target_list:
        print '- %s' % t_name


def show_sdt(sc):
    print("Available siebel data types:")
    for t_name in sc.sdata_cmd_list.keys():
        print '- %s' % t_name


def main(argv):
    target = ''
    sc = SiebelCollector()

    if len(argv) > 0:
        try:
            opts, args = getopt.getopt(argv, "hTSs:d:t:", ["help", "list_targets", "list_data_types", "data_type=",
                                                         "debug=", "target="])
        except getopt.GetoptError:
            show_usage()
            sys.exit(2)
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                show_version()
                show_usage()
                sys.exit()
            elif opt in ('-T', '--list_targets'):
                show_tl(sc)
                sys.exit()
            elif opt in ('-S', '--list_data_types'):
                show_sdt(sc)
                sys.exit()
            elif opt in ('-s', '--data_type'):
                arg_list = arg.split(",")
                checked = True
                for a in arg_list:
                    if a not in sc.sdata_cmd_list.keys():
                        checked = False
                        print '!!! ERROR !!! Invalid value for the siebel data type flag = "%s"' % a
                        show_sdt(sc)
                        break
                if checked:
                    sc.set_data_req_cmd(tuple(arg_list))
                else:
                    sys.exit(2)
            elif opt in ('-d', '--debug'):
                if arg in ('ALL', 'COL', 'SND'):
                    sc.set_dbg_level(arg)
                else:
                    print '!!! ERROR !!! Invalid value for the debug flag = "%s"' % arg
                    show_usage()
                    sys.exit(2)
            elif opt in ('-t', '--target'):
                if arg in sc.target_list:
                    target = arg
                else:
                    print '!!! ERROR !!! Invalid name of target = "%s"\n' % arg
                    show_tl(sc)
                    sys.exit(2)

    for stend in sc.target_list:
        if len(target) > 0 and stend != target:
            continue
        else:
            sc.reset_log_filename(stend)
            sc.collect_data(stend)
    sys.exit()


if __name__ == "__main__":
    main(sys.argv[1:])
