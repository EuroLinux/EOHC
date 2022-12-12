#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import copy
import os
import re
import subprocess
import sys
import time
from core.release import EuroLinuxRelease


class Test:
    def __init__(self, path):
        self.path = path
        # self.priority = 999
        self.description = ""
        self.release = EuroLinuxRelease()
        self.interactive = False
        self.marking = False # is <output> sub-section currently active?
        self.result = False
        self.test_time = 0
        self.params = ""

    """
    client abstract interface
    ------------------------------------------------------------------
    """

    def plan(self):
        """Called to generate a list of test instances.
        This default implementation returns list with self
        """
        tests = list()
        tests.append(self)
        return tests

    def get_required_rpms(self):
        """Test should implement this method if they have package
        requirements dependant on hardware or RHEL release
        returns a list of package names"""
        return list()

    def get_harmful_rpms(self):
        """Test should implement this method if they have package
        that should be removed on hardware or RHEL release.
        returns a list of package names"""
        return list()

    def install_rpms(self, rpms):
        """ performs installation of given rpms """
        str_rpms = " ".join(rpms)
        return subprocess.getstatusoutput("sudo yum install -y %s" % str_rpms)[0]

    def start(self):
        """ performs any initialization before the test is to be run """

    def run(self):
        """ run the test  - must return True for passing, False for failing"""

    def finish(self, planner, runDocument):
        """ called after test run """

    def add(self, planner):
        """ called when a test is manually (interactively) added to the plan
            subclasses should define this when more information is needed from the tester """
        pass

    """
    server abstract interface
    ------------------------------------------------------------------
    """

    def start_server(self):
        """ start server-end of the test """
        pass

    def stop_server(self):
        """ stop the server-end of the test """
        pass

    def status_server(self):
        """ display status information of server-end test services """
        pass

    """
    access
    ------------------------------------------------------------------
    """

    def get_name(self):
        return self.path.split('/')[-1]

    def get_suite_name(self):
        """
        Child class should override this.
        Keeping the path logic as a fallback approach to figure out the suite name
        """
        return self.path.split('/')[0]

    def get_path(self):
        return self.path

    # def get_priority(self):
    #     return ("%u" % self.priority)

    def get_description(self):
        return self.description

    def get_release(self):
        return self.release.dump()

    def get_interactive(self):
        return self.interactive

    def get_result(self):
        return self.result

    def get_test_time(self):
        return self.test_time

    def set_params(self, params):
        self.params = params

    def get_params(self):
        return self.params

    # def _compare(self, other):
    #     """ returns -1 self < other, 0 self == other, 1 self > other """
    #     # 1) interactive
    #     if self.interactive and not other.interactive:
    #         return -1
    #     if not self.interactive and other.interactive:
    #         return 1
    #     # 2) priority
    #     # higher priorities runs first
    #     if self.priority > other.priority:
    #         return -1
    #     if self.priority < other.priority:
    #         return 1
    #     # 3) - alphabetical by path
    #     if self.get_path() < other.get_path():
    #         return -1
    #     if self.get_path() > other.get_path():
    #         return 1
    #     return 0

    # def __lt__(self, other):
    #     return self._compare(other) == -1

    # def __le__(self, other):
    #     return self._compare(other) in [-1, 0]

    # def __eq__(self, other):
    #     return self._compare(other) == 0

    # def __ge__(self, other):
    #     return self._compare(other) in [0, 1]

    # def __gt__(self, other):
    #     return self._compare(other) == 1

    # def __ne__(self, other):
    #     return self._compare(other) != 0

    def __str__(self):
        return self.path

    def __hash__(self):
        return hash(self.path)

    # utilities
    def make_copy(self):
        test_copy = copy.copy(self)
        test_copy.params = self.params
        return test_copy

    def get_memory_info(self):
        self.check_nfs_root_file_system()
        proc_meminfo = open("/proc/meminfo", "r")
        self.free_memory = 0
        self.system_memory = 0
        self.swap_memory = 0
        while True:
            line = proc_meminfo.readline()
            if line:
                tokens = line.split()
                if len(tokens) == 3:
                    if "MemTotal:" == tokens[0].strip():
                        self.system_memory = int(tokens[1].strip())/1024
                    elif tokens[0].strip() in ["MemFree:", "Cached:", "Buffers:"]:
                        self.free_memory +=  int(tokens[1].strip())
                    elif "SwapTotal:" == tokens[0].strip():
                        self.swap_memory = int(tokens[1].strip())/1024
            else:
                break
        proc_meminfo.close()
        self.free_memory = self.free_memory/1024
        print("System Memory: %u MB" % self.system_memory)
        print("Free Memory: %u MB" % self.free_memory)
        print("Swap Memory: %u MB" % self.swap_memory)

        if self.system_memory == 0:
            print("Error: could not determine system RAM")
            return False

        # Process Memory
        self.process_memory = self.free_memory
        self.process_limited = False
        try:
            arch = subprocess.getoutput("uname -i")
            if (arch in ["i386", "i686", "s390"]) and self.free_memory > 1024:
                self.process_limited = True
                self.process_memory = 1024 # MB, due to 32-bit address space
                print("%s arch, Limiting Process Memory: %u" % (arch, self.process_memory))
        # others?  what about PAE kernel?
        except Exception as e:
            print("Error: could not determine system architecture via uname -i")
            print(e)
            return False

        #otherwise
        return True

    def check_nfs_root_file_system(self):
        self.nfs_root_system = False
        mount = os.popen("mount")
        while True:
            line = mount.readline()
            if not line:
                break
            words = line.split()
            # line should be <source> on <destination> type <mounttype> <other stuff>
            if words and len(words) >= 5 and words[2] == "/" and words[4] == "nfs":
                self.nfs_root_system = True
                break

    def run_sub_test(self, subtest_function, name, description=None, params=""):
        self.mark_output(name, description)
        if params == "":
            result = subtest_function()
        else:
            result = subtest_function(params)
        self.mark_summary(result)
        self.close_output()
        return result

    def mark_output(self, name, description=None, path=""):
        self.close_output()
        output = open(path + 'output.html', 'a')
        if description:
            output.write("<output name=\"%s\" description=\"%s\">\n" % (name, description))
            output.write("\t%s - %s\n" % (name, description))
        else:
            output.write("<output name=\"%s\">\n" % (name))
            output.write("\t%s:\n" % name)
        output.close()
        self.marking = True

    def mark_summary(self, summary, path=""):
        summary = str(TestResult(summary))
        button_class = "warning"
        if summary == "PASS":
            button_class = "success"
        elif summary == "FAIL":
            button_class = "error"
        output = open(path + 'output.html', 'a')
        output.write("\t<button class=\"pure-button button-%s\">%s</button>\n" % (button_class, summary))
        output.close()

    def close_output(self, path=""):
        if self.marking:
            output = open(path + 'output.html', 'a')
            output.write("</output>\n\n")
            output.close()
            self.marking = False

    # def remove_directory(self, directory):
    #     "Remove a directory (and all its contents)"
    #     try:
    #         for (root,dirs,files) in os.walk(directory, topdown=False):
    #             for f in files: os.unlink(os.path.join(root,f))
    #             for d in dirs: os.rmdir(os.path.join(root,d))
    #             os.rmdir(directory)
    #     except OSError:
    #         return


    #     return self.nfs_root_system

    # def load_kernel_module(self, module):
    #     # is it already running?
    #     if os.system("lsmod | fgrep -q %s" % module) == 0:
    #         print("Module %s is already loaded" % module)
    #         return True
    #     # otherwise, does it exist?
    #     if os.system("modinfo %s" % module) == 0:
    #         if self.promptConfirm("Probe Module %s?" % module):
    #             os.system("modprobe %s" % module)
    #             if os.system("lsmod | fgrep -q %s" % module) == 0:
    #                 print("Module %s is loaded" % module)
    #                 return True
    #             # otherwise
    #             print("Error: module would not load %s" % module)
    #             return False

    #         # otherwise - cancelled
    #         return False

    #     # otherwise:
    #     print("Error: no module %s" % module)
    #     return False

    # def checkKernelModule(self, module):
    #     # is it already running?
    #     lsmod = Command("lsmod")
    #     try:
    #         lsmod.getString(module, singleLine=False)
    #         print("Module %s is loaded" % module)
    #         return True
    #     except:
    #         pass
    #     # otherwise, does it exist?
    #     modinfo = Command("modinfo %s" % module)
    #     modprobe = Command("modprobe %s" % module)

    #     try:
    #         modinfo.run()
    #         modprobe.run()
    #         lsmod.getString(module, singleLine=False)
    #         print("Loaded module %s" % module)
    #         return True
    #     except:
    #         print("Warning: could not load module %s" % module)

    #     return False

    # def runOnServer(self, args, outFile):
    #     outFile.write("Server side test for %s not implemented\n" % self.Name())

    def get_load_avg(self):
        loadAvgFile = "/proc/loadavg"
        if os.path.exists(loadAvgFile):
            file = open(loadAvgFile)
            line = file.readline()
            if len(line.strip()) > 0:
                params = line.strip().split()
                loadAvg = float(params[0])
                print("Current load average: %s" % loadAvg)
                sys.stdout.flush()
                return loadAvg
        else:
            return 0

    def sync_disks(self):
        try:
            print("Syncing disks")
            sys.stdout.flush()
            print(subprocess.getoutput("/bin/sync"))
        except Exception as e:
            print("Warning: rhcert attempt to sync failed")
            print(e)

    def wait_for_lull(self):
        waitTime = 5
        retryLimit = 20
        self.sync_disks()

        print("Waiting for low load...")
        sys.stdout.flush()
        retryCount = 0
        while self.get_load_avg() > 1 and retryCount < retryLimit:
            time.sleep(waitTime)
            retryCount = retryCount + 1
        print("Done waiting")
        sys.stdout.flush()

    

    # def parseRecords(self, command, keyNames):
    #     """ parse output into records separated by blank lines, with name:value pairs.
    #     command: rhcert.Command
    #     keyNames: list(string)
    #     returns: dict[keyName][propertyName] ( dict by keyname of dict by property name of values )"""
    #     records = dict()
    #     properties = dict()
    #     command.start()
    #     while True:
    #         line = command.readline()
    #         # blank or empty line (EOF)
    #         if not line or line.strip() == "":
    #             # save the record
    #             if len(properties) > 0:
    #                 for keyName in keyNames:
    #                     if keyName in properties:
    #                         records[properties[keyName]] = properties
    #                 properties = dict()
    #             if not line:
    #                 break
    #             else:
    #                 continue
    #         tokens = line.split(":", 1)
    #         if len(tokens) == 2:
    #             properties[tokens[0].strip()] = tokens[1].strip()
    #         continue
    #     return records


