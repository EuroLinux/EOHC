#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import sys, time, os, subprocess

directory = subprocess.getoutput("cat \"/tmp/eohc_workdir\"")
if directory == "":
    directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test
from core.lib.continuation import Continuation

class RebootTest(Test):

    def __init__(self):
        Test.__init__(self, "reboot")
        self.interactive = False
        self.priority = 10 # run last
        self.coreCollector = "makedumpfile -d 31"
        self.kdumpConfigPath = "/etc/kdump.conf"
        self.continuation = Continuation()

    def reboot(self):
        print("The system must be restarted for this test")

        # set up restart, and log start time
        self.continuation.set_init_config(self.get_path(), "reboot")

        # we need a delay here to give hwcert time to finish writing results.xml
        sys.stdout.flush()
        self.wait_for_lull()

        print(subprocess.getoutput("shutdown -r 0"))

        # wait here for reboot
        waitTime = 60 #sec
        print("Waiting for shutdown...")
        time.sleep(waitTime)
        print("Error: shutdown took too long")
        return False

    def run(self):
        if self.continuation.isInitialized():
            workdir = directory + "/"
            self.mark_output("Reboot", path=workdir)
            result = self.continuation.verify(marker=self.get_path())
            self.mark_summary(result, path=workdir)
            self.continuation.removeInitConfig()
            self.close_output(path=workdir)
            # remove task from crontab
            subprocess.getoutput("sed -i '$ d' /etc/crontab")
            subprocess.getoutput("echo \"Reboot test PASSED\" >> %s/eohc.log" % (directory))
        else:
            subprocess.getoutput("pwd > \"/tmp/eohc_workdir\"")
            filepath = os.path.join(subprocess.getoutput("pwd"), 'tests/reboot/reboot.py')
            # add one task to crontab
            subprocess.getoutput("echo \"@reboot root %s\" >> /etc/crontab" % (filepath))
            result = self.reboot()

        return result

if __name__ == "__main__":
    test = RebootTest()
    returnValue = test.run()
    sys.exit(returnValue)
