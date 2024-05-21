import matplotlib.pyplot as plt
import numpy as np
import h5py
import seaborn as sns
from scipy import signal
import sys 
import os
from PIL import Image
import matplotlib.gridspec as gridspec
import pandas as pd
import argparse
from mycolorpy import colorlist as mcp
from matplotlib.ticker import MultipleLocator, FixedLocator
import matplotlib as mpl

mpl.rcParams["pdf.fonttype"] = 42
mpl.rcParams["ps.fonttype"] = 42
# mpl.rcParams['text.usetex'] = True

ABS_TH = 702
PLOT_FOLDER = "/tmp/"

class CIR_Analyzer():
    def get_noise_estimates(cirs):
        offset = 10
        window  = 128
        main_peaks = np.argmax(cirs, axis=1)
        noise_estimate_std = [np.std(cir[idx-window-offset: idx-offset]) for cir, idx in zip(cirs, main_peaks)]
        noise_estimate_rms = [np.sqrt(np.mean(cir[idx-window-offset: idx-offset]**2)) for cir, idx in zip(cirs, main_peaks)]
        return noise_estimate_rms, noise_estimate_std
    
    def get_first_peak_abs(cirs, ABS_TH):
        def intercept(x1, y1, x2, y2, y3): 
            a = (y2 - y1) / (x2 - x1)
            return (y3 - y1) / a + x1

        def get_toa(cir, th):
            idx = 0 
            # Find bottom of the peak
            while idx < 510:
                if (cir[idx] > th):
                    # Found first peak above the threshold
                    return intercept(idx-1, cir[idx-1], idx, cir[idx], th)
                idx += 1
            return idx
        toa = [get_toa(cir, ABS_TH) for cir in cirs]
        return toa
    
    def get_first_peak_abs_opt(cirs, stsFpIndex, ABS_TH):   
        toaAbs = CIR_Analyzer.get_first_peak_abs(cirs, ABS_TH)         
        toaOpt = [max(absIdx, stsIdx) for absIdx, stsIdx in zip(toaAbs, stsFpIndex)]
        toaHeight = [ABS_TH if absIdx == toaOptIdx else int(cir[int(toaOptIdx)]) for absIdx, toaOptIdx, cir in zip(toaAbs, toaOpt, cirs)]
        return toaOpt, toaHeight      
    
    def true_peak_index(cir, fpIndex):
        peaks = signal.find_peaks(cir)[0]
        for i in range(len(peaks)-1, -1, -1):
            if peaks[i] < fpIndex:
                try:
                    return peaks[i+1]
                except:
                    print("Failed to find peaks")
                    return peaks[-1]
        return peaks[0]
    
    def get_percentiles_handles(data):
        percentiles = [1, 2, 10]
        handle = []
        values = np.percentile(data["trueFpHeight"], percentiles)
        for v in values:
            diff = np.abs(data["trueFpHeight"]- v)
            closest = data[diff == np.min(diff)].index[0]
            handle.append(closest)
        return handle
    
    def get_worst(data, n):
        data["err"] = data["stsFpIndex"]- data["pureFpIndex"]
        data.sort_values(by = "err")
        return data.iloc[:n]
        
def hd2pandas(f):
    data = {}
    min_len = -1
    for k in f.keys():
        if k == "cir_sts" or len(np.array(f[k]).squeeze().shape)>1:
            continue
        data[k] = np.array(f[k]).squeeze()
        if min_len == -1:
            min_len = len(data[k])
        if len(data[k]) < min_len:
            min_len = len(data[k])
    data_out = {}
    for k in data.keys():
        data_out[k] = data[k][:min_len]
    return pd.DataFrame(data_out)

def read_multiple(paths):
    measure_types = [os.path.basename(x) for x in paths]
    datas = []
    cirs = {}
    print("Loading data from:")
    for measure_type, path in zip(measure_types, paths):
        print(f"\t{path}")
        f =  h5py.File(os.path.join(path, "output.hdf5"), 'r')
        data = hd2pandas(f)
        data["measure_type"] = measure_type
        datas.append(data)
        cirs[measure_type] = np.abs(f["cir_sts"][:len(data), :])
    df = pd.concat(datas)
    print("\n\n")
    df.reset_index(inplace=True)
    return df, cirs

