#!/usr/bin/python3
# Author: Radoslaw Kolba
#
import sys
import subprocess
import os
subprocess.call("clear")
if subprocess.getstatusoutput("pip --version")[0] != 0:
    print("There is no pip. Installing . . .")
    (status, info) = subprocess.getstatusoutput("sudo yum install -y python-pip")
    if status != 0:
        print(info)
        exit()
if subprocess.getstatusoutput("sudo pip show inquirer")[0] != 0:
    print("There is no module 'inquirer'. Installing . . .")
    (status, info) = subprocess.getstatusoutput("sudo pip install inquirer")
    print(info)
    os.execv(sys.argv[0], sys.argv)
        
import inquirer
import inquirer.themes
import glob

# Class to redirect stdout into given file
class Tee(object):
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            if not f.closed:
                f.flush()

# Handle help argument
helps = ['help', '--help', '-h', 'h']
help = False
if len(sys.argv) > 1:
    for arg in sys.argv:
        if arg.lower() in helps:
            help = True
            break
if help:
    print("EuroLinux Open Hardware Certification\n")
    print("usage: ./start_gui.py [-h help]")
    print("-h\t: print this help message and exit (also --help)\n")
    print("Results will appear in file\t: output.html")
    print("Logs will appear in file\t: eohc.log")
    exit()

print("GUI: EuroLinux Open Hardware Certification /EOHC/")
print()

# Define paths
main_path = os.path.dirname(os.path.realpath(__file__))
subprocess.getoutput('export PYTHONPATH=' + main_path)

# 0. Reset all output
subprocess.getoutput("cp -f " + main_path + "/core/static/base.html output.html")

# 1. Find all python scripts in 'tests' folder
files = glob.glob(main_path + '/tests/*/*.py', recursive=True)
# 2. From files list create paths for import
import_paths = sorted([f.replace('/', '.').replace('.py', '')[len(main_path) + 1:] for f in files])
tests_dict = {f.split('.')[-1]: f for f in import_paths}

# 3. Create question and await answer
theme = {"Checkbox": {"selection_color": "bold_red", "selected_icon": "[X]", "unselected_icon": "[ ]"}}
all_choices = list(tests_dict.keys())
default_values = list(tests_dict.keys())
default_values.remove('reboot')
try:
    questions = [inquirer.Checkbox(
        'ELHC',
        message="Press SPACE to select [X] or deselect [ ] EOHC tests to run. Results of the tests will be in output.html file. Press ENTER to start testing",
        default=default_values,
        choices=all_choices,
    )]
    answers = inquirer.prompt(questions, theme = inquirer.themes.load_theme_from_dict(theme))['ELHC']
    selected_paths = [tests_dict[test] for test in answers]
except:
    exit()

output = open('output.html', 'a')
output.write("<info>Selected EOHC tests:</info>")
output.write("<tests>")
for test in tests_dict.keys():
    selected = ""
    if test in answers:
        selected = " class=\"selected\""
    output.write("<test%s>%s</test>" % (selected, test))
output.write("</tests>")
output.write("<info>Results:</info>")
output.close()
# 4. Find all Makefile's and make it! - Make sure that gcc is installed.
makefiles = glob.glob(main_path + '/tests/*/Makefile', recursive=True)
for makefile in makefiles:
    if subprocess.getstatusoutput("gcc --version")[0] != 0:
        print("There is no gcc. Installing . . .")
        (status, info) = subprocess.getstatusoutput("sudo yum install -y gcc")
        if status != 0:
            print(info)
            exit()
    os.system("make -C " + makefile[:-8] + ' &> /dev/null')

# 5. Redirect stdout into log file
log_file = open('eohc.log', 'w')
sys.stdout = Tee(sys.stdout, log_file)

# 6. Start the import
tests = {}
for path in selected_paths:
    try:
        # 7. Generate class name from path (For example: CpuTest, FingerprintreaderTest)
        #    This must be correct from side of each test!
        test_class = path.split('.')[-1].capitalize() + "Test"
        # 8. From path import test_class (almost):
        _temp = __import__(path, globals(), locals(), [test_class], 0)
        # 9. Add instance of test_class to dictionary 'tests' 
        tests[test_class] = getattr(_temp, test_class)()
        print("Successfully imported ", path)
    except ImportError:
        print("Error importing ", path)

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ END IMPORT ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


# 10. Sort test classes - interactive first!
priority_sorted = dict(sorted(tests.items(), key = lambda kv: kv[1].priority))
interactive_sorted = dict(sorted(priority_sorted.items(), key = lambda kv: kv[1].interactive, reverse = True))

# 11. Run tests
for test_class in interactive_sorted.values():
    rpms = test_class.get_required_rpms()
    if rpms != []:
        test_class.install_rpms(rpms)
    inside_tests = test_class.plan()
    for inside_test in inside_tests:
        inside_test.run()

# 12. Close log file
log_file.close()

# 13. Open output html
subprocess.call(('firefox', 'output.html'))
