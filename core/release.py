#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os
import re


class Release:
    def __init__(self, file):
        self.product = None
        self.product_short_name = None
        self.version = None
        self.update = None
        self.code_name = None
        self.candidate = None
        self.valid = False
        self.text = None
        self.debug = False
        self.__read(file)
        self.__parse()

    def __read(self, file):
        try:
            f = open(file)
            self.text = f.readline().strip('\n')
            f.close()
        except:
            pass

    def __parse(self):
        self.product = None
        self.version = None
        self.update = None
        self.code_name = None
        self.candidate = None
        if self.text:
            # look for <product> release <number>
            pattern = re.compile(
                "^(?P<product>[a-zA-Z\ ]+)release\s+(?P<number>[0-9\.]+)\s*(?P<label>Beta?)*")
            # development preview: "Red Hat Enterprise Linux Server for ARM (Development Preview release 1.5)"
            alternate_pattern = re.compile(
                "^(?P<product>[a-zA-Z\ ]+)\([a-zA-Z\ ]+release\s+(?P<number>[0-9\.]+)\)")
            match = pattern.match(self.text)
            if not match:
                match = alternate_pattern.match(self.text)
            if not match:
                self.valid = False
                if self.debug:
                    print("\"%s\" is Not Valid" % self.text)
                return
            # otherwise
            self.valid = True
            if match.group("product"):
                self.product = match.group("product").strip()
            if match.group("number"):
                major_minor = match.group("number").split('.')
                if len(major_minor) > 0:
                    self.version = int(major_minor[0])
                    if len(major_minor) > 1:
                        self.update = int(major_minor[1])
                    elif self.code_name:
                        name_parts = self.code_name.split(' ')
                        if len(name_parts) == 3:
                            self.update = int(name_parts[2])
            try:
                self.label = match.group("label").strip()
            except (IndexError,  AttributeError):
                # no label group
                self.label = ""
            # try for other info after the release number
            text = self.text[match.end("number"):].strip()
            pattern = re.compile(
                "(?P<candidate>[^\(\)]*)(\((?P<name>[a-zA-Z0-9\ ]+)\))?")
            match = pattern.match(text)
            if match:
                if match.group("name"):
                    self.code_name = match.group("name").strip()
                if match.group("candidate"):
                    self.candidate = match.group("candidate").strip()

    def is_valid(self):
        return self.valid and self.product and self.version

    def get_product(self): return self.product
    def get_product_short_name(self): return self.product_short_name
    def get_version(self): return self.version

    def get_update(self):
        if self.update:
            return self.update
        return "0"

    def get_label(self): return self.label
    def get_code_name(self): return self.code_name
    def get_candidate(self): return self.candidate

    def get_version_point_update(self):
        if self.update != None:
            return "%u.%u" % (self.version, self.update)
        # otherwise no minor AKA update number as in Fedora
        return "%u" % self.version

    def dump(self):
        print("")
        print(self.text)
        print("-------------------------------")
        print("Product: \"" + self.get_product() + "\"")
        print("Version.Update \"" + self.get_version_point_update() + "\"")
        if self.candidate:
            print("Candidate: \"" + self.get_candidate() + "\"")
        if self.code_name:
            print("Code Name: \"" + self.get_code_name() + "\"")
        if not self.is_valid():
            print("Not Valid")

    def parse(self):
        self.__parse()


class EuroLinuxRelease(Release):
    def __init__(self):
        Release.__init__(self, "/etc/redhat-release")
        self.kernel = None
        self.arch = None
        if self.is_valid():
            self.__get_kernel_info()

    def __get_kernel_info(self):
        uname = os.popen('uname -r')
        self.kernel = uname.readline()[:-1]
        uname.close()
        uname = os.popen('uname -m')
        self.arch = uname.readline()[:-1]
        uname.close()
        uname = os.popen("uname -r")
        uname_output = uname.readline()
        uname.close()
        if not uname_output:
            print("Error: uname failed")
        else:
            uname_output = uname_output.strip()
        self.get_product_from_uname(uname_output)

    def get_product_from_uname(self, uname_output):
        pattern = re.compile(
            "(?P<product>.ael|.el|.fc|.aa)(?P<version>[0-9]+[a-z]{0,1})")
        self.product = None
        self.version = None
        match = pattern.search(uname_output)
        if match:
            if match.group("product").startswith(".aa") or uname_output.endswith("arch64"):
                self.product = "EuroLinux for ARM"
            elif match.group("product") == ".el":
                self.product = "EuroLinux"
            elif match.group("product").startswith(".ael"):
                self.product = "EuroLinux Asterisk Extension Logic"
            if match.group("version"):
                self.version = int(match.group("version")[0])
            return True
        else:
            return False

    def get_kernel(self): return self.kernel
    def get_arch(self): return self.arch

    def dump(self):
        Release.dump(self)
        print("Kernel Version \"" + self.get_kernel() + "\"")
        print("Architecture \"" + self.get_arch() + "\"")
