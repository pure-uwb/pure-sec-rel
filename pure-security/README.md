## PURE: Payments with UWB RElay-protection
This repository contains the security analysis performed in the context of the paper "PURE: Payments with UWB RElay-protection". Specifically, it anaylsis the security of a fixed threshold for leading edge detection using UWB-HRP.

## Content

The folder `nsame_2000_2500` contains the CIRs collected injecting STSes in a Qorvo DW3000 board with increasing number of correct pulses (from 2000/4096 to 2500/4096) at the maximum power an adversary can transmit before the receiver clips. 
Run 
```
python3 nsame-analyze-plot.py --single nsame_2000_2500
```
To analyze the attacker success probability with importance sampling.

The script `nsame-analyze-sampling.py` contains additional plots comparing the experimental results with the theoretical attacker probability.
```
python3 nsame-analyze-sampling.py --multiple nsame_2000_2500
```
