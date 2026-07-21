# -*- coding: utf-8 -*-
from typing import List, Tuple, Optional, Dict
from scipy import signal
import os
import logging
import datetime
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import joblib
from sklearn.preprocessing import StandardScaler,MinMaxScaler
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, confusion_matrix, ConfusionMatrixDisplay,
                             roc_curve, auc, precision_recall_curve)
from imblearn.over_sampling import SMOTE
from lightgbm import LGBMClassifier
import mne
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.colors import TwoSlopeNorm
from matplotlib.ticker import FuncFormatter
from tqdm import tqdm
import numpy as np
from scipy.signal import butter, filtfilt
# 设置支持中文的字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows上的黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号 '-' 显示为方块的问题
# 设置日志配置
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# -------------------- 数据处理函数 --------------------

def read_edf_file(edf_file_path: str, filter_range: Tuple[float, float] = (1, 35),
                  start_time: Optional[List[int]] = None,
                  end_time: Optional[List[int]] = None) -> mne.io.Raw:
    """
    读取EDF文件，应用滤波，并裁剪到指定的时间范围。
    """
    try:
        raw = mne.io.read_raw_edf(edf_file_path, preload=True)
        raw._data *= 1e6  # 转换为微伏
        raw.filter(filter_range[0], filter_range[1])
        raw.notch_filter(freqs=50)

        meas_date = raw.info['meas_date']

        if meas_date is None:
            logging.warning("数据中没有可用的测量日期，使用当前时间作为测量日期。")
            meas_date = datetime.datetime.now()

        if isinstance(meas_date, (tuple, list)):
            meas_timestamp = meas_date[0] + meas_date[1] * 1e-6
            meas_date = datetime.datetime.fromtimestamp(meas_timestamp)
        elif isinstance(meas_date, datetime.datetime):
            meas_date = meas_date.replace(tzinfo=None)
        elif isinstance(meas_date, float):
            meas_date = datetime.datetime.fromtimestamp(meas_date)
        else:
            raise TypeError(f"无法解析 meas_date 的类型：{type(meas_date)}")

        data_duration = raw.times[-1]  # 数据总时长（秒）
        data_end_time = meas_date + datetime.timedelta(seconds=data_duration)

        logging.info(f"数据起始时间：{meas_date}")
        logging.info(f"数据结束时间：{data_end_time}")

        # 处理起始和结束时间
        tmin = 0
        tmax = data_duration

        if start_time is not None:
            start_time_dt = datetime.datetime(*start_time)
            if not (meas_date <= start_time_dt <= data_end_time):
                raise ValueError("起始时间不在数据的时间范围内。")
            tmin = (start_time_dt - meas_date).total_seconds()

        if end_time is not None:
            end_time_dt = datetime.datetime(*end_time)
            if not (meas_date <= end_time_dt <= data_end_time):
                raise ValueError("结束时间不在数据的时间范围内。")
            tmax = (end_time_dt - meas_date).total_seconds()

        if tmin > tmax:
            raise ValueError("起始时间不能晚于结束时间。")

        raw.crop(tmin=tmin, tmax=tmax)

        return raw
    except Exception as e:
        logging.exception(f"读取EDF文件时出错: {e}")
        raise e




def find_edf_files(directory: str, device: str = 'DSI') -> List[str]:
    """
    查找指定目录下的.edf文件。
    """
    edf_files = []
    try:
        for root, _, files in os.walk(directory):
            for file in files:
                if device == 'DSI' and "repaired" in file and file.endswith('.edf'):
                    edf_files.append(os.path.join(root, file))
                elif device == 'AR4' and file.endswith('.edf'):
                    edf_files.append(os.path.join(root, file))
    except Exception as e:
        logging.exception(f"查找EDF文件时出错: {e}")
    return edf_files


# -------------------- 特征提取函数 --------------------

def extract_features_using_epochs(data_segment: np.ndarray, fs: int = 256,
                                  fmin: float = 0.5, fmax: float = 40) -> np.ndarray:
    """
    使用 epoch 提取特征，包括各频段功率占比、RMS、绝对值和。
    """
    try:
        n_epochs, n_channels, n_times = data_segment.shape

        # 创建 MNE info 对象
        info = mne.create_info([f'Channel_{i + 1}' for i in range(n_channels)], sfreq=fs, ch_types='eeg')
        epochs = mne.EpochsArray(data_segment, info)

        # 计算 PSD
        psd, freqs = epochs.compute_psd(fmin=fmin, fmax=fmax, n_jobs=-1).get_data(return_freqs=True)
        # 对 PSD 取对数
        psd = 10*np.log(psd + 1e-10)  # 加一个小常数避免对 0 取对数

        # 定义频段
        bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 13),
            'seizureIDX': (13, 16),
            # 'gamma': (30, 40)  # 可根据需求调整 gamma 上限
        }

        # 假设已定义的变量
        # n_epochs: 试验次数
        # n_channels: 通道数量
        # freqs: 频率数组，例如从0.5Hz到40Hz
        # psd: 功率谱密度数组，形状为 (n_epochs, n_channels, n_freqs)

        # 初始化数组存储频段总功率和每Hz功率
        band_psd = np.zeros((n_epochs, n_channels, len(bands)))
        band_psd_per_hz = np.zeros((n_epochs, n_channels, len(bands)))

        # 计算每个频段的总功率和每Hz功率
        for idx, (_, (low, high)) in enumerate(bands.items()):
            # 创建频段掩码
            band_mask = (freqs >= low) & (freqs < high)

            # 计算频段总功率
            band_psd[:, :, idx] = np.sum(psd[:, :, band_mask], axis=2)

            # 计算频段带宽
            band_width = high - low

            # 计算每Hz的平均功率
            band_psd_per_hz[:, :, idx] = band_psd[:, :, idx] / band_width

        # 计算总功率
        total_psd = np.sum(band_psd, axis=2, keepdims=True) + 1e-10  # 避免除以零

        # 计算各频段的功率占比
        band_ratio = band_psd / total_psd*1000  # 形状: (n_epochs, n_channels, len(bands))

        # 计算其他时域特征
        amp=np.max(data_segment, axis=2)-np.min(data_segment, axis=2)
        rms = np.sqrt(np.mean(data_segment ** 2, axis=2))  # RMS 特征
        # abs_sum = np.sum(np.abs(data_segment), axis=2)  # 所有数值绝对值的和

        # 拼接所有特征
        features = np.concatenate([
            amp[..., np.newaxis],
            rms[..., np.newaxis],  # RMS 特征
            # abs_sum[..., np.newaxis],  # 所有数值绝对值的和
            band_psd_per_hz,
            band_ratio  # 各频段功率占比
        ], axis=2)

        # # # 重塑为二维数组
        # features_reshaped = np.squeeze(features)
        # #
        # # # 逐列归一化前三列特征（RMS 和 abs_sum）
        # scaler = StandardScaler()
        # features_scaled = np.array([scaler.fit_transform(f.reshape(-1, 1)) for f in features_reshaped[:, :].T]).T
        # # features_scaled = np.squeeze(features_scaled)  # 取绝对值并乘以0.2
        # # features_scaled = features_scaled[:, np.newaxis]
        # # # # # 拼接标准化后的特征与未标准化的特征
        # # features_final = np.concatenate([features_scaled, features_reshaped[:, :]], axis=1)
        # features_final=np.squeeze(features_scaled)
        #

        features_final = np.squeeze(features)
        return features_final
    except Exception as e:
        logging.exception(f"提取特征时出错: {e}")
        return np.array([])


