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
        self.target.set_watchpoint(self.diagnostics_ready_ptr)