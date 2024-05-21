import pylink
import struct
import numpy as np
from pwn import ELF
from  matplotlib import pyplot as plt
import time

class QorvoDWM3000EVB():
    def __init__(
        self,
        usb_id = "682111612",
        ykush_serial="YK23299",
        binary_file = '/home/dan/ETH/THESIS/EMV/code_repos/Qorvo_Nearby_Interaction_3_1_0/Software/Accessory/Sources/QANI-All-FreeRTOS_QNI_3_0_0/Projects/Projects/QANI/FreeRTOS/nRF52832DK/ses/Output/Common/Exe/nRF52832DK-QANI-FreeRTOS.hex',
        elf_file = '/home/dan/ETH/THESIS/EMV/code_repos/Qorvo_Nearby_Interaction_3_1_0/Software/Accessory/Sources/QANI-All-FreeRTOS_QNI_3_0_0/Projects/Projects/QANI/FreeRTOS/nRF52832DK/ses/Output/Common/Exe/nRF52832DK-QANI-FreeRTOS.elf'
    ):
        self.usb_id = usb_id
        self.ykush_serial = ykush_serial
        self.binary_file = binary_file
        self.elf_file = elf_file

        self.elf = ELF(self.elf_file)
        if "save_cir" in self.elf.symbols.keys():
            self.save_cir = self.elf.symbols['save_cir']
            print(f"Save_cir ptr = {self.save_cir}")
        else:
            print("Symbol not found: save_cir")
            exit(-1)
        if "cir_I_ptr" in self.elf.symbols.keys():
            self.cir_I_ptr = self.elf.symbols['cir_I_ptr']
        else:
            print("Symbol not found: cir_ptr")
            exit(-1)
        if "cir_Q_ptr" in self.elf.symbols.keys():
            self.cir_Q_ptr = self.elf.symbols['cir_Q_ptr']
        else:
            print("Symbol not found: cir_ptr")
            exit(-1)
            
        # if "flag" in self.elf.symbols.keys():
        #     self.flag = self.elf.symbols['flag']
        #     print(f"Flag address = {self.flag}")
        # else:
        #     print("Symbol not found: flag")
        #     exit(-1)
        self.jlink = pylink.JLink()
        self.jlink.open(self.usb_id)
        self.jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
        self.jlink.connect('nrf52', speed = 1000, verbose=True)
        if not self.jlink.target_connected():
            raise Exception("Failed to connect to targer")
        print(f"I_ptr: {hex(self.cir_I_ptr)}\t Q_ptr: {hex(self.cir_Q_ptr)}")

        # self.cir_I_ptr = None
        # self.cir_Q_ptr = None
    
    def read_flag(self):
        return self.jlink.memory_read32(self.flag, 1)[0]
        
    def read_save_cir(self):
        return self.jlink.memory_read32(self.save_cir, 1)[0]
    
    def read_cir_I_ptr(self):
        return self.jlink.memory_read32(self.cir_I_ptr, 1)[0]
    
    def read_cir_Q_ptr(self):
        return self.jlink.memory_read32(self.cir_Q_ptr, 1)[0]
           
    def set_save_cir(self, value):
        self.jlink.memory_write32(self.save_cir, [value])

    def read_cir(self):
        # self.set_save_cir(0) # stop the dut from writing in the buffer
        dut.set_save_cir(1)
        while dut.read_save_cir() != 0:
            time.sleep(1/1000)  
        print(f"I_ptr: {hex(self.cir_I_ptr)}\t Q_ptr: {hex(self.cir_Q_ptr)}")
        cir_I_raw = self.jlink.memory_read32(self.cir_I_ptr, 512)
        cir_Q_raw = self.jlink.memory_read32(self.cir_Q_ptr, 512)

        # self.set_save_cir(1) # reenable writing in the buffer
        # cir_I_iter = struct.iter_unpack('i', cir_I_raw)
        # cir_Q_iter = struct.iter_unpack('i', cir_Q_raw)
        cir = np.array([np.complex64(i + 1j*q) for i,q in zip(cir_I_raw, cir_Q_raw)])
        
        return cir
    
    





if __name__ == "__main__":
    dut = QorvoDWM3000EVB()
    for i in range(10):
        cir = dut.read_cir()
        plt.plot(range(len(cir)), np.abs(cir))
        plt.show()