def extract_features(raw: mne.io.Raw, window_length_sec: int, for_training: bool = True,device='DSI') -> Tuple[
    np.ndarray, List[str]]:
    """
    从原始数据中提取特征，用于训练或分类。
    """
    try:
        sfreq = raw.info['sfreq']

        annotations = raw.annotations
        num_annotations = len(annotations)
        logging.info(f"注释数量: {num_annotations}")

        window_length_samples = int(window_length_sec * sfreq)
        n_channels = len(raw.ch_names)
        channel_idx = 3 if device == 'AR4' else 0 if device == 'DSI' else None
        if channel_idx is None:
            raise ValueError("不支持的通道数量")

        logging.info(f"选择的通道索引: {channel_idx}，通道数量: {n_channels}")

        # raw.filter(l_freq=1, h_freq=35)
        # raw.notch_filter(freqs=50)
        # plt.plot(raw.get_data()[0])
        # plt.show()
        data = raw.get_data(picks=channel_idx).flatten()
        logging.info(f"滤波后的数据形状: {data.shape}")

        all_segments, all_labels = [], []
        for i in tqdm(range(0, num_annotations - 1, 2), desc="处理数据段"):
            onset_current, onset_next = annotations.onset[i], annotations.onset[i + 1]
            description_current = annotations.description[i].lower()
            description_next = annotations.description[i + 1].lower()

            # 根据注释对确定标签
            if (description_current == '0' and description_next == '1'):
                label = 'S'
            elif (description_current == '2' and description_next == '3'):
                label = 'NS'
            else:
                logging.warning(f"无效的注释对 '{description_current}-{description_next}'，索引 {i}-{i + 1}。跳过该段。")
                continue

            start_sample = int(onset_current * sfreq)
            stop_sample = int(onset_next * sfreq)
            event_data = data[start_sample:stop_sample]
            total_samples = stop_sample - start_sample

            if total_samples < window_length_samples:
                logging.warning(f"注释对 {i}-{i + 1} 的数据段长度小于窗口长度。跳过。")
                continue

            window_starts = np.arange(0, total_samples - window_length_samples + 1, window_length_samples)
            window_ends = window_starts + window_length_samples

            for start, end in zip(window_starts, window_ends):
                data_segment = event_data[start:end]
                if data_segment.shape[0] < window_length_samples:
                    continue
                all_segments.append(data_segment[np.newaxis, np.newaxis, :])  # Shape: (1, 1, window_length_samples)
                all_labels.append(label)

        if not all_segments:
            raise ValueError("未找到有效的数据段。")

        all_data_segments = np.concatenate(all_segments, axis=0)
        features = extract_features_using_epochs(all_data_segments, fs=sfreq)

        if for_training:
            return features, all_labels
        else:
            return features, []
    except Exception as e:
        logging.exception(f"提取特征时出错: {e}")
        return np.array([]), []


# -------------------- 模型处理函数 --------------------

def save_to_parquet(features: np.ndarray, labels: np.ndarray, output_file_path: str) -> None:
    """
    将特征和标签保存到Parquet文件中。
    """
    try:
        df = pd.DataFrame(features)
        df['label'] = labels
        pq.write_table(pa.Table.from_pandas(df), output_file_path)
        logging.info(f"数据集已保存到 {output_file_path}")
    except Exception as e:
        logging.exception(f"保存到Parquet文件时出错: {e}")


def load_parquet(output_file_path: str) -> Tuple[np.ndarray, List[str]]:
    """
    从Parquet文件加载特征和标签。
    """
    try:
        df_loaded = pq.read_table(output_file_path).to_pandas()
        return df_loaded.drop('label', axis=1).values, df_loaded['label'].tolist()
    except Exception as e:
        logging.exception(f"从Parquet文件加载数据时出错: {e}")
        return np.array([]), []


def replace_nan_with_mean(X: np.ndarray) -> np.ndarray:
    """
    用均值替换数组中的NaN值。
    """
    try:
        col_means = np.nanmean(X, axis=0)
        inds = np.where(np.isnan(X))
        X[inds] = np.take(col_means, inds[1])
        return X
    except Exception as e:
        logging.exception(f"替换NaN值时出错: {e}")
        return X


def train_and_evaluate_model(model_path: str, data_list: List[str],
                             output_file_path: str, epochlength: int = 5,
                             rms_lower_factor: float = 1.4,
                             amp_upper_factor=3,
                            device='DSI',
                             show_plots: bool = False) -> None:
    """
    训练和评估模型，包括超参数调优。
    """
    try:
        # 加载或提取特征
        if os.path.exists(output_file_path):
            X, y = load_parquet(output_file_path)
            X = replace_nan_with_mean(X)
            logging.info(f"从 {output_file_path} 加载特征")
        else:
            all_features, all_labels = [], []
            for data_path in data_list:
                try:
                    raw = read_edf_file(data_path)
                    features, labels = extract_features(raw, window_length_sec=epochlength, for_training=True,device=device)
                    if features.size == 0:
                        continue
                    all_features.extend(features)
                    all_labels.extend(labels)
                except Exception as e:
                    logging.exception(f"处理 {data_path} 时出错: {e}")
                    continue
            if not all_features:
                logging.error("未从训练数据中提取到任何特征。")
                return
            save_to_parquet(np.array(all_features), np.array(all_labels), output_file_path)
            X, y = np.array(all_features), np.array(all_labels)
            X = replace_nan_with_mean(X)
            logging.info(f"已提取并保存特征到 {output_file_path}")

        # 映射标签：'S' -> 1, 'NS' -> 0
        y_mapped = np.array([1 if label == 'S' else 0 for label in y])
        logging.info(f"SMOTE前的类别分布: {np.bincount(y_mapped)}")

        # 处理类别不平衡
        smote = SMOTE(random_state=42)
        X_resampled, y_resampled = smote.fit_resample(X, y_mapped)
        logging.info(f"SMOTE后的类别分布: {np.bincount(y_resampled)}")

        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X_resampled, y_resampled, test_size=0.2, random_state=42
        )
        logging.info(f"训练集大小: {X_train.shape[0]}, 测试集大小: {X_test.shape[0]}")

        # 定义模型和参数网格
        model = LGBMClassifier(random_state=42)
        param_grid = {
            'n_estimators': [200],
            'learning_rate': [0.05],
            'max_depth': [25],
            'num_leaves': [150],
            'subsample': [1.0]
        }

        grid_search = GridSearchCV(
            estimator=model,
            param_grid=param_grid,
            cv=StratifiedKFold(n_splits=5),
            scoring='accuracy',
            n_jobs=-1,
            verbose=1
        )

        logging.info("开始进行超参数调优（GridSearchCV）。")
        grid_search.fit(X_train, y_train)
        logging.info("超参数调优完成。")

        # 获取最佳模型
        logging.info(f"找到的最佳参数: {grid_search.best_params_}")
        best_model = grid_search.best_estimator_

        # 在测试集上评估最佳模型
        y_pred_proba = best_model.predict_proba(X_test)[:, 1]
        final_classifications  = (y_pred_proba >= 0.5).astype(int)
        if X_test.shape[1] >= 2:
            amp = X_test[:, 0]
            rms = X_test[:, 1]

            final_classifications = apply_dynamic_threshold(amp,rms, final_classifications, rms_lower_factor=rms_lower_factor, amp_upper_factor=amp_upper_factor)

        # 计算评估指标
        precision = precision_score(y_test, final_classifications, zero_division=0)
        accuracy = accuracy_score(y_test, final_classifications)
        recall = recall_score(y_test, final_classifications, zero_division=0)
        f1 = f1_score(y_test, final_classifications, zero_division=0)

        logging.info(f"测试集准确率: {accuracy:.4f}")
        logging.info(f"测试集精确率: {precision:.4f}")
        logging.info(f"测试集召回率: {recall:.4f}")
        logging.info(f"测试集F1分数: {f1:.4f}")

        # 混淆矩阵
        cm = confusion_matrix(y_test, final_classifications, labels=[1, 0])
        cm_percent = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis] * 100
        disp = ConfusionMatrixDisplay(confusion_matrix=cm_percent, display_labels=['Seizure', 'Non-Seizure'])
        disp.plot(cmap=plt.cm.Blues, values_format=".2f")
        plt.title('混淆矩阵（百分比）')
        cm_plot_path = os.path.join(os.path.dirname(model_path), 'confusion_matrix.png')
        plt.savefig(cm_plot_path)
        if show_plots:
            plt.show()
        plt.close()
        logging.info(f"混淆矩阵已保存到 {cm_plot_path}")

        # 保存最佳模型
        joblib.dump(best_model, model_path)
        logging.info(f"最佳模型已保存到 {model_path}")

        # 绘制ROC和PR曲线
        plot_roc_pr_curves(y_test, y_pred_proba, os.path.dirname(model_path), show_plots=show_plots)
    except Exception as e:
        logging.exception(f"在训练和评估模型时出错: {e}")


