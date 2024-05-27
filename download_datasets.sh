#!/bin/bash
powerUrl="https://polybox.ethz.ch/index.php/s/xdxPUxJHLgBuAa4/download"
nsameUrl="https://polybox.ethz.ch/index.php/s/vTZJ83sRuTCjz0y/download"
relUrl="https://polybox.ethz.ch/index.php/s/AoVypmDR70jCdEU/download"

powerName="power_dataset.zip"
nsameName="nsame_2000_2500.zip"
relName="full_test_output.zip"

cd pure-security
wget $powerUrl
unzip $powerName
rm $powerName

wget $nsameName
unzip $nsameName
rm $nsameName

cd ../pure-reliability
wget $relUrl
unzip $relName
rm $relName
