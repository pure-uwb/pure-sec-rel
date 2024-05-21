#!/usr/bin/python3
import sys
import os
import gdb
from itertools import chain
import struct
import numpy as np
import os
import cv2
import time
import signal 
from matplotlib import pyplot as plt
sys.path.append(f'{os.getcwd()}/monitor/dwm3000')
from HDF5Storage import HDF5Storage

sound = True
point_number = 512
intermeasure_time = 1
cameras = [0, 2]

def parse_cir(str_out):
    lines = str_out.split("\n")
    lines2 = list(chain.from_iterable([x.split(":")[1:] for x in lines]))
    lines3 = list(chain.from_iterable([x.split("\t") for x in lines2]))
    lines4 = list(filter( lambda x : len(x) > 0, lines3))
    lines5 = [bytes.fromhex(x[2:]) for x in lines4]
    return struct.iter_unpack(">i", b"".join(lines5))

def array2int(a):
    return a[0]+(a[1]<<8)+(a[2]<<16)+(a[3]<<24)+(a[4]<<32)
    
    
def parse_rx_diag(rx_diag):
    """Converts gdb value into dictionary.

    Args:
        rx_diag (gdb.Value): rx diagnostics
    """
    rx_dict = {}
    rx_dict['ipatovRxTime']  = int(array2int(rx_diag['ipatovRxTime']))
    rx_dict['stsRxTime']     = int(array2int(rx_diag['stsRxTime']))
    rx_dict['sts2RxTime']    = int(array2int(rx_diag['sts2RxTime']))
    rx_dict['tdoa']          = int(array2int(rx_diag['tdoa']))
    rx_dict['ipatovFpIndex'] = float((rx_diag['ipatovFpIndex'] >> 6) + (rx_diag['ipatovFpIndex']&0x3f)/100)
    rx_dict['stsFpIndex'] = float((rx_diag['stsFpIndex'] >> 6) + (rx_diag['stsFpIndex']&0x3f)/100)
    rx_dict['ipatovPeakIndex'] = float((rx_diag['ipatovPeak'] >> (16+5)) + ((rx_diag['ipatovPeak']>>16)&0x1f)/100)
    rx_dict['stsPeakIndex'] = float((rx_diag['stsPeak'] >> (16+5)) + ((rx_diag['stsPeak']>>16)&0x1f)/100)
    rx_dict["stsPower"] = int(rx_diag["stsPower"])
    rx_dict["ipatovPower"] = int(rx_diag["ipatovPower"])
    rx_dict["stsAccumCount"] = int(rx_diag["stsAccumCount"])
    return rx_dict
            
def reset():
    gdb.execute("monitor reset")
    gdb.execute("c")

def signal_handler(sig, frame):
    print("Flush buffer before exit.")
    storage.save_buffer_to_file()
    #sys.exit(0)


if __name__ == "__main__":
    storage = HDF5Storage(filename="init.hdf5.tmp")
    buffering = 10
    
    signal.signal(signal.SIGINT, signal_handler)
    vcs = []
    for camera in cameras:
        vc = cv2.VideoCapture(camera)
        vc.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        vcs.append((camera, vc)) # name, vc
    
    def stop_handler(event):
        print(event)
        where = gdb.execute("where", False, True)
        print(where)
        if "report_cb" in where:
            reset()
        elif "rx_get_frame" in where: 
            # For each camera take a picture
            timestamp = int(time.time()) 
            for name, vc in vcs:
                print(f"Camera: {name}")
                img_name = f"{timestamp}_video{name}.png"
                ret,frame = vc.read()
                ret,frame = vc.read()
                cv2.imwrite(f'imgs/{img_name}',frame)
    
            if sound:
                os.system("paplay beep.wav")
            print("Reading rx_diag...")
            rx_dict = parse_rx_diag(gdb.parse_and_eval("rx_diag"))
            print(rx_dict)            
            print("Reading cir_I...")
            cir_I_raw = gdb.execute(f"x/{point_number}xw cir_I_ptr", False, True)
            cir_I = parse_cir(cir_I_raw.encode().decode())
            
            print("Reading cir_Q...")
            cir_Q_raw = gdb.execute(f"x/{point_number}xw cir_Q_ptr", False, True)
            cir_Q = parse_cir(cir_Q_raw.encode().decode())
            rx_dict["cir_sts"] = np.array([np.complex64(i[0] + 1j * q[0]) for i,q in zip(cir_I, cir_Q)])
            #plt.clf() 
            #plt.plot(np.abs(rx_dict["cir_sts"]))
            #plt.scatter(int(rx_dict["stsFpIndex"]), np.abs(rx_dict["cir_sts"])[int(rx_dict["stsFpIndex"])])
            #plt.show()
            rx_dict["imgs_timestamp"] = timestamp
            # print("Reading cir_I_pre...")
            # cir_I_pre_raw = gdb.execute(f"x/{point_number}xw cir_I_preamble_ptr", False, True)
            # cir_I_pre = parse_cir(cir_I_pre_raw.encode().decode())
            # 
            # print("Reading cir_Q_pre...")
            # cir_Q_pre_raw = gdb.execute(f"x/{point_number}xw cir_Q_preamble_ptr", False, True)
            # cir_Q_pre = parse_cir(cir_Q_raw.encode().decode())
            # rx_dict["cir_pre"] = np.array([np.complex64(i[0] + 1j * q[0]) for i,q in zip(cir_I_pre, cir_Q_pre)])
            

            print("Save diagnostics...")
            storage.save_to_buffer(rx_dict)
            print(f"Buffered {len(storage.buffer)}/{buffering}.\t Tot: {storage.total}")
            if len(storage.buffer) >= buffering:
                print("Saving buffer to file")
                storage.save_buffer_to_file()
                print("Saved")
            if sound:
                time.sleep(intermeasure_time)
                os.system("paplay boing2.wav")
            reset()
        else:
            gdb.execute("c")
    
    def exit_handler(event):
        print("Exit handler...")
        storage.save_buffer_to_file()
        
    gdb.execute("watch diagnostics_ready")    
    #gdb.execute("watch successful_range_count")
    gdb.events.stop.connect(stop_handler)
    gdb.events.exited.connect(exit_handler)
    reset()

