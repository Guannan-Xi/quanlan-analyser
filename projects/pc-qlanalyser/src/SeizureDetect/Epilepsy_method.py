import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QFileDialog
import numpy as np
import warnings
# 屏蔽所有警告
warnings.filterwarnings("ignore")
from tqdm import tqdm
from .Model import SVMModel
from .Data import DataLoader, DataFeature
import mne
import pandas as pd
from datetime import datetime
#raw = mne.io.read_raw_edf(r'C:\Users\evian\Desktop\QL\m010001_r_labeled_edited.edf', preload=True, verbose=False)
#raw.crop(tmin=0, tmax=1000)

def Epilepsy_method(raw,epochlength):


    # 使用示例
    parquet_path = r'src\SeizureDetect\m010001_r_labeled_edited_dataset.parquet'
    model_save_path = r"src\SeizureDetect\Pkl\model_bandpower.pkl"

    dataloader = DataLoader(parquet_path=parquet_path)
    data, labels,channel_names, sample_rate = dataloader.get_data()

    # 创建 SVMModel 实例
    svm_model = SVMModel()

    # 加载训练好的模型
    loaded_model = svm_model.eval(model_save_path)


    # 读取EDF文件并进行滤波
    #edf_file_path = r'C:\Users\evian\Desktop\QL\ExampleData\ECG\10248\10248.edf'
    #raw = mne.io.read_raw_edf(edf_file_path, preload=True)
    raw.filter(0.5, 35)

    sample_rate = int(raw.info['sfreq'])
    new_data = raw.get_data()

   # # 计算前1000秒对应的样本数
   # num_samples = 100 * sample_rate

   # # 提取前1000秒的数据
   # new_data = new_data[:, :num_samples]
    # # 提取前1000秒的数据
    # new_data = new_data[:,:]

    # 每3秒对应的采样点数
    segment_length = 3 * sample_rate
    step_size = int(0.5*segment_length)  # 滑动窗口的步长，1秒对应sample_rate个数据点

    # 创建与new_data等长的布尔数组
    pred_bool_array = np.zeros(len(new_data[0]), dtype=bool)

    # 初始化DataFeature对象
    data_feature = DataFeature(sample_rate)

    # 初始化布尔数组，长度为new_data[0]的长度
    pred_bool_array = np.zeros(len(new_data[0]), dtype=bool)

    # 预先计算步数
    num_steps = (len(new_data[0]) - segment_length + 1) // step_size

    # 提前定义组合段的形状
    combined_segment_shape = (1, 2 * segment_length)

    # 使用tqdm显示进度条
    for step in tqdm(range(num_steps), desc="Processing segments"):
        start_index = step * step_size
        end_index = start_index + segment_length
        segment1 = new_data[0, start_index:end_index]
        segment2 = new_data[1, start_index:end_index]

        # 组合两个段并reshape
        combined_segment = np.concatenate((segment1, segment2)).reshape(combined_segment_shape)

        # 提取特征并进行预测
        X_predict = data_feature.get_features(combined_segment)
        prediction = svm_model.predict(X_predict)

        # 将预测结果填充到布尔数组中
        if prediction == 1:
            pred_bool_array[start_index:end_index] = True

    # 确保布尔数组长度与原始数据长度相同
    pred_bool_array = pred_bool_array[:len(new_data[0])]
  
   # print("预测完成，布尔数组长度:", len(pred_bool_array))

    print(f"end_analysis_time:{datetime.now()}\n")       
    epoch_length = epochlength * sample_rate
    epoch_bool_array = np.zeros(len(pred_bool_array) // epoch_length, dtype=bool)

    
    for i in range(len(epoch_bool_array)):
        start_index = i * epoch_length
        end_index = start_index + epoch_length
        segment = pred_bool_array[start_index:end_index]
        epoch_bool_array[i] = np.sum(segment) > (epoch_length / 2)

   # print("Epoch布尔数组:", epoch_bool_array)

    annotations_df = pd.DataFrame(pred_bool_array, columns=['Predicted Annotation'])
    epoch_annotations_df = pd.DataFrame(epoch_bool_array, columns=['Epoch Annotation'])

    epoch_int_array = epoch_bool_array.astype(int)
    return epoch_int_array