def evaluate_model_on_test_set(model_path: str, test_data_list: List[str], epochlength: int,
                               rms_lower_factor: Optional[float] = None,
                               amp_upper_factor: Optional[float] = None) -> Tuple[float, float, float]:
    """
    在测试集上评估模型。

    返回:
        Tuple[float, float, float]: (精确率, 准确率, 特异性)
    """
    try:
        # 加载模型
        model = joblib.load(model_path)

        all_features, all_labels = [], []
        for data_path in test_data_list:
            try:
                raw = read_edf_file(data_path)
                features, labels = extract_features(raw, window_length_sec=epochlength, for_training=True)
                if features.size == 0:
                    continue
                all_features.extend(features)
                all_labels.extend(labels)
            except Exception as e:
                logging.exception(f"处理 {data_path} 时出错: {e}")
                continue

        if not all_features:
            logging.warning("未从测试数据中提取到任何特征。")
            return 0.0, 0.0, 0.0

        X_test = np.array(all_features)
        y_test = np.array([0 if label == 'NS' else 1 for label in all_labels])

        # 处理NaN值
        X_test = replace_nan_with_mean(X_test)

        # 分类概率
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        # 基础分类
        y_pred = (y_pred_proba >= 0.5).astype(int)

        # 动态阈值筛选
        if rms_lower_factor is not None and X_test.shape[1] >= 2:
            rms = X_test[:, 0]
            y_pred = apply_dynamic_threshold(rms, y_pred, rms_lower_factor=rms_lower_factor,amp_upper_factor=amp_upper_factor)

        # 计算指标
        precision = precision_score(y_test, y_pred, zero_division=0)
        accuracy = accuracy_score(y_test, y_pred)
        cm = confusion_matrix(y_test, y_pred)
        tn, fp, fn, tp = cm.ravel()
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

        return precision, accuracy, specificity

    except Exception as e:
        logging.exception(f"在测试集上评估模型时出错: {e}")
        return 0.0, 0.0, 0.0


# -------------------- 预测函数 --------------------

def split_into_epochs(data, window_size, step=1):
    """
    将数据切分成多个窗口段。
    """
    num_epochs = (len(data) - window_size) // step + 1
    epochs = np.array([data[i * step: i * step + window_size] for i in range(num_epochs)])
    return epochs


def classify_new_data(model, new_edf_file_path: str, save_folder: str, epoch_length: int = 3,
                      seizure_length_sec: int = 60, device: str = 'AR4', rms_lower_factor: float = 1.4,
                        amp_upper_factor=3,
                      show_plots: bool = False, ylim: List[int] = [-500, 500],
                      min_no_seizure_epochs: int = 10, offset: int = 0) -> None:
    """
    在新的 .edf 数据文件中分类癫痫发作。

    参数：
        model: 训练好的模型。
        new_edf_file_path (str): 新的 EDF 文件路径。
        save_folder (str): 保存结果的文件夹路径。
        epoch_length (int): 每个窗口的长度（秒）。
        seizure_length_sec (int): 绘制的癫痫发作片段的长度（秒）。
        device (str): 设备类型 ('DSI' 或 'AR4')。
        rms_lower_factor (float): 用于动态阈值筛选的 RMS 因子。
        show_plots (bool): 是否显示绘制的图像。
        ylim (List[int]): 原始数据的 y 轴范围。
        min_no_seizure_epochs (int): 判定为新的癫痫发作所需的最小非发作 epoch 数。
        offset (int): 绘图的时间偏移量（秒）。
    """
    downsample_factor=10
    try:
        # 读取并预处理 EDF 文件
        raw = read_edf_file(new_edf_file_path)
        raw_copy = raw.copy()
        sfreq = raw_copy.info['sfreq']

        meas_date = raw_copy.info.get('meas_date', None)

        if meas_date is None:
            logging.warning("数据中没有可用的测量日期，使用当前时间作为测量日期。")
            meas_date = datetime.datetime.now()

        if isinstance(meas_date, datetime.datetime):
            start_time_ts = meas_date.timestamp()
        else:
            start_time_ts = meas_date[0] + meas_date[1] * 1e-6  # tuple/list格式

        # 选择通道索引
        n_channels = len(raw_copy.ch_names)
        channel_idx = 3 if device == 'AR4' else 0 if device == 'DSI' else None
        if channel_idx is None:
            logging.error(f"不支持的设备类型或通道数量: {device}, 通道数量={n_channels}")
            return

        # 获取信号数据
        data = raw_copy.get_data(picks=[channel_idx]).flatten()

        # 切分为多个窗口段
        window_length_samples = int(epoch_length * sfreq)
        epochs = split_into_epochs(data, window_length_samples, step=window_length_samples)

        if epochs.size == 0:
            logging.error("信号长度不足以切分为一个窗口。")
            return

        # 扩展维度以符合模型输入要求（假设模型需要的输入形状为 [batch, channels, samples]）
        data_segments = np.expand_dims(epochs, axis=1)  # Shape: [num_epochs, 1, window_length_samples]

        # 特征提取
        features = extract_features_using_epochs(data_segment=data_segments, fs=sfreq)

        if features.size == 0:
            logging.error("未提取到用于分类的特征。")
            return

        # 模型分类
        classifications_proba = model.predict_proba(features)[:, 1]
        classifications = (classifications_proba >= 0.5).astype(int)

        # 动态阈值筛选
        if features.shape[1] >= 2:
            amp = features[:, 0]
            rms = features[:, 1]
            final_classifications = apply_dynamic_threshold(amp,rms, classifications, rms_lower_factor=rms_lower_factor,amp_upper_factor=amp_upper_factor)



        # 检测癫痫发作
        seizure_info, seizure_per_minute = detect_seizures(
            final_classifications,
            data,
            sfreq,
            # n_epoch_no_seizure=min_no_seizure_epochs,
            epoch_length=epoch_length,
            start_time_ts=start_time_ts,
            min_no_seizure_epochs=min_no_seizure_epochs
        )
        # 绘制原始数据和分类结果
        try:

            plot_raw_and_classifications(
                data=data,
                classifications=final_classifications,
                save_folder=save_folder,
                sfreq=sfreq,
                epoch_length=epoch_length,
                start_time_ts=start_time_ts,
                downsample_factor=downsample_factor,
                ylim=ylim,
                x_interval=120,
                show_plots=show_plots
            )
        except Exception as e:
            logging.error(f"在绘制原始数据和分类结果时出错: {e}")
        
        
        # 会生成大量图
        # if seizure_info:
        #     # 为每一次癫痫发作绘制图像
        #     plot_seizure_data(
        #         raw_2_plot=raw,
        #         data=data,
        #         seizure_info_list=seizure_info,
        #         seizure_length_sec=seizure_length_sec,
        #         sfreq=sfreq,
        #         offset=offset,
        #         save_folder=save_folder,
        #         fig_size=(16, 4.5),
        #         ylim=ylim,
        #         plot_results=True,
        #         show_plots=show_plots,
        #         start_time=start_time_ts,
        #         channel_idx=channel_idx,
        #         relative_v=True,
        #         epoch_length=epoch_length
        #     )
        # else:
        #     logging.info("未检测到任何癫痫发作。")



        # 保存癫痫发作信息
        save_seizure_info(seizure_info, seizure_per_minute, save_folder)
        logging.info(f"癫痫发作信息和每分钟发作频率已保存到 {os.path.join(save_folder, 'seizure_info.xlsx')}")


    except Exception as e:
        logging.error(f"处理 {new_edf_file_path} 时出错: {e}")


