#!/usr/bin/python3
# Author: Radoslaw Kolba
#

import os

def get_devices(search = "", criteria_field = "SUBSYSTEM"):
    dirty_info = os.popen("udevadm info --export-db").readlines()
    devices = list()
    criteria = ""
    info = dict()
    for line in dirty_info:
        if line[0] == "\n" and (search == "" or search == criteria):
            info["_TYPE"] = get_attr(info, "type")
            devices.append(info)
            criteria = ""
            info = dict()
        elif line[0] == "P":
            info["_PATH"] = line[3:-1]
        elif line[0] == "N":
            info["_NAME"] = line[3:-1]
        elif line[0] == "E":
            i = line[3:-1].split('=')
            if i[0] == criteria_field:
                criteria = i[1]
            info[i[0]] = i[1]
    return devices

def get_devices_from_file(search = ""):
    dirty_info = os.popen("cat /proc/bus/input/devices").readlines()
    devices = list()
    info = dict()
    for line in dirty_info:
        if line[0] == "I":
            tmp = line[3:].split(" ")
            d = dict()
            for i in tmp:
                x = i.split("=")
                d[x[0]] = x[1].replace("\n", "")
            info["Info"] = d
        elif line[0] == "N":
            info["Name"] = line[9:-2]
        elif line[0] == "P":
            info["Phys"] = line[9:-2]
        elif line[0] == "S":
            info["Sysfs"] = line[10:-1]
        elif line[0] == "\n":
            if search == "":
                devices.append(info)
            elif search == info["Name"]:
                devices.append(info)
    return devices

def get_attr(device, attr):
        attrpath = os.path.join("/sys" + device.get("DEVPATH"), attr)
        try:
            with open(attrpath) as f:
                return f.read().strip()
        except EnvironmentError as e:
            return None