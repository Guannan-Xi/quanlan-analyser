import matplotlib.pyplot as plt
import mne
import pyedflib
import numpy as np
from datetime import datetime

# 使用MNE读取EDF文件
edf_file_path = r'D:\Data\AR4\HStech\20240626\m10.0001\m10.0001.edf'
edf_file_path = r'D:\Data\AR4\HStech\20240626\m13.0001\m13.0001.edf'
raw = mne.io.read_raw_edf(edf_file_path, preload=True)

# 获取数据和采样率
data = raw.get_data()*1000*1000
sfreq = raw.info['sfreq']
n_channels = raw.info['nchan']
ch_names = raw.info['ch_names']

# 获取开始时间
if raw.info['meas_date'] is not None:
    meas_date = raw.info['meas_date']
    # 检查是否为datetime对象，否则进行转换
    if not isinstance(meas_date, datetime):
        meas_date = datetime.utcfromtimestamp(meas_date)
    startdate_str = meas_date
else:
    startdate_str = ''

# 创建一个新的EDF文件并设置通道信息
edf_writer = pyedflib.EdfWriter('your_output_file.edf', n_channels, file_type=pyedflib.FILETYPE_EDFPLUS)

# 设置header信息
header = {
    'technician': '',
    'recording_additional': '',
    'patientname': '',
    'patient_additional': '',
    'patientcode': '',
    'equipment': '',
    'admincode': '',
    'sex': '',
    'startdate': startdate_str,
    'birthdate': '',
    'recording_date': ''
}

edf_writer.setHeader(header)

# 设置通道信息
channel_info = []
for i, ch in enumerate(ch_names):
    dmin, dmax = -32768, 32767  # 默认的数字最小值和最大值
    pmin, pmax = data[i].min(), data[i].max()  # 每个通道的物理最小值和最大值
    transducer = ''
    dimension = 'uV'
    channel_info.append({
        'label': ch,
        'dimension': dimension,
        'samplefrequency': sfreq,
        'physical_min': pmin,
        'physical_max': pmax,
        'digital_min': dmin,
        'digital_max': dmax,
        'transducer': transducer,
        'prefilter': ''
    })

edf_writer.setSignalHeaders(channel_info)
plt.plot(data[0])
plt.show()
edf_writer.writeSamples(data)
# # 写入信号数据
# for i in range(n_channels):
#     print(f"Writing data for channel {i} with shape {data[i, :].shape}")  # 调试信息
#     edf_writer.writeSamples(data[i, :])

# 关闭文件
edf_writer.close()

print('修改后的数据已保存')