def classify_new_data_directory(model_path: str, directory: str, epoch_length: int = 3,
                                seizure_length_sec: int = 60, device: str = 'AR4',
                                rms_lower_factor: float = 1.4,
                                amp_upper_factor: float = 3,
                                show_plots: bool = False,
                                ylim: List[int] = [-500, 500], min_no_seizure_epochs: int = 10,
                                offset: int = 0) -> None:
    """
    使用训练好的模型对指定目录下的所有 .edf 文件进行癫痫发作分类。

    参数：
        model_path (str): 已训练模型的路径。
        directory (str): 包含待分类 .edf 文件的目录。
        epoch_length (int): 每个窗口的长度（秒）。
        seizure_length_sec (int): 绘制的癫痫发作片段的长度（秒）。
        device (str): 设备类型 ('DSI' 或 'AR4')。
        rms_lower_factor (float): 用于动态阈值筛选的 RMS 因子。
        show_plots (bool): 是否显示绘制的图像。
        ylim (List[int]): 原始数据的 y 轴范围。
        min_no_seizure_epochs (int): 判定为新的癫痫发作所需的最小非发作 epoch 数。
        offset (int): 绘图的时间偏移量（秒）。
    """
    try:
        # 加载模型
        model = joblib.load(model_path)
        logging.info(f"成功加载模型：{model_path}")

        # 查找所有符合条件的EDF文件
        edf_files = find_edf_files(directory, device=device)
        logging.info(f"找到 {len(edf_files)} 个 EDF 文件用于分类。")

        for edf_file in edf_files:
            base_name = os.path.splitext(os.path.basename(edf_file))[0]
            save_folder = os.path.join(os.path.dirname(edf_file), f"{base_name}_Results&Figures")

            # 跳过已处理过的文件
            if os.path.exists(save_folder) and os.listdir(save_folder):
                logging.info(f"跳过 {save_folder}，因为它已经存在且非空。")
                continue

            os.makedirs(save_folder, exist_ok=True)
            logging.info(f"创建保存文件夹：{save_folder}")

            # 分类新的EDF数据
            classify_new_data(
                model=model,
                new_edf_file_path=edf_file,
                save_folder=save_folder,
                epoch_length=epoch_length,
                seizure_length_sec=seizure_length_sec,
                device=device,
                rms_lower_factor=rms_lower_factor,
                amp_upper_factor=amp_upper_factor,
                show_plots=show_plots,
                ylim=ylim,
                min_no_seizure_epochs=min_no_seizure_epochs,
                offset=offset
            )

            logging.info(f"完成对 {edf_file} 的分类，并保存结果到 {save_folder}")

    except Exception as e:
        logging.error(f"在分类新数据时出错: {e}")



# -------------------- 绘图函数 --------------------

def plot_raw_and_classifications(data: np.ndarray, classifications: np.ndarray, sfreq: float,epoch_length,
                                 start_time_ts: float, downsample_factor: int,
                                 save_folder: str, ylim: List[int], x_interval:int,
                                 show_plots: bool = False) -> None:
    """
    绘制原始EEG数据和癫痫发作分类结果，用散点标记癫痫发作的数据点。
    """
    try:

        data_downsampled = data[::downsample_factor]
        sfreq=np.round(sfreq/downsample_factor)


        classifications_resampled = np.repeat(classifications, int(sfreq * epoch_length))
        classifications_resampled = np.resize(classifications_resampled, len(data_downsampled ))


        time_downsampled = np.linspace(0, len(data_downsampled) / sfreq, len(data_downsampled))
        time_downsampled = [datetime.datetime.utcfromtimestamp(ts + start_time_ts) for ts in time_downsampled]

        plt.figure(figsize=(16, 4.5))
        plt.plot(time_downsampled, data_downsampled, label='原始数据', color='black', linewidth=0.5)

        # 用散点标记癫痫发作的数据点
        seizure_indices = classifications_resampled == 1
        seizure_times = np.array(time_downsampled)[seizure_indices]
        seizure_data_points = np.array(data_downsampled)[seizure_indices]
        plt.scatter(seizure_times, seizure_data_points, color='red', s=0.2, label='癫痫发作数据点', zorder=5)

        plt.xlabel('时间 (UTC)')
        plt.ylabel('振幅 (μV)')
        plt.title('原始数据与癫痫发作分类结果')
        plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=x_interval))
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.gcf().autofmt_xdate()
        plt.legend()
        plt.ylim(ylim)
        plt.xlim(time_downsampled[0], time_downsampled[-1])
        plt.grid(False)
        plt.tight_layout()
        plt.savefig(os.path.join(save_folder, 'raw_data_with_classifications.png'))
        if show_plots:
            plt.show()
        plt.close()
    except Exception as e:
        logging.error(f"绘制原始数据和分类结果时出错: {e}")


def format_utc(x: float, pos: int) -> str:
    """
    将 matplotlib 的日期数字格式转换为 'HH:MM:SS' 格式。
    """
    try:
        dt = mdates.num2date(x)
        return dt.strftime("%H:%M:%S")
    except Exception as e:
        logging.error(f"格式化 UTC 时间时出错: {e}")
        return "00:00:00"


