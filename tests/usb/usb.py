#!/usr/bin/python3
# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Author: Greg Nichols
#
import os, sys, re, subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test
from core.lib.devices import get_devices
from core.lib.command_line import prompt_integer, prompt_confirm

class UsbTestBase(Test):

    def __init__(self, path):
        Test.__init__(self, "usbbase/" + path)
        self.plugged_in_devices = list()
        self.deviceDetector = None
        self.interactive = True
        self.priority = 5 # medium

    def set_plugged_in_devices(self):
        devices = get_devices()
        if not devices:
            return None
        self.plugged_in_devices = list()
        for dev in devices:
            found = self.get_only_usb_details(dev)
            if found:
                (bus_id, dev_num, name, device_id) = found
                self.plugged_in_devices.append(device_id)

    def list_all_new_plugged(self):
        ''' should run set_plugged_in_devices() first
            returns list of all newly plugged ports '''
        items = []
        devices = get_devices()
        if not devices:
            return None
        for dev in devices:
            found = self.get_only_usb_details(dev)
            if found:
                (bus_id, dev_num, name, device_id) = found
                if (not device_id in self.plugged_in_devices) and bus_id and dev_num:
                    print("    %s appears to be plugged into bus %s port %s" % (name, bus_id, dev_num))
                    items.append((bus_id, dev_num, name, device_id))
        return items

    def check_unplugged(self, search_id):
        ''' should run set_plugged_in_devices() first '''
        devices = get_devices()
        if not devices:
            return True
        for dev in devices:
            found = self.get_only_usb_details(dev)
            if found:
                (bus_id, dev_num, name, device_id) = found
                if device_id == search_id:
                    return False

        return True

    def get_only_usb_details(self, device):
        if (device.get("SUBSYSTEM") != "usb" or
            device.get("DEVTYPE") != "usb_device" or
            device.get("ID_BUS") != "usb" or
            device.get("BUSNUM") == "" or
            device.get("DEVNUM") == ""):
                return None

        device_id = device.get("DEVPATH")
        bus_id = device.get("BUSNUM")
        dev_num = device.get("DEVNUM")
        name = "%s %s" % (device.get("ID_VENDOR"), device.get("ID_MODEL"))

        return (bus_id, dev_num, name, device_id)


