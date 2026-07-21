import numpy as np
import pandas as pd
from mne.io import read_raw_edf
# import shap
import sqlite3
import time
import os
import pickle
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
import mne


def printW (string):
    f = open("log", "a")
    f.write(str(string) + '\n\n')
    f.close()


def cut_epochs (full_single_trace, sfreq, epoch_len = None):
    epoch_length = (epoch_len * sfreq)
    n_epochs = len(full_single_trace) // epoch_length
    output = np.zeros((n_epochs,epoch_length))
    for index in range(n_epochs):
        data_this_epoch = np.array([
            full_single_trace[index*epoch_length: (index+1)*epoch_length]
        ])
        output[index] = data_this_epoch
    return output


def get_epoch_abs_mean (full_single_trace, sfreq, epoch_len = None):
    epoch_length = (epoch_len * sfreq)
    n_epochs = len(full_single_trace) // epoch_length
    output = np.zeros(n_epochs)
    for index in range(n_epochs):
        data_this_epoch = np.array(
            full_single_trace[index*epoch_length: (index+1)*epoch_length]
        )
        output[index] = np.abs(data_this_epoch).mean()
    return output


def get_epoch_abs_median (full_single_trace, sfreq, epoch_len = None):
    epoch_length = (epoch_len * sfreq)
    n_epochs = len(full_single_trace) // epoch_length
    output = np.zeros(n_epochs)
    for index in range(n_epochs):
        data_this_epoch = np.array(
            full_single_trace[index*epoch_length: (index+1)*epoch_length]
        )
        output[index] = np.median(np.abs(data_this_epoch))
    return output


def get_epoch_abs_max (full_single_trace, sfreq, epoch_len = None):
    epoch_length = (epoch_len * sfreq)
    n_epochs = len(full_single_trace) // epoch_length
    output = np.zeros(n_epochs)
    for index in range(n_epochs):
        data_this_epoch = np.array(
            full_single_trace[index*epoch_length: (index+1)*epoch_length]
        )
        output[index] = np.abs(data_this_epoch).max()
    return output


def get_epoch_abs_std (full_single_trace, sfreq, epoch_len = None):
    epoch_length = (epoch_len * sfreq)
    n_epochs = len(full_single_trace) // epoch_length
    output = np.zeros(n_epochs)
    for index in range(n_epochs):
        data_this_epoch = np.array(
            full_single_trace[index*epoch_length: (index+1)*epoch_length]
        )
        output[index] = np.abs(data_this_epoch).std()
    return output


def get_epoch_psd (full_single_trace, sfreq, epoch_len = None):
    epoch_length = (epoch_len * sfreq)
    n_epochs = len(full_single_trace) // epoch_length
    output = np.zeros((6, n_epochs))
    for index in range(n_epochs):
        data_this_epoch = np.array(
            full_single_trace[index*epoch_length: (index+1)*epoch_length]
        )
        psd = np.abs(np.fft.fft(data_this_epoch))**2
        time_step = 1 / sfreq

        freqs = np.fft.fftfreq(data_this_epoch.size, time_step)
        idx = np.argsort(freqs)
        freqs = freqs[idx]
        psd = psd[idx]
        
        delta = np.sum(psd[np.logical_and(freqs >= 1, freqs <= 4)])
        theta = np.sum(psd[np.logical_and(freqs >= 4, freqs <= 8)])
        alpha = np.sum(psd[np.logical_and(freqs >= 8, freqs <= 12)])
        sigma = np.sum(psd[np.logical_and(freqs >= 12, freqs <= 15)])
        beta  = np.sum(psd[np.logical_and(freqs >= 15, freqs <= 30)])
        gamma = np.sum(psd[freqs >= 30])

        output[0,index] = delta
        output[1,index] = theta
        output[2,index] = alpha
        output[3,index] = sigma
        output[4,index] = beta
        output[5,index] = gamma
    return output


def rmsValue(arr):
    square = 0
    mean = 0.0
    root = 0.0
    n = len(arr)
    #Calculate square
    for i in range(0,n):
        square += (arr[i]**2)

    #Calculate Mean
    mean = (square / (float)(n))

    #Calculate Root
    root = mean**0.5

    return root


def get_epoch_rms (full_single_trace, sfreq, epoch_len = None):
    epoch_length = (epoch_len * sfreq)
    n_epochs = len(full_single_trace) // epoch_length
    output = np.zeros(n_epochs)
    for index in range(n_epochs):
        data_this_epoch = np.array(
            full_single_trace[index*epoch_length: (index+1)*epoch_length]
        )
        output[index] = rmsValue(data_this_epoch)
    return output


def remove_channel_outlier(df_input, channel):
    df = df_input.copy()
    stats = df.groupby(['subject_id'])[channel].agg(['mean', 'count', 'std'])
    
    ci_hi = []
    ci_lo = []
    
    for i in stats.index:
        m, c, s = stats.loc[i]
        ci_hi.append(m + 3*s)
        ci_lo.append(m - 3*s)
    
    stats['ci_hi'] = ci_hi
    stats['ci_lo'] = ci_lo
    
    df['ci_hi'] = df['subject_id'].map(stats['ci_hi'])
    df['ci_lo'] = df['subject_id'].map(stats['ci_lo'])
    
    df.loc[df[channel] > df['ci_hi'], channel] = np.nan
    df.loc[df[channel] < df['ci_lo'], channel] = np.nan

    # print(df['ci_hi'])
    # print(df['ci_lo'])
    
    # print(df.shape)
    # print(df[channel].isna().sum())
    
    return df