def data_load(paths, ABS_TH):
    data, cirs = read_multiple(paths)
    cirs = np.vstack(list(cirs.values()))
    data["rms"], data["std"]= CIR_Analyzer.get_noise_estimates(cirs)
    data["cir"] = [cir for cir in cirs]    
    data["stsFpHeight"] = [cir[int(data["stsFpIndex"][i])] for i, cir in enumerate(cirs)]
    data["pureFpIndex"], data["pureFpHeight"] = CIR_Analyzer.get_first_peak_abs_opt(data["cir"],data["stsFpIndex"], ABS_TH)
    data["toaDiff"] =  data["pureFpIndex"] - data["stsFpIndex"]
   
    # Used in the compare visualization to avoid over complicated plots with dots not on the top of the peak.
    data["trueFpIndex"] = [CIR_Analyzer.true_peak_index(cir,data["stsFpIndex"][i]) for i, cir in enumerate(cirs)]
    data["trueFpHeight"] = [cir[data["trueFpIndex"][i]] for i, cir in enumerate(cirs)]

    return data
            
def plot_cir(data,  ax = None, show = True, show_th = False, db = True):
    TP_COLOR = "#648FFF"
    PURE_COLOR = "#FFB000"
    if ax is None:
        ax = plt.subplot(111)
    if isinstance(data, pd.Series):
        ax.plot(data["cir"], color = f"C{2}")
    else:
        for i, cir in enumerate(data["cir"]):
            ax.plot(cir, zorder = -1, color = f"C{i}")
    ax.scatter(data["stsFpIndex"], data["stsFpHeight"], marker = "s", color = TP_COLOR, label="Early Peak")
    ax.scatter(data["pureFpIndex"], data["pureFpHeight"], marker = "s", color = PURE_COLOR, label="PURE Early Peak")
    if show_th == True:
        ax.hlines(ABS_TH, 0, 512, color = "C0", label="Absolute Threshold $T$")
    if show:
        plt.show()

def plot_cir_setting(data, basedir, n = 20, savefig = True):
    data = data.loc[CIR_Analyzer.get_percentiles_handles(data)]
    data = CIR_Analyzer.get_worst(data, n)
    data = data.reset_index()
    for idx in range(n):
        gs = gridspec.GridSpec(2, 2, hspace=0.30)
        ax1 = plt.subplot(gs[0, 0])
        ax2 = plt.subplot(gs[0, 1])
        ax3 = plt.subplot(gs[1, :])
        yaw = data["yaw"].iloc[idx]
        roll = data["roll"].iloc[idx]
        pitch = data["pitch"].iloc[idx]
        timestamp = data["imgs_timestamp"].iloc[idx]
        img_dir = os.path.join(basedir, data["measure_type"].iloc[idx], "imgs")
        try:
            ax1.imshow(np.asarray(Image.open(os.path.join(img_dir, f"{timestamp}_video0.png" ))), aspect = "auto")
        except:
            ax1.imshow(np.asarray(Image.open(os.path.join(img_dir, f"{timestamp}_video2.png" ))), aspect = "auto")
            
        ax2.imshow( np.asarray(Image.open(os.path.join(img_dir, f"{timestamp}_video4.png" ))))
        ax1.set_title("View A")
        ax2.set_title("View B")
        plot_cir(data.iloc[idx], ax = ax3, show = False, show_th=True)
        ax3.set_title(f"yaw = {yaw}\npitch = {pitch}\nroll = {roll}")
        ax3.set_ylabel("|CIR[i]|")
        ax3.set_xlabel("i")
        plt.grid(visible=True)
        plt.legend()

        if savefig:
            plt.savefig(PLOT_FOLDER+f"/worst_pics_{idx}.png", dpi=300)
        plt.show()

