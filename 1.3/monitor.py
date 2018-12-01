import sys
import getopt
from siebel_collector.scollector import SiebelCollector
from system.info import *


def show_tl(sc):
    print("Available target names:")
    for t_name in sc.target_list:
        print '- %s' % t_name


def main(argv):
    target = ''
    sc = SiebelCollector()

    if len(argv) > 0:
        try:
            opts, args = getopt.getopt(argv, "hld:t:", ["help", "list_targets", "debug=", "target="])
        except getopt.GetoptError:
            show_usage()
            sys.exit(2)
        for opt, arg in opts:
            if opt in ('-h', '--help'):
                show_version()
                show_usage()
                sys.exit()
            elif opt in ('-l', '--list_targets'):
                show_tl(sc)
                sys.exit()
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


if __name__ == "__main__":
    main(sys.argv[1:])