class UsbTest(UsbTestBase):

    def __init__(self):
        UsbTestBase.__init__(self, "usb")
        self.require_version = 0 # no required version (unknown)
        self.expected_speed = None
        self.usb = None

    def get_required_rpms(self):
        return ["usbutils"]

    def plan(self):
        tests = list()
        while True:
            if prompt_confirm("Make sure that all testing USB sockets are free - begin test?"):
                break
        usb_types = [{"path": "usb2", "require_version": 2, "expected_speed": None},
                    {"path": "usb3_5gbps", "require_version": 3, "expected_speed": 5000},
                    {"path": "usb3_10gbps", "require_version": 3, "expected_speed": 10000},
                    {"path": "usb3_20gbps", "require_version": 3, "expected_speed": 20000},
                    {"path": "usb4_20gbps", "require_version": 4, "expected_speed": 20000},
                    {"path": "usb4_40gbps", "require_version": 4, "expected_speed": 40000}]
        devices = get_devices("usb")
        print(subprocess.getoutput("lsusb -t"))
        for usb_type in usb_types:
            self.path = "usbbase/" + usb_type.get("path")
            self.require_version = usb_type.get("require_version")
            self.expected_speed = usb_type.get("expected_speed")
            for device in devices:
                (root_hubs, root_hubs_by_id) = self.get_root_hubs()
                id  = "%s:%s" % (device.get("ID_VENDOR_ID"), device.get("ID_MODEL_ID"))
                if id in root_hubs_by_id and self.require_version == root_hubs_by_id[id].get("major-version"):
                    test = self.make_copy()
                    test.usb = device
                    tests.append(test)
                    # only plan one test no matter how many are found
                    break
        return tests

    def get_ls_usb_devices(self):
        pipe = os.popen("lsusb")
        devices = list()
        # lsusb output is expected to look like this
        # Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
        pattern = re.compile("Bus (?P<bus>[0-9]+) Device (?P<device>[0-9]+): ID (?P<id>[^\ ]+) (?P<product>.+)$")
        while True:
           line = pipe.readline()
           if not line:
               break
           match = pattern.search(line)
           if match:
               properties = dict()
               for attribute in ["bus", "device", "id", "product"]:
                   properties[attribute] = match.group(attribute)
               devices.append(properties)

        return devices

    def get_root_hubs(self):
        devices = self.get_ls_usb_devices()
        root_hubs_by_id = dict() # indexed by ID
        root_hubs = list()
        pattern = re.compile("Linux Foundation (?P<major>[0-9]+).(?P<minor>[0-9]+) root hub")
        for device in devices:
            match = pattern.search(device.get("product"))
            if match:
                try:
                    device["major-version"] = int(match.group("major"))
                    device["minor-version"] = int(match.group("minor"))
                    root_hubs_by_id[device.get("id")] = device
                    root_hubs.append(device)
                except ValueError:
                    print("Warning: could not parse major/minor bus version")
        return (root_hubs, root_hubs_by_id)
    
    def get_root_hub(self, bus):
        (root_hubs, root_hubs_by_id) = self.get_root_hubs()
        for root_hub in root_hubs:
            try:
                if int(root_hub.get("bus")) == int(bus):
                    return root_hub
            except ValueError:
                pass
        return None

    def check_root_hub(self, bus_id):
        root_hub = self.get_root_hub(bus_id)
        if not root_hub:
            if self.require_version:
                print("Error: could not find version of connected hub for bus ID %s" % bus_id)
                return False
            else:
                print("    could not find connected root hub")
                return True
        else:
            print("    connected to root hub %s %s" % (root_hub.get("id"), root_hub.get("product")))
            if self.require_version:
                if root_hub.get("major-version") == self.require_version:
                    print("Success: Plugged device is connected to a version %s root hub." % root_hub.get("major-version"))
                    print("test version: %s" % self.require_version)
                    return True
                else:
                    print("Warning: Plugged device is connected to a version %s root hub." % root_hub.get("major-version"))
                    print("test version: %s" % self.require_version)
                    return False

    def check_speed(self, dev_path):
        """
        This function checks the speed of the given device.
        eg: dev_path = "/devices/pci0000:00/0000:00:14.0/usb2/2-2"
        """
        # For USB2 where expected speed is None
        if not self.expected_speed:
            return True

        # Get Tx Lanes using the file `/sys/devices/pci0000:00/0000:00:14.0/usb2/2-2/tx_lanes`
        tx_lanes = 1
        tx_file_path = os.path.join("/sys/", dev_path.lstrip("/"), "tx_lanes")
        if os.path.isfile(tx_file_path):
            try:
                tx_lanes = int(subprocess.getoutput("cat %s" % tx_file_path))
            except Exception:
                print("Warning: Exception occurred while fetching tx_lanes. "
                      "Using the default value : %s" % tx_lanes)

        # Get the speed of the device using the file `/sys/devices/pci0000:00/0000:00:14.0/usb2/2-2/speed`
        speed_file_path = os.path.join("/sys/", dev_path.lstrip("/"), "speed")
        if os.path.isfile(speed_file_path):
            try:
                device_speed = int(subprocess.getoutput("cat %s" % speed_file_path))
            except Exception as e:
                print("Warning: Exception occurred while fetching device speed.")
                print(e)
                return False

            # PCFTD-291 - scenario where device_speed returns the correct value
            if int(device_speed) == int(self.expected_speed):
                print("Device matches the expected speed (%sM). Speed: %sM"
                      % (self.expected_speed, device_speed))
                return True

            # total speed is device speed * no of lanes
            total_speed = int(device_speed * tx_lanes)
            if total_speed == int(self.expected_speed):
                print("Device matches the expected speed (%sM). Speed: %sM, Lane(s): %s"
                      % (self.expected_speed, device_speed, tx_lanes))
                return True
            print("Warning: Device doesn't match expected speed (%sM). Speed: %sM, Lane(s): %s"
                  % (self.expected_speed, device_speed, tx_lanes))
            return False
        # Speed file is not found
        print("Warning: Unable to get the speed of the device !!")
        return False

    def run_plug_test(self):
        speed_info = ""
        if self.expected_speed is not None:
             speed_info = " (speed: %sMb/s)" % str(self.expected_speed)
        info = str(self.require_version) + speed_info

        print("USB%s test:" % info)
        self.pluggedPorts = list()
        self.set_plugged_in_devices()
        self.fixed_devices = len(self.plugged_in_devices)

        self.sockets_number = prompt_integer("How many USB%s sockets are required to be tested? " % info)
        if self.sockets_number < 1:
            print("No USB sockets to test")
            return "PASS"

        while len(self.plugged_in_devices) - self.fixed_devices < self.sockets_number:
            print("testing socket %s of %s..." % (len(self.plugged_in_devices) - self.fixed_devices + 1, self.sockets_number))
            if prompt_confirm("Please plug in a USB%s device - begin test?" % str(self.require_version)):
                valid = False
                # find out which port was plugged
                for found in self.list_all_new_plugged():
                    (bus_id, dev_num, name, device_id) = found
                    # when not required check_speed (like in usb2) simply returns True in every call
                    if self.check_root_hub(bus_id) and self.check_speed(device_id):
                        print("found inserted device on expected hub version meeting speed criteria")
                        valid = True
                        break
                if not valid:
                    if prompt_confirm("Unable to detect the USB Device. Please unplug the device and try again. - continue?"):
                        continue
                    else:
                        return "ABORT"
                if prompt_confirm("Please unplug the device - continue?"):
                    if self.check_unplugged(device_id):
                        print("confirmed device %s (%s) unplugged" % (name, device_id))
                        self.plugged_in_devices.append(device_id)
                    else:
                        print("Did not confirm the device - repeating test.")
            else:
                return "ABORT"

        if len(self.plugged_in_devices) - self.fixed_devices == self.sockets_number:
            return "PASS"
        else:
            return "FAIL"

    def run(self):
        speed_info = ""
        if self.expected_speed is not None:
             speed_info = " (speed: %sMb/s)" % str(self.expected_speed)
        info = str(self.require_version) + speed_info
        if not self.run_sub_test(self.run_plug_test, "USB%s hotplug" % info, "Run USB%s hot-plug/unplug test" % info):
            print("USB test FAILED")
            return False
        print("USB test PASSED")
        return True

if __name__ == "__main__":
    test = UsbTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        test.run()
    sys.exit(0)
