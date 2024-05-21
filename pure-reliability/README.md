## PURE: Payments with UWB RElay-protection

This README accompanies the reliability analysis of PURE described in the paper "PURE: Payments with UWB RElay-protection".

### Content
The repository contains: 
* The CIRs collected in payment scenarios (in the folder `full_test_output`)
* The analysis of such CIRs with a LED and absolute threshold as proposed in the paper.
* All the code used to collect the data in full_test_output in the folder `data_collection`

## PURE: Reliability analysis
The folder `full_test_output` contains CIRs collected in: 
* Realistic payment conditions;
* Payments with purposefully obstructed antenna;
* Full LoS CIR at less than 20 cm;
* Sever NLoS 
 The script `reliability_analysis.py` can be used to plot the results presented in the paper as follows. The script shows examples of the measurement setting together with the CIR and peaks detected by the Qorvo board and PURE. The flag `--multiple` allows selecting the sets of measurements to include in the analysis. Following are the commands necessary to obtain the paper plots and results.   

* Figure 11:
```
python3 reliability_analysis.py --compare --medium full_test_output/qorvo_hand_above full_test_output/qorvo_hand_below_lower_ant_dly full_test_output/six_hand_above full_test_output/six_hand_below full_test_output/sumup_hand_above full_test_output/sumup_hand_below --good full_test_output/full_los --bad full_test_output/bad_hand_position full_test_output/bad_hand_position_10 full_test_output/bad_hand_position_2 full_test_output/bad_hand_position_3 full_test_output/bad_hand_position_4 full_test_output/bad_hand_position_5 full_test_output/bad_hand_position_6 full_test_output/bad_hand_position_7 full_test_output/bad_hand_position_8 full_test_output/bad_hand_position_9 full_test_output/bad_hand_position_antenna_away_from_contactless full_test_output/bad_hand_position_different_pos --severe_nlos full_test_output/nlos_bad_channel_max_50
```

* Table 3: 
```
python3 reliability_analysis.py --multiple full_test_output/qorvo_hand_above full_test_output/qorvo_hand_below_lower_ant_dly full_test_output/six_hand_above full_test_output/six_hand_below full_test_output/sumup_hand_above full_test_output/sumup_hand_below
```

* Blocked antenna examples:
```
python3 reliability_analysis.py --multiple full_test_output/bad_hand_position full_test_output/bad_hand_position_10 full_test_output/bad_hand_position_2 full_test_output/bad_hand_position_3 full_test_output/bad_hand_position_4 full_test_output/bad_hand_position_5 full_test_output/bad_hand_position_6 full_test_output/bad_hand_position_7 full_test_output/bad_hand_position_8 full_test_output/bad_hand_position_9 full_test_output/bad_hand_position_antenna_away_from_contactless full_test_output/bad_hand_position_different_pos
```

## Data collection

We refer to the README in the `data_collection` folder for the instruction on how to recreate the testing environment.
