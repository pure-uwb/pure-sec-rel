# python3 nsame-analyze-final.py --single dir
# Put the output.hdf5 in dir

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
from scipy.stats import binom , sem
from scipy import stats

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
    for measure_type, path in zip(measure_types, paths):
        print(path)
        f =  h5py.File(os.path.join(path, "output.hdf5"), 'r')
        data = hd2pandas(f)
        data["measure_type"] = measure_type
        datas.append(data)
        cirs[measure_type] = np.abs(f["cir_sts"][:len(data), :])
    df = pd.concat(datas)
    df.reset_index(inplace=True)
    return df, cirs

def data_load(paths, ABS_TH):
    data, cirs = read_multiple(paths)
    cirs = np.vstack(list(cirs.values()))
    data["rms"], data["std"]= CIR_Analyzer.get_noise_estimates(cirs)
    data["cir"] = [cir for cir in cirs]    
    data["stsFpHeight"] = [cir[int(data["stsFpIndex"][i])] for i, cir in enumerate(cirs)]
    data["pureFpIndex"], data["pureFpHeight"] = CIR_Analyzer.get_first_peak_abs_opt(data["cir"],data["stsFpIndex"], ABS_TH)
    data["trueFpIndex"] = [CIR_Analyzer.true_peak_index(cir, data["stsFpIndex"][i]) for i, cir in enumerate(cirs)]
    data["trueFpHeight"] = [cir[data["trueFpIndex"][i]] for i, cir in enumerate(cirs)]
    data["maxFpIndex"] = [np.argmax(cir) for i, cir in enumerate(cirs)]
    data["maxFpHeight"] = [np.max(cir) for i, cir in enumerate(cirs)]
    
    data["toaDiff"] =  data["pureFpIndex"] - data["stsFpIndex"]
    print(data["power"])
    return data
            
def plot_cir(data,  ax = None, show = True, show_th = True, db = True):
    TP_COLOR = "#648FFF"
    PURE_COLOR = "#FFB000"
    if ax is None:
        ax = plt.subplot(111)
    maxPeakIdx = np.max(data["maxFpIndex"])
    offset = maxPeakIdx - data["maxFpIndex"]
    for i, cir in enumerate(data["cir"]):
        ax.plot(np.hstack([np.zeros(offset.iloc[i]), cir]), zorder = -1, color = f"C{i}")
    ax.scatter(data["stsFpIndex"] + offset, data["stsFpHeight"], marker = "s", color = TP_COLOR, label="Early Peak")
    ax.scatter(data["trueFpIndex"]+ offset, data["trueFpHeight"], marker = "s", label="True Early Peak")
    ax.scatter(data["maxFpIndex"] + offset, data["maxFpHeight"], marker = "s", label="True Early Peak")
    
    plt.legend()
    if show:
        plt.show()

def distance_errors(data):
    distance_errors = {}
    for abs_th in range(600, 1300, 50):
        toa, _ =   CIR_Analyzer.get_first_peak_abs_opt(data["cir"],
                                                       data["stsFpIndex"], 
                                                       abs_th)
        distance_errors[abs_th] = (toa - data["stsFpIndex"]) * 30 # Every index is 30 cm
    distance_errors_df = pd.DataFrame(distance_errors)
    print(distance_errors_df)
    print(distance_errors_df.describe())
    quantiles_list = [1, 0.995, 0.99, 0.985, 0.98]
    quantiles = distance_errors_df.quantile(quantiles_list)
    print(quantiles)
    print(type(quantiles))
    for i, q in enumerate(quantiles_list):
        plt.plot(quantiles.columns, quantiles.iloc[i], label = f"quantile {q}")
    plt.xlabel("ABS_TH")
    plt.ylabel("Distance error (cm)")
    plt.grid(visible=True)
    plt.legend()
    plt.show()

def stat_tests(data):
    def gaussian_test(var, values):
        stat1, p1 = stats.shapiro(values)
        stat2, p2 = stats.normaltest(values)

        print(f"Gaussian: {var}\n\t{p1:5f} (Shapiro-Wilk)\n\t{p2:5f} (D'Agostino's)")
    
    grouped = data.groupby("nsame")["maxFpHeight"].apply(list)
    print(grouped)
    grouped_dict = {}
    sem_trend = {}
    for nsame in grouped.index:
        grouped_dict[nsame] = grouped[nsame]
        sem_trend[nsame] = []
        for i in range(len(grouped[nsame])):
            sem_trend[nsame].append(sem( grouped[nsame][:i]))
    for k, v in sem_trend.items():
        plt.plot(v, label = f"nsame: {k}, total: {len(grouped_dict[nsame])}")
    plt.legend()
    plt.show()

def get_grouped_by_nsame(data):
    return data.groupby("nsame")["maxFpHeight"].apply(list)    
 