def distance_errors(data):
    """
    In this plot for a given FRR   (= 1 - percentile), we show the distance that has to be accepted varying the absolute threshold that yields the specific FRR.
    In other words, the FRR is affected by the absolute threshold on the peak and by the accepted distance. The curves plotted show for a given FRR the tradeoff between distance error and absolute th. 
    """
    
    distance_errors = {}
    for abs_th in [702, 708, 720, 750, 800]:
        toa, _ =   CIR_Analyzer.get_first_peak_abs_opt(data["cir"],
                                                       data["stsFpIndex"], 
                                                       abs_th)
        distance_errors[abs_th] = (toa - data["stsFpIndex"]) * 30 # Every index is 30 cm
    distance_errors_df = pd.DataFrame(distance_errors)
    quantiles_list = [1, 0.995, 0.99, 0.985, 0.98, 0.90]
    quantiles = distance_errors_df.quantile(quantiles_list)
    print(f"FRR with d_max = 46 cm: {1 - np.sum(distance_errors_df[ABS_TH]<21)/len(distance_errors_df)}")
    print(f"FRR d_max = 85 cm: {1 - np.sum(distance_errors_df[ABS_TH]<55)/len(distance_errors_df)}")
    print(f"FRR with d_max = 95 cm: {1 - np.sum(distance_errors_df[ABS_TH]<70)/len(distance_errors_df)}")
    for i, q in enumerate(quantiles_list):
        plt.plot(np.array(quantiles.columns), np.array(quantiles.iloc[i]), label = f"quantile {q}")
    plt.xlabel("ABS_TH")
    plt.ylabel("Distance error (cm)")
    plt.grid(visible=True)
    plt.legend()
    for th in quantiles.columns:
        quantiles[f"RP({th})"] = quantiles[th] + 25     
    plt.show()
    

def plot_cir_compare(data, ax = None, show = True, show_th = True, db = True):
    TP_COLOR = "#648FFF"
    ESTIMATE_COLOR = "#FFB000"
    colors = list(reversed(mcp.gen_color(cmap="Greys",n=len(data)+4)))
    colors = [colors[0], colors[3], colors[4]] 
    linestyles = [ ":", "-", "-."]
    labels = ["0.01  quantile", "0.02 quantile", "0.10 quantile"]
    if ax is None:
        ax = plt.subplot(111)
    maxPeakIdx = np.max(data["trueFpIndex"])
    offset = [2, 7, 3]#np.random.choice(range(5), replace = False, size = 3)#np.round(maxPeakIdx - data["trueFpIndex"]).astype(int)
    i = 0
    for cir, color, linestyle, label in zip(data["cir"],
                                            colors,
                                            linestyles, 
                                            labels):
        
        ax.plot(np.hstack([np.zeros(offset[i]), cir]), zorder = -1, linestyle = linestyle, color = color, label = label, markersize=5)
        if i == 0:
            ax.scatter(data["trueFpIndex"].iloc[i] + offset[i], data["trueFpHeight"].iloc[i], marker = "s", color = color, label="Early Peak")
        else:
            ax.scatter(data["trueFpIndex"].iloc[i] + offset[i], data["trueFpHeight"].iloc[i], marker = "s", color = color)
        i += 1
    # for cir, color, linestyle, label in zip(data["cir"],
    #                                         colors,
    #                                         linestyles, 
    #                                         labels):
        
    #     ax.plot(np.hstack([ cir]), zorder = -1, linestyle = linestyle, color = color, label = label, markersize=5)
    #     if i == 0:
    #         ax.scatter(data["trueFpIndex"].iloc[i], data["trueFpHeight"].iloc[i], marker = "s", color = color, label="Early Peak")
    #     else:
    #         ax.scatter(data["trueFpIndex"].iloc[i], data["trueFpHeight"].iloc[i], marker = "s", color = color)
    #     i += 1

    ax.hlines(ABS_TH, 0, 512, color = "C0", label="Absolute Threshold = 702")
    start = maxPeakIdx - 15
    end = maxPeakIdx + 15
    ax.set_xlim(start, end)
    ax.xaxis.set_major_locator(MultipleLocator(4))
    ax.xaxis.set_minor_locator(MultipleLocator(1))
    
    ax.yaxis.set_minor_locator(MultipleLocator(500))
    ax.yaxis.set_major_locator(FixedLocator([x*1000 for x in range(5)]))

    ax.set_yticklabels(ax.get_yticks(), rotation=45)
    ax.set_xticklabels([])

    if show:
        plt.show()
   

