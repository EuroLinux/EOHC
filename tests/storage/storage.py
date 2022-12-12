#!/usr/bin/python3

import re
import os
import sys
import random
import subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.lib.devices import get_devices
from core.test import Test
from core.release import EuroLinuxRelease


class StorageTest(Test):
    # 
    def __init__(self):
        Test.__init__(self, "storagetest")
        self.interactive = False
        self.priority = 9 #better to be one of the latests
        self.host_pattern_string = "(host|css|cciss|hspa|mmc|nvme|virtio|vbd-)[0-9]+"
        # Min and max blocksizes, in bytes. For each test, we loop through block sizes
        # starting with min_bs and doubling until we hit max_bs. Both should be
        # powers of 2 in the range [1024-65536].
        self.default_min_bs = 1024
        self.default_max_bs = 65536
        # Maximum size of the test area, in KB. (defaults to 1GB)
        self.max_size = 1048576
        self.file_system_type = "vfat"
        self.release = EuroLinuxRelease()
        self.test_pkg = "fio"
        # MY
        self.host_name = ""
        self.device_name = ""
        self.device = ""
        self.show_info = False

    def get_required_rpms(self):
        return ["xfsprogs", self.test_pkg]

    def plan(self):
        tests = list()
        disks = self.get_disks()
        for disk_id, (name, devices) in enumerate(disks.items()):
            print(str(disk_id), name)
            for device_id, device in enumerate(devices):
                test = self.make_copy()
                if disk_id == 0 and device_id == 0:
                    test.show_info = True
                test.host_name = name
                test.device_name = device.get("DEVNAME").split('/')[-1]
                test.device = device
                print(" -> " + str(device_id), test.device_name)
                tests.append(test)
        return tests

    # -> plan
    def get_disks(self):
        disks = dict()
        # find disks that are not either partitions or virtual block devices
        devices = []
        all_devices = get_devices()
        for device in all_devices:
            if ((device.get("ID_TYPE") == "disk" and device.get("DEVTYPE") != "partition") or (not device.get("ID_TYPE") and device.get("DEVTYPE") == "disk")):
                devices.append(device)
        host_pattern = re.compile("\/(?P<host>%s)" % self.host_pattern_string)
        for device in devices:
            match = host_pattern.search(device.get("DEVPATH"))
            if match:
                host = match.group("host")
                if not host in disks:
                    print("    Found host bus adapter: %s" % host)
                    disks[host] = list()
                disks[host].append(device)
        return disks

    # 
    def run(self):
        # unmount only external storages!
        subprocess.getoutput("sudo umount /run/media/$USER/*")
        if self.show_info == True:
            if not self.run_sub_test(self.log_lvm, "Storage LVM", "show LVM info"):
                print("Storage test FAILED")
                return False
            if not self.run_sub_test(self.grab_hardware_info, "Storage hardware", "show hardware info"):
                print("Storage test FAILED")
                return False
        if not self.run_sub_test(self.log_info_storage_ssd, "Storage SSD", "show SSD block and request size info"):
            print("Storage test FAILED")
            return False
        print("+------------------------------------------------------------------------------------------+\n")
        if not self.run_storage():
            print("Storage test FAILED")
            return False
        # mount all external storages
        subprocess.getoutput("sudo mount -a")
        print("Storage test PASSED")
        return True
    
    # -> run
    def log_lvm(self):
        try:
            # these commands write to standard error for no reason
            subprocess.getoutput("pvdisplay")
            subprocess.getoutput("vgdisplay")
            subprocess.getoutput("lvdisplay")
        except Exception as e:
            print("Warning: could not log LVM info")
            print(e)
        return True

    def grab_hardware_info(self):
        """Gather some Hardware information for reviewers."""
        print("+------------------------------- System Hardware Info Start -------------------------------+")
        print(subprocess.getoutput("uname -a"))
        print(subprocess.getoutput("cat /proc/partitions"))
        print(subprocess.getoutput("cat /proc/swaps"))
        print(subprocess.getoutput("cat /proc/diskstats"))
        print(subprocess.getoutput("cat /proc/mounts"))
        print(subprocess.getoutput("cat /etc/sysconfig/hwconf"))
        print(subprocess.getoutput("fdisk -l"))
        print(subprocess.getoutput("lsmod"))
        try:
            lspci_cmd = subprocess.getoutput("lspci -D")
            print(lspci_cmd)
        except Exception as e:
            print("Error in running command 'lspci -D'")
            print(e)
        else:
            self.lspci = lspci_cmd
        print("+-------------------------------- System Hardware Info End --------------------------------+\n")
        return True

    def log_info_storage_ssd(self):
        device_path = self.device.get("DEVNAME")
        if self.is_storage_device_ssd():
            print("+--------------------------------- Storage SSD Info Start ---------------------------------+")
            command = "lsblk %s -o NAME,PHY-SEC,LOG-SEC,MIN-IO,OPT-IO,ALIGNMENT,SIZE" % device_path
            try:
                print(subprocess.getoutput(command))
            except Exception as e:
                print("Warning: cannot run command '%s'\n" % command)
                print(e)
            print("+---------------------------------- Storage SSD Info End ----------------------------------+\n")
        return True
    
    # -> run -> log_info_storage_info
    def is_storage_device_ssd(self):
        """check if disk is SSD: SSD: 0, normal HDD:1"""
        device_name = self.device.get("DEVNAME").replace("/dev/", "").strip()
        rotational = "/sys/block/%s/queue/rotational" % device_name
        if not os.path.isfile(rotational):
            return False
        try:
            rotational_cmd = subprocess.getoutput("cat %s" % rotational)
            if rotational_cmd == "0":
                return True
        except Exception as e:
            print("Warning: cannot run command 'cat %s'\n" % rotational)
            print(e)
        return False

    # -> run
    def run_storage(self):
        if not self.device:
            print("Error: could not find disk or host matching \"%s\"" % self.device_name)
            return False

        return self.run_sub_test(self.run_disk, "Storage I/O", "tests storage I/O for %s" % self.device_name)

    # -> run -> run_storage
    def run_disk(self):
        # initialize
        size = 0
        isLvm = "false"

        # Device sanity check: does it exist?
        print("Checking if device is present")
        partition_file_tmp = open("/proc/partitions", "r")
        partition_file = partition_file_tmp.read()
        partition_file_tmp.close()

        if self.device_name in partition_file:
            print("Found %s in /proc/partitions." % self.device_name)
        else:
            print("SKIP: Can not find %s in /proc/partitions !" % self.device_name)
            return "SKIP"

        # If there's a swap device, use that for testing
        # turn 'em all on first, just in case
        print("Checking if swap is present for given device")
        subprocess.getoutput("swapon -a 2>/dev/null")
        swap_file_tmp = open("/proc/swaps", "r")
        swap_file = swap_file_tmp.read()
        swap_file_tmp.close()
        command = "sort -rgk3 /proc/swaps | grep -m1 '/dev/%s' | awk '{print $1}' | colrm 1 5 " % self.device_name
        try:
            swapdev = subprocess.getoutput(command)
        except Exception:
            swapdev = None

        if self.device_name not in swap_file:
            # if we find a swap device that's an LVM LV, and that LV
            # is restricted to the target device, then we can use that
            lines = swap_file.split("\n")
            for line in lines:
                if line.strip():
                    items = line.split()
                    key = items[0]
                    if key.find('/dev/') == 0:
                        if self.device_is_lvm(key, self.device_name):
                            swapdev = key[5:]  # cut off the leading "/dev/"
                            isLvm = "true"
                            break
        # check if the swap has label and record it here
        swap_label = self.get_swap_label(swapdev)
        # check the test device
        testdev = self.get_test_device(self.device_name, swapdev, isLvm)
        if not testdev:
            return "SKIP"

        max_bs = self.default_max_bs

        # min_bs is required for dt
        min_bs = self.default_min_bs
        if self.device_name[0:4] == "dasd":
            min_bs = 4096
        # Check set min block size to its sector size
        size_tmp = self.dev_sector_size(testdev)
        if size_tmp:
            min_bs = size_tmp

        # start to torture the disks
        success = True
        result = "failed"
        try:
            if not self.test_vfs(self.device_name, testdev, min_bs, max_bs):
                success = False
            if not self.test_raw_io(self.device_name, testdev, min_bs, max_bs):
                success = False
        except Exception as e:
            print("Error Occurred %s" % str(e))
            success = False
        finally:
            # Clean up, try to restore swap if needed.
            if testdev == swapdev:
                if self.restoreSwap(swapdev, swap_label):
                    print("restored the swap device.")
                else:
                    print("Error: restore swap error !")
                    success = False
            # try to remove temp directories
            print(subprocess.getoutput("pwd"))
            print("Removing the temp directory `%s.*`" % self.device_name)
            subprocess.getoutput("sudo rm -rf %s.*" % self.device_name)

        if success:
            result = "passed"

        print("\nStorage test on device %s %s !!" % (self.device_name, result))
        return success

    # -> run -> run_storage -> run_disk
    def device_is_lvm(self, key, device):
        """Return true if the given device is actually an LV, and that LV is only on
           the device we're trying to test."""
        # ls -l /dev/dm-1 | tr -d , | awk '{print $5"\\s\\+"$6}'  ==>  253\s\+1
        tmp = '{print $5"\\\\s\\\\+"$6}'
        command = "ls -l %s | tr -d , | awk '%s'" % (key, tmp)
        try:
            device_number = subprocess.getoutput(command)
        except Exception:
            print("Unable to find the device number using command: %s" % command)
            return False

        # lvs -okernel_major,kernel_minor,devices | grep -e "253\s\+1"
        command = "lvs -okernel_major,kernel_minor,devices | grep -e '%s'" % device_number
        try:
            cmd_lvs = subprocess.getoutput(command)
        except Exception:
            print("Unable to get device in lvs output using command: %s" % command)
            return False

        if len(cmd_lvs) == 1 and device in cmd_lvs[0]:
            print("Given device %s is a LV" % device)
            return True
        return False

    def get_swap_label(self, swapdev):
        """try to get the swap label"""
        swap_label = None
        if swapdev:
            try:
                blkid_command = subprocess.getoutput("blkid /dev/%s" % swapdev)
                swap_string = blkid_command.split(" ")
                for swap_string_item in swap_string:
                    if swap_string_item[:5] == "LABEL":
                        swap_label = swap_string_item[7:-1]
                        print("----swap device has label '%s'----" % swap_label)
            except Exception as exception:
                # not really an error - just didn't find a label, carry on
                pass
        return swap_label

    def get_test_device(self, storage_device, swapdev, isLvm):
        """find the test device"""
        if swapdev:
            # Found a swap device!
            print("----swapdev is %s----" % swapdev)
            print("----lvm is %s----" % isLvm)
            print("Using swap device %s for testing." % swapdev)
            sys.stdout.flush()
            # Turn off swapping.
            print("Turning off swap")
            try:
                subprocess.getoutput("swapoff /dev/%s" % swapdev)
                testdev = swapdev
            except Exception:
                print("Error: can not swapoff %s" % swapdev)
                return False
        else:
            # No swap, but if the disk is unused, we'll test with it.
            # Is it in use by LVM?
            print("Checking if disk is used by LVM")
            if subprocess.getstatusoutput("pvs | grep '/dev/%s' " % storage_device)[0] == 0:
                print("Error: %s is currently in use by LVM." % storage_device)
                print("It cannot be tested. You may need to reinstall.")
                return False
            # Is it part of a RAID set?
            print("Checking if disk is part of RAID")
            mdstat_file_tmp = open("/proc/mdstat", "r")
            mdstat_file = mdstat_file_tmp.read()
            mdstat_file_tmp.close()
            if storage_device in mdstat_file:
                print("Error: %s is part of a RAID set." % storage_device)
                print("It cannot be tested. You may need to reinstall.")
                return False

            # Is there an active filesystem on it?
            print("Checking if disk has active filesystem")
            mounts_file_tmp = open("/proc/mounts", "r")
            mounts_file = mounts_file_tmp.read()
            mounts_file_tmp.close()
            print("File: /proc/mounts \n%s" % mounts_file)

            mtab_file_tmp = open("/etc/mtab", "r")
            mtab_file = mtab_file_tmp.read()
            mtab_file_tmp.close()
            print("File: /etc/mtab \n%s" % mtab_file)

            if ("/dev/%s" % storage_device) in mounts_file or ("/dev/%s" % storage_device) in mtab_file:
                print("SKIP: %s has active filesystems on it." % storage_device)
                print("It cannot be tested. You may need to reinstall.")
                return False

            testdev = storage_device

            # You can't use a dasd without a partition table..
            if testdev[0:4] == "dasd" and testdev[0:5] == testdev:
                try:
                    subprocess.getoutput("fdasd -a /dev/%s; sync" % testdev)  # sync avoids the udev race
                    subprocess.getoutput("stat /dev/%s" % testdev)
                    testdev = testdev + "1"
                except Exception:
                    print("Error: /dev/%s1 was not created" % testdev)
                    return False
        print("----test device is %s----" % testdev)
        return testdev

    def dev_sector_size(self, test_device):
        size = 0
        command = "cat /sys/block/%s/queue/hw_sector_size" % test_device
        try:
            size = int(subprocess.getoutput(command))
        except Exception:
            print("Warning: can't get device sector size from /sys/block/%s/queue/hw_sector_size" % test_device)
        sys.stdout.flush()
        return size

    def test_vfs(self, storage_device, testdev, min_bs, max_bs):
        """VFS (buffered filesystem) testing."""
        print("\n*** Testing buffered filesystem (%s) performance on %s" % (self.file_system_type, testdev))
        # Create a new filesystem and mount it.
        old_mountdir = storage_device + ".XXXXXX"
        # replace '/' with '-' for cciss devices
        # e.g. 'cciss/c0d0' -> 'cciss-c0d0'
        old_mountdir = old_mountdir.replace('/', '-')

        try:
            mountdir = subprocess.getoutput("mktemp -d %s" % old_mountdir)
            dt_test_file = mountdir + "/dt_test_file"
        except Exception:
            print("Error: can not create the mount dir %s." % old_mountdir)
            return False

        mkfs_cmd = "mkfs -t %s -f /dev/%s" % (self.file_system_type, testdev)
        mount_cmd = "mount -t %s /dev/%s %s" % (self.file_system_type, testdev, mountdir)
        try:
            print("Formatting the device using %s" % mkfs_cmd)
            subprocess.getoutput(mkfs_cmd)
        except Exception:
            print("Error: mkfs on %s failed" % testdev)
            return False

        try:
            print("Mounting the device using %s" % mount_cmd)
            subprocess.getoutput(mount_cmd)
            print("Device %s mounted at: %s" % (testdev, mountdir))
        except Exception:
            print("Error: Failed to mount %s" % testdev)
            return False

        try:
            print("Getting mount directory size")
            junk_size = int(subprocess.getoutput("df -Pk %s | awk '{print $4}' | tail -n1" % mountdir))
        except Exception:
            print("Error: can not get mountdir size.")
            self.unmount(testdev)
            return False

        size = self.max_size
        junk_size = int(junk_size)
        if junk_size < self.max_size:
            size = junk_size

        # options = "--filename=%s --size=%sk --bs=%s" % (dt_test_file, size, max_bs)
        options_dict = {"test_file": dt_test_file, "size": size, "min_bs": min_bs, "max_bs": max_bs}

        print("\nTesting random read-write on Filesystem")
        if not self.fio_dt_test("throughput-rand-rw-file", options_dict, is_random=True, is_direct=False):
            print("Error: Filesystem random read-write test failed")
            self.unmount(testdev)
            return False
        print("Filesystem random read-write test passed !!")

        print("\nTesting sequential read-write on Filesystem")
        if not self.fio_dt_test("throughput-seq-rw-file", options_dict, is_random=False, is_direct=False):
            print("Error: Filesystem random read-write test failed")
            self.unmount(testdev)
            return False
        print("Filesystem sequential read-write test passed !!")

        if not self.unmount(testdev):
            print("Error: Unable to unmount %s" % testdev)
            return False
        print("VFS (buffered filesystem) testing passed.\n")
        return True

    def test_raw_io(self, storage_device, testdev, min_bs, max_bs):
        """Test raw I/O. """
        print("\n*** Testing raw I/O performance on %s" % testdev)
        size = self.dev_size(testdev)
        raw_test_file = "/dev/" + testdev

        # options = "--filename=%s --size=%sk --bs=%s" % (raw_test_file, size, max_bs)
        options_dict = {"test_file": raw_test_file, "size": size, "min_bs": min_bs, "max_bs": max_bs}

        print("\nTesting random read-write on Device")
        if not self.fio_dt_test("throughput-rand-rw-device", options_dict, is_random=True, is_direct=True):
            print("Error: Device random read-write test failed")
            self.unmount(testdev)
            return False
        print("Device random read-write test passed !!")

        print("\nTesting sequential read-write on Device")
        if not self.fio_dt_test("throughput-seq-rw-device", options_dict, is_random=False, is_direct=True):
            print("Error: Device random read-write test failed")
            self.unmount(testdev)
            return False
        print("Device sequential read-write test passed !!")
        print("Raw I/O testing passed.\n")
        return True 

    # -> run -> run_storage -> run_disk -> test_vfs/test_raw_io
    def fio_dt_test(self, name, options_dict, is_random=False, is_direct=False):
        """
        Execute the fio test if RHEL version is greater than 7.4
        else call the dt test
        """
        # Call fio test if RHEL version > 7.4
        if self.test_pkg == "fio":
            return self.fio_test(name, options_dict, is_random, is_direct)

        # Call dt test
        return self.dt_test(options_dict, is_random, is_direct)
    
    # -> run -> run_storage -> run_disk -> test_vfs/test_raw_io -> fio_dt_test
    def fio_test(self, name, options_dict, is_random=False, is_direct=False):
        """
        Execute the fio command and log the output
        """
        options = "--filename=%s --size=%sk --bs=%s" \
                  % (options_dict.get("test_file"), options_dict.get("size"), options_dict.get("max_bs"))

        parameters = "--ioengine=libaio --numjobs=4 --runtime=60 --time_based --group_reporting --eta-newline=1"
        direct_param = ""
        if is_direct:
            direct_param = "--direct=1"

        rand_param = "--rw=rw"
        if is_random:
            rand_param = "--rw=randrw --iodepth=64"

        command = "fio --name=%s %s %s %s %s" % (name, options, rand_param, direct_param, parameters)
        try:
            print("Executing the fio command: %s" % command)
            sys.stdout.flush()
            print(subprocess.getoutput(command))
        except Exception as e:
            print("Error: Failed to excute the fio command !!")
            print(e)
            return False
        sys.stdout.flush()
        return True

    def dt_test(self, options_dict, is_random, is_direct):
        """
        Do a few passes of read/write testing on the given device.
        """
        size = options_dict.get("size")
        min_bs = options_dict.get("min_bs")
        max_bs = options_dict.get("max_bs")
        test_file = options_dict.get("test_file")
        direct_params = "enable=aio aios=8"
        if is_direct:
            direct_params = "flags=direct rlimit=%s" % (size * 1024)

        random_params = "iotype=sequential dispose=keep"
        if is_random:
            # generate a random seed first
            seed = random.randint(0, 32767)
            random_params = "iotype=random dispose=keep enable=verify ralign=%s rseed=%s dlimit=%s" % (min_bs, seed, size)

        parameters = "of=%s %s %s" % (test_file, direct_params, random_params)
        sys.stdout.flush()

        return self.do_dt(min_bs, max_bs, size, parameters)

    def do_dt(self, min_bs, max_bs, size, parameters):
        """
        Run dt with various block sizes
        """
        records = size * 1024 / max_bs
        bs = min_bs
        while bs <= max_bs:
            command = "dt pattern=0xDEADBEEF bs=%d records=%d %s" % (bs, records, parameters)
            try:
                print("Executing the dt command: %s" % command)
                sys.stdout.flush()
                print(subprocess.getoutput(command))
            except Exception as e:
                print("Error: Failed to execute the dt command !!")
                print(e)
                return False
            sys.stdout.flush()
            bs = bs * 2
        return True

    # -> run -> run_storage -> run_disk -> test_vfs/test_raw_io
    def unmount(self, testdev):
        """Unmount, if the device is mounted"""
        device_file = "/dev/" + testdev
        # print("Warning: device %s not in /proc/mounts" % device_file)
        command = "umount %s" % device_file
        print("Unmounting device using command: %s" % command)
        try:
            subprocess.getoutput(command)
            return True
        except Exception:
            print("Failed to unmount device ")
            return False

    # -> run -> run_storage -> run_disk -> test_raw_io
    def dev_size(self, test_device):
        # Use 1GB or the device size whichever is smaller.
        size = self.max_size
        command = "cat /sys/block/%s/size" % test_device
        # Why is the /sys size value 2x what /proc shows?
        try:
            size_output = int(subprocess.getoutput(command))
            act_size = size_output / 2
            if act_size < self.max_size:
                size = act_size
            print("Testing device size %s" % size)
        except Exception:
            print("Warning: can not get device size from /sys/block/%s/size, defaulting to %s. " % (test_device, size))

        sys.stdout.flush()
        return size

    # -> run -> run_storage -> run_disk
    def restoreSwap(self, swapdev, swap_label):
        """restore a swap device, given its short name (e.g. 'hda')"""
        swap_file_tmp = open("/proc/swaps", "r")
        swap_file = swap_file_tmp.read()
        swap_file_tmp.close()
        if swapdev not in swap_file:
            swap_on_device = "/dev/%s" % swapdev
            if swap_label:
                swap_on_device = "LABEL=%s" % swap_label
                mkswap_option = "-L %s" % swap_label
                print("restoring swap label '%s' ..." % swap_label)
            else:
                mkswap_option = " "
                print("swap device has no label.")
            # restore the swap device
            print("restoring swap device /dev/%s ..." % swapdev)
            try:
                subprocess.getoutput("umount /dev/%s" % swapdev)
            except Exception as e:
                print("umount failed:")
                print(e)

            try:
                subprocess.getoutput("mkswap %s /dev/%s" % (mkswap_option, swapdev))
            except Exception as e:
                print("Warning: mkswap may have failed.")
                print(e)
            try:
                subprocess.getoutput("swapon %s" % swap_on_device)
                print("done.")
                return True
            except Exception as e:
                print("Error: could not restore swap")
                print(e)
                return False
        return True

if __name__ == "__main__":
    test = StorageTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        value = test.run()
    sys.exit(0)
