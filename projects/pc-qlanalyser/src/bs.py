import numpy as np
import mne
from .utils import ellip_filter,calc_NLEO,smooth_NLEO,smooth_NLEO_bs
from datetime import datetime


#raw = mne.io.read_raw_edf(r'C:\Users\evian\Desktop\QL\m010001_r_labeled_edited.edf', preload=True, verbose=False)
#raw.crop(tmin=0, tmax=100)


def bs_detection(raw, channel_name, epochlength, bs_band_h_freq = 8, bs_band_l_freq = None, artifact_band_h_freq = None, artifact_band_l_freq = 47, thr_artifact = 0.1, thr_burst = 0.25, thr_suppression = 0.25, min_suppr_len = 2, scale=1000):
    artifact_value = 0
    suppression_value = 1
    burst_value = 2
    # 提取特定通道数据
    data, times = raw[channel_name, :]
    Fs = int(raw.info['sfreq'])  # 采样频率

    info = mne.create_info(ch_names=['EEG1'], ch_types=['eeg'], sfreq=Fs)
    data_array = mne.io.RawArray(data, info)

 # 用椭圆滤波器处理信号
    artifact = ellip_filter(data_array, artifact_band_l_freq, artifact_band_h_freq, 8)
    bs = ellip_filter(data_array, bs_band_l_freq, bs_band_h_freq, 6)

 
    NLEO_artifact = calc_NLEO(artifact, info, scale=scale)
    NLEO_bs = calc_NLEO(bs, info, scale=scale)
    smoothed_artifact = smooth_NLEO(Fs, NLEO_artifact, info, scale=scale)
    smoothed_bs = smooth_NLEO_bs(Fs, NLEO_bs, info, scale=scale)

    status = np.zeros(data.shape[-1])
    status[:2*Fs] = artifact_value

    artifact_len = 1
    burst_len = 0
    suppression_len = 0

    smoothed_bs_data = smoothed_bs.get_data()
    smoothed_artifact_data = smoothed_artifact.get_data()


    for i in range(1, data.shape[-1]):
        if smoothed_artifact_data[:, i] >= thr_artifact and smoothed_bs_data[:, i] < thr_burst:
            burst_len = 0
            artifact_len += 1
            if artifact_len >= Fs and status[i-1] != burst_value:
                status[i] = artifact_value
                suppression_len = 0
            elif artifact_len >= 2*Fs and status[i-1] == burst_value:
                status[i] = artifact_value
                suppression_len = 0
            elif suppression_len >= min_suppr_len*Fs:
                if smoothed_bs_data[:, i] <= thr_suppression:
                    status[i] = suppression_value 
        elif smoothed_artifact_data[:, i] >= thr_artifact:   
            suppression_len = 0
            artifact_len += 1
            burst_len += 1
            if artifact_len >= Fs and status[i-1] != burst_value:
                status[i] = artifact_value
                burst_len = 0
            elif artifact_len >= 2*Fs and status[i-1] == burst_value:
                status[i] = artifact_value
                burst_len = 0
            elif burst_len == Fs and status[i-1] != artifact_value:
                status[max(1, i-Fs):i] = burst_value
            elif burst_len > Fs and status[i-1] != artifact_value:
                status[i] = burst_value
            elif burst_len == 2*Fs and status[i-1] == artifact_value:
                status[max(1, i-2*Fs):i] = burst_value 
            elif burst_len > 2*Fs and status[i-1] == artifact_value:
                status[i] = burst_value 
        elif smoothed_bs_data[:, i] >= thr_burst:
            artifact_len = 0
            suppression_len = 0
            burst_len += 1
            # original
            if burst_len == Fs and status[i-1] != artifact_value:
                status[max(1, i-Fs):i] = burst_value
            elif burst_len > Fs and status[i-1] != artifact_value:
                status[i] = burst_value
            elif burst_len == 2*Fs and status[i-1] != artifact_value:
                status[max(1, i-2*Fs):i] = burst_value
            elif burst_len > 2*Fs and status[i-1] != artifact_value:
                status[i] = burst_value
        else:
            artifact_len = 0
            burst_len = 0
            suppression_len += 1
            if suppression_len >= min_suppr_len*Fs:
                if smoothed_bs_data[:, i] <= thr_suppression:
                    status[i] = suppression_value 
            else:
                status[i] = suppression_value


        epoch_length = epochlength * Fs
           
        num_epochs = len(status) // epoch_length

        epoch_int_array = np.zeros(num_epochs, dtype=int)

        for i in range(num_epochs):
            start_index = i * epoch_length
            end_index = start_index + epoch_length
            current_epoch = status[start_index:end_index]
            current_epoch = current_epoch.astype(int)
            counts = np.bincount(current_epoch)  
            most_frequent = np.argmax(counts)
            epoch_int_array[i] = most_frequent

    return epoch_int_array

#bs_detection(raw,'EEG')