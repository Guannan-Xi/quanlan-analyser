import os
import mne
import mat73
import numpy as np
import pandas as pd

from Data import DataLoader
from scipy.io import loadmat
from scipy.stats import mode
from scipy import signal
# dataset: https://ieee-dataport.org/open-access/eeg-genetic-absence-epilepsy-rats-gaers
# dataloader = DataLoader
data_path = r"E:\data\Data GAERS\Day3\Day3"
sample_rate = 1600

# anno 
# annotation_dir = r"E:\data\ClassifiedGAERSdata\ClassifiedGAERSdata\R3_Data\R3_Data"
# result_all = []
# data_csv = pd.DataFrame()
# for anno_file in sorted(os.listdir(annotation_dir), key=lambda x: int((x.split('_')[3]).split('-')[0])):
#     print(anno_file)
#     anno_file_name = os.path.join(annotation_dir, anno_file, f'{anno_file}.txt')
#     anno = np.loadtxt(anno_file_name)[:, 0]
#     anno = anno.reshape(-1, sample_rate)
#     most_common_values = mode(anno, axis=1).mode
#     result_array = most_common_values.flatten()
#     result_all = np.concatenate([result_all, result_array])

# data_csv['annotation'] = result_all
# data_csv.to_csv(f'E:\data\R3.csv', index=True)



# data
sample_rate = 1600
data_path = r"E:\data\Data GAERS\Day3\Day3\R1.mat"
data_R1 = mat73.loadmat(data_path)['raw_data'].T

data_R1_0 = data_R1[0, :]
# data_R1_1 = data_R1[1, :]
# data_R1_2 = data_R1[2, :]
# data_R1_0 = signal.resample(data_R1_0, len(data_R1_0)//16)
data_R1_0 = DataLoader.slice_data_1s(data_R1_0, sample_rate)
# data_R1_1 = DataLoader.slice_data_1s(data_R1_1, sample_rate)
# data_R1_2 = DataLoader.slice_data_1s(data_R1_2, sample_rate)

# data_R1 = pd.concat([data_R1_0.iloc[60*60:1200*60, :], data_R1_1.iloc[60*60:1200*60, :], data_R1_2.iloc[60*60:1200*60, :]])

data_path = r"E:\data\Data GAERS\Day3\Day3\R2.mat"
data_R2 = mat73.loadmat(data_path)['raw_data'].T

data_R2_0 = data_R2[0, :]
# data_R2_1 = data_R2[1, :]
# data_R2_2 = data_R2[2, :]
# data_R2_0 = signal.resample(data_R2_0, len(data_R2_0)//16)

data_R2_0 = DataLoader.slice_data_1s(data_R2_0, sample_rate)
# data_R2_1 = DataLoader.slice_data_1s(data_R2_1, sample_rate)
# data_R2_2 = DataLoader.slice_data_1s(data_R2_2, sample_rate)
# data_R2 = pd.concat([data_R2_0.iloc[60*60:1200*60, :], data_R2_1.iloc[60*60:1200*60, :], data_R2_2.iloc[60*60:1200*60, :]])

data_path = r"E:\data\Data GAERS\Day3\Day3\R3.mat"
data_R3 = mat73.loadmat(data_path)['raw_data'].T

data_R3_0 = data_R3[0, :]
# data_R3_1 = data_R3[1, :]
# data_R3_2 = data_R3[2, :]
# data_R3_0 = signal.resample(data_R3_0, len(data_R3_0)//16)

data_R3_0 = DataLoader.slice_data_1s(data_R3_0, sample_rate)
# data_R3_1 = DataLoader.slice_data_1s(data_R3_1, sample_rate)
# data_R3_2 = DataLoader.slice_data_1s(data_R3_2, sample_rate)

# data_R3 = pd.concat([data_R3_0.iloc[60*60:780*60, :], data_R3_1.iloc[60*60:780*60, :], data_R3_2.iloc[60*60:780*60, :]])


# data_R = pd.concat([data_R1, data_R2, data_R3], axis=0)
data_R = pd.concat([data_R1_0.iloc[60*60:1200*60, :], data_R2_0.iloc[60*60:1200*60, :], data_R3_0.iloc[60*60:780*60, :]], axis=0)
# data_R = data_R.fillna(0)
# data_R = data_R.values
np.save("E:\data\R.npy", data_R)
# data_R.to_csv("E:\data\R.csv", index=False)

# data = np.load("E:\data\R.npy")
# # mne.filter.resample(data, 1600)
# cols = 1600
# data = data[:, np.linspace(0, cols-1, 100, dtype=int)]
# np.save("E:\data\R_resample.csv", data)

anno_R1 = pd.read_csv("E:\data\R1.csv")
anno_R2 = pd.read_csv("E:\data\R2.csv")
anno_R3 = pd.read_csv("E:\data\R3.csv")
anno = pd.concat([anno_R1, anno_R2, anno_R3], axis=0)
anno = anno.iloc[:, 1]
anno = anno.values
np.save("E:\data\anno.npy", anno)