def plot_roc_pr_curves(y_true: np.ndarray, y_scores: np.ndarray, save_folder: str, show_plots: bool = False) -> None:
    """
    绘制 ROC 曲线和 PR 曲线，并保存至指定文件夹。
    """
    try:
        # ROC 曲线
        fpr, tpr, _ = roc_curve(y_true, y_scores)
        roc_auc = auc(fpr, tpr)

        # PR 曲线
        precision, recall, _ = precision_recall_curve(y_true, y_scores)
        pr_auc = auc(recall, precision)

        plt.figure(figsize=(12, 5))

        # ROC 曲线
        plt.subplot(1, 2, 1)
        plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC 曲线 (AUC = {roc_auc:.2f})')
        plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('假阳性率')
        plt.ylabel('真阳性率')
        plt.title('接收器操作特征曲线 (ROC)')
        plt.legend(loc="lower right")

        # PR 曲线
        plt.subplot(1, 2, 2)
        plt.plot(recall, precision, color='blue', lw=2, label=f'PR 曲线 (AUC = {pr_auc:.2f})')
        plt.xlabel('召回率')
        plt.ylabel('精确率')
        plt.title('精确率-召回率曲线 (PR)')
        plt.legend(loc="lower left")

        plt.tight_layout()
        roc_pr_plot_path = os.path.join(save_folder, 'roc_pr_curves.png')
        plt.savefig(roc_pr_plot_path)
        if show_plots:
            plt.show()
        plt.close()
        logging.info(f"ROC 和 PR 曲线已保存到 {roc_pr_plot_path}")
    except Exception as e:
        logging.error(f"绘制 ROC 和 PR 曲线时出错: {e}")


# -------------------- 癫痫发作检测与绘图函数 --------------------

def detect_seizures(classifications: np.ndarray, data: np.ndarray, sfreq: float,
                     epoch_length: int, start_time_ts: float,
                    min_no_seizure_epochs: int = 10) -> Tuple[List[Dict], Dict]:
    """
    从分类结果中检测癫痫发作。
    """
    # plt.plot(classifications)
    # plt.show()
    try:
        seizure_info = []
        in_seizure = False
        seizure_counter = 1
        non_seizure_count = 0
        seizure_per_minute = {}
        total_minutes = int(np.ceil(len(data) / sfreq / 60))

        for minute in range(total_minutes):
            seizure_per_minute[minute] = 0

        last_seizure_end_epoch = -np.inf

        for i, pred in tqdm(enumerate(classifications), total=len(classifications), desc="检测癫痫发作"):
            if pred == 1:
                if not in_seizure:
                    if (i - last_seizure_end_epoch) >= min_no_seizure_epochs:
                        seizure_start_epoch = i
                        in_seizure = True
                        seizure_minute = int((seizure_start_epoch * epoch_length) / 60)
                        seizure_per_minute[seizure_minute] += 1
                    # else:
                    #     in_seizure = True
                non_seizure_count = 0
            elif pred == 0 and in_seizure:
                non_seizure_count += 1
                if non_seizure_count >= min_no_seizure_epochs:
                    in_seizure = False
                    # seizure_end_epoch = i - non_seizure_count
                    seizure_end_epoch = i
                    seizure_end_epoch = max(seizure_end_epoch, seizure_start_epoch)

                    # 计算样本索引
                    start_sample = int(seizure_start_epoch * epoch_length * sfreq)
                    end_sample = int(seizure_end_epoch * epoch_length * sfreq)


                    if start_sample >= len(data) or end_sample > len(data) or start_sample >= end_sample:
                        logging.warning(f"癫痫发作 {seizure_counter} 的样本索引无效。跳过。")
                        last_seizure_end_epoch = seizure_end_epoch
                        continue

                    seizure_data_segment = data[start_sample:end_sample]
                    if seizure_data_segment.size == 0:
                        logging.warning(f"癫痫发作 {seizure_counter} 的数据段为空。跳过。")
                        last_seizure_end_epoch = seizure_end_epoch
                        continue

                    rms_value = np.sqrt(np.mean(seizure_data_segment ** 2))
                    max_value = np.max(seizure_data_segment)
                    rms_value = round(rms_value, 1)
                    max_value = round(max_value, 1)

                    start_timestamp = seizure_start_epoch * epoch_length
                    end_timestamp = seizure_end_epoch * epoch_length
                    duration_sec = round(end_timestamp - start_timestamp, 1)

                    # 计算 UTC 时间
                    start_time_utc = start_timestamp + start_time_ts
                    end_time_utc = end_timestamp + start_time_ts

                    seizure_info.append({
                        '癫痫发作编号': seizure_counter,
                        'RMS值': rms_value,
                        '最大值': max_value,
                        '开始时间戳 (s)': start_timestamp,
                        '结束时间戳 (s)': end_timestamp,
                        '开始时间 (UTC)': datetime.datetime.utcfromtimestamp(start_time_utc),
                        '结束时间 (UTC)': datetime.datetime.utcfromtimestamp(end_time_utc),
                        '持续时间 (s)': duration_sec,
                        '起始 epoch': seizure_start_epoch,
                        '结束 epoch': seizure_end_epoch
                    })

                    seizure_counter += 1
                    last_seizure_end_epoch = seizure_end_epoch
                    non_seizure_count = 0

        # 处理在数据结束时仍在进行的癫痫发作
        if in_seizure:
            seizure_end_epoch = len(classifications) - 1

            start_sample = int(seizure_start_epoch * epoch_length * sfreq)
            end_sample = int(seizure_end_epoch * epoch_length * sfreq)

            if start_sample < end_sample:
                seizure_data_segment = data[start_sample:end_sample]
                rms_value = np.sqrt(np.mean(seizure_data_segment ** 2))
                max_value = np.max(seizure_data_segment)
                rms_value = round(rms_value, 1)
                max_value = round(max_value, 1)

                start_timestamp = seizure_start_epoch * epoch_length
                end_timestamp = seizure_end_epoch * epoch_length
                duration_sec = end_timestamp - start_timestamp
                duration_sec = round(end_timestamp - start_timestamp, 1)

                # 计算 UTC 时间
                start_time_utc = start_timestamp + start_time_ts
                end_time_utc = end_timestamp + start_time_ts

                seizure_info.append({
                    '癫痫发作编号': seizure_counter,
                    'RMS值': rms_value,
                    '最大值': max_value,
                    '开始时间戳 (s)': start_timestamp,
                    '结束时间戳 (s)': end_timestamp,
                    '开始时间 (UTC)': datetime.datetime.utcfromtimestamp(start_time_utc),
                    '结束时间 (UTC)': datetime.datetime.utcfromtimestamp(end_time_utc),
                    '持续时间 (s)': duration_sec,
                    '起始 epoch': seizure_start_epoch,
                    '结束 epoch': seizure_end_epoch
                })

        seizure_per_minute_df = {
            'Minute': list(seizure_per_minute.keys()),
            'Seizure Count': list(seizure_per_minute.values()),
            'UTC Time': [datetime.datetime.utcfromtimestamp(start_time_ts + minute * 60) for minute in
                         seizure_per_minute.keys()]
        }

        return seizure_info, seizure_per_minute_df
    except Exception as e:
        logging.error(f"检测癫痫发作时出错: {e}")
        return [], {}


