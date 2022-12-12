#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os, sys, time

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test
from core.lib.command_line import prompt_confirm
from core.lib.devices import get_devices, get_attr

class BatteryTest(Test):

    def __init__(self):
        Test.__init__(self, "battery")
        self.interactive = True
        self.priority = 6 # run after some tests
        self.battery = None
        self.ac_adapter_device = None
        self.unit_factor = 1000 # parse from mu-Wh to mWh
        self.units = "mWh"

    def get_required_rpms(self):
        return ["upower"]

    def plan(self):
        tests = list()
        ac_adapter_device = None
        devices = get_devices("power_supply")
        for device in devices:
            type = get_attr(device, "type")
            if type == "Battery":
                test = self.make_copy()
                battery = device
                tests.append(test)
            if type == "Mains":
                ac_adapter_device = device
        for test in tests:
            if ac_adapter_device:
                test.ac_adapter_device = ac_adapter_device
            if battery:
                test.battery = battery
        return tests

    def refresh_devices(self):
        """ get the battery and ac adapter devices """
        devices = get_devices("power_supply")
        for device in devices:
            type = get_attr(device, "type")
            if type == "Mains":
                self.ac_adapter_device = device
            if type == "Battery":
                self.battery = device
        if not self.battery:
            print("Error: battery is not present")
        if not self.ac_adapter_device:
            print("Error: could not find udev device for battery and AC Adapter")
            return False
        return True

    def get_status(self):
        level_full = ''
        level = ''
        """ get battery and ac adapter status """
        if self.refresh_devices():
            self.ac_adapter_present = bool(int(self.ac_adapter_device.get("POWER_SUPPLY_ONLINE")))
            # fedora uses "ENERGY" instead of "CHARGE"
            level_full = self.battery.get("POWER_SUPPLY_CHARGE_FULL")
            if not level_full:
                level_full = self.battery.get("POWER_SUPPLY_ENERGY_FULL")
            if level_full:
                self.level_full = int(level_full) / self.unit_factor
            level = self.battery.get("POWER_SUPPLY_CHARGE_NOW")
            if not level:
                level = self.battery.get("POWER_SUPPLY_ENERGY_NOW")
            self.level = int(level) / self.unit_factor
            self.charging_status = self.battery.get("POWER_SUPPLY_STATUS").lower()
            if self.charging_status == "unknown":
                self.charging_status = self.get_charging_status(self.battery.get("POWER_SUPPLY_NAME"))
            return True
        return False

    def get_charging_status(self, device_name):
        """Get the battery status using upower command"""
        print("Fetching battery status using upower command...")
        status = "unknown"
        list_cmd = "upower -e | grep %s" % device_name
        try:
            battery = os.popen(list_cmd).read()
        except Exception as e:
            print("Warning: Failed to get battery using upower command")
            print(str(e))
            return status
        status_cmd = "upower -i %s | grep state" % battery[:-1]
        try:
            status = os.popen(status_cmd).read()
        except Exception as e:
            print("Warning: Failed to get battery status using upower command")
            print(str(e))
            return status
        return status

    def print_status(self):
        state = "is" if self.ac_adapter_present else "is not"
        print("-------------------------------")
        print("AC Adapter %s connected" % state)
        print("Battery:")
        level_percentage = 100 * self.level / self.level_full
        print("    charged to %s%% - %s %s" % ( level_percentage, self.level, self.units))
        print("    current charging status is %s" % self.charging_status)
        print("-------------------------------")

    def check_status(self):
        status = True
        delta = 10     # in units of charge level
        waitTime = 10  # seconds to wait each try
        tryLimit = 10  # number of times to look for level change
        self.get_status()
        if self.charging_status == "discharging":
            if self.ac_adapter_present:
                print("Error: battery is discharging while AC adapter is connected")
                success = False

        if self.charging_status == "charging":
            if not self.ac_adapter_present:
                print("Error: battery is charging while AC adapter is disconnected")
                success = False
        # wait if status is unknown:
        tries = 0
        while self.charging_status != "charging" and self.charging_status != "discharging":
            if tries > tryLimit:
                print("Error: battery charging status is %s after retry limit." % self.charging_status)
                return False
            # otherwise
            print("battery charging status is %s, waiting..." % self.charging_status)
            tries = tries + 1
            sys.stdout.flush()
            time.sleep(waitTime)
            self.get_status()
        # check for changes in battery level.
        tries = 0
        level = self.level
        while True:
            self.get_status()
            if ((self.charging_status == "charging" and self.level > level + delta)
                    or (self.charging_status == "discharging" and self.level < level - delta)):
                print("verified battery is %s" % self.charging_status)
                break
            if tries > tryLimit:
                print("Error: could not verify battery %s" % self.charging_status)
                status = False
                break
            tries = tries + 1
            print("waiting to verify battery %s more than %s %s" % (self.charging_status, delta, self.units))
            sys.stdout.flush()
            time.sleep(waitTime)
        return status


    def battery_test(self):
        if not self.get_status():
            return False
        self.print_status()
        action = None
        tested_connected = False
        tested_disconnected = False
        while not tested_connected or not tested_disconnected:
            # ask user to add/remove AC power
            action = "disconnect" if self.ac_adapter_present else "connect"
            if not prompt_confirm("Please %s AC Power - continue? " % action):
                return False
            if not self.get_status():
                return False
            if action == "connect":
                if self.ac_adapter_present:
                    tested_connected = True
                else:
                    print("AC Power is not connected!")
                    continue
            elif action == "disconnect":
                if self.ac_adapter_present:
                    print("AC Power is not disconnected!")
                    continue
                else:
                    tested_disconnected = True
            if not self.check_status():
                return False
            if not self.get_status():
                return False
            self.print_status()
        return True

    def run(self):
        if not self.run_sub_test(self.battery_test, "Battery", "check battery status"):
            print("Battery test FAILED")
            return False
        print("Battery test PASSED")
        return True

if __name__ == "__main__":
    test = BatteryTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        value = test.run()
        if value != 0:
            sys.exit(value)
    sys.exit(0)
