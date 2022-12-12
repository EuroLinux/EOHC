# EuroLinux Open Hardware Certification

## Run hardware certification process
To run only selected EOHC tests with GUI, type:
> sudo python3 start_gui.py

## Documentation
Check [EOHC documentation](EOHC_docs.md) to learn more about EuroLinux Open Hardware Certification.

## Already done scripts from [categories](CATEGORIES_PL.md):
* CPU (core)
* fingerprintreader
* battery
* suspend
* reboot
* lid (+ backlight)
* sosreport
* storage
* memory
* usb
* audio
* video
* wlan

## Rules to add new tests
1. Every new test is a python script
2. Every new test have to be a subclass of `Test`
3. Test class naming rule is following: `YournewclassTest` - where *Yournewclass* is anything You like (but with capitalize)
4. For test class name `YournewclassTest` python file should be saved with name **yournewclass.py**
5. Folder with python script and additional files should be named just like python script (without .py) and placed in **tests** folder
