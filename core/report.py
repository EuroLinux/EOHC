#!/usr/bin/python3
# Author: Radoslaw Kolba
#
import os, sys, shutil, re, rpm, subprocess
from core.release import EuroLinuxRelease

class GenerateSystemReport():

    def __init__(self, output_dir = "./"):
        self.maximum_sos_plugin_size = 52428800 # 50 MB
        self.maximum_attachment_size = 524288000 # 500 MB
        self.feature_data = dict()
        self.output_dir = output_dir

    def get_sos_version(self):
        sos_version = subprocess.getoutput('rpm -qa | grep sos')
        self.sos_version = '.'.join(sos_version.split('.')[:-2])
        return self.sos_version

    def check_min_version(self):
        min_version = 'sos-3.4-6'
        match = rpm.labelCompare(('0', 'sos', self.sos_version.partition('sos-')[-1]), ('0', 'sos', min_version.partition('sos-')[-1]))
        if match >= 0:
            return True
        else:
            return False

    def compare_sos_versions(self):
        self.get_sos_version()
        accepted_versions = ['sos-3.3-5.el7_3.bz1415972', 'sos-3.3-5.bz1415972.el7_3']
        print("Info: Checking sos version to see if required information will be collected.")
        if (self.sos_version in accepted_versions) or self.check_min_version():
            print("Info: sos version is in the accepted versions.")
            return True
        else:
            print("Needs Review: sos version is not in accepted versions.")
            return False

    def check_sos_plugins(self, plugins):
        plugin_list = plugins.split("|")
        print("Checking if '%s' plugins are active in sos ..." % (','.join(plugin_list)))
        try:
            self.sos_plugins = subprocess.getoutput('sosreport -l').strip()
            expr2 = 'openstack_(?:%s)\s+Open.*' % plugins
            match_active = re.findall(expr2, self.sos_plugins, re.IGNORECASE)
            if len(match_active) == len(plugin_list):
                print("Success: Found all the required plugins as active")
                return True
            else:
                print(
                    "Needs Review: Some of the plugins are not active. Please check sos tarball.")
                return False
        except Exception as err:
            print("Needs Review: Failed to determine the status of plugins. "
                  "The command '%s' execution failed with error: '%s'." %
                  ('sosreport -l', str(err)))
            return False

    def check_container_plugin(self, container_utility):
        print("Checking if '%s' plugins are active in sos ..." % (container_utility))
        if not(hasattr(self, 'sos_plugins') and self.sos_plugins):
            print("Needs Review: Failed to determine the status of plugins.")
            return False

        expr2 = '%s\s+%s.*' %(container_utility, container_utility.capitalize())
        match_active = re.findall(expr2, self.sos_plugins, re.IGNORECASE)
        if len(match_active) == 1:
            print("Success: Found %s plugin as active in sos utility" % container_utility)
            return True
        else:
            print("Needs Review: %s plugin is inactive in sos utility." % container_utility)
            return False

    def run_generation(self):
        print("Generating System Report(sosreport). It may take a while. Please wait ...\n")
        # limit the size of collected logs
        log_size = int(self.maximum_sos_plugin_size/(1024*1024)) # bytes to MB conversion

        # skip ebpf plugin in certain conditions, to avoid kernel-taint
        sos_version = self.get_sos_version()
        skip_ebpf = "-n ebpf" if int(EuroLinuxRelease().get_version()) == 7 and float(sos_version.split('-')[1]) >= 3.9 else ""

        result = self._processSystemReport("sosreport --batch -n selinux -n logs --log-size {0} {1}".format(log_size, skip_ebpf))
        return result

    def _processSystemReport(self, reportCommand):
        pipe = os.popen("echo -e '\n\n' | %s -k rpm.rpmva=off 2>&1" % reportCommand)
        result = False
        while True:
            line = pipe.readline()
            if line:
                sys.stdout.flush()
                tarFile = None
                if "generated and saved in" in line:
                    tarFile = pipe.readline().strip()
                    print(tarFile)
                    sys.stdout.flush()

                if tarFile:
                    if os.path.getsize(tarFile) > self.maximum_attachment_size:
                        print(("Error: sosreport is %s MB, and too large to attach (Max size: %s MB)"
                                 % (int(os.path.getsize(tarFile)/(1024*1024)),
                                    int(self.maximum_attachment_size/(1024*1024)))))
                        return False
                    shutil.copy(tarFile, self.output_dir)
                    print("Copied %s %s to %s" % (reportCommand, tarFile, self.output_dir))
                    sys.stdout.flush()
                    result = True
                    break
            else:
                break
        pipe.close()
        return result

        