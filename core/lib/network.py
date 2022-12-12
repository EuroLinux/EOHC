#!/usr/bin/python3
# Author: Radoslaw Kolba
# Network library is used by wlan test
#

import os, signal, sys, re, time, subprocess
import math

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.release import EuroLinuxRelease
from core.test import Test
from core.lib.devices import get_devices


class Wireless:
    def __init__(self):
        self.interfaces = list()
        self.parameters = dict() # parameter[interface][name]
        self.output = None
        self.__parse()
        self.debug = "off"

    def __parse(self, search_interface=None):
        nmcli = "nmcli device"
        """
        expected output:
            NetworkManager-0.9.9.0
            DEVICE             TYPE      STATE
            wlp3s0             wifi      connected
            0C:71:5D:F6:AD:A3  bt        disconnected
            em1                ethernet  unavailable
            lo                 loopback  unmanaged
            virbr0-nic         tap       unmanaged
            tun0               tun       unmanaged'

            NetworkManager-0.9.9.1-13:
            DEVICE   TYPE      STATE                                  CONNECTION
            enp0s25  ethernet  connected                              enp0s25
            wlp3s0   wifi      connected                              Auto Metropolis 5GHz
            virbr0   bridge    connecting (getting IP configuration)  virbr0
            lo       loopback  unmanaged                              --
            tun0     tun       unmanaged                              --
        """

        try: # python3
            pipe = subprocess.Popen(nmcli, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8')
        except TypeError: # python2
            pipe = subprocess.Popen(nmcli, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (output, errors) = pipe.communicate()
        
        if output:
            self.output = output.splitlines()
            interface_patten = re.compile("(?P<interface>[^\s]+)\s+(?P<type>[^\s]+)\s+(?P<state>[^\s]+)")
            for line in self.output:
                match = interface_patten.search(line)
                if match:
                    if match.group("type") == "wifi":
                        self.interfaces.append(match.group("interface"))

        for interface in self.interfaces:
            iw =  "iw %s link" % interface
            """
            Connected to 00:18:f8:70:8b:ee (on wlp3s0)
                SSID: AtomicSpatula
                freq: 2462
                RX: 886341 bytes (2184 packets)
                TX: 82203 bytes (473 packets)
                signal: -59 dBm
                tx bitrate: 54.0 MBit/s
                bss flags:    short-slot-time
                dtim period:    0
                beacon int:    100
            """
            try: # python3
                pipe = subprocess.Popen(iw, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8')
            except TypeError: # python2
                pipe = subprocess.Popen(iw, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            (output, errors) = pipe.communicate()

            if output:
                self.output = output.splitlines()
                for line in self.output:
                    self.__add_parameters(interface, line)

    def __add_parameters(self, interface, parameter_string):
            pair = parameter_string.split(":")
            if len(pair) == 2:
                if not interface in self.parameters:
                    self.parameters[interface] = dict()
                self.parameters[interface][pair[0].strip()] = pair[1].strip()

    def get_type(self, logical_name=None):
        phy_list = self.get_phy_list()
        for phy in phy_list:
            if phy != self.get_phy(logical_name):
                continue
            try:
                all_the_info = subprocess.getoutput("iw %s info" % phy).split("\n")
            except Exception as e:
                continue
            vht_capabilities = [x for x in all_the_info if 'VHT Capabilities' in x]
            short_GI80 = [x for x in all_the_info if 'short GI (80 MHz)' in x]
            ht20_ht40 = [x for x in all_the_info if 'HT20/HT40' in x]
            fifty_four_Mbps = [x for x in all_the_info if '54.0 Mbps' in x]

            if self.is_ax_device(logical_name) and self.test_interface_speed(logical_name, 1200):
                print("Wireless AX")
                return "ax"
            elif vht_capabilities and short_GI80 and self.test_interface_speed(logical_name, 1200):
                print("Wireless AX")
                return "ax"
            elif vht_capabilities and short_GI80:
                print("Wireless AC")
                return "ac"
            elif ht20_ht40 and not vht_capabilities:
                print("Wireless N")
                return "n"
            elif fifty_four_Mbps and not ht20_ht40 and not vht_capabilities:
                print("Wireless G")
                return "g"
            else:
                print("Wireless B")
                return "b"
        return None

    def get_phy_list(self):
        rfkill_command = "rfkill list all"
        try:
            pattern = re.compile("\d: (?P<wifi>.*):.*Wireless LAN")
            rfkill = subprocess.getoutput(rfkill_command)
            return pattern.findall(rfkill)
        except:
            print("Warning: no wifi device found")
            return []

    def get_phy(self, logical_name):
        """
        This method returns phy of device from
        the logical_name
        Parameters:
        logical_name (str):  Logical Name of Device

        Returns:
        char: 'phy' of Device
        """
        try:
            dev_cmd_info = subprocess.getoutput("iw dev").split("\n")
        except Exception as e:
            return None

        phy = str()
        for attr in dev_cmd_info:
            try:
                if attr.startswith("phy"):
                    phy = attr.replace('#','')
                elif 'Interface' in attr:
                    interface_name = attr.strip().split(' ')[1]
                    if interface_name == logical_name:
                        return phy
            except KeyError as e:
                continue
        return None

    def is_ax_device(self, logical_name):
        """
        This method identifies whether the device has
        AX Support based on the Product Name.

        Parameters:
        logical_name (str):  Logical Name of Device

        Returns:
        bool: True if the device passes the AX Test
        parameters else False.
        """
        # Check product name that includes 'AX' or 'Wifi 6'
        product_name = self.get_product_name(logical_name)
        filtered_product_name = ''.join(e.lower() for e in product_name if e.isalnum())
        if 'ax' in filtered_product_name or 'wifi6' in filtered_product_name:
            return True
        return False

    def get_product_name(self, logical_name):
        lshw_command = "lshw -c network | grep -B5 'logical name: {}'".format(logical_name)
        try:
            lshw_command_string_list = subprocess.getoutput(lshw_command).strip("\n")
            products = [x.strip().replace('product: ','') for x in lshw_command_string_list if 'product' in x]
            if products:
                return products[0]
        except Exception as e:
            print("Error: Could not identify product name from logical device name.")
            print(e)
        return str()

    def test_interface_speed(self, logical_name, test_speed=0):
        """
        This method performs interface speed test.

        Parameters:
        logical_name (str):  Logical Name of Device
        test_speed (int):  Assuming integer values as test speed.
        Applicable for float type also.

        Returns:
        bool: True if the device passes the Speed Test
        parameters else False.
        """
        # Check Interface Speed (Connection Speed)
        connection_speed = self.get_connected_speed(logical_name)
        try:
            print("Wifi Connection Speed:")
            print(connection_speed)
            connection_speed_value = connection_speed.split('MBit/s')[0].strip()
            #Check if the interface speed is greater than or equal to 1200
            if float(connection_speed_value) >= test_speed:
                return True
            else:
                return False
        except:
            return False

    def get_connected_speed(self, interface):
        if interface in self.interfaces and interface in self.parameters:
            if "tx bitrate" in self.parameters[interface]:
                return self.parameters[interface]["tx bitrate"]
        return None

    def get_interfaces(self): return self.interfaces


class NetworkTest(Test):
    """ NetworkTest is the base class for specific network tests """

    iperf_port = 5201
    ipref_total_ports = 2

    def __init__(self, path):
        self.release = EuroLinuxRelease()
        self.user = None
        self.test_server = "lon.speedtest.clouvider.net"
        path = "network/" + path
        Test.__init__(self, path)
        self.no_proc = 2
        self.ip_address = ""
        self.test_file = "/var/www/html/httptest.file"
        self.temp_file = "/tmp/scp-test.txt"
        self.all_other_interfaces = list()
        self.interface_speed = 100 # speed in Mb/sec
        self.old_handler = None
        self.is_nfs_root_system = False
        self.ignore_interfaces = re.compile("lo$|peth\d+|virbr\d+|vif\d+.\d+|xenbr\d+|wmaster\d+|sit\d+")
        self.enforce_speed = False
        self.bandwidth_target = 0.6 # 60%
        self.interface_connect = "nmcli conn up"
        self.interface_disconnect = "nmcli conn down"
        self.alt_interface_connect = "nmcli dev connect"
        self.alt_interface_disconnect = "nmcli dev disconnect"
        self.opened_ports = list()
        if self.release.get_version() == 7:
            self.interface_connect = "ifup"
            self.interface_disconnect = "ifdown"

    def get_required_rpms(self):
        return ["ethtool", "coreutils", "iperf3", "biosdevname"]

    def get_network_devices(self):
        """ returns a dictionary of devices by logical device names that are networking interfaces """
        interface_devices = dict()
        devices = get_devices("net")
        for device in devices:
            logical_device = None
            logical_device = device["INTERFACE"]

            """ if network logical device was found, and not already planned,
            and it's not in the ignore list, add it"""
            if logical_device and logical_device != "" and not logical_device in interface_devices and not self.ignore_interfaces.search(logical_device):
                interface_devices[logical_device] = device
        return interface_devices

    def run(self):
        self.user = "root"
        try:
            # start preparing systems
            if not self.run_sub_test(self.prepare_for_run, "Network setup", "prepare for network testing"):
                return False
            if not self.run_sub_test(self.start_iperf_services_on_lts, "Network iperf3", "start iperf3 service on test server"):
                return False
            if not self.run_sub_test(self.configure_interfaces, "Network interfaces", "configuration of the interfaces"):
                return False
            if not self.run_sub_test(self.print_info, "Network info", "showing NIC informations"):
                return False
            if not self.run_sub_test(self.device_naming, "Network device", "show device naming and types for all detected interfaces"):
                return False

            # start testing
            success = True
            if not self.run_sub_test(self.tcp_test_latency, "Network latency TCP", "checking TCP latency via iperf3"):
                success = False
            if not self.run_sub_test(self.tcp_test_bandwidth, "Network throughput TCP", "checking TCP throughput via iperf3"):
                success = False
            if not self.run_sub_test(self.udp_test, "Network latency UDP", "checking UDP latency via iperf3"):
                success = False
            if not self.run_sub_test(self.icmp_test, "Network ICMP test", "checking number of loss packets"):
                success = False
            if not self.run_sub_test(self.stop_iperf_services_on_lts, "Network iperf3 stop", "stops iperf3 service on test server"):
                success = False

            self.set_signal_handler(None)
            if self.is_nfs_root_system:
                self.remove_route()
            else:
                self.restore_all_other_interfaces()
            if success:
                return True
            return False
        except Exception as e:
            print(e)
        finally:
            self.close_ports(NetworkTest.iperf_port, NetworkTest.iperf_port + NetworkTest.ipref_total_ports)
    
    # 1
    def prepare_for_run(self):
        print("\nStarting network test verification...")
        errors = list()
        self.interface = self.logical_device_name
        if not self.interface:
            errors.append("No logical interface name set.")
        else:
            self.ip_address = self.get_ip_address(self.interface)
            if not self.ip_address:
                errors.append("Could not determine IP Address.")

        if self.test_server is None or self.test_server == "unknown":
            errors.append("No test server was set.")

        self.get_all_other_interfaces()
        self.check_nfs_root_file_system()
        self.open_ports(NetworkTest.iperf_port, NetworkTest.iperf_port + NetworkTest.ipref_total_ports)

        if errors:
            print("\nNetwork test for %s failed verification:" % self.interface)
        else:
            print("\nNetwork test verified for %s at %s" % (self.interface, self.ip_address))
            return True

        for error in errors:
            print("Error: %s" % error)

    def get_ip_address(self, interface):
        pipe = os.popen("ip -4 addr show %s" % (interface))
        pattern = re.compile("\d+\.\d+\.\d+\.\d+")
        while 1:
            line = pipe.readline()
            match = pattern.search(line)
            if match or not line:
                break
        pipe.close()
        if match:
            ip_address = match.group()
            return ip_address
        else:
            return None

    def get_all_other_interfaces(self):
        self.all_other_interfaces = list()
        # Added awk for @ to support rdma interfaces eg: qib_ib0.8006@qib_ib0
        pipe = os.popen("/sbin/ip -o link show | awk -F \": \" '/UP>/ { print $2 }' | awk -F \"@\" '{print $1}'")
        while 1:
            line = pipe.readline()
            if line:
                interface = line.strip()
                if not self.ignore_interfaces.search(interface):
                    if interface != self.interface:
                        self.all_other_interfaces.append(interface)
                print("ignoring interface %s" % interface)
            else:
                break
        pipe.close()

    def open_ports(self, start_port, end_port):
        print("Openning ports")
        for port in range(start_port, end_port):
            print("\nOPENING PORT: " + str(port))
            self.opened_ports.append(port)
            print(subprocess.getoutput('sudo firewall-cmd --add-port ' + str(port)+'/tcp'))
            print(subprocess.getoutput('sudo firewall-cmd --add-port ' + str(port)+'/udp'))
    
    def close_ports(self, start_port, end_port):
        print("Closing ports")
        for port in range(start_port, end_port):
            if port in self.opened_ports:
                print("\nCLOSING PORT: " + str(port))
                self.opened_ports.remove(port)
                print(subprocess.getoutput('sudo firewall-cmd --remove-port ' + str(port)+'/tcp'))
                print(subprocess.getoutput('sudo firewall-cmd --remove-port ' + str(port)+'/udp'))

    # 2
    def start_iperf_services_on_lts(self):
        no_proc = self.no_proc
        try:
            no_proc = int(subprocess.getoutput("nproc"))
        except Exception:
            print("Warning: Unable to fetch no of processors. Using the default value: %s" % self.no_proc)
        # Calculate required parallel thread
        # +1 thread for each 10 Gbps throughput
        # eg: speed 25000
        # speed_in_gbps 25
        speed_in_gbps = float(self.interface_speed) / 1000
        # req_threads = 2.5
        req_thread = max(float(speed_in_gbps) / 10, 2)
        # req_threads = 3
        req_thread = math.ceil(req_thread)
        self.no_proc = min(req_thread, no_proc)
        print("No. of parallel iperf thread required: %s" % self.no_proc)
        check_firewall = True
        check_firewall = self.__check_firewall_ports()
        result = self.__do_iperf_action('start', no_proc=self.no_proc)
        if not check_firewall:
            return "WARN"
        return result

    def __check_firewall_ports(self):
        result = True
        start_iperf_port = NetworkTest.iperf_port
        total_iperf_ports = NetworkTest.ipref_total_ports
        req_ports = []
        for port in range(start_iperf_port, start_iperf_port + total_iperf_ports):
            req_ports.append(port)
        ports_to_open = self.__get_firewall_ports(req_ports)
        if ports_to_open:
            result = False
            print("Warning: Following ports need to be opened: %s " % str(ports_to_open))
            print("Warning: Network test may fail if above ports are not opened on the Test Server.")
        return result

    def __get_firewall_ports(self, req_ports):
        print("Checking firewall ports on Test Server")
        fw_open_ports_cmd = "firewall-cmd --zone=public --list-ports"
        print("Required Ports: %s" % str(req_ports))
        try:
            output = subprocess.getoutput(fw_open_ports_cmd)
            fw_open_ports = output.split()
        except Exception as error:
            print("Warning: Could not check port status using firewall-cmd")
            print(error)
            print("Warning: Please check that port %s is opened for both TCP and UDP" % str(req_ports))
            return []
        req_open_ports = []
        for port in req_ports:
            req_open_ports.append("%s/tcp" % port)
            req_open_ports.append("%s/udp" % port)
        ports_to_open = list(set(req_open_ports) - set(fw_open_ports))
        return ports_to_open

    def __do_iperf_action(self, verb, no_proc=2):
        if verb not in ['start', 'stop']:
            return False
        result = True
        start_port = NetworkTest.iperf_port
        if verb == 'start':
            print("Starting iperf3 server on Test Server")
            try:
                cmd_wt_port = "for port in `seq %s %s`; do iperf3 -s -D -p $port; done"\
                              % (start_port, (start_port + int(no_proc) - 1))
                print("Using the command: %s" % cmd_wt_port)
                print(subprocess.getoutput(cmd_wt_port))
            except Exception as e:
                print("Error: Failed to start the iperf3 server on Test Server")
                print(e)
                result = False
        else:          
            print("Stopping iperf3 server on Test Server")
            subprocess.getoutput("pkill -f -15 iperf3")

        return result

    # 3
    def configure_interfaces(self):
        sys.stdout.flush()
        if not self.bounce_interface():
            print("Error: could not bounce interface %s" % self.interface)
            return False
        if self.is_nfs_root_system:
            if not self.add_route():
                print("Error: could not add route for testing")
                return False
            self.set_signal_handler(self.remove_route)
        else:
            if not self.down_all_other_interfaces():
                print("Error: could not shutdown all other interfaces")
                return False
            self.set_signal_handler(self.restore_all_other_interfaces)

        if not self.create_test_file():
            print("Error: Unable to create test file")
            return False
        return True

    def bounce_interface(self):
        if self.is_nfs_root_system:
            print("It appears that the root file system is NFS mounted")
        success = True
        # shut it down
        if not self.shutdown_interface(self.interface):
            print("Error: could not shut down interface %s" % self.interface)
            success = False
        # Waiting for 2 sec, before we start the interface again
        time.sleep(2)
        if not self.start_interface(self.interface):
            print("Error: could not restart interface %s" % self.interface)
            success = False
        if not self.ping_test_server(self.interface):
            print("Error: could not ping test server %s " % self.test_server)
            success = False
        return success
    
    def shutdown_interface(self, interface):
        try_alt = False
        print("Shutting down interface %s" % interface)
        if subprocess.getstatusoutput("%s %s" % (self.interface_disconnect, interface))[0] != 0:
            print("Warning: Unable to shutdown the interface %s. Using alternate command" % interface)
            try_alt = True
        if try_alt:
            print("Shutting down interface using command: %s %s" % (self.alt_interface_disconnect, interface))
            if subprocess.getstatusoutput("%s %s" % (self.alt_interface_disconnect, interface))[0] != 0:
                print("Warning: could not shut down interface %s" % interface)

        # confirm that it really went down (or is all ready down)
        slept=0
        delay=15
        down = False
        while not down and slept < delay:
            if subprocess.getstatusoutput("ip -f inet addr show %s | grep inet" % interface)[0] == 0:
                print("Interface %s is up" % interface)
                time.sleep(1)
                slept = slept + 1
            else:
                print("interface %s is down" % interface)
                down = True
        if not down:
            print("Error: Unable to shut down interface %s" % interface)
        return down

    def start_interface(self, interface):
        count = 0
        retry_count = 10
        interface_up = False
        while count < retry_count and not interface_up:
            sys.stdout.flush()
            print("Bringing up interface %s attempt no. %s" % (interface, count))
            if subprocess.getstatusoutput("%s %s" % (self.interface_connect, interface))[0] == 0:
                interface_up = True
            else:
                if subprocess.getstatusoutput("%s %s" % (self.alt_interface_connect, interface))[0] == 0:
                    interface_up = True
                time.sleep(2)
                count += 1
        if not interface_up:
            print("Error: Failed to bring up the device %s" % interface)
            return False
        sys.stdout.flush()

        # Since there can be a delay between ifup and linkup we need to
        # wait to see the interface running.
        slept=0
        wait = 3
        delay=30
        print(subprocess.getoutput("ip -f inet addr show %s | grep inet" % interface))
        while slept < delay:
            try:
                print("Interface %s is UP" % interface)
                return True
            except Exception:
                time.sleep(wait)
                slept = slept + wait
                sys.stdout.flush()
        return False

    def get_interface_ip(self, interface):
        try:
            ip_addr_command = subprocess.getoutput("ip addr show %s | grep inet" % interface)
            match = re.search('.*inet (?P<ip_address>.+)\/.*', ip_addr_command)
            return match.group('ip_address')
        except Exception:
            print("Error: ip addr show %s has no inet configured" % interface)
            return None

    def ping_test_server(self, interface):
        interface_ip = self.get_interface_ip(interface)
        if not interface_ip:
            return False
        wait = 3 # sec
        slept=0
        delay=30 # sec
        sys.stdout.write("Checking via ping to %s... " % self.test_server)
        print("ping -I %s -Ac1 %s > /dev/null" % (interface_ip, self.test_server))
        while slept < delay:
            if os.system("ping -I %s -Ac1 %s > /dev/null" % (interface_ip, self.test_server)):
                time.sleep(wait)
                slept = slept + wait
            else:
                print("done")
                return True
        return False

    def get_interface_speed(self, interface):
        interface_speed = 0
        for interface_string in (interface, "p%s" % interface):
            try:
                ethtool_command = subprocess.getoutput("ethtool %s" % interface_string)
                match = re.search('([ \t]+Speed:[ \t]+)(?P<speed>\d+)(Mb/s)', ethtool_command)
                interface_speed = match.group('speed')
                if interface_speed:
                    break
            except Exception as e:
                pass

        return interface_speed

    def create_test_file(self):
        if not self.interface_speed:
            self.interface_speed = self.get_interface_speed(self.interface)

        if not self.interface_speed:
            self.interface_speed = 100 # Mb/s
            print("Warning: Unable to determine interface speed")
            print("Assuming %u Mb/s" % self.interface_speed)
        else:
            print("interface speed is %u Mb/s" % self.interface_speed)
        self.regenerate_test_file(file=self.temp_file)
        return self.regenerate_test_file()

    def add_route(self):
        pattern = re.compile("\d+\.\d+\.\d+\.\d+")
        match = pattern.search(self.test_server)
        if match:
            self.test_server_spec = "-net"
        else:
            self.test_server_spec = "-host"

        if os.system("route add %s %s dev %s" % (self.test_server_spec, self.test_server, self.interface )) != 0:
            return False
        else:
            return True

    def down_all_other_interfaces(self):
        if not self.all_other_interfaces:
            return True
        print("Shutting down all other network interfaces...")
        for interface in self.all_other_interfaces:
            print(interface)
            if not self.shutdown_interface(interface):
                return False
        wait = 10 # sec
        sys.stdout.write("waiting %d sec..." % wait)
        sys.stdout.flush()
        time.sleep(wait)
        print("done")
        return True

    def regenerate_test_file(self, file=None):
        if not file:
            file = self.test_file
        try:
            os.remove(file)
        except OSError:
            pass
        # use interface_speed/8, creating a file that takes very roughly 10 sec to transfer
        count = self.interface_speed/8
        blocksize = 128 # KB
        try:
            subprocess.getoutput("dd if=/dev/urandom of=%s bs=%uk count=%u" % (file, blocksize, count))
        except Exception:
            # dd shows output on stderr, ignore this
            pass
        return True

    # 4
    def print_info(self):
        # YK: grab NIC info and running status
        sys.stdout.flush()
        try:
            ethtool_cmd = "ethtool %s" % self.interface
            print(ethtool_cmd)
            subprocess.getoutput(ethtool_cmd)
            print("")
            try:
                ip_link_show = subprocess.getoutput("ip link show %s | grep link/ether" % self.interface)
                match = re.search('.*link/ether (?P<address>[a-fA-F0-9:]+)', ip_link_show)
                address = match.group('address')
                print("MAC Address: %s" % address)
            except Exception as e:
                print("Warning: could not determine MAC address")
                print(e)
            biosdevname_cmd = "biosdevname -d %s" % self.interface
            print("")
            print(biosdevname_cmd)
            subprocess.getoutput(biosdevname_cmd)
        except Exception as e:
            print("Warning: %s" % e)

        return True

    # 5
    def device_naming(self):
        """ show device naming and types for all detected interfaces """
        interface_devices = dict()
        devices = get_devices("net")
        for device in devices:
            logical_device = None
            logical_device = device["INTERFACE"]
            interface_devices[logical_device] = device

        biosdevname = subprocess.getoutput("sudo biosdevname -d")
        bios_devices = None
        try:
            devices = dict()
            device = dict()
            for line in biosdevname.split("\n"):
                if line == "":
                    devices[device["Kernel name"]] = device
                    device = dict()
                value = line.split(":")
                if len(value) == 2 and value[1].strip() != "":
                    device[value[0].strip()] = value[1].strip()
            bios_devices = devices
        except Exception as e:
            print("Note: could not read biosdevname")
            print(e)

        for (interface_name, interface_device) in interface_devices.items():
            print("\n%s:\n%s" % (interface_name, '-' * (len(interface_name)+1)))
            #1. Verify the interface is under network manager control (psuedo verifying default naming is in play) label each as NM true/false
            managed = "GENERAL.NM-MANAGED"
            nmcli_cmd = "nmcli device show %s" % interface_name
            attributes = dict()
            try:
                nmcli = subprocess.getoutput(nmcli_cmd)
                for line in nmcli.split("\n"):
                    if ":" in line:
                        values = line.split(":")
                        attributes[values[0].strip()] = values[1].strip()
            except Exception as e:
                print("Error: running %s" % nmcli_cmd)
                print(e)
                return False

            answer = "no"
            if managed in attributes:
                answer = attributes[managed]
            print("Network Manager Controlled: %s" % answer)
            #2. For all of the Firmeware or BIOS provided indexes (including biosdevname) device names label these in the output as "firmware based naming"
            embedded = None
            removable = None
            if bios_devices and (interface_name in bios_devices):
                #3. For all of the Firmware based naming options which are not slot based label these as "embedded"
                pci_slot = "PCI Slot"
                if pci_slot in bios_devices[interface_name] and "embedded" in bios_devices[interface_name][pci_slot]:
                    embedded = "yes"
                    removable = "no"
                else:
                    removable = "yes"
                    embedded = "no"
            else:
                #2a. For all others, label these as "non-firmware based naming"
                print("BIOS device: non-firmware based naming")
            if embedded:
                print("Embedded: %s" % embedded)
            if removable:
                print("Removable: %s" % removable)

        return True

    # 6
    def tcp_test_latency(self):
        print("Testing TCP latency to %s..." % self.test_server)
        sys.stdout.flush()
        try:
            cmd_wo_port = "iperf3 -c %s -t 5" % self.test_server
            for i in range(5):
                result = subprocess.getstatusoutput(NetworkTest.add_iperf_port(cmd_wo_port))
                if result[0] == 0:
                    print(result[1])
                    break
                print(result)
                time.sleep(5)
        except Exception as e:
            print("Error: TCP latency test failed")
            print(e)
            return False
        return True

    @staticmethod
    def add_iperf_port(cmd):
        if NetworkTest.iperf_port:
            cmd = cmd + " -p %s" % NetworkTest.iperf_port
        return cmd

    # 7
    def tcp_test_bandwidth(self):
        print("Testing TCP bandwidth to %s..." % self.test_server)
        cycles = 5
        no_proc = self.no_proc
        start_port = NetworkTest.iperf_port
        bw_tcp = "for port in `seq %s %s`; do iperf3 -c %s -p $port -f m -T $port & done | grep Mbits/sec" % (start_port, (start_port + int(no_proc) - 1), self.test_server)
        for p in range(cycles):
            print("\n\nAttempt No: %s" % (p + 1))
            try:
                while True:
                    bw_output = subprocess.getstatusoutput(bw_tcp)
                    if bw_output[0] == 0:
                        bw_output = bw_output[1].split("\n")
                        break
                    time.sleep(1)
            except Exception as e:
                print("Error: TCP bandwidth test failed")
                print(e)
                return False
            speed = 0.0
            for output in bw_output:
                match = re.search(".*?(?P<speed>[\d\.]+)\s+Mbits/sec.*", output)
                if match:
                    sp = match.group("speed")
                    print("Bandwidth Output: '%s'\n    Speed: %s Mb/sec" % (output.split(":")[1].strip(), sp))
                    speed += float(sp)
            print("\nTotal Bandwidth: %s Mb/sec" % speed)
            if speed > self.interface_speed * self.bandwidth_target:
                print("\nSuccess: Required bandwidth achieved !!")
                return True
            print("\nWarning: Total Bandwidth %s Mb/sec is less than %s%% of the interface speed of %s Mb/sec" % (speed, self.bandwidth_target * 100, self.interface_speed))
        if self.enforce_speed:
            print("\nError: Could not achieve required bandwidth")
            return False
        return True

    # 8
    def udp_test(self):
        print("Testing UDP latency to %s..." % self.test_server)
        sys.stdout.flush()
        try:
            cmd_wo_port = "iperf3 -c %s -t 5 -u" % self.test_server
            for i in range(5):
                result = subprocess.getstatusoutput(NetworkTest.add_iperf_port(cmd_wo_port))
                if result[0] == 0:
                    print(result[1])
                    break
                print(result)
                time.sleep(5)
        except Exception as e:
            print("Error: UDP latency test failed")
            print(e)
            return False
        return True

    # 9
    def icmp_test(self):
        retries = 5
        packet_count = 5000
        loss_margin = 1.00
        loss_margin_error = 3.00
        while retries > 0:
            try:
                ping_cmd = "/bin/ping -i 0 -q -c %u %s" % (packet_count, self.test_server)
                print(ping_cmd)
                ping = subprocess.getoutput(ping_cmd)
                match = re.search(".*, (?P<packetLoss>\d+\.{0,1}\d*)% packet loss.*", ping)
                packet_loss = match.group("packetLoss")
                if float(packet_loss) <= loss_margin:
                    print("SUCCESS: Packet loss of %s%% is less than %s%% expected!" % (packet_loss, loss_margin))
                    return True
                elif float(packet_loss) <= loss_margin_error:
                    print("WARNING: Packet loss of %s%% is high, but less than maximum %s%% expected!" % (packet_loss, loss_margin_error))
                    return "WARN"
                else:
                    print("Note: packet loss of %s%% is greater than %s%% expected" % (packet_loss, loss_margin_error))
            except Exception as e:
                print("Warning:")
                print(e)
            retries = retries -1
        return False
    
    # 10
    def stop_iperf_services_on_lts(self):
        return self.__do_iperf_action('stop')

    # 11
    def set_signal_handler(self, handler):
        signals = [signal.SIGINT, signal.SIGTERM]
        for sig in signals:
            if handler:
                self.old_handler = signal.signal(sig, handler)
            else:
                signal.signal(sig, self.old_handler)
    
    def remove_route(self, sig=None, frame=None):
        if os.system("route del %s %s dev %s" % (self.test_server_spec, self.test_server, self.interface )) != 0:
            return False
        return True
    
    def restore_all_other_interfaces(self, sig=None, frame=None):
        print("Restoring all interfaces...")
        for interface in self.all_other_interfaces:
            print("    interface: %s" % interface)
            try_alt = False
            try:
                subprocess.getoutput("%s %s" % (self.interface_connect, interface))
            except Exception as e:
                print("Warning: unable to restore interface %s. Using alternate command" % interface)
                print(e)
                try_alt = True

            if try_alt:
                try:
                    subprocess.getoutput("%s %s" % (self.alt_interface_connect, interface))
                except Exception as e:
                    print("Error: could not restore interface %s" % interface)
                    print(e)

        # Bring down and up the interface if current interface is VLAN interface e.g: qib_ib0.8006
        # Required because bringing qib_ib0 up causes qib_ib0.8006 to go down: CERTPX-3796
        pattern = re.compile("(.*)\.(\d+)$")
        match = pattern.match(self.interface)
        if match:
            if match.group(1) in self.all_other_interfaces:
                self.bounce_interface()