def nsame_vs_peak(data):
    
    plt.scatter(data["nsame"], data["maxFpHeight"])
    plt.xlabel("nsame")
    plt.ylabel("Peak Height")
    plt.savefig("./diagrams/nsame_vs_peak_height.pdf")

    plt.show() 
        
    grouped = data.groupby("nsame")["maxFpHeight"].agg(["mean", "std", "max", "count"])
    print(print(grouped["count"].describe()))
    
    plt.errorbar(grouped.index, grouped["mean"], yerr = 3*grouped["std"], label = "mean +- 3std")
    plt.scatter(grouped.index, grouped["max"], label = "max")
    plt.grid(visible = True)
    npulses = 4096
    x = np.array(list(range(2048, 2600, 10)))
    y = 2 * x - npulses
    plt.plot(x, y, color = "red", label = "2*nsame - npulses")
    plt.xlabel("nsame")
    plt.ylabel("Peak Height")
    plt.legend()
    plt.savefig('./diagrams/nsame_vs_peak_height_std.pdf')
    plt.show()
    
    def nsame_to_probability(nsame):
        if nsame < 2048:
            nsame = 4096 - nsame 
        # Multiply by two because > nsame and < 4906 - nsame
        # Both contribute to attacker advantage
        return binom.sf(nsame, npulses, 0.5) * 2
    
    def adjust_nsame(nsame):
        if nsame < 2048:
            nsame = 4096 - nsame 
        return nsame
    
    security_bits = [np.log2(nsame_to_probability(nsame)) for nsame in grouped.index]
    data["securityBits"] = np.log2(data["nsame"].apply(nsame_to_probability))
    plt.errorbar(grouped["mean"], security_bits, xerr = 3*grouped["std"], label = "mean +- 3std")
    plt.scatter(grouped["mean"], security_bits)
    #plt.scatter(data["maxFpHeight"], data["securityBits"])
    plt.xlabel("Peak Height")
    plt.ylabel("$log_2(p_a)$")
    plt.savefig("./diagrams/peak_height_vs_probability.pdf")
    plt.show()

def success_rate_importance_sampling(data):

    # Compute using importance sampling
    # It takes into account the effect of both Binomial and Gaussian noise on
    # success rate
    def sr_importance_sampling(sample_success, sample_nsame, npulses, nsamples, window_len):
    
        double = 2 # consider two sides
        x = sample_success*double*binom.pmf(sample_nsame, npulses, 0.5)*window_len
        sr = (1/nsamples)*np.sum(x)
    
        num = np.sum((sr - x)**2)
        den = nsamples - 1
        stdev = np.sqrt(num/den)
        sem = stdev / np.sqrt(nsamples)
        return [sr, sem]

    npulses = 4096
    grouped = get_grouped_by_nsame(data)
    sample_nsame = grouped.keys() #data["nsame"]
    sample_peaks = grouped.apply(np.mean) + 3*grouped.apply(np.std) # data["maxFpHeight"]
    nsamples = len(sample_nsame)
    window_len = len(grouped) # TODO better
    
    srs = []
    sems = []
    th_min = 300
    th_max = 2200
    thresholds = [th for th in range(th_min, th_max, 1)]
    for threshold in thresholds:
        sample_success = sample_peaks > threshold
        sr, sem = sr_importance_sampling(sample_success, sample_nsame, npulses, nsamples, window_len)
        srs.append(sr)
        sems.append(sem)
    
    thresholds = np.array(thresholds)
    srs = np.array(srs)
    sems = np.array(sems)

    # Compute with classic way for comparison
    def nsame_to_probability(nsame):
        if nsame < 2048:
            nsame = 4096 - nsame 
        return binom.sf(nsame, npulses, 0.5) * 2

    grouped = data.groupby("nsame")["maxFpHeight"].agg(["mean", "std", "max", "count"])
    security_bits = [np.log2(nsame_to_probability(nsame)) for nsame in grouped.index]
    data["securityBits"] = np.log2(data["nsame"].apply(nsame_to_probability))
    plt.scatter(grouped["mean"]+3*grouped["std"],
            security_bits, s=1, label="conservative")
    plt.scatter(grouped["mean"], security_bits,
            s=1, label="underestimate")

    plt.plot(thresholds, np.log2(srs), '+' , linewidth=0.1, label="log_2(p_a)")
    plt.plot(thresholds, np.log2(srs+3.291*sems), '+', linewidth=0.1, label="$log_2(p_a+3.291\sigma)$")
    plt.plot(thresholds, np.log2(srs-3.291*sems), '+', linewidth=0.1, label="$log_2(p_a-3.291\sigma)$")
 
    plt.xlabel("Peak Height Absolute Threshold")
    plt.ylabel("$log_2(Attack \; Success \; Probability)$")

    plt.legend()
    plt.savefig("./diagrams/sr_vs_threshold.pdf")
    plt.show()

    return 

def show_single(basedir): 
    show_multiple([basedir])
    
def show_multiple(paths, GRAPHS_OUTPUT = "./full_test_output_graphs"):
    ABS_TH = 1000
    data = data_load(paths, ABS_TH)
    #stat_tests(data)
    nsame_vs_peak(data)
    #plot_cir(data[(data["nsame"] > 2300) *( data["trueFpHeight"] < 320) ])
    # For Giovanni: Do what you want here
    success_rate_importance_sampling(data)

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
    
    args = parser.parse_args()
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
 