class TestResult:
    """ represent a test result at the four levels: PASS > WARN > REVIEW > FAIL """
    PASS = "PASS"
    WARN = "WARN"
    REVIEW = "REVIEW"
    FAIL = "FAIL"

    def __init__(self, result="PASS"):
        # always convert to string representation
        if type(result) is bool:
            if result:
                self.result = TestResult.PASS
            else:
                self.result = TestResult.FAIL
        else:
            self.result = str(result)

    def __str__(self):
        return self.result
    def __repr__(self):
        return self.__str__()
    def __eq__(self, other):
        return self.result == str(TestResult(other))
    def __ne__(self, other):
        return not self.__eq__(other)

    def combine(self, nextValue):
        """ accumulate test results PASS > WARN > REVIEW > FAIL """
        # assign a value for comparison
        resultMap = {TestResult.PASS: 3, TestResult.WARN: 2, TestResult.REVIEW: 1, TestResult.FAIL: 0}
        nextResult = str(TestResult(nextValue))
        if resultMap.get(nextResult) < resultMap.get(self.result):
            self.result = nextResult

    def better(self, nextValue):
        """ accumulate best test result PASS > WARN > REVIEW > FAIL """
        # assign a value for comparison
        resultMap = {TestResult.PASS: 3, TestResult.WARN: 2, TestResult.REVIEW: 1, TestResult.FAIL: 0}
        nextResult = str(TestResult(nextValue))
        if resultMap.get(nextResult) > resultMap.get(self.result):
            self.result = nextResult
            return True
        return False

    def getMessagePrefix(self):
        if self.result == TestResult.PASS:
            return "Success: "
        if self.result == TestResult.WARN:
            return "Warning: "
        if self.result == TestResult.REVIEW:
            return "Needs Review: "
        # self.result == TestResult.FAIL:
        return "Error: "