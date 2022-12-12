# Documentation of EuroLinux Open Hardware Certifications

## GOAL: The main goal of the EOHC is to ensure full hardware compatibility before the migration process begins.

## 1. About EOHC
The EuroLinux Open Hardware Certification tests ensures compatibility of EuroLinux partner's hardware and software products with EuroLinux operating system. Tests are prepared to be fully compatible with EuroLinux 8. EOHC is a open product, based on Red Hat Certification Program, but simpler to understand, modify and add new content. Feel free to modify tests for your personal preferences.

## 2. How to test using EOHC
The EuroLinux Open Hardware Certification tool have a dedicated Python3 script named `start_gui.py` that opens graphical user interface inside terminal. Before the interface starts, the script downloads necessary packages - pip (standard python download and instalation manager) & inquirer (python simple GUI package). To start hardware certification process, simply execute following command: 
> python3 start_gui.py

After the interface appears use SPACE to select [X] or deselect [ ] EOHC tests to run. Pressing ENTER starts selected tests in following order: Interactive tests with the highest priority first. Before the tests begins use command `make` to execute all Makefiles included in tests (script installs gcc if necessary).

## 3. Where are the results?
Results of the tests will be in `output.html` file. The `start_gui.py` script also creates an `eohc.log` file that contains all of the informations printed out to standard output during tests.

## 4. Advanced informations

This informatios are for developers

### 4.1. Understanding the core components

Core components of the EOHC tests are inside the `core` folder. 

#### 4.1.1. `controller.py`
This script contains the superclass `Controller` having the following uses:

* manages system directories
* manages logs
* returns current time

#### 4.1.2. `release.py`
This script contains the superclass `Release` and subclass `EuroLinuxRelease` having the following uses:

* keeps and shows informations about system release
* keeps and shows informations kernel

#### 4.1.3. `report.py`
This script contains the superclass `GenerateSystemReport` having the following uses:

* gather information and creates system report (sosreport)

#### 4.1.4. `test.py`
This script contains the superclasses `Test` and `TestResult` having the following uses:

* defines default and stores values of each test
* creates simple methods that each test can extend according to its needs, including:
    * preparations to run test
    * creating copy of self
    * accessing variables
    * creating output file 
    * and other utility methods used by more than one test
* returns human-readable result string from non-standardized input like string, int or bool

### 4.2. Dive into library

Library is a part of `core` components of the EOHC tests and have its place in the following directory: `core/lib`. Inside the library folder are several python scripts, with names corresponding to their roles.

#### 4.2.1. `command_line.py`
This script enables users to interact during execution of the scripts. It has following prompts: confirm, select, integer.

#### 4.2.2. `compatability.py`
This script provides compatibility with python 2.7 and adds some additional rhcert functions

#### 4.2.3. `continuation.py`
This script contains the subclass `Continuation(Controller)`, having the following uses:

* keeps and shows informations about reboot plans
* configures system init
* validates reboot process

#### 4.2.4. `devices.py`
This script returns devices available on current machine. It can also get devices from file or return an attributes.

#### 4.2.5. `network.py`
This script contains the superclass `Wireless` and subclass `NetworkTest(Test)`, having the following uses:

* checks network configuration, speed and measures all this data
* manage network connection and interfaces
* prepare network to test
* some sort of testing methods like ping

### 4.3. Check out the static folder

Static is a part of `core` components of the EOHC tests and have its place in the following directory: `core/static`. Static folder contains only one file - `base.html`. This html file is an template file for `output.html`, which means You can change css in this file to alter the `output.html` layout.

### 4.4 Adding new tests to `start_gui.py` script

Creating new tests is quite eazy, same as adding it to `start_gui.py` script. Just follow the following rules and Your tests will be automaticlly imported:

* Every new test is a python script
* Every new test have to be a subclass of `Test`
* Test class naming rule is following: `YournewclassTest` - where *Yournewclass* is anything You like (but capitalize)
* For test class name `YournewclassTest` python file should be saved with name **yournewclass.py**
* Folder with python script and additional files should be named just like python script (without .py) and placed in tests folder