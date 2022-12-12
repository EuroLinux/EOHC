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
import os, sys, subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test


class MemoryTest(Test):
    def __init__(self):
        Test.__init__(self, "memory")
        self.interactive = False
        self.priority = 5

    def run(self):
        if not self.run_sub_test(self.get_memory_info, name="Memory limits", description="get test parameters based on hardware"):
            print("Memory test FAILED")
            return False
        if not self.run_sub_test(self.run_memory_test, name="Memory main", description="proceed main memory test"):
            print("Memory test FAILED")
            return False
        print("Memory test PASSED")
        return True
    
    def run_memory_test(self):
        print("Starting Memory Test")
        # run for Free Memory plus the lesser of 5% or 1GB
        print("free memory: %s" % self.free_memory)
        memory = (self.free_memory * 5)/100
        print("memory: %s" % memory)
        if memory > 1024: # MB
            memory = 1024 # MB
        memory = memory + self.free_memory
        threads = 0
        try:
            page_size = subprocess.getoutput("getconf PAGESIZE")
            num_cpus = subprocess.getoutput("grep -c ^processor /proc/cpuinfo")
            minimum_memory = int(page_size) * 2 * int(num_cpus)
            if memory < minimum_memory:
                new_threads = memory / int(page_size)
                #subtract one thread so that elhc won't be killed
                if new_threads > 1:
                    new_threads = new_threads - 1
                # if new_threads is eg: 0.796, function 'atoi' in C file will convert it to 0 and throw error
                if new_threads < 1:
                    new_threads = 1
                new_memory = int(page_size) * new_threads / 8 # bits to bytes
                if new_memory <= 0:
                    print("Warning: could not calculate new number of threads and memory values")
                    print("originally calculated memory value: %s" % memory)
                    print("page size: %s" % page_size)
                    print("number of cpus: %s" % num_cpus)
                else:
                    memory = new_memory
                    threads = new_threads
                    print("threads set to %s" % threads)
                    print("memory for test set to %s" % memory)
        except Exception:
            print("Warning: Could not determine pagesize.")
        
        # run a test that will swap, except for nfs root systems without swap
        if not (self.nfs_root_system and self.swap_memory == 0):
            if not self.swap_memory:
                print("Error: this test requires non-zero swap memory.")
                return False
            # is there enough swap memory for the test?
            # ignoring when there's any theads
            if threads:
                pass
            elif memory > self.system_memory + self.swap_memory:
                print("Error: this test requires a minimum of %u KB of swap memory (%u configured)" % (memory-self.system_memory, self.swap_memory))
                return False

            runtime = 60 # sec.
            if threads:
                threadString = " -n%s " % threads
                threadStringMessage = " using %s threads" % threads
            else:
                threadString = threadStringMessage = ""
            print("running for more than free memory at %u MB for %u sec%s." % (memory, runtime, threadStringMessage))
            try:
                os.system("./tests/memory/threaded_memtest -qpv -m%um -t%u %s" % (memory, runtime, threadString))
                print("done.")
            except Exception:
                print("Error encountered when running command.")
                return False

        # run again for 15 minutes
        print("running for free memory")
        result = os.system("./tests/memory/threaded_memtest -qpv")
        print("done.")
        sys.stdout.flush()
        return (result == 0)

if __name__ == "__main__":
    test = MemoryTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        value = test.run()
    sys.exit(0)
