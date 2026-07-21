import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import welch, butter, filtfilt, lfilter
from datetime import datetime,timedelta
import matplotlib.dates as mdates
def fp(raw, channels, bands, result_path, progress_callback=None):

    sfreq = raw.info['sfreq']
    data_dict_raw = {ch: raw.get_data(picks=ch) for ch in channels}
    
    all_ch = raw.info['ch_names']
    id_l = [all_ch.index(ch) + 1 for ch in channels]
    data_dict = {f'Ch{id_l[i]}_{channels[i]}': v for i, (k, v) in enumerate(list(data_dict_raw.items())[:len(channels)])}

    def notch_filter(EEG, fs, order=1,AR4=True):

        nyquist = 0.5 * fs
        low_cutoff = 49.5 / nyquist
        high_cutoff = 50.5 / nyquist
        b, a = butter(order, [low_cutoff, high_cutoff], btype='bandstop')
        if AR4:
            EEG_filtered = np.squeeze(filtfilt(b, a, EEG)) #当 数据来源是全澜AR4时，改用该滤波器
        else:
            EEG_filtered = np.squeeze(filtfilt(b, a, EEG))

        low_cutoff = 99 / nyquist
        high_cutoff = 101 / nyquist
        b, a = butter(order, [low_cutoff, high_cutoff], btype='bandstop')
        EEG_filtered = np.squeeze(filtfilt(b, a,EEG_filtered))
        return EEG_filtered

    data_dict = {ch: notch_filter(data, sfreq) for ch, data in data_dict.items()}
    for channel, channel_data in data_dict.items():
        for band, (fmin, fmax) in bands.items():
            filter_data = bandpass_filter(channel_data,fmin,fmax,sfreq,2)

            t = np.array(range(len(filter_data))) /sfreq
            start_time = raw.info['meas_date'].replace(tzinfo=None)
            t_datetime = [start_time + timedelta(seconds=x) for x in t]

            fig,ax=plt.subplots(figsize=(16,4.5))
            fig, ax=plt.subplots(figsize=(16,4.5))
            ax.plot(t_datetime,filter_data,color='black')
            ax.set_title(f'Channel {channel}_{band}_raw_data')
            ax.set_xlabel('Time')
            ax.set_xlim(t_datetime[0],t_datetime[-1])
            ax.set_ylabel('Amplitude(μV)')
            ax.set_ylim(-200,200)

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
            ax.xaxis.set_major_locator(mdates.SecondLocator(interval=3600))
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            plt.tight_layout()

            png_path = os.path.join(result_path, f'{channel}_{band}.png')
            plt.savefig(png_path)
            plt.close()
        
        if progress_callback:
            progress_callback(1)  # 完成一个步骤

def bandpass_filter(EEG, low_cutoff_frequency, high_cutoff_frequency, fs, order):
        nyquist = 0.5 * fs
        low_cutoff = low_cutoff_frequency / nyquist
        high_cutoff = high_cutoff_frequency / nyquist
        b_bp, a_bp = butter(order, [low_cutoff, high_cutoff], btype='bandpass')
        EEG_filtered = lfilter(b_bp, a_bp, EEG)
        return EEG_filtered