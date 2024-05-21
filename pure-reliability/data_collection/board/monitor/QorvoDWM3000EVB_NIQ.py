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

sys.path.append('/home/dan/ETH/THESIS/EMV/code_repos/Qorvo_Nearby_Interaction_3_1_0/Software/Accessory/Sources/QANI-All-FreeRTOS_QNI_3_0_0/Projects/monitor/dwm3000-monitor')
from HDF5Storage import HDF5Storage

class QorvoDWM3000EVB():
    def __init__(
        self,
        gdb_port=1234,
        usb_id=682111612,
        ykush_port=1,
        ykush_serial="YK23299",
        gdb_exe='gdb-multiarch',
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

        # Resetting ykush
        #os.system(f"ykushcmd -s {self.ykush_serial} -d {self.ykush_port}")
        #os.system(f"ykushcmd -s {self.ykush_serial} -u {self.ykush_port}")
        # subprocess.call(f"ykushcmd -s {self.ykush_serial} -d {self.ykush_port}", shell = True)
        # subprocess.call(f"ykushcmd -s {self.ykush_serial} -u {self.ykush_port}", shell = True)
        # time.sleep(1)
        # while str(self.usb_id) not in subprocess.run("nrfjprog -i", shell = True, capture_output=True).stdout.decode():
        #     time.sleep(1)

        self.elf = ELF(self.elf_file)
        self.diagnostics_ready_ptr = self.elf.symbols['diagnostics_ready']
        # self.rx_diag_ptr = self.elf.symbols['rx_diag']   
        self.cir_I_ptr = self.elf.symbols['cir_I_ptr']          
        self.cir_Q_ptr = self.elf.symbols['cir_Q_ptr'] 

        self.diagnostics_struct_def = '''
        #include <stdint.h>
        typedef struct
        {
            uint8_t       ipatovRxTime[5] ;   // RX timestamp from Ipatov sequence
            uint8_t       ipatovRxStatus ;    // RX status info for Ipatov sequence
            uint16_t      ipatovPOA ;         // POA of Ipatov
        
            uint8_t       stsRxTime[5] ;   // RX timestamp from STS
            uint16_t      stsRxStatus ;    // RX status info for STS
            uint16_t      stsPOA;          // POA of STS block 1
            uint8_t       sts2RxTime[5];   // RX timestamp from STS
            uint16_t      sts2RxStatus;    // RX status info for STS
            uint16_t      sts2POA;         // POA of STS block 2
        
            uint8_t       tdoa[6];            // TDOA from two STS RX timestamps
            int16_t       pdoa;               // PDOA from two STS POAs signed int [1:-11] in radians
        
            int16_t       xtalOffset ;        // estimated xtal offset of remote device
            uint32_t      ciaDiag1 ;          // Diagnostics common to both sequences
        
            uint32_t      ipatovPeak ;        // index and amplitude of peak sample in Ipatov sequence CIR
            uint32_t      ipatovPower ;       // channel area allows estimation of channel power for the Ipatov sequence
            uint32_t      ipatovF1 ;          // F1 for Ipatov sequence
            uint32_t      ipatovF2 ;          // F2 for Ipatov sequence
            uint32_t      ipatovF3 ;          // F3 for Ipatov sequence
            uint16_t      ipatovFpIndex ;     // First path index for Ipatov sequence
            uint16_t      ipatovAccumCount ;  // Number accumulated symbols for Ipatov sequence
        
            uint32_t      stsPeak ;        // index and amplitude of peak sample in STS CIR
            uint16_t      stsPower ;       // channel area allows estimation of channel power for the STS
            uint32_t      stsF1 ;          // F1 for STS
            uint32_t      stsF2 ;          // F2 for STS
            uint32_t      stsF3 ;          // F3 for STS
            uint16_t      stsFpIndex ;     // First path index for STS
            uint16_t      stsAccumCount ;  // Number accumulated symbols for STS
        
            uint32_t      sts2Peak;        // index and amplitude of peak sample in STS CIR
            uint16_t      sts2Power;       // channel area allows estimation of channel power for the STS
            uint32_t      sts2F1;          // F1 for STS
            uint32_t      sts2F2;          // F2 for STS
            uint32_t      sts2F3;          // F3 for STS
            uint16_t      sts2FpIndex;     // First path index for STS
            uint16_t      sts2AccumCount;  // Number accumulated symbols for STS
        
        } dwt_rxdiag_t ;
        '''
        
        self.definitions = pycstruct.parse_str(self.diagnostics_struct_def)

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
        self.target.shutdown
        self.target.init()
        self.target.set_watchpoint(self.diagnostics_ready_ptr)


    def stop(self):
        os.system(f"ykushcmd -s {self.ykush_serial} -d {self.ykush_port}")

    def wait_rx(self):
        self.target.cont()
        print("Continue")
        print("Wait")
        self.target.wait()
        
        

    def array2int(self, a):
        return a[0]+(a[1]<<8)+(a[2]<<16)+(a[3]<<24)+(a[4]<<32)

    def get_diagnostics(self):
        rx_diag = {}
        #print("")
        #print("Diagnostics ready")
        #rx_diag_raw = self.target.read_memory(self.rx_diag_ptr, 1, 116, raw=True)
        #rx_diag = self.definitions['dwt_rxdiag_t'].deserialize(rx_diag_raw)
        #rx_diag['ipatovRxTime'] = self.array2int(rx_diag['ipatovRxTime'])
        #rx_diag['stsRxTime'] = self.array2int(rx_diag['stsRxTime'])
        #rx_diag['sts2RxTime'] = self.array2int(rx_diag['sts2RxTime'])
        #rx_diag['tdoa'] = self.array2int(rx_diag['tdoa'])
        #rx_diag['ipatovFpIndex'] = (rx_diag['ipatovFpIndex'] >> 6) + (rx_diag['ipatovFpIndex']&0x3f)/100
        #rx_diag['stsFpIndex'] = (rx_diag['stsFpIndex'] >> 6) + (rx_diag['stsFpIndex']&0x3f)/100
        #rx_diag['ipatovPeakIndex'] = (rx_diag['ipatovPeak'] >> (16+5)) + ((rx_diag['ipatovPeak']>>16)&0x1f)/100
        #rx_diag['stsPeakIndex'] = (rx_diag['stsPeak'] >> (16+5)) + ((rx_diag['stsPeak']>>16)&0x1f)/100

        # Read status reg
        # status_reg_raw = self.target.read_memory(self.status_reg_ptr, 4, 1, raw=True)
        # status_reg = struct.unpack_from('I', status_reg_raw)[0]
        # rx_diag['status_reg'] = status_reg

        # rx_valid_raw = self.target.read_memory(self.rx_valid_ptr, 1, 1, raw=True)
        # rx_valid = struct.unpack_from('?', rx_valid_raw)[0]
        # rx_diag['rx_valid'] = rx_valid
        
        # rx_timeout_raw = self.target.read_memory(self.rx_timeout_ptr, 1, 1, raw=True)
        # rx_timeout = struct.unpack_from('?', rx_timeout_raw)[0]
        # rx_diag['rx_timeout'] = rx_timeout
        
        # rx_error_raw = self.target.read_memory(self.rx_error_ptr, 1, 1, raw=True)
        # rx_error = struct.unpack_from('?', rx_error_raw)[0]
        # rx_diag['rx_error'] = rx_error

        # # read STS indicators
        # goodSTS_raw = self.target.read_memory(self.goodSTS_ptr, 1, 1, raw=True)
        # goodSTS = struct.unpack_from('?', goodSTS_raw)[0]
        # rx_diag['goodSTS'] = goodSTS
        # #print(f"goodSTS {goodSTS}")
 
        # cpqual_raw = self.target.read_memory(self.cpqual_ptr, 2, 1, raw=True)
        # cpqual = struct.unpack_from('h', cpqual_raw)[0]
        # rx_diag['cpqual'] = cpqual
        # #print(f"cpqual {cpqual}")
 
        # goodCPQ_raw = self.target.read_memory(self.goodCPQ_ptr, 4, 1, raw=True)
        # goodCPQ = struct.unpack_from('i', goodCPQ_raw)[0]
        # rx_diag['goodCPQ'] = goodCPQ
        # #print(f"goodCPQ {goodCPQ}")
        
        # clkOffset_raw = self.target.read_memory(self.clkOffset_ptr, 2, 1, raw=True)
        # clkOffset = struct.unpack_from('h', clkOffset_raw)[0]
        # rx_diag['clkOffset'] = clkOffset
        # #print(f"cpqual {cpqual}")
 
        # cpStatus_raw = self.target.read_memory(self.cpStatus_ptr, 2, 1, raw=True)
        # cpStatus = struct.unpack_from('H', cpStatus_raw)[0]
        # cpStatus_flags = [bool(cpStatus & (1<<n)) for n in range(9)]
        # cpStatus_keys = [
        #     "Warning:_0_Logistic_regression_failed",
        #     "Warning:_1_Non-triangle",
        #     "Warning:_2_High_noise_threshold",
        #     "Warning:_3_Coarse_estiamtion_empty",
        #     "Warning:_4_Late_coarse_estimation",
        #     "Warning:_5_Late_first_path_estimation",
        #     "Warning:_6_SFD_count_warning",
        #     "Warning:_7_ADC_count_warning", 
        #     "Warning:_8_Peak_growth_rate_warning"
        # ]
        # #cpStatus = dict(zip(cpStatus_keys, cpStatus_flags))
        # for key, item in zip(cpStatus_keys, cpStatus_flags):
        #     rx_diag[key] = item
        # #print(f"cpStatus {cpStatus}")

        # rmarkerRxTime_raw = self.target.read_memory(self.rmarkerRxTime_ptr, 1, 5, raw=True)
        # rmarkerRxTime = struct.unpack_from('BBBBB', rmarkerRxTime_raw)
        # rmarkerRxTime = self.array2int(rmarkerRxTime)
        # rx_diag['rmarkerRxTime'] = rmarkerRxTime

        # rmarkerRxTimeUnadj_raw = self.target.read_memory(self.rmarkerRxTimeUnadj_ptr, 1, 5, raw=True)
        # rmarkerRxTimeUnadj = struct.unpack_from('BBBBB', rmarkerRxTimeUnadj_raw)
        # rmarkerRxTimeUnadj = self.array2int(rmarkerRxTimeUnadj)
        # rx_diag['rmarkerRxTimeUnadj'] = rmarkerRxTimeUnadj

        # rmarkerRxTimeSts_raw = self.target.read_memory(self.rmarkerRxTimeSts_ptr, 1, 5, raw=True)
        # rmarkerRxTimeSts = struct.unpack_from('BBBBB', rmarkerRxTimeSts_raw)
        # rmarkerRxTimeSts = self.array2int(rmarkerRxTimeSts)
        # rx_diag['rmarkerRxTimeSts'] = rmarkerRxTimeSts

        # Read CIR
        cir_I_raw = self.target.read_memory(self.cir_I_ptr, 4, 1536, raw=True)
        cir_Q_raw = self.target.read_memory(self.cir_Q_ptr, 4, 1536, raw=True)

        cir_I_iter = struct.iter_unpack('i', cir_I_raw)
        cir_Q_iter = struct.iter_unpack('i', cir_Q_raw)
        cir = np.array([complex(i[0],q[0]) for i,q in zip(cir_I_iter, cir_Q_iter)])
        #rx_diag['cir_ipatov'] = cir[0:1016]
        #rx_diag['cir_undocumented'] = cir[1016:1024]
        rx_diag['cir_sts'] = cir[1024:1536]

        # Read extra diagnosics
        return rx_diag

if __name__ == '__main__':
    from HDF5Storage import HDF5Storage
    storage = HDF5Storage()
    dut = QorvoDWM3000EVB()
    dut.start()
    buffering = 50
    for i in range(100):
        dut.wait_rx()
        print("Post wait")
        diags = dut.get_diagnostics()
        storage.save_to_buffer(diags)
        if len(storage.buffer) >= buffering:
            storage.save_buffer_to_file()
    storage.save_buffer_to_file()
    dut.stop()