def plot_seizure_data(raw_2_plot, data, seizure_info_list, seizure_length_sec, sfreq, offset,
                      save_folder,
                      fig_size, ylim, plot_results, show_plots,
                      start_time, channel_idx, relative_v, epoch_length):
    """
    为每一次癫痫发作绘制原始数据和时频图，文件名包含发作序号、片段序号和起止时间。
    """
    try:
        # for seizure_info in seizure_info_list:
        #     seizure_counter = seizure_info['癫痫发作编号']
        #     seizure_start_epoch = seizure_info['起始 epoch']
        #     seizure_end_epoch = seizure_info['结束 epoch']
        #
        #     # 将癫痫发作按片段进行划分
        #     total_seizure_duration_sec = (seizure_end_epoch - seizure_start_epoch) * epoch_length
        #     num_segments = int(np.ceil(total_seizure_duration_sec / seizure_length_sec))
        #
        #     for segment_idx in range(num_segments):
        #         segment_start_sec = seizure_start_epoch * epoch_length + segment_idx * seizure_length_sec
        #
        #         segment_end_sec = segment_start_sec + seizure_length_sec
        #
        #         plot_start = int(segment_start_sec * sfreq) + int(offset * sfreq)
        #         plot_end = int(segment_end_sec * sfreq)
        #
        #         # 确保索引有效
        #         plot_start = max(plot_start, 0)
        #         plot_end = min(plot_end, len(data))
        #
        #         data_slice = data[plot_start:plot_end]
        #         t = np.linspace(plot_start / sfreq, plot_end / sfreq, len(data_slice), endpoint=False)
        #         t_datetime = [datetime.datetime.utcfromtimestamp(ts + start_time) for ts in t]
        #         t_datetime = [dt + datetime.timedelta(seconds=offset) for dt in t_datetime]
        #
        #         # 获取癫痫发作的起始和结束 UTC 时间
        #         seizure_start_time = datetime.datetime.utcfromtimestamp(segment_start_sec + start_time)
        #         seizure_end_time = datetime.datetime.utcfromtimestamp(segment_end_sec + start_time)
        #
        #         ST = seizure_start_time.strftime("%Y%m%d%H%M%S")
        #         ET = seizure_end_time.strftime("%Y%m%d%H%M%S")
        #         raw_image_path = os.path.join(save_folder,
        #                                       f'Seizure{seizure_counter}_Segment{segment_idx + 1}_{ST}_{ET}_raw.png')
        #
        #         if plot_results and not os.path.exists(raw_image_path):
        #             plt.figure(figsize=fig_size)
        #             plt.plot(t_datetime, data_slice, color='black', linewidth=0.5)
        #
        #             seizure_indices = classifications_resampled == 1
        #             seizure_times = np.array(time_downsampled)[seizure_indices]
        #             seizure_data_points = np.array(data_downsampled)[seizure_indices]
        #             plt.scatter(seizure_times, seizure_data_points, color='red', s=1, label='癫痫发作数据点', zorder=5)
        #
        #             plt.xlabel('时间 (UTC)')
        #             plt.ylabel('振幅 (μV)')
        #             plt.xlim(t_datetime[0], t_datetime[-1])
        #             plt.ylim(ylim)
        #             plt.title(f'癫痫发作 {seizure_counter} - 片段 {segment_idx + 1} - 原始数据')
        #             plt.xticks(rotation=45)
        #             plt.tight_layout()
        #             plt.savefig(raw_image_path)
        #             if show_plots:
        #                 plt.show()
        #             plt.close()
        for seizure_info in seizure_info_list:
            seizure_counter = seizure_info['癫痫发作编号']
            seizure_start_epoch = seizure_info['起始 epoch']
            seizure_end_epoch = seizure_info['结束 epoch']

            # 将癫痫发作按片段进行划分
            total_seizure_duration_sec = (seizure_end_epoch - seizure_start_epoch) * epoch_length
            num_segments = int(np.ceil(total_seizure_duration_sec / seizure_length_sec))

            for segment_idx in range(num_segments):

                # 计算癫痫发作的中心时间
                seizure_center_sec = ((seizure_start_epoch+segment_idx) * epoch_length + seizure_end_epoch * epoch_length) / 2

                # 调整 segment_start_sec 和 segment_end_sec，使癫痫发作片段居中
                segment_start_sec = seizure_center_sec - seizure_length_sec / 2
                segment_end_sec = segment_start_sec + seizure_length_sec

                plot_start = int(segment_start_sec * sfreq) + int(offset * sfreq)
                plot_end = int(segment_end_sec * sfreq)

                # 确保索引有效
                plot_start = max(plot_start, 0)
                plot_end = min(plot_end, len(data))

                data_slice = data[plot_start:plot_end]
                t = np.linspace(plot_start / sfreq, plot_end / sfreq, len(data_slice), endpoint=False)
                t_datetime = [datetime.datetime.utcfromtimestamp(ts + start_time) for ts in t]
                t_datetime = [dt + datetime.timedelta(seconds=offset) for dt in t_datetime]

                # 获取癫痫发作的全局起始和结束 UTC 时间
                seizure_start_time_global = datetime.datetime.utcfromtimestamp(
                    (seizure_start_epoch+segment_idx) * epoch_length + start_time)
                seizure_end_time_global = datetime.datetime.utcfromtimestamp(
                    (seizure_end_epoch+segment_idx) * epoch_length + start_time)



                # 获取当前片段的起始和结束 UTC 时间
                segment_start_time = datetime.datetime.utcfromtimestamp(segment_start_sec + start_time)
                segment_end_time = datetime.datetime.utcfromtimestamp(segment_end_sec + start_time)

                ST = segment_start_time.strftime("%Y%m%d%H%M%S")
                ET = segment_end_time.strftime("%Y%m%d%H%M%S")
                raw_image_path = os.path.join(save_folder,
                                              f'Seizure{seizure_counter}_Segment{segment_idx + 1}_{ST}_{ET}_raw.png')

                if plot_results and not os.path.exists(raw_image_path):
                    plt.figure(figsize=fig_size)
                    plt.plot(t_datetime, data_slice, color='black', linewidth=0.5)

                    # 添加透明度来标记癫痫发作期间的数据
                    # plt.axvspan(seizure_start_time_global, seizure_end_time_global, color='red', alpha=0.3)

                    plt.xlabel('时间 (UTC)')
                    plt.ylabel('振幅 (μV)')
                    plt.xlim(t_datetime[0], t_datetime[-1])
                    plt.ylim(ylim)
                    plt.title(f'癫痫发作 {seizure_counter} - 片段 {segment_idx + 1} - 原始数据')
                    plt.xticks(rotation=45)
                    plt.tight_layout()
                    plt.savefig(raw_image_path)
                    if show_plots:
                        plt.show()
                    plt.close()

                # 时频分析并保存图像
                if plot_results:
                    # 计算裁剪的起始和结束时间（以秒为单位）
                    tmin = plot_start / sfreq
                    tmax = plot_end / sfreq
                    # tmax = min(tmax, raw_2_plot.times[-1])  # 确保tmax不超过数据的实际持续时间

                    # 裁剪原始数据
                    cropped_raw = raw_2_plot.copy().crop(tmin=tmin, tmax=tmax)

                    # 检查裁剪后的数据是否为空
                    if cropped_raw.n_times == 0:
                        logging.warning(
                            f"癫痫发作 {seizure_counter} 的片段 {segment_idx + 1} 的裁剪数据为空。跳过时频图绘制。")
                        continue

                    nperseg=sfreq*2
                    # 定义STFT的参数
                    f, t, Zxx = signal.stft(cropped_raw.get_data(picks=[channel_idx])[0], fs=sfreq, nperseg=nperseg,
                                            noverlap=int(0.5*nperseg))

                    # 只保留0-35 Hz的频率范围
                    freq_mask = (f >= 0) & (f <= 35)
                    f = f[freq_mask]
                    Zxx = Zxx[freq_mask, :]

                    # 计算功率数据
                    power_data = np.abs(Zxx) ** 2
                    power_data = 10 * np.log10(power_data + 1e-10)

                    # 定义保存时频图的路径
                    tfr_image_path = os.path.join(
                        save_folder,
                        f'Seizure{seizure_counter}_Segment{segment_idx + 1}_{ST}_{ET}_tfr.png'
                    )

                    # 检查图像是否已存在，以避免重复处理
                    if not os.path.exists(tfr_image_path):
                        # 确定颜色刻度的上下限
                        if relative_v:
                            vmin, vmax = np.percentile(power_data, [5, 95])
                        else:
                            vmin, vmax = 0, 30

                        # 计算颜色映射的中心
                        vcenter = np.percentile(power_data, 50)

                        # 如果中心不在vmin和vmax之间，则调整颜色映射
                        if not (vmin < vcenter < vmax):
                            vmin, vcenter, vmax = -1, 0, 1

                        # 定义颜色映射的规范化
                        norm = TwoSlopeNorm(vmin=vmin, vcenter=vcenter, vmax=vmax)

                        # 创建图形对象
                        plt.figure(figsize=fig_size)

                        # 计算绝对 UTC 时间
                        absolute_t = t + tmin + start_time  # t 以秒为单位
                        absolute_datetime = [datetime.datetime.utcfromtimestamp(ts) for ts in absolute_t]
                        absolute_mdates = mdates.date2num(absolute_datetime)

                        # 绘制时频图
                        plt.pcolormesh(
                            absolute_mdates,
                            f,
                            power_data,
                            shading='gouraud',
                            cmap='RdBu_r',
                            norm=norm
                        )
                        plt.ylabel('频率 (Hz)')
                        plt.xlabel('时间 (UTC)')
                        plt.title(f'癫痫发作 {seizure_counter} - 片段 {segment_idx + 1} - 时频图 (STFT)')
                        plt.xlim([absolute_mdates[0], absolute_mdates[-1]])

                        # 设置 x 轴的格式化器
                        plt.gca().xaxis.set_major_formatter(FuncFormatter(format_utc))
                        plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())

                        # 旋转 x 轴刻度标签
                        plt.xticks(rotation=45)

                        # 添加颜色条并设置标签
                        plt.colorbar(label='功率 (dB)')

                        # 自动调整布局以防止标签被截断
                        plt.tight_layout()

                        # 保存图像到指定路径
                        plt.savefig(tfr_image_path)

                        # 如果需要显示图像
                        if show_plots:
                            plt.show()

                        # 关闭图形以释放内存
                        plt.close()

    except Exception as e:
        logging.error(f"绘制癫痫发作数据时出错: {e}")


