#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import sys, time, os, subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test
from core.lib.devices import get_devices_from_file
from core.lib.command_line import prompt_confirm

class LidTest(Test):

    def __init__(self):
        Test.__init__(self, "lid")
        self.device = ""
        self.priority = 5
        self.interactive = True

    def plan(self):
        tests = list()
        devices = get_devices_from_file("Lid Switch")
        for device in devices:
                test = self.make_copy()
                test.device = device
                tests.append(test)
        return tests

    def check_lid(self, check_for_open):
        lid_state = subprocess.getoutput("cat /proc/acpi/button/lid/*/state")
        if 'open' in lid_state:
            return check_for_open
        else:
            return not check_for_open

    def start(self):
        SLEEPLIMIT=20 # sleep cycles
        SLEEPTIME=1 # sec

        if not self.check_lid(True):
            print("Error: lid must be open for this test")
            return False
        if not prompt_confirm("Ready to begin the lid/backlight test?"):
            return False

        print("Please close the lid, verify the backlight turns off when the lid is closed, then reopen it.")
        sys.stdout.flush()

        sleep_limit = SLEEPLIMIT
        #wait while lid is open and limit has not expired
        while self.check_lid(True) and sleep_limit > 0:
            sys.stdout.write("%d..." % sleep_limit)
            sys.stdout.flush()
            time.sleep(SLEEPTIME)
            sleep_limit = sleep_limit -1
        print("")

        if sleep_limit <= 0:
            print("Error: did not detect the lid was closed within %d sec." % (SLEEPLIMIT*SLEEPTIME))
            return False

        sleep_limit = SLEEPLIMIT
        # wait while lid is closed and time is not expired
        while self.check_lid(check_for_open=False) and sleep_limit > 0:
            sys.stdout.write("%d..." % sleep_limit)
            sys.stdout.flush()
            time.sleep(SLEEPTIME)
            sleep_limit = sleep_limit -1
        print("")

        if sleep_limit <= 0:
            print("Error: did not detect the lid was re-opened within %d sec." % (SLEEPLIMIT*SLEEPTIME))
            return False
        if not prompt_confirm("Did the display backlight turn off when the lid was closed?"):
            print("Error: backlight must turn off when the lid is closed")
            return False
        return True

    def run(self):
        if not self.run_sub_test(self.start, "Lid verifying", "verify the lid and backlight"):
            print("Lid test FAILED")
            return False
        print("Lid test PASSED")
        return True


if __name__ == "__main__":
    test = LidTest()
    tests = test.plan()
    for test in tests:
        value = test.run()
        if value != 0:
            sys.exit(value)
    sys.exit(0)
