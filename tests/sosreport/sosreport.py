#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import sys, os, glob, subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test
from core.report import GenerateSystemReport

class SosreportTest(Test):

    def __init__(self):
        Test.__init__(self, "sosreport")
        self.interactive = False
        self.priority = 9
        self.device = None
        self.source = None

    def run(self):
        result = True
        system_report = GenerateSystemReport()
        if not self.run_sub_test(system_report.run_generation, name="Sosreport generation", description="generate full system report"):
            print("Sosreport test FAILED")
            result = False
        sosreports = ' '.join(glob.glob('./sosreport-*.tar.xz'))
        if sosreports == '':
            print("Sosreport test FAILED")
            result = False
        else:
            print("Script generated files: %s" % sosreports)
            print("Cleanup those files . . .")
            subprocess.getoutput('rm -rf %s' % sosreports)
        print("Sosreport test PASSED")
        return result

if __name__ == "__main__":
    test = SosreportTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    returnValue = test.run()
    sys.exit(returnValue)