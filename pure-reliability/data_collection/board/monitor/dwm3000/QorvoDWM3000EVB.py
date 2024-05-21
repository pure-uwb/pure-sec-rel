import os
import subprocess
import struct
import pycstruct
import h5py
import os
import time
import numpy as np
from avatar2 import *
from pwn import ELF

class QorvoDWM3000EVB():
    def __init__(
        self,
        gdb_port=1234,
        usb_id=682111612,
        ykush_port=1,
        ykush_serial="YK23299",
        gdb_exe='/usr/bin/gdb-multiarch',
        binary_file = '/home/dan/ETH/THESIS/EMV/code_repos/Qorvo_Nearby_Interaction_3_1_0/Software/Accessory/Sources/QANI-All-FreeRTOS_QNI_3_0_0/Projects/Projects/QANI/FreeRTOS/nRF52832DK/ses/Output/Common/Exe/nRF52832DK-QANI-FreeRTOS.hex',
        elf_file = '/home/dan/ETH/THESIS/EMV/code_repos/Qorvo_Nearby_Interaction_3_1_0/Software/Accessory/Sources/QANI-All-FreeRTOS_QNI_3_0_0/Projects/Projects/QANI/FreeRTOS/nRF52832DK/ses/Output/Common/Exe/nRF52832DK-QANI-FreeRTOS.elf'
    ):
        self.gdb_port = gdb_port
        self.usb_id = usb_id
        self.ykush_port = ykush_port
        self.ykush_serial = ykush_serial
        self.gdb_exe = gdb_exe
        self.binary_file = binary_file
        self.elf_file = elf_file

        self.elf = ELF(self.elf_file)
        if "save_cir" in self.elf.symbols.keys():
            self.save_cir = self.elf.symbols['save_cir']
            print(f"Save_cir address = {self.save_cir}")
        else:
            print("Symbol not found: save_cir")
            exit(-1)
        # if "cir_address" in self.elf.symbols.keys():
        #     self.cir_address = self.elf.symbols['cir_address']
        # else:
        #     print("Symbol not found: cir_address")
        #     exit(-1)
        if "flag" in self.elf.symbols.keys():
            self.flag = self.elf.symbols['flag']
            print(f"Flag address = {self.flag}")
        else:
            print("Symbol not found: flag")
            exit(-1)
        
             
    def start(self):
        # Create the avatar instance and specify the architecture for this analysis
        self.avatar = Avatar(arch=ARM_CORTEX_M3, output_directory='/tmp/avatar')
        self.avatar.log.setLevel('ERROR')
        
        # Create memory region see ld script
        self.ram  = self.avatar.add_memory_range(0x20000000, 0x10000) # see .ld script
        # Create the endpoint: a gdbserver connected to our tiny ELF file
        self.gdbserver = subprocess.Popen(
                'JLinkGDBServerCLExe \
                -if SWD \
                -device nrf52 \
                -speed 4000 \
                -autoconnect 1 \
                -select USB=%d \
                -port %d \
                -singlerun' % (self.usb_id, self.gdb_port),
                shell=True
                )
        time.sleep(1) 
        # Create the corresponding target, using the GDBTarget backend
        self.target = self.avatar.add_target(GDBTarget,
                gdb_executable=self.gdb_exe, gdb_port=self.gdb_port)

        # Initialize the target. 
        # This usually connects the target to the endpoint
        self.target.init()
        self.target.set_watchpoint(self.save_cir)

    
    def wait_rx(self):
        self.target.cont()
        self.target.wait()

    def cont(self):
        self.target.cont()
    
    def read_flag(self):
        flag = self.target.read_memory(self.flag, 4, 1, raw=True)
        flag = struct.unpack_from('BBBB', flag)[0]
        return flag
    
    def read_save_cir(self):
        save_cir = self.target.read_memory(self.save_cir, 1, 1, raw=True)
        save_cir = struct.unpack_from('B', save_cir)[0]
        return save_cir

    def set_save_cir(self, value):
        self.target.write_memory(self.save_cir, 1, bytes(value), 1, raw=True)

    def stop(self):
        self.avatar.shutdown()
        
if __name__ == '__main__':
    from HDF5Storage import HDF5Storage
    storage = HDF5Storage()
    dut = QorvoDWM3000EVB()
    dut.start()
    buffering = 50
    # for i in range(100):
    i = 0;
    dut.cont();
    while(1):
        # dut.wait_rx()
        
        sleep(1);
        flag = dut.read_flag()
        print(f"FLAG: {flag}, save_cir: {dut.read_save_cir()}")
        if i == 10:
            dut.set_save_cir(1)
        i+=1 
