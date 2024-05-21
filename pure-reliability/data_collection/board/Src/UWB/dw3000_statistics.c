/**
 * @file      dw3000_statistics.c
 *
 * @brief     Compute various statistics of a signal
 *
 * @author    Decawave Applications
 *
 * @attention Copyright (c) 2021 - 2022, Qorvo US, Inc.
 * All rights reserved
 * Redistribution and use in source and binary forms, with or without modification,
 *  are permitted provided that the following conditions are met:
 * 1. Redistributions of source code must retain the above copyright notice, this
 *  list of conditions, and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright notice,
 *  this list of conditions and the following disclaimer in the documentation
 *  and/or other materials provided with the distribution.
 * 3. You may only use this software, with or without any modification, with an
 *  integrated circuit developed by Qorvo US, Inc. or any of its affiliates
 *  (collectively, "Qorvo"), or any module that contains such integrated circuit.
 * 4. You may not reverse engineer, disassemble, decompile, decode, adapt, or
 *  otherwise attempt to derive or gain access to the source code to any software
 *  distributed under this license in binary or object code form, in whole or in
 *  part.
 * 5. You may not use any Qorvo name, trademarks, service marks, trade dress,
 *  logos, trade names, or other symbols or insignia identifying the source of
 *  Qorvo's products or services, or the names of any of Qorvo's developers to
 *  endorse or promote products derived from this software without specific prior
 *  written permission from Qorvo US, Inc. You must not call products derived from
 *  this software "Qorvo", you must not have "Qorvo" appear in their name, without
 *  the prior permission from Qorvo US, Inc.
 * 6. Qorvo may publish revised or new version of this license from time to time.
 *  No one other than Qorvo US, Inc. has the right to modify the terms applicable
 *  to the software provided under this license.
 * THIS SOFTWARE IS PROVIDED BY QORVO US, INC. "AS IS" AND ANY EXPRESS OR IMPLIED
 *  WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. NEITHER
 *  QORVO, NOR ANY PERSON ASSOCIATED WITH QORVO MAKES ANY WARRANTY OR
 *  REPRESENTATION WITH RESPECT TO THE COMPLETENESS, SECURITY, RELIABILITY, OR
 *  ACCURACY OF THE SOFTWARE, THAT IT IS ERROR FREE OR THAT ANY DEFECTS WILL BE
 *  CORRECTED, OR THAT THE SOFTWARE WILL OTHERWISE MEET YOUR NEEDS OR EXPECTATIONS.
 * IN NO EVENT SHALL QORVO OR ANYBODY ASSOCIATED WITH QORVO BE LIABLE FOR ANY
 *  DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 *  (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 *  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
 *  ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 *  SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 * 
 *
 */

#include <math.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "deca_device_api.h"
#include "dw3000_statistics.h"
#include "reporter.h"
#include "FreeRTOS.h"
#include "task.h"
#include "nrf_log.h"

#define SIG_LVL_FACTOR     0.4     // Factor between 0 and 1; default 0.4 from experiments and simulations.
#define SIG_LVL_THRESHOLD  12      // Threshold unit is dB; default 12dB from experiments and simulations.
#define ALPHA_PRF_16       113.8   // Constant A for PRF of 16 MHz. See User Manual for more information.
#define ALPHA_PRF_64       120.7   // Constant A for PRF of 64 MHz. See User Manual for more information.
#define RX_CODE_THRESHOLD  8       // For 64 MHz PRF the RX code is 9.
#define LOG_CONSTANT_C0    63.2    // 10log10(2^21) = 63.2    // See User Manual for more information.
#define LOG_CONSTANT_D0_E0 51.175  // 10log10(2^17) = 51.175  // See User Manual for more information.
#define IP_MIN_THRESHOLD   3.3     // Minimum Signal Level in dB. Please see App Notes "APS006 PART 3"
#define IP_MAX_THRESHOLD   6.0     // Minimum Signal Level in dB. Please see App Notes "APS006 PART 3"
#define CONSTANT_PR_IP_A   0.39178 // Constant from simulations on DW device accumulator, please see App Notes "APS006 PART 3"
#define CONSTANT_PR_IP_B   1.31719 // Constant from simulations on DW device accumulator, please see App Notes "APS006 PART 3"
#define CIR_SIZE 512
#define STS_CIR_OFFSET 1024 + 0
#define PRE_CIR_OFFSET 512
volatile static uint8_t save_cir = 0;
volatile static bool memory_reader_ready = true;
volatile static bool cir_ready = false;

volatile static int32_t flag = 7;
volatile static int32_t cir_I_ptr[CIR_SIZE];
volatile static int32_t cir_Q_ptr[CIR_SIZE];
//volatile static int32_t cir_I_preamble_ptr[CIR_SIZE];
//volatile static int32_t cir_Q_preamble_ptr[CIR_SIZE];
volatile static int32_t iteration = 0;
volatile static int32_t diagnostics_ready;
static dwt_rxdiag_t rx_diag;

void calculateStats(struct dwchip_s *dw, struct mcps_diag_s *diag)
{   
    iteration = (iteration + 1);

    // if ( (save_cir == 1 ) && iteration == 9){
    //     flag = 7;
    if ( save_cir == 1 ){
        NRF_LOG_INFO("SAVE CIR");

        uint8_t cir_sample[7];
        int32_t re;
        int32_t im;
        for(int i=0; i<CIR_SIZE; i++){
            dwt_readaccdata(cir_sample, 7, STS_CIR_OFFSET + i);
            re = (cir_sample[1] << 8 | cir_sample[2] << 16 | cir_sample[3] << 24) >> 8;
            im = (cir_sample[4] << 8 | cir_sample[5] << 16 | cir_sample[6] << 24) >> 8;
            cir_I_ptr[i] = re;
            cir_Q_ptr[i] = im;
        }
        NRF_LOG_INFO("CIR ready");



        // Read preamble 
        // for(int i=0; i<CIR_SIZE; i++){
        //     dwt_readaccdata(cir_sample, 7, PRE_CIR_OFFSET + i);
        //     re = (cir_sample[1] << 8 | cir_sample[2] << 16 | cir_sample[3] << 24) >> 8;
        //     im = (cir_sample[4] << 8 | cir_sample[5] << 16 | cir_sample[6] << 24) >> 8;
        //     cir_I_preamble_ptr[i] = re;
        //     cir_Q_preamble_ptr[i] = im;
        // }

        dwt_readdiagnostics(&rx_diag);
        diagnostics_ready += 1;
    }else{
        NRF_LOG_INFO("SKIP CIR");

        save_cir = 1; // Do not save CIR on the first RANGE, save it on second and restart the app
    }
    int16_t rxSTSQualityIndex;
    dwt_readstsquality (&rxSTSQualityIndex);
    NRF_LOG_INFO("Sts quality: %d", rxSTSQualityIndex);
    /* Simply toggle the LED every 500ms, blockin
    g between each toggle. */
}