def save_seizure_info(seizure_info_list: List[Dict], seizure_per_minute: Dict, save_folder: str) -> None:
    """
    将癫痫发作信息保存到 Excel 文件中。
    """
    try:
        if not seizure_info_list:
            logging.info("未检测到任何癫痫发作，跳过保存癫痫发作信息。")
            return

        seizure_df = pd.DataFrame(seizure_info_list)

        # 创建每分钟发作频率的 DataFrame
        seizure_per_minute_df = pd.DataFrame({
            '分钟': seizure_per_minute['Minute'],
            '癫痫发作次数': seizure_per_minute['Seizure Count'],
            'UTC 时间': seizure_per_minute['UTC Time']
        })

        excel_path = os.path.join(save_folder, 'seizure_info.xlsx')
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            seizure_df.to_excel(writer, sheet_name='癫痫发作详情', index=False)
            seizure_per_minute_df.to_excel(writer, sheet_name='每分钟发作频率', index=False)

        logging.info(f"癫痫发作信息已保存到 {excel_path}")
    except Exception as e:
        logging.error(f"保存癫痫发作信息时出错: {e}")


# -------------------- 预测工具函数 --------------------

def apply_dynamic_threshold( amp: np.ndarray, rms: np.ndarray, model_classifications: np.ndarray,
                            amp_percentile: float = 95, amp_upper_factor: float = 2.5,
                            rms_lower_factor: float = 1.4) -> np.ndarray:
    """
    根据动态阈值筛选模型分类结果。
    """
    try:

        # # 设计高通滤波器
        def butter_highpass(cutoff, fs, order=5):
            nyq = 0.5 * fs
            normal_cutoff = cutoff / nyq
            b, a = butter(order, normal_cutoff, btype='high', analog=False)
            return b, a

        def highpass_filter(data, cutoff, fs, order=5):
            b, a = butter_highpass(cutoff, fs, order=order)
            y = filtfilt(b, a, data)
            return y

        # 示例参数
        fs = 100  # 采样频率
        cutoff = 1.0  # 截止频率
        # 高通滤波和计算绝对值
        filtered_signal = highpass_filter(rms, cutoff, fs)
        rms = np.abs(filtered_signal)
        amp_upper_threshold = amp_upper_factor * np.percentile(amp, amp_percentile)
        # rms_lower_threshold = rms_lower_factor * np.mean(rms)
        amp_lower_threshold = rms_lower_factor * np.percentile(amp, amp_percentile)


        # plt.plot(rms, label='RMS')
        # # 绘制阈值线
        # threshold_line_upper = np.full_like(rms, rms_upper_threshold)  # 创建与相同长度的阈值线
        # plt.plot(threshold_line_upper, label='Lower AMP Threshold', linestyle='--')
        # # 绘制阈值线
        # threshold_line_lower = np.full_like(rms, rms_lower_threshold)  # 创建与相同长度的阈值线
        # plt.plot(threshold_line_lower, label='Lower AMP Threshold', linestyle='--')
        # plt.show()


        model_classifications = np.where(amp <= amp_upper_threshold, model_classifications, 0)
        # plt.plot(model_classifications)
        # model_classifications = np.where(rms >= rms_lower_threshold, model_classifications, 0)
        model_classifications = np.where(amp >= amp_lower_threshold, model_classifications, 0)
        model_classifications = np.where((amp < 10) & (rms < 10), 0, model_classifications)

        return model_classifications
    except Exception as e:
        logging.error(f"应用动态阈值时出错: {e}")
        return model_classifications


