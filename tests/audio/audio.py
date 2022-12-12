# Copyright (c) 2006-14 Red Hat, Inc. All rights reserved. This copyrighted material
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
import os, sys, time, glob, re, subprocess

directory = os.path.abspath('../..')
sys.path.append(directory)

from core.test import Test
from core.lib.devices import get_devices
from core.lib.command_line import prompt_confirm

class AudioTest(Test):

    def __init__(self):
        Test.__init__(self, "audio")
        self.card_number = 0
        self.capture_support = False
        self.hdmi = False
        self.audio = None
        self.interactive = True
        self.priority = 5 # medium

    def get_required_rpms(self):
        return ["alsa-utils"]

    def plan(self):
        """
        Plans tests for audio test.  Can handle multiple variations of cards and
        functionality including one solitary card supporting hdmi and internal sound.
        First, tests are planned by matching devices to a set of criteria, assigning
        one test per sound card matching it, where if hdmi is supported, that will be
        the test run on that card.  This is enough for where hdmi and internal sound
        are not supported on the same card.  In order to handle the case where they
        are on the same card, we must check and see if there is an Internal sound test
        planned and if not, plan one if possible, even if the card is already planned
        for an hdmi test.
        """
        tests = list()
        list_aplay_command = subprocess.getoutput("aplay -l")
        pattern = re.compile("(?P<card>(?<=card )\d+(?=.*Analog))")
        match = pattern.search(list_aplay_command)
        if match:
            card_number = int(match.group("card"))
            devices = get_devices("sound")
            for device in devices:
                if "/card%s" % card_number in device['_PATH'] and \
                    "/card%s/" % card_number not in device['_PATH']:
                    self.card_number = card_number
                    test = self.make_copy()
                    test.audio = device
                    test.audio["_DEVICE_NAME"] = "Internal"
                    tests.append(test)
        return tests

    def set_logical_name(self, test):
        pipe = os.popen("amixer -c %s controls" % self.card_number)
        if 'HDMI/DP,pcm=' in ' '.join(pipe.readlines()):
            test.audio["_DEVICE_NAME"] = "HDMI/DP"
        else:
            test.audio["_DEVICE_NAME"] = "Internal"

    def log_sound_card_info(self):
        if self.audio:
            print("\nSound card info:")
            for info in self.audio.keys():
                print("\t%s: %s" % (info, self.audio[info]))
            for infopath in glob.glob("/proc/asound/card%s/pcm*/info" % self.card_number):
                print("")
                print(infopath)
                print(subprocess.getoutput("cat %s" % infopath))
                print("")
            self.get_device_number()
            return True
        return False

    def get_device_number(self):
        self.audio_number = -1
        numid_pattern = re.compile("numid=(?P<id>[0-9]+)")
        pcm_pattern = re.compile("pcm=(?P<id>[0-9]+)")
        pipe = os.popen("amixer -c %s controls" % self.card_number)
        for line in pipe.readlines():
            if "Capture" in line:
                self.capture_support = True
            if 'HDMI/DP,pcm=' in line and "Internal" not in self.audio["_DEVICE_NAME"]:
                self.hdmi = True
                match = numid_pattern.search(line)
                if match:
                    id = match.group("id")
                    match = pcm_pattern.search(line)
                    if match:
                        pcm = match.group("id")
                        check_status_command = subprocess.getoutput("amixer -c %s cget numid=%s" % (self.card_number, id))
                        try:
                            if "values=on" in check_status_command:
                                print("device numid = %s" % id)
                                print("device pcm = %s" % pcm)
                                self.audio_number = int(pcm)
                                print(self.audio_number)
                                break
                        except Exception as e:
                            print("Exception searching for device id:")
                            print(str(e))

    def run_audio(self):
        #set hdmi to false here because the class is re-used for every audio test
        self.hdmi = False
        if not self.log_sound_card_info():
            print("Error: could not log sound card information")
            return False

        if self.audio_number < 0 and self.hdmi:
            print("Error: No active HDMI/DP audio devices found")
            print("       Please make sure the cable is connected and device turned on")
            return False

        # otherwise
        message = "This test plays a sound sample and records it to another file. \nPlease use the Volume Control application and insure that the capture settings will record the sound.\n"
        if not prompt_confirm(message + "Continue?"):
            self.result = "FAIL"
            return False

        if self.capture_support:
            wave_file_duration = 8  # sec. total
            subprocess.getoutput('rm -rf ./test.wav')
            recorded_wave_file = "./test.wav"
            print("starting recording while playing demo sound")
            is_recorded = os.system("arecord -r 44100 -d %s -D plughw:%s %s &" % (wave_file_duration, self.card_number, recorded_wave_file))

            if is_recorded != 0:
                print("Error: arecord command failed")
                self.result = "FAIL"
                return False
        else:
            print("Note: No Capture Support")

        for wave_file in ["/usr/share/sounds/alsa/Front_Right.wav", "/usr/share/sounds/alsa/Front_Left.wav"]:
            if os.path.exists(wave_file):
                play_command = "aplay %s -D plughw:%s" % (wave_file, self.card_number)
                if self.audio_number >= 0:
                    play_command = "aplay %s -D plughw:%s,%s" % (wave_file, self.card_number, self.audio_number)
                print(play_command)
                if os.system(play_command) != 0:
                    print("Error: aplay command failed")
                    self.result = "FAIL"
                    return False
                time.sleep(1)
        sys.stdout.flush()
        if not prompt_confirm("Did you hear the played sound?"):
            self.result = "FAIL"
            return False
        if self.capture_support:
            print("playing recorded sound")
            play_command = "aplay %s -D plughw:%s" % (recorded_wave_file, self.card_number)
            if self.audio_number >= 0:
                play_command = "aplay %s -D plug:hdmi:%s,%s" % (recorded_wave_file, self.card_number, self.audio_number)
            print(play_command)
            if os.system(play_command) != 0:
                print("Error: aplay command failed")
                self.result = "FAIL"
                return False
            if not prompt_confirm("Did you hear the recorded sound?"):
                self.result = "FAIL"
                return False
        subprocess.getoutput("rm -rf ./test.wav")
        self.result = "PASS"
        return True

    def run(self):
        if not self.run_sub_test(self.run_audio, "Audio card", "testing audio card (play + record)"):
            print("Audio test FAILED")
            return False
        print("Audio test PASSED")
        return True


if __name__ == "__main__":
    test = AudioTest()
    rpms = test.get_required_rpms()
    test.install_rpms(rpms)
    tests = test.plan()
    for test in tests:
        value = test.run()
    sys.exit(0)
