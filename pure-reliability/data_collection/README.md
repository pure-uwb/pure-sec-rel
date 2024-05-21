## PURE: Payments with UWB RElay-protection

## Data collection

The distane measurements are performed between a Qorvo DW3000 board and an Iphone running a modified version of the [Qorvo Nearby Interaction](https://apps.apple.com/ml/app/qorvo-nearby-interaction) app. Original sources for both the iOS application and the firmware can be downloaded [here](https://www.qorvo.com/products/p/DWM3001CDK#evaluation-tools).
In order to make the payment scenario more realistic we used a flat UWB antenna to equip real receivers with UWB capabilities. The ranging however was still performed with the Qorvo board.


### Hardware
The necessary hardware consists of:
* 1 x [Qorvo DWM3000EVB](https://www.qorvo.com/products/p/DWM3000EVB)
* 1 x [Nordic Semiconductor nRF52 DK (pca10040)](https://www.nordicsemi.com/Products/Development-hardware/nrf52-dk)
* 1 x Iphone
Additionally, we used to webcams to capture the position of the hand and phone when performing the measurement. Please adjust the script `gdb_script.py` depenging if you want to collect images of your measurement or not. 

### Measurement description
Each measurement consists of the following events
* The Iphone and Qorvo board execute UWB ranging,
* The flag `diagnostics_ready` in `./UWB/dw3000_statistics.c` is set
* The execution is halted and the debugger reads the collected CIR and triggers the picture with webcam
* When the ranging is finished the phone registers its 3D position (roll, pitch and yaw) and reports it to a server (`server.py`) which collects the values from the phone.
All informations are saved into an hdf5 file which can be analysed later with the script `reliability_analysis.py`.

### Files description

Important files in the `board` folder for testing:
- ./gdb_script.py: set watchpoint, extracts value from memory, saves them in hdf5.
- ./initial_cmd.gdb: connects to target and sources gdb_script
- ./merge_files.py: at the end of the tests, used to merge the hdf5 files
- ./start_test_full.sh: starts gdb server, and gdb. Press CTRL-C to stop, merge_files.py will save the output in output.hdf5

The QANI-ios contains the modified QANI ios application.

### Quickstart

#### Board
Install [Segger Embedded Studio](https://www.segger.com/products/development-tools/embedded-studio/) (SES) and [SEGGER JLink](https://www.segger.com/downloads/jlink/JLink_Linux_V786e_x86_64.deb).
Install the required dependencies executing 
```
sudo apt-get install gdb-multiarch hdf5-tools 
```
And finnaly install the required python packages
```
pip install -r requirement.txt
```

With SES build and flash the NIQ application or use J-Link to flash the elf at `Projects/QANI/FreeRTOS/nRF52832DK/ses/Output/Common/Exe/nRF52832DK-QANI-FreeRTOS.elf`.

NOTE: if you are using a python virtual environment make sure gdb uses it (See [gdb-python-interpreter](https://gist.github.com/tyhoff/060e480b6cf9ad35dfd2ba9d01cad4b6)) 

#### Iphone
Install the modified Qorvo app present in the QANI-iOS folder. You will need an IoS machine with [XCode](https://developer.apple.com/xcode/) installed. 

IMPORTANT: Make sure that the Iphone and your host machine can communicate, as the iphone reports its measurements to a server running on port 9000. On the iphone app, click on the dots on the top right and set the IP of the host machine.

#### Start the CIR collection
Execute `./start_test_full.sh` to
1. Start gdb server
2. Connect gdb to the remote target
3. A watchpoint for the variable diagnostics_ready is set
4. Every time the watchpoint is hit, extract memory, save to hdf5, and reset the target.

Pressing CTRL-C interrupts the measurements and triggers the executing of `merge_files.py` that is responsible to merge the produced hdf5 files into a single one. 

All the collected information are saved in ./full_test_output/$(date +"%Y-%m-%d-%T")

NOTE: due the application being realtime after halting the CPU the application on the board crashes.We perform two ranging: one where the measurement of distance is saved and the second where the CIR is collected causing the application to crash. On every measurement the board is automatically restarted.

#### How to modify
If you want to extract more values from the UWB chip, modify the caclucateStatsSave function to save the values you are interested in a static variable. Then recompile and flash.
In gdb_script.py add the value to rx_dict.

