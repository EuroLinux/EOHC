#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os, sys, subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.lib.network import NetworkTest, Wireless


class WlanTest(NetworkTest):

    def __init__(self, path=None):
        if path:
            path = "wlan/" + path
        else:
            path = "wlan"
        NetworkTest.__init__(self, path)
        self.required_support = None
        self.proc_net_dev = "/proc/net/dev"
        self.interface_connect = "nmcli dev connect"
        self.interactive = False
        self.priority = 2 # set priority high so it runs before longer tests
        self.device = None
        self.logical_device_name = ""

    def get_required_rpms(self):
        install = ' '.join(NetworkTest.get_required_rpms(self))
        install = install + " rfkill"
        return install.split(' ')

    def plan(self):
        # get the wireless device name
        wireless = Wireless()
        interfaces = wireless.get_interfaces()
        speed_info_list = [{"supp": "g","speed": 22}, {"supp": "n","speed": 100}, {"supp": "ac","speed": 300}, {"supp": "ax","speed": 1200}]
        tests = list()
        if interfaces:
            devices = self.get_network_devices()
            print("Interfaces: " + str(interfaces))
            for info in speed_info_list:
                print("Checking Wireless" + info["supp"].upper())
                self.path = "wlan/Wireless" + info["supp"].upper()
                self.required_support = info["supp"]
                self.enforce_support = True
                self.interface_speed = info["speed"]
                self.enforce_speed = True
                for (logical_device, device) in devices.items():
                    if logical_device in interfaces and self.is_best_type(wireless.get_type(logical_device)):
                        print("Found match!")
                        test = self.make_copy()
                        test.device = device
                        test.logical_device_name = logical_device
                        tests.append(test)
        return tests

    def is_best_type(self, supported_types):
        """ return True if this type is the best in the list """
        if supported_types:
            for type in ["ax", "ac", "n", "g"]:
                if type in supported_types:
                    return type == self.required_support
        # if ax, ac, n or g is not supported and we don't require support, we're the best
        return not self.required_support

    def run(self):
        result = True
        if not self.run_sub_test(self.log_proc_net_dev, "Wireless log proc info", "check details in log " + self.proc_net_dev):
            result = False
        if not self.run_sub_test(self.scan, "Wireless scan networks", "show all available networks"):
            result = False
        if not self.run_sub_test(self.iw, "Wireless info", "show informations about connection"):
            result = False
        if self.required_support and not self.run_sub_test(self.checkSupport, "Wireless support", "show information about support"):
            result = False
        if NetworkTest.run(self) != True:
            result = False
        if result:
            print("Wlan test PASSED")
        else:
            print("Wlan test FAILED")
        return result

    # 1. output of /proc/net/Dev should provide wireless interfaces details.
    def log_proc_net_dev(self):
        try:
            print(subprocess.getoutput("cat " + self.proc_net_dev))
        except Exception as e:
            print("Error: could not log %s" % self.proc_net_dev)
            print(e)
            return False
        return True

    # 2. should provide list of access points in scan range of <dev> and properties of AP
    def scan(self):
        commands = ["iw %s link" % self.logical_device_name, "iw %s scan" % self.logical_device_name]
        for command in commands:
            try:
                print(subprocess.getoutput(command))
            except Exception as e:
                print("Error: %s:" % command)
                print(e)
                return False
        return True

    # 3. Following iw commands are useful for simple outputs
    def iw(self):
        commands = ["iw %s link" % self.logical_device_name, "iw %s info" % self.logical_device_name]
        for command in commands:
            try:
                print(subprocess.getoutput(command))
            except Exception as e:
                print("Error: %s:" % command)
                print(e)
                return False
        return True

    # 4. Should provide information about support
    def checkSupport(self):
        wireless = Wireless()
        if self.required_support in wireless.get_type(self.logical_device_name):
            print("Wireless %s is supported." % self.required_support.upper())
            return True
        print("Error: wireless %s is not supported by %s" % (self.required_support.upper(), wireless.get_type(self.logical_device_name).upper()))
        return False

if __name__ == "__main__":
    test = WlanTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    print(tests)
    for test in tests:
        value = test.run()
    sys.exit(0)
