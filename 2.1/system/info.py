def show_usage():
    import platform

    if platform.system() == 'Windows':
        tab_mult = {'d': 4, 'T': 2, 't': 3, 'S': 1, 's': 3, 'h': 4}
    else:
        tab_mult = {'d': 2, 'T': 1, 't': 2, 'S': 1, 's': 2, 'h':2}

    print("\nUsage: monitor.py [-d <DEBUG_VALUE> (not required) -t <TARGET> (not required) -s <SIEBEL_DATA_TYPE> "
          "(not required)]")
    print("If you run monitor.py witout parameters, will be processed by all available targets and all available "
          "siebel data types in the normal mode.\n")
    print("\t-d, --debug" + "\t"*tab_mult['d'] + "- Enable debug mode")
    print("\t\tDEBUG_VALUE=ALL(debug all steps) or COL(debug collect step) or SND(debug sending step)\n")
    print("\t-T, --list_targets" + "\t"*tab_mult['T'] + "- Print avalable target names")
    print("\t-t, --target" + "\t"*tab_mult['t'] + "- Processing a specific target. The name is taken from the file "
                                                  "\"targets.ini\"")
    print("\t-S, --list_data_types" + "\t"*tab_mult['S'] + "- Print avalable siebel data types")
    print("\t-s, --data_type" + "\t"*tab_mult['s'] + "- Processing a specific siebel data type. ")
    print("\t-h, --help" + "\t"*tab_mult['h'] + "- Print this help\n\n")


def show_version():
    print("----------------------------------------------------------------------------")
    print("PMon version 2.1 (c) created by Andrey Kostrenko")
    print("----------------------------------------------------------------------------")
