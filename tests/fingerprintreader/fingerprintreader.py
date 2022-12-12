#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os
import sys
import traceback
import dbus.glib
from gi.repository import GLib
import dbus
import dbus.mainloop.glib

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.lib.command_line import prompt_confirm
from core.test import Test
from core.release import EuroLinuxRelease


class FingerprintreaderTest(Test):

    def __init__(self):      
        Test.__init__(self, "fingerprintreader")
        self.interactive = True
        self.priority = 5 # medium
        self.release = EuroLinuxRelease()
        self.reader = None
        self.bus = None
        self.proxy = None
        self.interface = None
        self.loop = None
        self.name = None
        self.scan_type = None
        self.enroll_success = False
        self.verify_success = False
        self.enroll_signal = None
        self.verify_signal = None
        self.unsuccessful_attempts = 0

    def get_required_rpms(self):
        return ["fprintd"]

    def plan(self):
        tests = list()
        try:
            bus = dbus.SystemBus()
            readers = bus.call_blocking("net.reactivated.Fprint",
                                         "/net/reactivated/Fprint/Manager",
                                         "net.reactivated.Fprint.Manager",
                                         "GetDevices",
                                         "",
                                         ())
        except dbus.exceptions.DBusException as e:
            return tests

        for reader in readers:
            self.reader = reader
            test = self.make_copy()
            tests.append(test)
        
        if len(tests) == 0:
            print("System doesn't find any fingerprint readers available.")
            if prompt_confirm("Do you have any physically?"):
                self.mark_output("Fingerprintreader", "Fingerprintreader is not available (no drivers?)")
                self.mark_summary(False)
                self.close_output()
                print("FingerprintReader test FAILED")
            else:
                self.mark_output("Fingerprintreader", "There is no fingerprintreader on this device")
                self.mark_summary("SKIP")
                self.close_output()
                print("FingerprintReader test SKIPPED")
            return []
        return tests

    def run(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()
        try:
            self.name = self.bus.call_blocking("net.reactivated.Fprint",
                                                self.reader,
                                                "org.freedesktop.DBus.Properties",
                                                "Get",
                                                "ss",
                                                ("net.reactivated.Fprint.Device", "name"))

            self.scan_type = self.bus.call_blocking("net.reactivated.Fprint",
                                                     self.reader,
                                                     "org.freedesktop.DBus.Properties",
                                                     "Get",
                                                     "ss",
                                                     ("net.reactivated.Fprint.Device", "scan-type"))
            self.proxy = self.bus.get_object("net.reactivated.Fprint", "/net/reactivated/Fprint/Device/0")
            self.interface = dbus.Interface(self.proxy, "net.reactivated.Fprint.Device")
        except dbus.DBusException as e:
            traceback.print_exc()
            print("Exception: %s" % e)
            print("Error: Exception occurred during initial configuration.")
            return False

        print("Testing '" + self.name + "' fingerprint reader:")
        if not self.run_sub_test(self.run_fingerprint_reader, "Fingerprintreader enrollment", "enroll a new fingerprint", "enroll"):
            print("FingerprintReader test FAILED")
            return False
        if not self.run_sub_test(self.run_fingerprint_reader, "Fingerprintreader verify", "verify the enrolled fingerprint", "verify"):
            print("FingerprintReader test FAILED")
            return False
        print("FingerprintReader test PASSED")
        return True

    def run_fingerprint_reader(self, type):
        if type == "enroll":
            GLib.idle_add(self.fingerprint_enroll_test)
        else:
            GLib.idle_add(self.fingerprint_verify_test)
        self.loop = GLib.MainLoop()
        self.loop.run()
        if type == "enroll":
            # self.enroll_success = False
            return self.enroll_success
        else:
            # self.verify_success = False
            return self.verify_success

    def retry_test(self, type):
        self.unsuccessful_attempts += 1
        if self.unsuccessful_attempts < 5:
            if type == "enroll":
                self.interface.EnrollStart("right-index-finger")
            else:
                self.interface.VerifyStart("right-index-finger")
            if self.scan_type == "swipe":
                print("  [%s]: Stage FAILED !!\n    Please swipe your finger more precisely" % type)
            else:
                print("  [%s]: Stage FAILED !!\n    Please place your finger more precisely" % type)
        else:
            print("ERROR: Failed to %s the finger !!\n" % type)
            self.quit_test(type)
    
    def quit_test(self, type):
        if (type == "enroll" and not self.enroll_success) or (type == "verify"):
            self.delete_enrolled_fingers("")
        self.interface.Release("")
        self.enroll_signal.remove()
        self.loop.quit()

    # Enrollment

    def delete_enrolled_fingers(self, finger_name):
        try:
            if self.release.get_version() < 8:
                self.interface.DeleteEnrolledFingers(finger_name)
            else:
                self.interface.DeleteEnrolledFingers2(finger_name)
        except Exception as e:
            print("There is no fingerprints to delete. \nMore info: %s" % e)

    def fingerprint_enroll_test(self):
        # Need to be seperate methods (enroll/verify) becouse of GLib.idle_add error: 
        # 'Callback needs to be a function or method not bool'
        try:
            self.unsuccessful_attempts = 0
            self.interface.Claim("")
            self.enroll_signal = self.interface.connect_to_signal("EnrollStatus", self.enroll_status_cb)
            self.interface.EnrollStart("right-index-finger")
            if self.scan_type == "swipe":
                print("  [enroll]: Swipe your finger through the '%s' reader." % (self.name))
            else:
                print("  [enroll]: Place your finger on the '%s' reader" % (self.name))
        except dbus.exceptions.DBusException as e:
            print("Exception: %s" % e)
            self.loop.quit()
        return False

    def enroll_status_cb(self, result, done):
        try:
            if result != "enroll-failed":
                print("  [enroll]: %s" % result)
            if done:
                if result == "enroll-completed":
                    print("INFO: Enrollment was Successful !!!")
                    self.enroll_success = True
                    self.interface.EnrollStop()
                    self.quit_test("enroll")
                elif result == "enroll-unknown-error":
                    print("ERROR: Enrollment encounter an unknown error !!!")
                    self.interface.EnrollStop()
                    self.quit_test("enroll")
            else:
                if result == "enroll-stage-passed":
                    if self.scan_type == "swipe":
                        print("  [enroll]: Stage PASSED !!\n    Swipe your finger again")
                    else:
                        print("  [enroll]: Stage PASSED !!\n    Place your finger again")
                else:
                    self.interface.EnrollStop()
                    self.retry_test("enroll")
        except dbus.exceptions.DBusException as e:
            print("Exception: %s" % e)
            self.interface.EnrollStop()
            self.quit_test("enroll")

    # Verification

    def fingerprint_verify_test(self):
        # Need to be seperate methods (enroll/verify) becouse of GLib.idle_add error: 
        # 'Callback needs to be a function or method not bool'
        try:
            self.unsuccessful_attempts = 0
            self.interface.Claim("")
            self.verify_signal = self.interface.connect_to_signal("VerifyStatus", self.verify_status_cb)
            self.interface.VerifyStart("right-index-finger")
            if self.scan_type == "swipe":
                print("  [verify]: Swipe your finger through the '%s' reader." % (self.name))
            else:
                print("  [verify]: Place your finger on the '%s' reader" % (self.name))
        except dbus.exceptions.DBusException as e:
            print("Exception: %s" % e)
            self.loop.quit()
        return False

    def verify_status_cb(self, result, done):
        print("  [verify]: %s" % result)
        try:
            self.interface.VerifyStop()
            if done:
                if result == "verify-match":
                    print("INFO: Verification was Successful !!!\n")
                    self.verify_success = True
                    self.quit_test("verify")
                elif result == "verify-no-match":
                    self.retry_test("verify")
                else:
                    self.quit_test("verify")
            else:
                self.retry_test("verify")

        except dbus.exceptions.DBusException as e:
            print("Exception: %s" % e)
            self.quit_test("verify")

if __name__ == "__main__":
    test = FingerprintreaderTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        value = test.run()
        if value != 0:
            sys.exit(value)
    sys.exit(0)
