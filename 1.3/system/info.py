def show_usage():
    print("\nUsage: monitor.py [-d <DEBUG_VALUE> (not required) -s <TARGET> (not required)]")
    print("If you run monitor.py without parameters, will be processed by all available targets in the normal mode.\n")
    print("\t-d, --debug\t\t- Enable debug mode")
    print("\t\tDEBUG_VALUE=ALL(debug all steps) or COL(debug collect step) or SND(debug sending step)\n")
    print("\t-l, --list_targets\t- Print avalable target names")
    print("\t-t, --target\t\t- Processing a specific target. The name is taken from the file \"targets.ini\"")
    print("\t-h, --help\t\t- Print this help\n\n")


def show_version():
    print("----------------------------------------------------------------------------")
    print("PMon version 1.3 (c) created by Andrey Kostrenko")
    print("----------------------------------------------------------------------------")
