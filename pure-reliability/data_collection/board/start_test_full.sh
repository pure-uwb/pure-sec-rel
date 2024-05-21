#!/bin/bash
function terminate() {
	echo "Received CTRL-C..."
	#sleep 5
	
	server_pid=$(ps -aux | grep "python3 server.py" | head -n 1|  tr -s " "| cut -d " " -f 2) 	
	echo "Kill server with PID: " $server_pid
	kill -s SIGINT $server_pid
	
	echo "Kill gdb-server"
	pkill --signal SIGINT gdb-multiarch
	pkill gdb-multiarch
	pkill JLinkGDBServerCLExe
	python3 merge_files.py
	
	#Move all output files to output folder
	mv output.hdf5 $output_folder
	mv ./imgs $output_folder/
	exit
}
trap terminate INT
# Create folder for outputs
output_folder=./full_test_output/$(date +"%Y-%m-%d-%T")
mkdir -p $output_folder
mkdir -p ./imgs

# Flash board
#./install_hex.sh ./Projects/QANI/FreeRTOS/nRF52832DK/ses/Output/Common/Exe/nRF52832DK-QANI-FreeRTOS.elf


gdb_command="initial_cmd.gdb"
elf="./Projects/QANI/FreeRTOS/nRF52832DK/ses/Output/Common/Exe/nRF52832DK-QANI-FreeRTOS.elf"

rm output.hdf5
JLinkGDBServerCLExe -if SWD -device nrf52 -speed 4000 -autoconnect 1 -port 1234 > /tmp/gdbSererOutput.log &

gdb-multiarch $elf  --command $gdb_command &
python3 server.py --log  &

sleep infinity