def remove_outlier(df_input):
    df = remove_channel_outlier(df_input, 'eeg1_rms')
    df = remove_channel_outlier(df, 'eeg1_rms')
    
    df = remove_channel_outlier(df_input, 'eeg2_rms')
    df = remove_channel_outlier(df, 'eeg2_rms')

    df = remove_channel_outlier(df_input, 'emg_rms')
    df = remove_channel_outlier(df, 'emg_rms')
    
    df = df[~df['eeg1_rms'].isna() & ~df['eeg2_rms'].isna() & ~df['emg_rms'].isna()]
    
    return df

# 只采用1个通道的EEG和1个通道的EMG数据
def save_single_edf_to_csv_1eeg(edf_filepath=None, epoch_len=None, model_name=None, test_run=False, include_score=False):
    file_firstname = edf_filepath.split("/")[-1].split('.edf')[0]
    edf_folderpath = edf_filepath.split(file_firstname)[0]

    if include_score:
        db3_filepath = edf_path + file_firstname + ".db3"
        connection = sqlite3.connect(db3_filepath)
        score_list = pd.read_sql_query(f"SELECT * from sleep_scores_table", connection)['score'].values
        print("score_list_shape", score_list.shape)
    else:
        score_list = np.nan
    
    # Save a downsampled data file
    downsampled_files = f"{edf_folderpath}{file_firstname}_{model_name}_rs_100hz.npy"
    if not os.path.exists(downsampled_files):
        raw = read_raw_edf(edf_filepath, preload=True)
        sfreq = int(raw.info["sfreq"])
        print(f"sfreq:{sfreq}")
        raw.resample(sfreq=100)
        resampled_data = raw.get_data()
        with open(downsampled_files, 'wb') as f:
            np.save(f, resampled_data)

    # 读取原始数据
    raw = read_raw_edf(edf_filepath, preload=True)
    raw_data_length = raw.get_data().shape[1]
    sfreq = int(raw.info["sfreq"])

    with open(f"{edf_folderpath}{file_firstname}_ch_names.pickle", 'wb') as fp:
        pickle.dump(raw.ch_names, fp)

    if include_score:
        print("raw_data_shape", raw_data_length)
        if raw_data_length != len(score_list) * epoch_len * sfreq:
            print("score list and raw data have different number of epochs")
            return
    if test_run:
        return

    raw.filter(1., 40., fir_design='firwin')

    # 对EMG通道进行20Hz的高通滤波
    # 创建原始数据的副本
    raw_highpass = raw.copy()

    # 只选择通道1进行滤波
    raw_highpass.pick_channels([raw.ch_names[1]])
    raw_highpass.filter(l_freq=20., h_freq=None, fir_design='firwin')

    # 获取滤波后的数据
    filtered_ch1 = raw_highpass.get_data()[0]

    
    raw_data = raw.get_data()
    # 将滤波后的数据替换回原始数据的通道1
    raw_data[1] = filtered_ch1
    
    df = pd.DataFrame()
    
    print("get basic features")
    eeg_no = 2 # eeg 通道序号
    emg_no = 1 # emg 通道序号

    df['eeg_abs_mean'] = get_epoch_abs_mean(raw_data[eeg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['emg_abs_mean'] = get_epoch_abs_mean(raw_data[emg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_abs_median'] = get_epoch_abs_median(raw_data[eeg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['emg_abs_median'] = get_epoch_abs_median(raw_data[emg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_abs_max'] = get_epoch_abs_max(raw_data[eeg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['emg_abs_max'] = get_epoch_abs_max(raw_data[emg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_abs_std'] = get_epoch_abs_std(raw_data[eeg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['emg_abs_std'] = get_epoch_abs_std(raw_data[emg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_rms'] = get_epoch_rms(raw_data[eeg_no], sfreq=sfreq, epoch_len=epoch_len)
    df['emg_rms'] = get_epoch_rms(raw_data[emg_no], sfreq=sfreq, epoch_len=epoch_len)
    
    df['eeg_abs_mean_n'] = df['eeg_abs_mean']/df['eeg_abs_mean'].median()
    df['emg_abs_mean_n'] = df['emg_abs_mean']/df['emg_abs_mean'].median()
    df['eeg_abs_median_n'] = df['eeg_abs_median']/df['eeg_abs_median'].median()
    df['emg_abs_median_n'] = df['emg_abs_median']/df['emg_abs_median'].median()
    df['eeg_abs_max_n'] = df['eeg_abs_max']/df['eeg_abs_max'].median()
    df['emg_abs_max_n'] = df['emg_abs_max']/df['emg_abs_max'].median()
    df['eeg_abs_std_n'] = df['eeg_abs_std']/df['eeg_abs_std'].median()
    df['emg_abs_std_n'] = df['emg_abs_std']/df['emg_abs_std'].median()
    df['eeg_rms_n'] = df['eeg_rms']/df['eeg_rms'].median()
    df['emg_rms_n'] = df['emg_rms']/df['emg_rms'].median()
    
    df['eeg_abs_mean_n2'] = df['eeg_abs_mean']/df['eeg_abs_mean'].mean()
    df['emg_abs_mean_n2'] = df['emg_abs_mean']/df['emg_abs_mean'].mean()
    df['eeg_abs_median_n2'] = df['eeg_abs_median']/df['eeg_abs_median'].mean()
    df['emg_abs_median_n2'] = df['emg_abs_median']/df['emg_abs_median'].mean()
    df['eeg_abs_max_n2'] = df['eeg_abs_max']/df['eeg_abs_max'].mean()
    df['emg_abs_max_n2'] = df['emg_abs_max']/df['emg_abs_max'].mean()
    df['eeg_abs_std_n2'] = df['eeg_abs_std']/df['eeg_abs_std'].mean()
    df['emg_abs_std_n2'] = df['emg_abs_std']/df['emg_abs_std'].mean()
    df['eeg_rms_n2'] = df['eeg_rms']/df['eeg_rms'].mean()
    df['emg_rms_n2'] = df['emg_rms']/df['emg_rms'].mean()
    
    # PSD
    print("get psd features")
    eeg_psd = get_epoch_psd(raw_data[eeg_no], sfreq=sfreq, epoch_len=epoch_len)
    
    df['eeg_delta'] = eeg_psd[0]
    df['eeg_theta'] = eeg_psd[1]
    df['eeg_alpha'] = eeg_psd[2]
    df['eeg_sigma'] = eeg_psd[3]
    df['eeg_beta'] = eeg_psd[4]
    df['eeg_gamma'] = eeg_psd[5]
    
    df['eeg_delta_n'] = df['eeg_delta']/df['eeg_delta'].median()
    df['eeg_theta_n'] = df['eeg_theta']/df['eeg_theta'].median()
    df['eeg_alpha_n'] = df['eeg_alpha']/df['eeg_alpha'].median()
    df['eeg_sigma_n'] = df['eeg_sigma']/df['eeg_sigma'].median()
    df['eeg_beta_n'] = df['eeg_beta']/df['eeg_beta'].median()
    df['eeg_gamma_n'] = df['eeg_gamma']/df['eeg_gamma'].median()
    
    df['eeg_delta_n2'] = df['eeg_delta']/df['eeg_delta'].mean()
    df['eeg_theta_n2'] = df['eeg_theta']/df['eeg_theta'].mean()
    df['eeg_alpha_n2'] = df['eeg_alpha']/df['eeg_alpha'].mean()
    df['eeg_sigma_n2'] = df['eeg_sigma']/df['eeg_sigma'].mean()
    df['eeg_beta_n2'] = df['eeg_beta']/df['eeg_beta'].mean()
    df['eeg_gamma_n2'] = df['eeg_gamma']/df['eeg_gamma'].mean()
                 
    df['eeg_theta_delta_ratio'] = df['eeg_theta']/df['eeg_delta']
    df['eeg_theta_delta_ratio_n'] = df['eeg_theta_n']/df['eeg_delta_n']
    df['eeg_theta_delta_ratio_n2'] = df['eeg_theta_n2']/df['eeg_delta_n2']
    
    df['eeg_alpha_delta_ratio'] = df['eeg_alpha']/df['eeg_delta']
    df['eeg_alpha_delta_ratio_n'] = df['eeg_alpha_n']/df['eeg_delta_n']
    df['eeg_alpha_delta_ratio_n2'] = df['eeg_alpha_n2']/df['eeg_delta_n2']
    
    df['eeg_sigma_delta_ratio'] = df['eeg_sigma']/df['eeg_delta']
    df['eeg_sigma_delta_ratio_n'] = df['eeg_sigma_n']/df['eeg_delta_n']
    df['eeg_sigma_delta_ratio_n2'] = df['eeg_sigma_n2']/df['eeg_delta_n2']
    
    df['eeg_beta_delta_ratio'] = df['eeg_beta']/df['eeg_delta']
    df['eeg_beta_delta_ratio_n'] = df['eeg_beta_n']/df['eeg_delta_n']
    df['eeg_beta_delta_ratio_n2'] = df['eeg_beta_n2']/df['eeg_delta_n2']
    
    df['eeg_gamma_delta_ratio'] = df['eeg_gamma']/df['eeg_delta']
    df['eeg_gamma_delta_ratio_n'] = df['eeg_gamma_n']/df['eeg_delta_n']
    df['eeg_gamma_delta_ratio_n2'] = df['eeg_gamma_n2']/df['eeg_delta_n2']
    
    # firwin band pass filter
    print("get firwin band passed features")
    raw_firwin_delta = raw.copy()
    raw_firwin_delta.filter(1, 4, fir_design='firwin')
    raw_firwin_delta_data = raw_firwin_delta.get_data()
    df['eeg_firwin_delta_abs_mean'] = get_epoch_abs_mean(raw_firwin_delta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_delta_abs_median'] = get_epoch_abs_median(raw_firwin_delta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_delta_abs_max'] = get_epoch_abs_max(raw_firwin_delta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_delta_abs_std'] = get_epoch_abs_std(raw_firwin_delta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_delta_rms'] = get_epoch_rms(raw_firwin_delta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_delta_abs_mean_n'] = df['eeg_firwin_delta_abs_mean']/df['eeg_firwin_delta_abs_mean'].median()
    df['eeg_firwin_delta_abs_median_n'] = df['eeg_firwin_delta_abs_median']/df['eeg_firwin_delta_abs_median'].median()
    df['eeg_firwin_delta_abs_max_n'] = df['eeg_firwin_delta_abs_max']/df['eeg_firwin_delta_abs_max'].median()
    df['eeg_firwin_delta_abs_std_n'] = df['eeg_firwin_delta_abs_std']/df['eeg_firwin_delta_abs_std'].median()
    df['eeg_firwin_delta_rms_n'] = df['eeg_firwin_delta_rms']/df['eeg_firwin_delta_rms'].median()
    df['eeg_firwin_delta_abs_mean_n2'] = df['eeg_firwin_delta_abs_mean']/df['eeg_firwin_delta_abs_mean'].mean()
    df['eeg_firwin_delta_abs_median_n2'] = df['eeg_firwin_delta_abs_median']/df['eeg_firwin_delta_abs_median'].mean()
    df['eeg_firwin_delta_abs_max_n2'] = df['eeg_firwin_delta_abs_max']/df['eeg_firwin_delta_abs_max'].mean()
    df['eeg_firwin_delta_abs_std_n2'] = df['eeg_firwin_delta_abs_std']/df['eeg_firwin_delta_abs_std'].mean()
    df['eeg_firwin_delta_rms_n2'] = df['eeg_firwin_delta_rms']/df['eeg_firwin_delta_rms'].mean()
    del raw_firwin_delta
    del raw_firwin_delta_data
    
    raw_firwin_theta = raw.copy()
    raw_firwin_theta.filter(4, 8, fir_design='firwin')
    raw_firwin_theta_data = raw_firwin_theta.get_data()
    df['eeg_firwin_theta_abs_mean'] = get_epoch_abs_mean(raw_firwin_theta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_theta_abs_median'] = get_epoch_abs_median(raw_firwin_theta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_theta_abs_max'] = get_epoch_abs_max(raw_firwin_theta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_theta_abs_std'] = get_epoch_abs_std(raw_firwin_theta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_theta_rms'] = get_epoch_rms(raw_firwin_theta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_theta_abs_mean_n'] = df['eeg_firwin_theta_abs_mean']/df['eeg_firwin_theta_abs_mean'].median()
    df['eeg_firwin_theta_abs_median_n'] = df['eeg_firwin_theta_abs_median']/df['eeg_firwin_theta_abs_median'].median()
    df['eeg_firwin_theta_abs_max_n'] = df['eeg_firwin_theta_abs_max']/df['eeg_firwin_theta_abs_max'].median()
    df['eeg_firwin_theta_abs_std_n'] = df['eeg_firwin_theta_abs_std']/df['eeg_firwin_theta_abs_std'].median()
    df['eeg_firwin_theta_rms_n'] = df['eeg_firwin_theta_rms']/df['eeg_firwin_theta_rms'].median()
    df['eeg_firwin_theta_abs_mean_n2'] = df['eeg_firwin_theta_abs_mean']/df['eeg_firwin_theta_abs_mean'].mean()
    df['eeg_firwin_theta_abs_median_n2'] = df['eeg_firwin_theta_abs_median']/df['eeg_firwin_theta_abs_median'].mean()
    df['eeg_firwin_theta_abs_max_n2'] = df['eeg_firwin_theta_abs_max']/df['eeg_firwin_theta_abs_max'].mean()
    df['eeg_firwin_theta_abs_std_n2'] = df['eeg_firwin_theta_abs_std']/df['eeg_firwin_theta_abs_std'].mean()
    df['eeg_firwin_theta_rms_n2'] = df['eeg_firwin_theta_rms']/df['eeg_firwin_theta_rms'].mean()
    del raw_firwin_theta
    del raw_firwin_theta_data
    
    raw_firwin_alpha = raw.copy()
    raw_firwin_alpha.filter(8, 12, fir_design='firwin')
    raw_firwin_alpha_data = raw_firwin_alpha.get_data()
    df['eeg_firwin_alpha_abs_mean'] = get_epoch_abs_mean(raw_firwin_alpha_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_alpha_abs_median'] = get_epoch_abs_median(raw_firwin_alpha_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_alpha_abs_max'] = get_epoch_abs_max(raw_firwin_alpha_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_alpha_abs_std'] = get_epoch_abs_std(raw_firwin_alpha_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_alpha_rms'] = get_epoch_rms(raw_firwin_alpha_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_alpha_abs_mean_n'] = df['eeg_firwin_alpha_abs_mean']/df['eeg_firwin_alpha_abs_mean'].median()
    df['eeg_firwin_alpha_abs_median_n'] = df['eeg_firwin_alpha_abs_median']/df['eeg_firwin_alpha_abs_median'].median()
    df['eeg_firwin_alpha_abs_max_n'] = df['eeg_firwin_alpha_abs_max']/df['eeg_firwin_alpha_abs_max'].median()
    df['eeg_firwin_alpha_abs_std_n'] = df['eeg_firwin_alpha_abs_std']/df['eeg_firwin_alpha_abs_std'].median()
    df['eeg_firwin_alpha_rms_n'] = df['eeg_firwin_alpha_rms']/df['eeg_firwin_alpha_rms'].median()
    df['eeg_firwin_alpha_abs_mean_n2'] = df['eeg_firwin_alpha_abs_mean']/df['eeg_firwin_alpha_abs_mean'].mean()
    df['eeg_firwin_alpha_abs_median_n2'] = df['eeg_firwin_alpha_abs_median']/df['eeg_firwin_alpha_abs_median'].mean()
    df['eeg_firwin_alpha_abs_max_n2'] = df['eeg_firwin_alpha_abs_max']/df['eeg_firwin_alpha_abs_max'].mean()
    df['eeg_firwin_alpha_abs_std_n2'] = df['eeg_firwin_alpha_abs_std']/df['eeg_firwin_alpha_abs_std'].mean()
    df['eeg_firwin_alpha_rms_n2'] = df['eeg_firwin_alpha_rms']/df['eeg_firwin_alpha_rms'].mean()
    del raw_firwin_alpha
    del raw_firwin_alpha_data
    
    raw_firwin_sigma = raw.copy()
    raw_firwin_sigma.filter(12, 15, fir_design='firwin')
    raw_firwin_sigma_data = raw_firwin_sigma.get_data()
    df['eeg_firwin_sigma_abs_mean'] = get_epoch_abs_mean(raw_firwin_sigma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_sigma_abs_median'] = get_epoch_abs_median(raw_firwin_sigma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_sigma_abs_max'] = get_epoch_abs_max(raw_firwin_sigma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_sigma_abs_std'] = get_epoch_abs_std(raw_firwin_sigma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_sigma_rms'] = get_epoch_rms(raw_firwin_sigma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_sigma_abs_mean_n'] = df['eeg_firwin_sigma_abs_mean']/df['eeg_firwin_sigma_abs_mean'].median()
    df['eeg_firwin_sigma_abs_median_n'] = df['eeg_firwin_sigma_abs_median']/df['eeg_firwin_sigma_abs_median'].median()
    df['eeg_firwin_sigma_abs_max_n'] = df['eeg_firwin_sigma_abs_max']/df['eeg_firwin_sigma_abs_max'].median()
    df['eeg_firwin_sigma_abs_std_n'] = df['eeg_firwin_sigma_abs_std']/df['eeg_firwin_sigma_abs_std'].median()
    df['eeg_firwin_sigma_rms_n'] = df['eeg_firwin_sigma_rms']/df['eeg_firwin_sigma_rms'].median()
    df['eeg_firwin_sigma_abs_mean_n2'] = df['eeg_firwin_sigma_abs_mean']/df['eeg_firwin_sigma_abs_mean'].mean()
    df['eeg_firwin_sigma_abs_median_n2'] = df['eeg_firwin_sigma_abs_median']/df['eeg_firwin_sigma_abs_median'].mean()
    df['eeg_firwin_sigma_abs_max_n2'] = df['eeg_firwin_sigma_abs_max']/df['eeg_firwin_sigma_abs_max'].mean()
    df['eeg_firwin_sigma_abs_std_n2'] = df['eeg_firwin_sigma_abs_std']/df['eeg_firwin_sigma_abs_std'].mean()
    df['eeg_firwin_sigma_rms_n2'] = df['eeg_firwin_sigma_rms']/df['eeg_firwin_sigma_rms'].mean()
    del raw_firwin_sigma
    del raw_firwin_sigma_data
    
    raw_firwin_beta = raw.copy()
    raw_firwin_beta.filter(15, 30, fir_design='firwin')
    raw_firwin_beta_data = raw_firwin_beta.get_data()
    df['eeg_firwin_beta_abs_mean'] = get_epoch_abs_mean(raw_firwin_beta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_beta_abs_median'] = get_epoch_abs_median(raw_firwin_beta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_beta_abs_max'] = get_epoch_abs_max(raw_firwin_beta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_beta_abs_std'] = get_epoch_abs_std(raw_firwin_beta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_beta_rms'] = get_epoch_rms(raw_firwin_beta_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_beta_abs_mean_n'] = df['eeg_firwin_beta_abs_mean']/df['eeg_firwin_beta_abs_mean'].median()
    df['eeg_firwin_beta_abs_median_n'] = df['eeg_firwin_beta_abs_median']/df['eeg_firwin_beta_abs_median'].median()
    df['eeg_firwin_beta_abs_max_n'] = df['eeg_firwin_beta_abs_max']/df['eeg_firwin_beta_abs_max'].median()
    df['eeg_firwin_beta_abs_std_n'] = df['eeg_firwin_beta_abs_std']/df['eeg_firwin_beta_abs_std'].median()
    df['eeg_firwin_beta_rms_n'] = df['eeg_firwin_beta_rms']/df['eeg_firwin_beta_rms'].median()
    df['eeg_firwin_beta_abs_mean_n2'] = df['eeg_firwin_beta_abs_mean']/df['eeg_firwin_beta_abs_mean'].mean()
    df['eeg_firwin_beta_abs_median_n2'] = df['eeg_firwin_beta_abs_median']/df['eeg_firwin_beta_abs_median'].mean()
    df['eeg_firwin_beta_abs_max_n2'] = df['eeg_firwin_beta_abs_max']/df['eeg_firwin_beta_abs_max'].mean()
    df['eeg_firwin_beta_abs_std_n2'] = df['eeg_firwin_beta_abs_std']/df['eeg_firwin_beta_abs_std'].mean()
    df['eeg_firwin_beta_rms_n2'] = df['eeg_firwin_beta_rms']/df['eeg_firwin_beta_rms'].mean()
    del raw_firwin_beta
    del raw_firwin_beta_data

    raw_firwin_gamma = raw.copy()
    raw_firwin_gamma.filter(30, 100, fir_design='firwin')
    raw_firwin_gamma_data = raw_firwin_gamma.get_data()
    df['eeg_firwin_gamma_abs_mean'] = get_epoch_abs_mean(raw_firwin_gamma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_gamma_abs_median'] = get_epoch_abs_median(raw_firwin_gamma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_gamma_abs_max'] = get_epoch_abs_max(raw_firwin_gamma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_gamma_abs_std'] = get_epoch_abs_std(raw_firwin_gamma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_gamma_rms'] = get_epoch_rms(raw_firwin_gamma_data[0], sfreq=sfreq, epoch_len=epoch_len)
    df['eeg_firwin_gamma_abs_mean_n'] = df['eeg_firwin_gamma_abs_mean']/df['eeg_firwin_gamma_abs_mean'].median()
    df['eeg_firwin_gamma_abs_median_n'] = df['eeg_firwin_gamma_abs_median']/df['eeg_firwin_gamma_abs_median'].median()
    df['eeg_firwin_gamma_abs_max_n'] = df['eeg_firwin_gamma_abs_max']/df['eeg_firwin_gamma_abs_max'].median()
    df['eeg_firwin_gamma_abs_std_n'] = df['eeg_firwin_gamma_abs_std']/df['eeg_firwin_gamma_abs_std'].median()
    df['eeg_firwin_gamma_rms_n'] = df['eeg_firwin_gamma_rms']/df['eeg_firwin_gamma_rms'].median()
    df['eeg_firwin_gamma_abs_mean_n2'] = df['eeg_firwin_gamma_abs_mean']/df['eeg_firwin_gamma_abs_mean'].mean()
    df['eeg_firwin_gamma_abs_median_n2'] = df['eeg_firwin_gamma_abs_median']/df['eeg_firwin_gamma_abs_median'].mean()
    df['eeg_firwin_gamma_abs_max_n2'] = df['eeg_firwin_gamma_abs_max']/df['eeg_firwin_gamma_abs_max'].mean()
    df['eeg_firwin_gamma_abs_std_n2'] = df['eeg_firwin_gamma_abs_std']/df['eeg_firwin_gamma_abs_std'].mean()
    df['eeg_firwin_gamma_rms_n2'] = df['eeg_firwin_gamma_rms']/df['eeg_firwin_gamma_rms'].mean()
    del raw_firwin_gamma
    del raw_firwin_gamma_data

    df['epoch_id'] = file_firstname + '___' + df.index.astype('str')
    df['subject_id'] = file_firstname
    df['score'] = score_list
    df.to_csv(f"{edf_folderpath}{file_firstname}_{model_name}_epoch_length_{epoch_len}_sec_features.csv")
    

def make_prediction (X, y_truth, model):
    # y_prediction_prob = model.predict_proba(X)
    # y_prediction = np.zeros(y_prediction_prob[:,0].shape)
    # y_prediction = y_prediction.astype('str')
    # y_prediction[y_prediction_prob[:,0] > 1/3] = 'nrem'
    # y_prediction[y_prediction_prob[:,2] > 1/3] = 'wake'
    # y_prediction[y_prediction_prob[:,1] > param['rem_threshold']] = 'rem'
    y_prediction = model.predict(X)
    report = classification_report(y_truth, y_prediction)
    printW(report)
    return y_prediction


def get_shap (df, features, model):
    explainer = shap.TreeExplainer(model)
    df_500samples = df.sample(500)
    indices_500samples = df_500samples.index.values
    shap_values_500samples = explainer.shap_values(df_500samples[features])
    return explainer, shap_values_500samples, indices_500samples


def extract_features_from_raw(raw_edf, epoch_len=4, model_name="2_LightGBM-1EEG", save_path=None, emg_channel=None, eeg_channel=None):

    try:
        # 获取采样率
        sfreq = int(raw_edf.info["sfreq"])
        
        # 获取通道名称
        ch_names = raw_edf.info["ch_names"]
        print("Available channels:", ch_names)  # 打印可用通道
        
        # 使用指定的通道
        if emg_channel is None:
            emg_channel = ch_names[1]  # 默认使用第二个通道作为EMG
        if eeg_channel is None:
            eeg_channel = ch_names[2]  # 默认使用第三个通道作为EEG

        # Apply bandpass filter to the entire raw data
        start_time = time.time()
        raw_edf.filter(1., 40., fir_design='firwin')  # 1秒多
        end_time = time.time()
        print(f"extract_features_from_raw需要消耗的时间：{end_time - start_time}")

        # raw_edf = parallel_filter(raw_edf)

        print(raw_edf)

        # Apply highpass filter to the EMG channel
        raw_highpass = raw_edf.copy()
        raw_highpass.pick_channels([emg_channel])
        raw_highpass.filter(l_freq=20., h_freq=None, fir_design='firwin')

        # Replace the EMG channel data with the filtered data
        raw_edf._data[raw_edf.ch_names.index(emg_channel)] = raw_highpass.get_data()[0]
        del raw_highpass
        
        # 根据模型选择通道数
        if "2EEG" in model_name:
            # 获取数据
            emg_data = raw_edf.get_data(picks=emg_channel) * 1e-6
            eeg1_data = raw_edf.get_data(picks=eeg_channel1) * 1e-6
            eeg2_data = raw_edf.get_data(picks=eeg_channel2) * 1e-6
            
            # 提取特征
            features = {
                # EEG1特征
                'eeg1_abs_mean': get_epoch_abs_mean(eeg1_data[0], sfreq, epoch_len),
                'eeg1_abs_median': get_epoch_abs_median(eeg1_data[0], sfreq, epoch_len),
                'eeg1_abs_std': get_epoch_abs_std(eeg1_data[0], sfreq, epoch_len),
                'eeg1_abs_max': get_epoch_abs_max(eeg1_data[0], sfreq, epoch_len),
                'eeg1_rms': get_epoch_rms(eeg1_data[0], sfreq, epoch_len),
                
                # EEG2特征
                'eeg2_abs_mean': get_epoch_abs_mean(eeg2_data[0], sfreq, epoch_len),
                'eeg2_abs_median': get_epoch_abs_median(eeg2_data[0], sfreq, epoch_len),
                'eeg2_abs_std': get_epoch_abs_std(eeg2_data[0], sfreq, epoch_len),
                'eeg2_abs_max': get_epoch_abs_max(eeg2_data[0], sfreq, epoch_len),
                'eeg2_rms': get_epoch_rms(eeg2_data[0], sfreq, epoch_len),
                
                # EMG特征
                'emg_abs_mean': get_epoch_abs_mean(emg_data[0], sfreq, epoch_len),
                'emg_abs_median': get_epoch_abs_median(emg_data[0], sfreq, epoch_len),
                'emg_abs_std': get_epoch_abs_std(emg_data[0], sfreq, epoch_len),
                'emg_abs_max': get_epoch_abs_max(emg_data[0], sfreq, epoch_len),
                'emg_rms': get_epoch_rms(emg_data[0], sfreq, epoch_len),
            }
            
            # EEG1频段功率
            eeg1_psd = get_epoch_psd(eeg1_data[0], sfreq, epoch_len)
            for i, band in enumerate(['delta', 'theta', 'alpha', 'sigma', 'beta', 'gamma']):
                features[f'eeg1_{band}'] = eeg1_psd[i]
                
            # EEG2频段功率
            eeg2_psd = get_epoch_psd(eeg2_data[0], sfreq, epoch_len)
            for i, band in enumerate(['delta', 'theta', 'alpha', 'sigma', 'beta', 'gamma']):
                features[f'eeg2_{band}'] = eeg2_psd[i]
                
        else:  # 1EEG模型
            # 获取数据
            emg_data = raw_edf.get_data(picks=emg_channel) * 1e-6
            eeg_data = raw_edf.get_data(picks=eeg_channel) * 1e-6  # 使用第一个EEG通道
            
            # 创建一个字典来存储所有特征
            feature_dict = {}
            
            # 基本特征
            base_features = {
                'eeg_abs_mean': get_epoch_abs_mean(eeg_data[0], sfreq, epoch_len),
                'eeg_abs_median': get_epoch_abs_median(eeg_data[0], sfreq, epoch_len),
                'eeg_abs_std': get_epoch_abs_std(eeg_data[0], sfreq, epoch_len),
                'eeg_abs_max': get_epoch_abs_max(eeg_data[0], sfreq, epoch_len),
                'eeg_rms': get_epoch_rms(eeg_data[0], sfreq, epoch_len),
                
                'emg_abs_mean': get_epoch_abs_mean(emg_data[0], sfreq, epoch_len),
                'emg_abs_median': get_epoch_abs_median(emg_data[0], sfreq, epoch_len),
                'emg_abs_std': get_epoch_abs_std(emg_data[0], sfreq, epoch_len),
                'emg_abs_max': get_epoch_abs_max(emg_data[0], sfreq, epoch_len),
                'emg_rms': get_epoch_rms(emg_data[0], sfreq, epoch_len),
            }
            feature_dict.update(base_features)
            
            # 添加归一化特征
            for base_col in base_features.keys():
                feature_dict[f'{base_col}_n'] = base_features[base_col] / np.median(base_features[base_col])
                feature_dict[f'{base_col}_n2'] = base_features[base_col] / np.mean(base_features[base_col])
            
            # EEG频段功率特征
            eeg_psd = get_epoch_psd(eeg_data[0], sfreq, epoch_len)
            bands = ['delta', 'theta', 'alpha', 'sigma', 'beta', 'gamma']
            
            for i, band in enumerate(bands):
                band_power = eeg_psd[i]
                feature_dict[f'eeg_{band}'] = band_power
                feature_dict[f'eeg_{band}_n'] = band_power / np.median(band_power)
                feature_dict[f'eeg_{band}_n2'] = band_power / np.mean(band_power)
            
            # 频段比率特征
            ratios = ['theta', 'alpha', 'sigma', 'beta', 'gamma']
            for ratio in ratios:
                feature_dict[f'eeg_{ratio}_delta_ratio'] = feature_dict[f'eeg_{ratio}'] / feature_dict['eeg_delta']
                feature_dict[f'eeg_{ratio}_delta_ratio_n'] = feature_dict[f'eeg_{ratio}_n'] / feature_dict['eeg_delta_n']
                feature_dict[f'eeg_{ratio}_delta_ratio_n2'] = feature_dict[f'eeg_{ratio}_n2'] / feature_dict['eeg_delta_n2']
            
            # Firwin特征
            freq_ranges = {
                'delta': (1, 4),
                'theta': (4, 8),
                'alpha': (8, 12),
                'sigma': (12, 15),
                'beta': (15, 30),
                'gamma': (30, 40)
            }
            
            for band in bands:
                raw_firwin = raw_edf.copy()
                l_freq, h_freq = freq_ranges[band]
                raw_firwin.filter(l_freq, h_freq, fir_design='firwin')
                raw_firwin_data = raw_firwin.get_data(picks=eeg_channel) * 1e-6
                
                base_name = f'eeg_firwin_{band}'
                metrics = {
                    'abs_mean': get_epoch_abs_mean,
                    'abs_median': get_epoch_abs_median,
                    'abs_max': get_epoch_abs_max,
                    'abs_std': get_epoch_abs_std,
                    'rms': get_epoch_rms
                }
                
                for metric_name, metric_func in metrics.items():
                    base_value = metric_func(raw_firwin_data[0], sfreq, epoch_len)
                    col = f'{base_name}_{metric_name}'
                    feature_dict[col] = base_value
                    feature_dict[f'{col}_n'] = base_value / np.median(base_value)
                    feature_dict[f'{col}_n2'] = base_value / np.mean(base_value)
                
                del raw_firwin
                del raw_firwin_data
            
            # 一次性创建DataFrame
            df = pd.DataFrame(feature_dict)
            
            # 确保特征顺序与原始模型训练时一致
            expected_features = pd.read_csv(os.path.join(os.path.dirname(__file__), "models", "feature_order.csv"),
                                          header=None, names=['feature'])
            feature_list = expected_features['feature'].str.strip().tolist()
            
            # 检查特征
            missing_features = set(feature_list) - set(df.columns)
            if missing_features:
                raise ValueError(f"Missing features: {missing_features}")
            
            # 按照预期顺序重排列特征
            df = df[feature_list]

            df.index = range(len(df))
            
            # 保存降采样数据和特征
            # if save_path is not None:
            #     # 保存降采样数据
            #     raw_100hz = raw_edf.copy()
            #     raw_100hz.resample(sfreq=100)
            #     resampled_data = raw_100hz.get_data() * 1e-6
            #     # np.save(os.path.join(save_path, f"{model_name}_rs_100hz.npy"), resampled_data)
            #     np.save(os.path.join(save_path, f"epoch_length_{epoch_len}_sec_rs_100hz.npy"), resampled_data)
                
                # 保存特征
                # df.to_csv(os.path.join(save_path, f"{model_name}_epoch_length_{epoch_len}_sec_features.csv"), index=False)
            # df.to_csv(os.path.join(save_path, f"epoch_length_{epoch_len}_sec_features.csv"), index=True)
            
            return df
            
    except Exception as e:
        print(f"Error in extract_features_from_raw: {str(e)}")
        raise


def filter_channel_group(args):
    """对一组通道进行滤波的辅助函数"""
    raw_chunk, l_freq, h_freq, fir_design = args
    return raw_chunk.filter(l_freq, h_freq, fir_design=fir_design, n_jobs=1)  # 单线程内不并行
def parallel_filter(raw, l_freq=1.0, h_freq=40.0, fir_design='firwin', n_threads=None):
    """多线程并行滤波"""
    if n_threads is None:
        n_threads = min(4, len(raw.ch_names))  # 默认使用4个线程或通道数，取较小值

    print(n_threads)

    # 分组通道（示例：按通道类型分组）
    channel_types = raw.get_channel_types()
    unique_types = set(channel_types)

    # 创建通道组
    channel_groups = []
    for ch_type in unique_types:
        picks = mne.pick_types(raw.info, **{ch_type: True})
        if picks:  # 确保组非空
            raw_group = raw.copy().pick_channels([raw.ch_names[i] for i in picks])
            channel_groups.append(raw_group)

    # 分配任务到线程池
    with ThreadPoolExecutor(max_workers=n_threads) as executor:
        args_list = [(group, l_freq, h_freq, fir_design) for group in channel_groups]
        filtered_groups = list(executor.map(filter_channel_group, args_list))

    # 合并结果
    if len(filtered_groups) == 1:
        return filtered_groups[0]
    else:
        return mne.io.concatenate_raws(filtered_groups)


# def get_epoch_abs_mean(full_single_trace, sfreq, epoch_len=None):
#     epoch_length = int(epoch_len * sfreq)
#     n_epochs = len(full_single_trace) // epoch_length
#
#     # Reshape data into epochs and calculate abs mean for each epoch
#     reshaped_data = full_single_trace[:n_epochs * epoch_length].reshape(n_epochs, epoch_length)
#     output = np.abs(reshaped_data).mean(axis=1)
#
#     return output
#
#
# def get_epoch_abs_median(full_single_trace, sfreq, epoch_len=None):
#     epoch_length = int(epoch_len * sfreq)
#     n_epochs = len(full_single_trace) // epoch_length
#
#     # Reshape data into epochs and calculate abs median for each epoch
#     reshaped_data = full_single_trace[:n_epochs * epoch_length].reshape(n_epochs, epoch_length)
#     output = np.median(np.abs(reshaped_data), axis=1)
#
#     return output
#
#
# def get_epoch_abs_max(full_single_trace, sfreq, epoch_len=None):
#     epoch_length = int(epoch_len * sfreq)
#     n_epochs = len(full_single_trace) // epoch_length
#
#     # Reshape data into epochs and calculate abs max for each epoch
#     reshaped_data = full_single_trace[:n_epochs * epoch_length].reshape(n_epochs, epoch_length)
#     output = np.abs(reshaped_data).max(axis=1)
#
#     return output
#
#
# def get_epoch_abs_std(full_single_trace, sfreq, epoch_len=None):
#     epoch_length = int(epoch_len * sfreq)
#     n_epochs = len(full_single_trace) // epoch_length
#
#     # Reshape data into epochs and calculate abs std for each epoch
#     reshaped_data = full_single_trace[:n_epochs * epoch_length].reshape(n_epochs, epoch_length)
#     output = np.abs(reshaped_data).std(axis=1)
#
#     return output
#
# # def rmsValue(arr):
# #     return np.sqrt(np.mean(np.square(arr), dtype=np.float64))
#
#
# def get_epoch_rms(full_single_trace, sfreq, epoch_len=None):
#     epoch_length = int(epoch_len * sfreq)
#     n_epochs = len(full_single_trace) // epoch_length
#
#     # Reshape data into epochs and calculate RMS for each epoch
#     reshaped_data = full_single_trace[:n_epochs * epoch_length].reshape(n_epochs, epoch_length)
#     output = np.sqrt(np.mean(np.square(reshaped_data), axis=1,dtype=np.float64))
#
#     return output