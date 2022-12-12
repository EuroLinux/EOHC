#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os
import errno
import re
import subprocess
import time

from core.lib.compatability import rhcert_make_unicode
# from rhcert.testUI import TestUI


class Controller(object):

    def __init__(self, echoResponses=True):
        # self.ui = TestUI(echoResponses)
        self.system_log_marker = "rhcert/runtests"
        self.system_log_boot_marker = "Linux version"

    def remove_directory(self, directory):
        "Remove a directory (and all its contents)"
        try:
            for (root, dirs, files) in os.walk(directory, topdown=False):
                for f in files:
                    os.unlink(os.path.join(root, f))
                for d in dirs:
                    os.rmdir(os.path.join(root, d))
            os.rmdir(directory)
        except OSError:
            return

    def make_directory_path(self, directory):
        """Emulate mkdir -p behavior: create the given directory, including all
        needed parent directories. Do not return an error if the directories 
        already exist."""
        try:
            os.makedirs(directory)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def remove_bad_characters_in_name(self, value):
        """Remove bad characters []()\/&@in generated names"""
        pattern = re.compile("[^\[\]\(\)\\\/&@,]")
        good_list = pattern.findall(value)
        return "".join(good_list)

    def get_system_log_marker(self, marker_name, mark, pid=True):
        if pid:
            return self.system_log_marker+"[%s]: %s: %s" % (os.getpid(), marker_name, mark)
        # otherwise
        return self.system_log_marker+": %s: %s" % (marker_name, mark)

    def get_system_log_open(self):
        return self.system_log_marker+"[%s]" % os.getpid()

    def get_system_log(self, marker_name, pid=True):
        "Get a named section of the system log"

        log = self.get_system_log_since_boot()
        begin_mark = self.get_system_log_marker(marker_name, "begin", pid)
        end_mark = self.get_system_log_marker(marker_name, "end", pid)
        contents = []
        logiter = iter(log)
        for l in logiter:
            if begin_mark in l:
                contents.append(l)
                break
        for l in logiter:
            contents.append(l)
            if end_mark in l:
                break
        return ''.join(contents)

    def get_system_log_since_boot(self):
        try:
            # Got logs for current boot
            try:  # python2
                contents = []
                log = subprocess.Popen(
                    ['journalctl', '-b0'], stdout=subprocess.PIPE).communicate()[0]
                for l in log.split('\n'):
                    try:
                        contents.append(l.decode('utf-8') + '\n')
                    except UnicodeDecodeError as error:
                        print(error)
                return contents
            except TypeError:  # python3
                log = subprocess.Popen(
                    ['journalctl', '-b0'], stdout=subprocess.PIPE, encoding='utf8').communicate()[0]
                return log.split('\n')
        except OSError:
            # If journalctl does not exist, fall back to normal log reading.
            pass
        except subprocess.CalledProcessError:
            # Try syslog if journalctl returns an error.
            pass

        syslog = '/var/log/messages'
        log = open(syslog)
        contents = list()
        marker = False
        for l in log:
            try:
                try:  # python2
                    l = l.decode("utf-8")
                except AttributeError:
                    pass  # python3 already unicode
                if l.find("kernel:") != -1 and l.find(self.system_log_boot_marker) != -1:
                    marker = True
                    # dump old contents
                    contents = list()
                if marker:
                    contents.append(l)
            except UnicodeDecodeError:
                # if we can't decode it, skip the whole line
                continue
        log.close()
        return contents

    # def release(self):
    #     return self.ui.release()

    def get_current_utc_time(self):
        return time.gmtime(time.time())