def compare(good, medium, bad, severe_nlos):
    default_figsize = plt.rcParams['figure.figsize']
    good_data = data_load(good, ABS_TH=ABS_TH)
    medium_data = data_load(medium,  ABS_TH=ABS_TH)
    bad_data = data_load(bad, ABS_TH=ABS_TH)
    severe_nlos_data = data_load(severe_nlos, ABS_TH=ABS_TH)
    
    medium_data["maxPeakIndex"] = [np.argmax(cir) for cir in medium_data["cir"]]    
    medium_data["backsearch"] = np.abs(medium_data["maxPeakIndex"] - medium_data["pureFpIndex"])
    def plot_grouped_by_setting_horizontal():
        cm = 1/2.54  # centimeters in inches
        plt.rcParams['figure.figsize'] =[27*cm, 6*cm]
        gs = gridspec.GridSpec(1, 4, wspace=0.2)
        ax1 = plt.subplot(gs[0, 0])
        ax2 = plt.subplot(gs[0, 1])
        ax3 = plt.subplot(gs[0, 2])
        ax4 = plt.subplot(gs[0, 3])
        plot_cir_compare(good_data.loc[CIR_Analyzer.get_percentiles_handles(good_data)],
                         ax1, show = False)
        plot_cir_compare(medium_data.loc[CIR_Analyzer.get_percentiles_handles(medium_data)], ax2, show = False)
        plot_cir_compare(bad_data.loc[CIR_Analyzer.get_percentiles_handles(bad_data)], ax3, show = False)
        plot_cir_compare(severe_nlos_data.loc[CIR_Analyzer.get_percentiles_handles(severe_nlos_data)], ax4, show = False)
        ax1.set_title("a. Full LoS")
        ax2.set_title("b. Common Payment")
        ax3.set_title("c. Blocked Antenna")
        ax4.set_title("d. NLoS at 3m")
        
        ax1.set_ylim(0, 3450)
        ax2.set_ylim(0, 3450)
        ax3.set_ylim(0, 3450)
        ax4.set_ylim(0, 3450)
        ax2.set_yticklabels([])
        ax3.set_yticklabels([])
        ax4.set_yticklabels([])
        
        
        handles, labels = plt.gca().get_legend_handles_labels()
        order = [0,3,2,1,4]
        ax3.legend([handles[idx] for idx in order],[labels[idx] for idx in order], loc='upper center', bbox_to_anchor=(-0.15, -0.12),
            fancybox=True, ncol=6)
        
        ratio = 0.8
        ax1.set_box_aspect(ratio) 
        ax2.set_box_aspect(ratio)
        ax3.set_box_aspect(ratio)
        ax4.set_box_aspect(ratio)
        ax1.set_ylabel("$\mid CIR(t) \mid$")
        ax1.set_xlabel("$t$", labelpad=1)
        ax2.set_xlabel("$t$", labelpad=1)
        ax3.set_xlabel("$t$", labelpad=1)
        ax4.set_xlabel("$t$", labelpad=1)
        
        plt.savefig(f"{PLOT_FOLDER}/cir_contactless.pdf", bbox_inches='tight')
        print(PLOT_FOLDER)
        plt.show()
    plot_grouped_by_setting_horizontal()

def show_single(basedir): 
    show_multiple([basedir])
    
def show_multiple(paths, GRAPHS_OUTPUT = "./full_test_output_graphs"):
    data = data_load(paths, ABS_TH)
    plot_cir_setting(data, basedir="./full_test_output", n = 3)
    #plot_cir_led(data[data.index == 37])
    plot_cir(data[data["toaDiff"] >= 1])
    distance_errors(data)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--single", help = "Path to output directory")
    group.add_argument("--multiple", help = "Path to outputs directories", nargs='+')
    group.add_argument("--all",help = "Path to full_test_output directory")
    group.add_argument("--test", help="For development")
    group.add_argument("--compare", action="store_true")
    parser.add_argument("--good", nargs= '+', required= False)
    parser.add_argument("--medium", nargs='+', required = False)
    parser.add_argument("--bad", nargs= '+', required = False)
    parser.add_argument("--severe_nlos", nargs= '+', required = False)
    parser.add_argument("--plot_folder", help="Folder where to save plots.")  
    args = parser.parse_args()
    if args.plot_folder is not None:
        PLOT_FOLDER = args.plot_folder
        print(PLOT_FOLDER)
    if args.compare:
        compare(args.good, args.medium, args.bad, args.severe_nlos)
        exit()
    if args.test is not None:
        test(args.test)
        exit()
    if args.single is not None:
        show_single(args.single)
    else:
        if args.multiple is not None:
            paths = args.multiple
            show_multiple(paths)
        else:
            paths = os.listdir(args.all)
            paths = [os.path.join(args.all, x) for x in paths]
            show_all(paths)
 
