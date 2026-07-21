import mne
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import pyarrow as pa
import pyarrow.parquet as pq
import os
import numpy as np
import pandas as pd
import mne
import matplotlib.pyplot as plt
import pyarrow as pa
import pyarrow.parquet as pq

# 读取 EDF 文件
edf_file_path = r'D:\Data\AR4\HStech\20240626\m01.0001\m010001_r_labeled_edited.edf'
raw = mne.io.read_raw_edf(edf_file_path, preload=True)

# 对 raw 对象进行 0.5~35 Hz 的滤波
raw.filter(0.5, 35)

# 获取注释
annotations = raw.annotations
sfreq = raw.info['sfreq']
channel_names = raw.ch_names

# 获取最后一个 onset 时间并截取数据
last_onset = annotations.onset[-1]
raw.crop(tmax=last_onset)

# 定义窗口长度（例如：3 秒）
window_length_sec = 3
window_length_samples = int(window_length_sec * sfreq)

# 初始化数据列表
data_segments = []
labels = []

# 遍历注释，根据描述筛选并分别存储数据段和标签
for i in range(len(annotations) - 1):
    onset = annotations.onset[i]
    next_onset = annotations.onset[i + 1]
    description = annotations.description[i]

    start_sample = int(onset * sfreq)
    stop_sample = int(next_onset * sfreq)

    # 确定标签
    label = 'S' if description == '0' else 'NS'

    # 提取并切分数据段
    for start in range(start_sample, stop_sample, window_length_samples):
        end = min(start + window_length_samples, stop_sample)
        data_segment, _ = raw[:, start:end]

        # 如果片段长度不够，重复前一部分数据
        if data_segment.shape[1] < window_length_samples:
            repeat_length = window_length_samples - data_segment.shape[1]
            repeat_segment = np.tile(data_segment[:, :repeat_length], (1, (repeat_length // data_segment.shape[1]) + 1))
            data_segment = np.hstack((data_segment, repeat_segment[:, :repeat_length]))

        data_segments.append(data_segment.flatten())
        labels.append(label)

# 将数据段和标签转换为 DataFrame
df = pd.DataFrame(data_segments)
df['label'] = labels

# 保存通道名称和采样率到 Parquet 文件
metadata = {
    b'channel_names': ','.join(channel_names).encode(),
    b'sample_rate': str(sfreq).encode()
}

# 生成保存 Parquet 文件的路径
edf_base_name = os.path.basename(edf_file_path).replace('.edf', '')
output_file_path = os.path.join(os.path.dirname(edf_file_path), f'{edf_base_name}_dataset.parquet')

# 使用 pyarrow 将 DataFrame 和元数据写入 Parquet 文件
table = pa.Table.from_pandas(df)
table = table.replace_schema_metadata(metadata)
pq.write_table(table, output_file_path)
print(f"数据集已保存到 {output_file_path}")

# 读取保存的 Parquet 文件
table = pq.read_table(output_file_path)
df_loaded = table.to_pandas()
channel_names = table.schema.metadata[b'channel_names'].decode().split(',')
sample_rate = float(table.schema.metadata[b'sample_rate'].decode())

# 创建标签目录
parent_dir = os.path.dirname(edf_file_path)
label_dir = os.path.join(parent_dir, 'labels')
ns_dir = os.path.join(label_dir, 'NS')
s_dir = os.path.join(label_dir, 'S')
os.makedirs(ns_dir, exist_ok=True)
os.makedirs(s_dir, exist_ok=True)

# 绘制并保存每个数据片段
for index, row in df_loaded.iterrows():
    data_segment = row.drop('label').values.reshape(-1, window_length_samples)
    label = row['label']

    plt.figure()
    plt.plot(data_segment.T)
    plt.title(f"Segment {index} - {label}")
    plt.xlabel('Samples')
    plt.ylabel('Amplitude')

    if label == 'NS':
        plt.savefig(os.path.join(ns_dir, f"Segment_{index}.png"))
    else:
        plt.savefig(os.path.join(s_dir, f"Segment_{index}.png"))

    plt.close()

print("所有数据片段均已绘制并保存到相应的目录中。")

