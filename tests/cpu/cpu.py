#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import sys
import subprocess
import inspect
import os
from distutils.version import LooseVersion

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.controller import Controller
from core.release import EuroLinuxRelease
from core.test import Test



class CpuTest(Test):

    def __init__(self):
        Test.__init__(self, "cpu")
        self.release = EuroLinuxRelease()
        self.stress = "stress-ng" if LooseVersion(
            self.release.get_version_point_update()) >= LooseVersion("8.6") else "stress"
        self.interactive = False
        self.priority = 5 # medium

    def get_required_rpms(self):
        rpms = list()
        if "EuroLinux" in self.release.get_product() and self.release.get_version() >= 6 and self.release.get_arch() == "ppc64":
            rpms.append("tree")  # for tree command
        rpms.append(self.stress)
        return rpms

    def run(self):
        result = True
        if not self.run_sub_test(self.get_memory_info, "CPU limits", "get test parameters based on hardware"):
            print("Error: could not determine memory limits, using default settings")
            result = False
        if not self.run_sub_test(self.run_clock_test, "CPU clocktest", "running clock tests"):
            result = False
        if not self.run_sub_test(self.run_stress, "CPU stress", "running stress tests"):
            result = False
        if result:
            print("CPU test PASSED")
        else:
            print("CPU test FAILED")
        return result

    def get_clock_info(self):
        print("Clock Info: ------------------------------------------")
        controller = Controller()
        clock_info = controller.get_system_log_since_boot()
        tsc = False
        clocksource = None
        for line in clock_info:
            if "TSC" in line or "clocksource" in line or " tsc " in line:
                print(line[line.find("kernel"):].strip())
                if "tsc" in line and "clocksource" in line:
                    tsc = True
                    clocksource = "TSC"
                elif "clocksource" in line:  # clocksource set to some other clock
                    tsc = False
                    clocksource = line.split()[-1]
        print("")
        if clocksource:
            print("Clock Source per system log: " + clocksource)
        else:
            print("Warning: could not determine clocksource from system log.")
        sys_current_clock_source = "/sys/devices/system/clocksource/clocksource*/current_clocksource"
        clocksource = subprocess.getoutput("cat " + sys_current_clock_source)
        print("Clock Source in " + sys_current_clock_source + ": " + clocksource)
        print("")
        return tsc

    def is_intel(self):
        print("")
        print("current function: " + inspect.stack()[0][3])
        try:
            intel = subprocess.getoutput(
                "cat /proc/cpuinfo | grep vendor | head -n 1")
            vendor = intel.split()[-1]
            print("CPU Vendor: " + vendor)
            if vendor in ["Intel", "GenuineIntel"]:
                return True
            return False
        except:
            return False

    def run_clock_test(self):
        try:
            # run clock tests - jitter and direction
            using_tsc = self.get_clock_info()
            if self.is_intel() and not using_tsc:
                print("Warning: Intel processor(s) not using TSC")
                # warn only for now
                # result = False
            print("Running clock tests")
            clock_test = subprocess.getstatusoutput("./tests/cpu/clocktest")
            if clock_test[0] == 0:
                return True
            else:
                return False
        except Exception as e:
            print("Error:")
            print(e)
            return False

    def run_stress(self):
        try:
            limit = 10  # min.
            number_of_processes = 12
            process_size = 128  # MB
            # check memory limits
            if self.free_memory < (number_of_processes * process_size):
                process_size = int(self.free_memory/number_of_processes)
                print("Note: scaling back %u processes at %u MB for memory limit of %u MB" % (
                    number_of_processes, process_size, self.free_memory))

            print("Running %s for %u min." % (self.stress, limit))
            stress = subprocess.getstatusoutput("%s --cpu %u --io %u --vm %u --vm-bytes %uM --timeout %um" % (
                self.stress, number_of_processes, number_of_processes, number_of_processes, process_size, limit))
            if stress[0] == 0:
                return True
            else:
                return False
        except Exception as e:
            print("Error:")
            print(e)
            return False


if __name__ == "__main__":
    test = CpuTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    returnValue = test.run()
    sys.exit(returnValue)