# -------------------- RMS 因子优化函数 --------------------
def optimize_rms_lower_factor(
        model_path: str,
        data_list: List[str],
        epochlength: int,
        initial_rms_lower_factor: float = 1.0,
        step: float = 0.1,
        max_iterations: int = 20,
        precision_threshold: float = 0.95,
        specificity_threshold: float = 0.90
) -> float:
    """
    优化 RMS 因子以在期望的精确率和特异性范围内最大化性能。
    """
    try:
        rms_lower_factor = initial_rms_lower_factor
        best_candidates: List[Tuple[float, float, float]] = []

        rms_lower_factor_history = []
        precision_history = []
        accuracy_history = []
        specificity_history = []

        for iteration in range(1, max_iterations + 1):
            logging.info(
                f"开始 RMS 因子优化迭代 {iteration}/{max_iterations}，当前 rms_lower_factor={rms_lower_factor:.4f}"
            )
            precision, accuracy, specificity = evaluate_model_on_test_set(
                model_path, data_list, epochlength, rms_lower_factor=rms_lower_factor
            )
            logging.info(
                f"迭代 {iteration}: 精确率={precision:.4f}, 准确率={accuracy:.4f}, 特异性={specificity:.4f}"
            )

            rms_lower_factor_history.append(rms_lower_factor)
            precision_history.append(precision)
            accuracy_history.append(accuracy)
            specificity_history.append(specificity)

            # 检查精确率和特异性是否满足阈值
            if precision >= precision_threshold and specificity >= specificity_threshold:
                best_candidates.append((rms_lower_factor, accuracy, specificity))
                logging.info(
                    f"迭代 {iteration}: rms_lower_factor={rms_lower_factor:.4f} 满足精确率和特异性阈值。"
                )

            rms_lower_factor += step

        if best_candidates:
            # 选择最佳候选者
            best_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
            best_rms_lower_factor, best_accuracy, best_specificity = best_candidates[0]
            logging.info(
                f"最佳 RMS 因子 (精确率≥{precision_threshold}, 特异性≥{specificity_threshold}): "
                f"{best_rms_lower_factor:.4f} (准确率={best_accuracy:.4f}, 特异性={best_specificity:.4f})"
            )
        else:
            logging.warning(
                "未找到同时满足精确率和特异性阈值的 RMS 因子，返回默认的 rms_lower_factor。"
            )
            best_rms_lower_factor = initial_rms_lower_factor

        # 绘制 RMS 因子优化曲线
        plt.figure(figsize=(10, 6))
        plt.plot(
            rms_lower_factor_history,
            precision_history,
            label='精确率 (Precision)',
            color='blue',
            marker='o'
        )
        plt.plot(
            rms_lower_factor_history,
            accuracy_history,
            label='准确率 (Accuracy)',
            color='green',
            marker='x'
        )
        plt.plot(
            rms_lower_factor_history,
            specificity_history,
            label='特异性 (Specificity)',
            color='red',
            marker='s'
        )
        plt.xlabel('RMS 因子')
        plt.ylabel('评分')
        plt.title('RMS 因子优化过程')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        optimization_plot_path = os.path.join(
            os.path.dirname(model_path), 'rms_lower_factor_optimization.png'
        )
        plt.savefig(optimization_plot_path)
        plt.close()
        logging.info(f"RMS 因子优化图已保存到 {optimization_plot_path}")

        return best_rms_lower_factor

    except Exception as e:
        logging.error(f"优化 RMS 因子时出错: {e}")
        return initial_rms_lower_factor


# -------------------- 主函数 --------------------

def main():
    """
    主函数，配置路径和参数，并执行训练和分类流程。
    """
    try:
        import glob

        # 设备类型配置
        device = "DSI"  # 'DSI' 或 'AR4'

        # 数据目录配置
        # base_data_dir_to_train = os.path.join('D:', os.sep, 'Data', 'ExampleData', 'Sezuire', 'LabeledDataSet', 'DataSet', device)
        base_data_dir_to_train = r'C:\Users\shangchungang\Desktop\SeizureAnalyser\DSI'
        data_list_to_train = glob.glob(os.path.join(base_data_dir_to_train, '*.edf'))

        # base_data_dir_to_classify=r'D:\Data\AR4\ExampleData\Sezuire\LabeledDataSet\DataSet\AR4'
        base_data_dir_to_classify = r'C:\Users\shangchungang\Desktop\SeizureAnalyser\testdata'
        if not data_list_to_train:
            raise FileNotFoundError(f"在 {base_data_dir_to_train} 中未找到 EDF 文件。")

        logging.info(f"找到 {len(data_list_to_train)} 个 EDF 文件。")

        # 模型保存路径配置
        # model_dir = os.path.join('C:', os.sep, 'Users', 'xiguannan', 'PycharmProjects', 'AR-Analyser', 'AR_Analyser', 'Demo', 'SeizureCaputure', 'SeizureAnalyser', 'Model')
        model_dir = r'C:\Users\shangchungang\Desktop\SeizureAnalyser\model'
        # os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, f'model_best_{device}.pkl')

        # 配置参数
        # 配置参数
        config = {
            'device':device,
            'model_path': model_path,
            'data_list_to_train': data_list_to_train,
            'directory': base_data_dir_to_classify,
            'epoch_length': 3,
            'seizure_length_sec': 120,
            'output_file_path': os.path.join(os.path.dirname(data_list_to_train[0]), f"FeatureFor{device}.parquet"),
            'flags': {
                'train_model': True,      # 设置为 True 以训练模型
                'optimize_rms': False,     # 设置为 True 以优化 RMS 因子
                'show_plots': False,       # 设置为 True 以显示绘图
                'rms_lower_factor': 0.8,
                'amp_upper_factor': 2.5 # 默认 RMS 因子
            },
            'min_no_seizure_epochs': 3,   # 判定为新的癫痫发作所需的最小非发作 epoch 数
            'ylim': [-500, 500],            # 原始数据的 y 轴范围
            'offset': 0                      # 绘图的时间偏移量（秒）
        }

        # 解包配置
        model_path = config['model_path']
        data_list_to_train = config['data_list_to_train']
        output_file_path = config['output_file_path']
        directory = config['directory']
        epoch_length = config['epoch_length']
        seizure_length_sec = config['seizure_length_sec']
        train_model = config['flags']['train_model']
        optimize_rms = config['flags']['optimize_rms']
        show_plots = config['flags']['show_plots']
        rms_lower_factor = config['flags']['rms_lower_factor']
        amp_upper_factor = config['flags']['amp_upper_factor']
        min_no_seizure_epochs = config['min_no_seizure_epochs']
        ylim = config['ylim']
        offset = config['offset']
        device=config['device']

        # 训练模型
        if train_model:
            train_and_evaluate_model(
                model_path=model_path,
                data_list=data_list_to_train,
                output_file_path=output_file_path,
                epochlength=epoch_length,
                rms_lower_factor=rms_lower_factor,
                amp_upper_factor=amp_upper_factor,
                show_plots=show_plots,
                device=device

            )

        # 优化 RMS 因子
        if optimize_rms:
            best_rms_lower_factor = optimize_rms_lower_factor(
                model_path=model_path,
                data_list=data_list_to_train,
                epochlength=epoch_length
            )
            logging.info(f"最佳 RMS 因子: {best_rms_lower_factor}")
            rms_lower_factor = best_rms_lower_factor

        logging.info(f"使用的 RMS 因子: {rms_lower_factor}")

        # 使用模型分类新数据
        classify_new_data_directory(
            model_path=model_path,
            directory=directory,
            epoch_length=epoch_length,
            seizure_length_sec=seizure_length_sec,
            rms_lower_factor=rms_lower_factor,
            amp_upper_factor=amp_upper_factor,
            show_plots=show_plots,
            ylim=ylim,
            min_no_seizure_epochs=min_no_seizure_epochs,
            offset=offset,
            device=device
        )

    except Exception as e:
        logging.error(f"主函数执行时出错: {e}")

if __name__ == '__main__':
    main()