#!/usr/bin/python3
# Copyright (c) 2006 Red Hat, Inc. All rights reserved. This copyrighted material
# is made available to anyone wishing to use, modify, copy, or
# redistribute it subject to the terms and conditions of the GNU General
# Public License v.2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.#
# Author: Irina Boverman
#         Aniket Khisti akhisti@redhat.com
#

import os, re, sys, platform, signal, time, io, subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.release import EuroLinuxRelease
from core.test import Test
from core.lib.devices import get_devices

class VideoTest(Test):

    def __init__(self):
        Test.__init__(self, "video")
        self.interactive = False
        self.priority = 5 # medium
        self.Xconfig_flag = ""
        self.depth = 0
        self.Xconfigfile = "/tmp/hwcertXconfig"
        self.release = EuroLinuxRelease()
        self.display = "0"
        self.device = None
        if self.release.get_version() > 8 and os.environ.get('DISPLAY'):
            self.display = os.environ.get('DISPLAY').replace(':','')

    def plan(self):
        tests = list()
        # test is for eurolinux 8
        devices = get_devices("30000", "PCI_CLASS")
        for device in devices:
            test = self.make_copy()
            test.device = device
            tests.append(test)
        return tests

    def get_required_rpms(self):
        rpms = list()
        rpms.append("xorg-x11-utils") # for xdpyinfo and xvinfo
        rpms.append("glx-utils") # for xdriinfo and glxinfo, and glxgears
        rpms.append("xorg-x11-server-Xorg") # for X
        rpms.append("xorg-x11-xinit") # for xinit
        rpms.append("xterm") # for xterm
        rpms.append("mesa-dri-drivers") # for openGL
        return rpms

    def get_config_file(self):
        self.Xconfigfile = None
        log_path = "/var/log/Xorg.0.log"
        if os.path.exists(log_path):
            log = io.open(log_path, encoding='utf-8', errors='ignore')
            pattern = re.compile("\(==\) Using config file: \"(?P<filepath>[^\"]+)\"")
            for line in log.readlines():
                match = pattern.search(line)
                if match:
                    self.Xconfigfile = match.group("filepath")
                    print("Using config file " + self.Xconfigfile)
                    break
            log.close()
        else:
            subprocess.getstatusoutput("sudo touch %s" % log_path)
        if not self.Xconfigfile:
            print("No config file found - using Default Config")
        return True

    def set_depth(self):
        if self.Xconfigfile:
            (status, self.depth) = subprocess.getstatusoutput("grep DefaultDepth " + self.Xconfigfile + " | awk ' { print $2; } '")
            if status != 0:
                print("Error: could not obtain default depth from config file")
                return False
            try:
                self.depth = int(self.depth)
                print("Depth set to %u" % self.depth)
            except:
                print("Error: could not convert depth %s to integer" % self.depth)
                self.depth = None
                return False
        return True

    def set_flag(self):
        # Adapt for flag changes
        (status, self.Xconfig_flag) = subprocess.getstatusoutput("X --help 2>&1 | grep xf86config -q && echo -xf86config || echo -config")
        if status != 0:
            print("Failed to obtain config flag")
            return False
        print("Depth flag: " + self.Xconfig_flag)
        return True

    def check_depth_and_resolution(self):
        success = True
        # try to get the current screen resolution and color depth first
        try:
            # inclue display flag to ensure it is set
            xdpyinfo = subprocess.getoutput("xdpyinfo -display :%s" % (self.display))
            for line in xdpyinfo.split("\n"):
                if "dimensions:" in line:
                    screenResolution = line.split(" ")[6].split("x")
                    horizontalResolution = screenResolution[0]
                    verticalResolution = screenResolution[1]
                if "depth of root window:" in line:
                    colorDepth = line.split(" ")[9]
            print("\nScreen resolution: %sx%s" % (horizontalResolution,verticalResolution))
            print("      Color depth: %s" % colorDepth)
            # minimum requirement is 1024x768@24bit, but on some wide-screen
            # systems, the vertical resolution maybe smaller than 768
            if int(horizontalResolution) < 1024:
                print("Error: Current screen resolution: %sx%s does not meet the minimum requirements !\n" % (horizontalResolution,verticalResolution))
                success = False
            if int(colorDepth) < 24:
                print("Error:  Current color depth: %s does not meet the minimum requirements !\n" % colorDepth)
                success = False
        except:
            # record error and continue
            print("Error: failed to obtain current screen resolution and color depth !")
            success = False

        return success

    def check_Xmodules(self):
        log_path = "/var/log/Xorg.%s.log" % self.display
        try:
            log = io.open(log_path, "r", encoding='utf-8', errors='ignore')
        except IOError:
            print("Error: could not open %s" % log_path)
            return False

        success = True
        print("Checking %s for loaded X modules -----------------------" % log_path)
        for line in log.readlines():
            # this presumes Loading lines that include a slash means a path
            if line.find("(II) Loading /") >= 0:
                 # is there a oneline way to do this?
                 xmoduleFile = line.split()
                 xmoduleFile = xmoduleFile[-1]

                 try:
                     subprocess.getoutput("rpm -Vf %s" % (xmoduleFile))
                     if not self.check_Xmodule_vendor_and_build_host(xmoduleFile):
                         success = False
                 except Exception as e:
                     print("Error: RPM verification failed for X module %s" % xmoduleFile)
                     print(e)
                     success = False

        print("-------------------------------------------------\n")
        log.close()
        return success

    def check_Xmodule_vendor_and_build_host(self, xmoduleFile):
        result = True
        goodVendorList = ["EuroLinux", "Red Hat", "Red Hat, Inc."]
        warnVendorList = ["Fedora", "Fedora Project"]
        try:

            vendor = subprocess.getoutput("rpm -qf %s --qf %%{VENDOR}" % (xmoduleFile))
            if vendor in goodVendorList:
                print("Found %s by %s" % (xmoduleFile, vendor))
            elif vendor in warnVendorList:
                print("Warning: %s module %s found" % (vendor, xmoduleFile))
            else:
                print("Error: Non-Red Hat vendor %s for module %s" % (vendor, xmoduleFile))
                result = False

            buildhost = subprocess.getoutput("rpm -qf %s --qf %%{BUILDHOST}" % (xmoduleFile))
            if "redhat.com" not in buildhost:
                print("Error: X module %s was built on %s and not built at Red Hat." % (xmoduleFile, buildhost))
                result = False
        except Exception as exception:
                print("Error: could not determine X module packager for  %s" % xmoduleFile)
                print(exception)
                result = False

        return result

    def log_driver_info(self):
        lib_dir = "/usr/lib64" if platform.architecture()[0] == "64bit" else "/usr/lib"
        log_path = "/var/log/Xorg.%s.log" % self.display
        try:
            log = io.open(log_path, "r", encoding='utf-8', errors='ignore')
        except IOError:
            print("Error: could not open %s" % log_path)
            return False
        print("\nDriver Info from %s:\n-------------------------------------------------" % log_path)
        copying = False
        entry_count = 0
        while 1:
            line = log.readline()
            if line:
                if not copying:
                    if line.find("%s/xorg/modules/drivers" % lib_dir) >= 0:
                        copying = True
                # stop on second "(II)" or blank line
                else:
                    if line.find("(II)") >= 0:
                        entry_count += 1
                    if line.strip() == "" or entry_count > 1:
                        copying = False
                        entry_count = 0
                        print("")
                if copying:
                    sys.stdout.write(line)
            else:
                log.close()
                break
        print("-------------------------------------------------")

        result = True
        for command in ["xvinfo", "xdriinfo", "glxinfo"]:
            info_command = "%s -display :%s" % (command, self.display)
            print("\n---------------------- %s ------------------" % info_command)
            try:
                print(subprocess.getoutput(info_command))
            except Exception:
                if command != "xvinfo":  # xvinfo always returns 1
                    result = False

        return result

    def startX(self):
        """ start an X server with gnome-shell """
        # Note: "xinit /usr/bin/gnome-shell --replace -- :%s " won't work as root
        startx_command = "xinit -- :%s " % (self.display)
        if self.Xconfigfile:
            startx_command += "%s %s " % (self.Xconfig_flag, self.Xconfigfile)
        if self.depth:
            startx_command +=  "-depth %u " % self.depth

        try:
            print("Running: " + startx_command)
            self.xServer = subprocess.Popen(startx_command.split(" "), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            time.sleep(3)
        except Exception as e:
            print("Error: %s failed" % startx_command)
            print(e)
            return False
        
        return True

    def run_glxgears(self):
        glxGears_command = "glxgears -display :%s" % (self.display)
        print(glxGears_command)
        try:
            p = subprocess.Popen(glxGears_command.split(" "), stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            try:
                output, err = p.communicate(timeout = 30)
            except subprocess.TimeoutExpired:
                p.kill()
                output, err = p.communicate()
                for out in output.decode("utf-8").split("\n"):
                    print(out)
        except Exception as e:
            print("Error: glxgears failed:")
            print(e)
            return False
        return True

    def stopX(self):
        try:
            print("Killing xinit")
            self.xServer.kill()
        except Exception as e:
            print("Error: could not kill X:")
            print(e)
            return False
        return True

    def check_connections(self):
        sys.stdout.write("Checking for displays...")
        try:
            print(subprocess.getoutput("xrandr"))
            sys.stdout.flush()
        except Exception as e:
            print(e)
        return True

    def set_configuration(self):
        return (self.get_config_file() and self.set_depth() and self.set_flag())

    def run_Xserver_test(self):
        success = True
        if not self.startX():
            success = False
        if not self.run_glxgears():
            success = False
        if not self.stopX():
            success = False

        return success

    def log_modules_and_drivers(self):
        time.sleep(3)
        self.startX()
        success = self.check_depth_and_resolution()
        if not self.check_Xmodules():
            success = False
        if not self.log_driver_info():
            success = False
        self.stopX()

        return success

    def run(self):
        print("Starting video test")
        success = True
        if not self.run_sub_test(self.check_connections, name="Video check connections", description="show xrandr output"):
            success = False
        if not self.run_sub_test(self.set_configuration, name="Video set configuration", description="set up configuration for test"):
            return False
        if not self.run_sub_test(self.run_Xserver_test, name="Video X server test", description="run a second X test server"):
            success = False
        if not self.run_sub_test(self.log_modules_and_drivers, name="Video module and drivers", description="show depth, module and driver information"):
            success = False

        if success:
            print("Video test PASSED")
            return True
        
        print("Video test FAILED")
        return False

if __name__ == "__main__":
    test = VideoTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        test.run()
    sys.exit(0)