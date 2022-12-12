#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os, sys, time, syslog

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test
from core.release import EuroLinuxRelease
from core.controller import Controller
from core.lib.command_line import prompt_confirm
from core.lib.devices import get_devices


# from rhcert.tags import Constants

class SuspendTest(Test):

    def __init__(self):
        Test.__init__(self, "suspend")
        self.release = EuroLinuxRelease()
        self.hwcert_controller = Controller()
        self.interactive = True
        self.priority = 5 # medium
        self.known_methods = ["mem", "disk"]
        self.need_to_reset_mem_sleep_to_default = False
        self.mem_sleep_file_path = os.path.join("/sys/power/mem_sleep")
        self.state_file_path = os.path.join("/sys/power/state")
        # Messages:
        self.suspend_message = dict()
        self.suspend_message["mem"] = "Starting Suspend"
        self.suspend_message["disk"] = "Starting Hibernate"
        self.state_message = dict()
        self.state_message["mem"] = ["PM: suspend entry (deep)", "PM: Entering mem sleep"]
        platform_specific_entry = "PM: hibernation: hibernation entry" if self.release.get_version() > 8 else "PM: hibernation entry"
        self.state_message["disk"] = [platform_specific_entry, "PM: Creating hibernation image"]
        # RHEL-8 and above specific sub-tests
        if int(self.release.get_version()) >= 8:
            self.known_methods.append("freeze")
            self.suspend_message["freeze"] = "Starting Freeze"
            self.state_message["freeze"] = ["PM: suspend entry (s2idle)", "PM: Entering freeze sleep"]

    def plan(self):
        tests = list()
        devices = get_devices("power_supply")
        for device in devices:
            if "BAT" in device["POWER_SUPPLY_NAME"] and self.get_suspend_methods():
                test = self.make_copy()
                tests.append(test)
                break
        return tests

    # Suspend
    def get_suspend_methods(self):
        methods = list()
        sys_power_state = open(self.state_file_path, "r")
        if sys_power_state:
            while True:
                line = sys_power_state.readline()
                if not line:
                    break
                states = line.split()
                for state in states:
                    if state in self.known_methods:
                        methods.append(state)

        if "mem" in methods and os.path.isfile("/sys/power/mem_sleep") \
                and 'deep' not in open("/sys/power/mem_sleep", "r").read():
            print("Warning: Removing suspend to memory option as `deep` is not present in `/sys/power/mem_sleep`")
            methods.remove("mem")
        if not methods:
            print("Error: could not determine allowable suspend methods")

        return methods

    def suspend_without_os_command(self, method):
        """ suspend using a write operation to /sys/power/state """
        if method == "mem" and os.path.exists(self.mem_sleep_file_path) \
                and '[s2idle]' in open(self.mem_sleep_file_path, "r").read():
            self.need_to_reset_mem_sleep_to_default = True if \
                os.system("echo deep > {}".format(self.mem_sleep_file_path)) == 0 else False
        sys_power_state = open(format(self.state_file_path), "w")
        if sys_power_state:
            sys_power_state.write(method)
            sys_power_state.close()
        else:
            print("Error: could not suspend the system")
            return False
        return True

    def suspend(self, source, method):
        print("This test will suspend the operating system.")
        print("Please resume by pressing the power button after suspend has completed.")
        sys.stdout.flush()
        markerName = "%s-%s-%s" % (self.get_path(), source, method)
        syslog.syslog(self.hwcert_controller.get_system_log_marker(markerName, "begin"))
        if source == "OSCommand":
            if not prompt_confirm(" suspend? "):
                return False
            waitTime = 5
            print("Suspending in %d sec" % waitTime)
            sys.stdout.flush()
            time.sleep(waitTime)
            return self.suspend_without_os_command(method)
        elif source == "FunctionKey":
            if not prompt_confirm(
                    "Does this system have a function key (Fn) to suspend the system to %s?" % method):
                print("Warning: suspend test to %s not run from function key" % method)
                return False
            if not prompt_confirm(
                    "Are you ready to press the function key (Fn) to suspend the system to %s. Answer the question and then press the function key (Fn) if you want to suspend the system" % method):
                return False
            return True
        else:
            print("Error: unknown suspend source")
            return False

    # Resume
    def check_resume(self, source, method):
        self.verified_resume_method = None
        sys.stdout.flush()
        prompt_confirm("Has resume completed? ")
        markerName = "%s-%s-%s" % (self.get_path(), source, method)
        syslog.syslog(self.hwcert_controller.get_system_log_marker(markerName, "end"))

        # get system log path
        log = self.hwcert_controller.get_system_log("%s-%s-%s" % (self.get_path(), source, method))

        if source == "FunctionKey":
            try:
                suspend_message = self.suspend_message[method]
            except KeyError:
                print("Error: unknown suspend method %s" % method)
                return False
            if not suspend_message in log:
                print("Error: could not verify suspend")
                return False

        # check suspend/hibernate/freeze message (given by kernel)
        suspend_message = "Freezing user space processes"
        if not suspend_message in log:
            print("Error: could not verify suspend")
            return False

        print("Verified suspend")
        resume_message = "Restarting tasks"
        if not resume_message in log:
            print("Error: could not verify resume")
            return False

        # check that they used the correct method
        for state in self.state_message.keys():
            method_messages = self.state_message[state]
            for method_message in method_messages:
                if method_message in log:
                    self.verified_resume_method = state
                    print("Found '%s' in log messages" % method_message)
                    break
            if self.verified_resume_method:
                break

        if not self.verified_resume_method:
            print("Error: No valid suspend method found in logs")
            return False
        if method != self.verified_resume_method:
            print("Error: The suspend method was %s and should have been %s" % (self.verified_resume_method, method))
            return False

        print("Verified resume from %s" % self.verified_resume_method)
        return True

    def reset_mem_sleep_to_default(self):
        if self.need_to_reset_mem_sleep_to_default:
            self.need_to_reset_mem_sleep_to_default = False if \
                os.system("echo s2idle > {}".format(self.mem_sleep_file_path)) == 0 else True

    def run_suspend_resume(self, source, method):
        if self.suspend(source, method):
            status = self.check_resume(source, method)
            self.reset_mem_sleep_to_default()
            return status
        elif source == "FunctionKey":
            # allow user to opt-out of fn key tests, since system may not have them
            self.verified_resume_method = method
            self.reset_mem_sleep_to_default()
            return True
        else:
            return False

    def run(self):
        methods = self.get_suspend_methods()
        if not methods:
            return False
        result = True
        for source in ["OSCommand", "FunctionKey"]:
            for method in methods:
                self.mark_output(name="Suspend " + source + "-" + method)
                if not self.run_suspend_resume(source, method):
                    result = False
                    self.mark_summary("FAIL")
                elif self.verified_resume_method != method:
                    result = False
                    self.mark_summary("FAIL")
                else:
                    self.mark_summary("PASS")
        self.close_output()
        if result:
            print("Suspend test PASSED")
        else:
            print("Suspend test FAILED")
        return result


if __name__ == "__main__":
    test = SuspendTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        value = test.run()
        if value != 0:
            sys.exit(value)
    sys.exit(0)
