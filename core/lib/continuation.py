#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os, time, syslog, subprocess, datetime
from core.release import EuroLinuxRelease
from core.controller import Controller

class Continuation(Controller):
    def __init__(self):
        Controller.__init__(self)
        self.rebootTimeLimit = 60 # ustawione z palca
        self.method = None
        self.timestamp = None
        self.kernel = None
        self.bootPrintPath = "/bootprint"
        self.release = EuroLinuxRelease()

    def set_init_config(self, marker, method=None):
        if self.release.get_version() < 7:
            pass
        else:
            print(subprocess.getoutput("systemctl restart systemd-journald"))
        if method:
            self.method = method
        if self.release.get_version() < 7:
            chkconfig = subprocess.getoutput("chkconfig --add rhcertd")
            print(chkconfig)
        else:
            print(subprocess.getoutput("systemctl enable rhcertd"))
            print(subprocess.getoutput("systemctl daemon-reload"))
        # get a timestamo, save it
        self.timestamp = datetime.datetime.now()
        # save it off to the side
        timestamp = open(self.bootPrintPath, "w")
        timestamp.write(self.timestamp.strftime("%Y-%m-%d %H:%M:%S") + "\n")
        if self.method:
            timestamp.write(self.method + "\n")
            timestamp.write(self.release.get_kernel() + "\n")
        timestamp.close()
        # mark the log with this run time
        markerName = "%s-%s" % (marker, self.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
        syslog.syslog(self.get_system_log_marker(markerName, "begin", pid=False))

    def removeInitConfig(self):
        if self.release.get_version() < 7:
            chkconfig = subprocess.getoutput("chkconfig --del rhcertd")
            chkconfig.echo()
        else:
            print(subprocess.getoutput("systemctl disable rhcertd"))
            print(subprocess.getoutput("systemctl daemon-reload"))

    def isInitialized(self):
        return os.path.isfile(self.bootPrintPath)

    def verify(self, marker, max_reboots=1):
        print(subprocess.getoutput("systemctl restart systemd-journald"))
        # get the log, verify reboot happened
        try:
            timestamp = open(self.bootPrintPath)
            timestamp_str = timestamp.readline().strip()
            self.timestamp = datetime.datetime(*(time.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")[0:5]))
            method = timestamp.readline()
            if method:
                self.method = method.strip()
                kernel = timestamp.readline()
                if kernel:
                    self.kernel = kernel.strip()
            timestamp.close()
            os.remove(self.bootPrintPath)

            duration = datetime.datetime.now() - self.timestamp
            print("reboot took " + str(duration))
            print("method: " + self.method)
            print("kernel: " + self.kernel)

            # failure if 2X reboot limit
            if duration.seconds > self.rebootTimeLimit*60*2:
                print("Error: reboot took longer than %u minutes" % (self.rebootTimeLimit*2))
                return False
            # warn for 1X reboot limit
            elif duration.seconds > self.rebootTimeLimit*60:
                print("Warning: reboot took longer than %u minutes" % self.rebootTimeLimit)
            kernel = self.release.get_kernel()
            if self.kernel != kernel:
                print("Error: rebooted a different kernel:")
                print("    before: " + self.kernel)
                print("    after:  " + kernel)
                return False

            log = self.get_system_log("%s-%s" % (marker, timestamp_str), pid=False)
            reboot_count = 0

            for line in log.split('\n'):
                if "kernel:" in line and self.system_log_boot_marker in line:
                    reboot_count += 1
            
            if reboot_count > max_reboots:
                print("Error: system rebooted %u times" % reboot_count)
                if max_reboots > 1:
                    print("Only %u reboots per test run are allowed." % max_reboots)
                return False
            if not reboot_count:
                print("Warning: could not detect reboot")

            print("reboot verified or otherwise accepted")
            # print "Reboot log:\n---------------------------------------------------------"
            # print log
        except Exception as e:
            print("Could not verify reboot")
            print(e)
            return False

        return True
