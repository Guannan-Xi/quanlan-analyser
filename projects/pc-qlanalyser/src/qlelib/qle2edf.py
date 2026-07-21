import numpy as np
import pyedflib
from datetime import datetime
import struct
from .data2edf import EdfHandle, pyedflib
from .pystruct import CStruct
from . import x7qledef
import os
from datetime import datetime
from .qle_sp_cal import get_qle_sample_rate
from .IDataFormat import IDataFormat, IChannelInfo
import re
from scipy import interpolate
from scipy import signal

class datalist:
    def __init__(self, max_size, dtype = np.int32):
        self.l = np.zeros(shape=max_size, dtype = dtype)
        self.len = 0
    
    def __len__(self):
        return self.len
    
    def append(self, v):
        self.l[self.len] = v
        self.len += 1

def charlist2str(c_list):
    if 0 in c_list:
        return bytes(c_list[:c_list.index(0)]).decode()
    else:
        return bytes(c_list).decode()
    
convert_config = {

}
ref_map = {
    0x2C:2000000,
    0x66:2000000,
    0x65:2500000,
}

def qle_clip(arr: np.ndarray, min, max):
    arr = np.round(arr)
    arr = np.clip(arr, min, max)
    return arr

def convert_config_clear():
    global convert_config
    convert_config = {}

def convert(conver_name, export_name):
    if 'sampleRate' in convert_config.keys():
        sample_rate = convert_config['sampleRate']
    else:
        sample_rate = get_qle_sample_rate(conver_name)

    qle_data_size = os.path.getsize(conver_name)
    print('real sp', sample_rate)
    qle_data = open(conver_name, 'rb')
    header_data = qle_data.read(x7qledef.STHeader.sizeof_struct())
    extra_data = qle_data.read(x7qledef.T_RecoderFileExtraData.sizeof_struct())

    header_data = x7qledef.STHeader.unpack(header_data)
    extra_data = x7qledef.T_RecoderFileExtraData.unpack(extra_data)
    print(header_data)
    magic = charlist2str(header_data['magic'][:3])
    channel_num = header_data['channel'][0]
    assert channel_num in [3, 7, 0xF]
    channel_num = bin(channel_num).count('1')

    pre_offset = extra_data['prefix_data_offset']
    Resolution = header_data['bype_per_point']
    PackageDataLength = extra_data['prefix_data_offset'] + channel_num * header_data['points_pre_package'] * header_data['bype_per_point']

    pkg_count = (qle_data_size - header_data['header_len'])/ PackageDataLength
    # pkg_count = int(pkg_count)
    assert pkg_count % 1 == 0
    pkg_count = int(pkg_count)
    anno = []
    
    start_time = header_data['start_time']
    def get_real_ms(i, sp):
        time_ms = start_time + 1000.0 * i * header_data['points_pre_package'] / sp
        return time_ms
    
    def pkgIndex2edfonset(i, real_index, mis_ms):
        time_ms = get_real_ms(i, int(sample_rate)) - start_time
        t = time_ms/1000
        real_ms = get_real_ms(real_index, sample_rate)
        real_t = datetime.fromtimestamp( real_ms /1000)
        ret = t,-1, str(mis_ms) + '_' + real_t.strftime('%y%m%d%H%M%S') + ':%d' % (real_t.microsecond / 1000)
        return ret
    time_ms_mis = 0
    # DataTotal = []
    all_ch_points_per_pkg = channel_num * header_data['points_pre_package']
    DataTotal = np.zeros((pkg_count, all_ch_points_per_pkg), dtype=np.int32)
    
    for i in range(pkg_count):
        PackageT = qle_data.read(extra_data['prefix_data_offset'])
        assert PackageT[0] == 0xA5 and PackageT[1] == 0x5A, 'file format is not correct'
        index = int.from_bytes(PackageT[10:14], byteorder = 'little', signed=False)
        time_ms = int.from_bytes(PackageT[2:10], byteorder = 'little', signed=False)
        file_pkg_id = int.from_bytes(PackageT[14:18], byteorder = 'little', signed=False)
        assert file_pkg_id == i, 'file format is not correct'
        assert time_ms >= 0 and time_ms <= (1000*3600*24*30), 'file format is not correct'
        if i > 1:
            d_i = index - last_index
            d_t = time_ms - last_time_ms
            if (d_i > 3 or d_i < 1) or d_t > 600:
                time_ms_mis += d_t
                real_index = i + (time_ms_mis) / 1000 *  (sample_rate / header_data['points_pre_package'])
                anno.append(pkgIndex2edfonset(i, real_index, d_t))

        last_index = index
        last_time_ms = time_ms
        DataTotal[i] = np.array(np.fromfile(qle_data, dtype=np.uint16,count=all_ch_points_per_pkg), dtype=np.int32)
    DataTotal = DataTotal.reshape(-1, channel_num).T
    DataTotal = np.ascontiguousarray(DataTotal)

    qle_data.close()
    del qle_data
    edf = EdfHandle()
    for a in anno:
        edf.add_annotation(*a)
    for i in range(channel_num):
        if 'phy_max' in convert_config.keys() and 'phy_min' in convert_config.keys():
            phy_max = convert_config['phy_max']
            phy_min = convert_config['phy_min']
        else:
            if magic =='EEG':
                h_type = extra_data['header_type']
                if h_type in ref_map.keys():
                    phy_max = round(ref_map[h_type] / 48 / 4)
                    phy_min = -phy_max
                    print('ar2 modify')
                else:
                    phy_max = int(charlist2str(extra_data['phy_max']))
                    phy_min = int(charlist2str(extra_data['phy_min']))
            else:
                phy_max = int(charlist2str(extra_data['phy_max']))
                phy_min = int(charlist2str(extra_data['phy_min']))

        rejust_v = int( (extra_data['digital_max'] + 1 + extra_data['digital_min']) / 2)
        dig_max = extra_data['digital_max'] - rejust_v
        dig_min = extra_data['digital_min'] - rejust_v
        dimension = charlist2str(extra_data['phy_unit'])
        ch = edf.add_channel(f'{magic}{i}', dimension, int(sample_rate), phy_max, phy_min, dig_max, dig_min)
        data = DataTotal[i]
        if rejust_v != 0:
            data -= rejust_v
        if magic == 'EEG':
            b_hp, a_hp = signal.butter(3, 1 / (sample_rate/ 2), 'highpass')
            data = signal.lfilter(b_hp, a_hp, data)
            data = qle_clip(data, ch.ch_dict['digital_min'], ch.ch_dict['digital_max'])
            # for j in range(len(data)):
            #     data[j] = round(data[j])
            #     data[j] = min(ch.ch_dict['digital_max'], data[j])
            #     data[j] = max(ch.ch_dict['digital_min'], data[j])
            data = data.astype(np.int16)
        ch.set_data(data)
        del data
    handle = edf.get_edf_handle(export_name)
    handle.setEquipment(charlist2str(extra_data['box_mac']) + '_' + charlist2str(extra_data['header_mac']))
    handle.setStartdatetime(datetime.fromtimestamp(header_data['start_time']/1000))
    # handle.setPatientName(charlist2str(extra_data['header_mac']))
    edf._export(handle)
    convert_config_clear()

def get_qle_ch_info(conver_name:str, need_sp = None):
    qle_data_size = os.path.getsize(conver_name)
    qle_data = open(conver_name, 'rb')
    header_data = qle_data.read(x7qledef.STHeader.sizeof_struct())
    extra_data = qle_data.read(x7qledef.T_RecoderFileExtraData.sizeof_struct())

    header_data = x7qledef.STHeader.unpack(header_data)
    extra_data = x7qledef.T_RecoderFileExtraData.unpack(extra_data)
    print(header_data)
    magic = charlist2str(header_data['magic'][:3])
    channel_num = header_data['channel'][0]
    assert channel_num in [3, 7, 0xF]
    channel_num = bin(channel_num).count('1')
    sample_rate = need_sp if need_sp is not None else header_data['sample_rate']
    pre_offset = extra_data['prefix_data_offset']
    Resolution = header_data['bype_per_point']
    PackageDataLength = extra_data['prefix_data_offset'] + channel_num * header_data['points_pre_package'] * header_data['bype_per_point']

    pkg_count = (qle_data_size - header_data['header_len'])/ PackageDataLength
    # pkg_count = int(pkg_count)
    assert pkg_count % 1 == 0
    pkg_count = int(pkg_count)

    all_ch_points_per_pkg = channel_num * header_data['points_pre_package']
    DataTotal = np.zeros((pkg_count, all_ch_points_per_pkg), dtype=np.int32)
    
    for i in range(pkg_count):
        PackageT = qle_data.read(extra_data['prefix_data_offset'])
        assert PackageT[0] == 0xA5 and PackageT[1] == 0x5A, 'file format is not correct'
        time_ms = int.from_bytes(PackageT[2:10], byteorder = 'little', signed=False)
        file_pkg_id = int.from_bytes(PackageT[14:18], byteorder = 'little', signed=False)
        assert file_pkg_id == i, 'file format is not correct'
        assert time_ms >= 0 and time_ms <= (1000*3600*24*30), 'file format is not correct'
        DataTotal[i] = np.array(np.fromfile(qle_data, dtype=np.uint16,count=all_ch_points_per_pkg), dtype=np.int32)

    DataTotal = DataTotal.reshape(-1, channel_num).T
    DataTotal = np.ascontiguousarray(DataTotal)
    qle_data.close()
    del qle_data
    i_data = IDataFormat()
    i_data.set_start_time(datetime.fromtimestamp(header_data['start_time']/1000))
    for i in range(channel_num):
        if 'phy_max' in convert_config.keys() and 'phy_min' in convert_config.keys():
            phy_max = convert_config['phy_max']
            phy_min = convert_config['phy_min']
        else:
            if magic =='EEG':
                phy_max = int(charlist2str(extra_data['phy_max']))
                phy_min = int(charlist2str(extra_data['phy_min']))
                if extra_data['header_type'] != 0x65:
                    phy_max = phy_max * 20/25
                    phy_min = phy_min * 20/25
                    print('ar2 modify')
            else:
                phy_max = int(charlist2str(extra_data['phy_max']))
                phy_min = int(charlist2str(extra_data['phy_min']))

        rejust_v = int( (extra_data['digital_max'] + 1 + extra_data['digital_min']) / 2)
        dig_max = extra_data['digital_max'] - rejust_v
        dig_min = extra_data['digital_min'] - rejust_v
        dimension = charlist2str(extra_data['phy_unit'])
        desc = IChannelInfo.gene_desc(f'{magic}{i}', dimension, round(sample_rate), phy_max, phy_min, dig_max, dig_min)
        data = DataTotal[i]
        if rejust_v != 0:
            data -= rejust_v
        if magic == 'EEG':
            b_hp, a_hp = signal.butter(3, 1 / (sample_rate/ 2), 'highpass')
            data = signal.lfilter(b_hp, a_hp, data)
            data = qle_clip(data, desc['digital_min'], desc['digital_max'])
            # for j in range(len(data)):
            #     data[j] = round(data[j])
            #     data[j] = min(desc['digital_max'], data[j])
            #     data[j] = max(desc['digital_min'], data[j])
            data = data.astype(np.int16)
        i_data.add_channel(data, desc)
    return header_data, extra_data, i_data

def acc_resample(i_data:IDataFormat, rate:float, after_sample_rate:int = None):
    for i in range(len(i_data.channels)):
        d = i_data.channels[i].data
        f = interpolate.interp1d(range(len(d)), d, kind='quadratic')
        tnew = np.linspace(0, len(d) - 1, round(len(d) * rate))
        xnew = f(tnew)
        xnew = qle_clip(xnew, i_data.channels[i].desc['digital_min'], i_data.channels[i].desc['digital_max'])
        # for j in range(len(xnew)):
        #     xnew[j] = round(xnew[j])
        #     xnew[j] = min(i_data.channels[i].desc['digital_max'], xnew[j])
        #     xnew[j] = max(i_data.channels[i].desc['digital_min'], xnew[j])
        i_data.channels[i].data = xnew.astype(np.int16)
        if after_sample_rate is not None:
            i_data.channels[i].desc['sample_rate'] = after_sample_rate
        else:
            i_data.channels[i].desc['sample_rate'] *= rate
            i_data.channels[i].desc['sample_rate'] = round(i_data.channels[i].desc['sample_rate'])
    return i_data

def convert_dir(file_dict:dict, export_name:str):
    assert 'EEG' in file_dict.keys(), 'EEG not in file_dict'
    if 'sampleRate' in convert_config.keys():
        eeg_sample_rate = convert_config['sampleRate']
    else:
        eeg_sample_rate = get_qle_sample_rate(file_dict['EEG'])
    print('real sp', eeg_sample_rate)
    eeg_sample_rate = round(eeg_sample_rate)
    header_data, extra_data, eeg_i_data = get_qle_ch_info(file_dict['EEG'], eeg_sample_rate)
    anno = []
    if 'TRI' in file_dict.keys():
        with open(file_dict['TRI'], 'r') as f:
            con = f.read()
        res = re.findall(r'\((\d+)\)(\d+),pkg:(\d+)\((\d+) ms\) ([^\r\n]*)\r*\n', con)
        real_res = []
        for r in res:
            r = list(r)
            for i in range(len(r)):
                try:
                    r[i] = int(r[i])
                except Exception as e:
                    pass
            rr = {}
            rr['ms_stamp'] = r[0]
            rr['ms'] = r[1]
            rr['point_count'] = (r[2] - 1)*header_data['points_pre_package'] + int(r[3] * eeg_sample_rate/1000) 
            rr['anno'] = str(r[4])
            real_res.append(rr)
        for r in real_res:
            anno.append((r['point_count']/eeg_sample_rate, -1, r['anno']))
    if 'SW' in file_dict.keys():
        with open(file_dict['SW'], 'r') as f:
            lines = f.readlines()
        real_res = []
        for l in lines:
            rr = {}
            res = re.search(r'(NoSti,Stage:[-\d]+),point count: (\d+)', l)
            if res is None:
                res = re.search(r'point count: (\d+)\s+(\w[\w :\(\)]+)', l)
                if res is not None:
                    rr['point_count'] = int(res.group(1))
                    rr['anno'] = res.group(2)
            else:
                rr['point_count'] = int(res.group(2))
                rr['anno'] = res.group(1)
            if len(rr) > 0:
                real_res.append(rr)
        for r in real_res:
            anno.append((r['point_count']/eeg_sample_rate, -1, r['anno']))
    edf = EdfHandle()
    for a in anno:
        edf.add_annotation(*a)
    for i_ch in eeg_i_data.channels:
        ch = edf.add_channel(**i_ch.desc)
        ch.set_data(i_ch.data)
    start_time = eeg_i_data.start_time
    del eeg_i_data
    if 'ACC' in file_dict.keys():
        _, __, acc_i_data = get_qle_ch_info(file_dict['ACC'], round(eeg_sample_rate/10))
        acc_i_data = acc_resample(acc_i_data, 10, eeg_sample_rate)
    else:
        acc_i_data = IDataFormat()
    for i_ch in acc_i_data.channels:
        ch = edf.add_channel(**i_ch.desc)
        ch.set_data(i_ch.data)
    del acc_i_data
    handle = edf.get_edf_handle(export_name)
    handle.setEquipment(charlist2str(extra_data['box_mac']) + '_' + charlist2str(extra_data['header_mac']))
    handle.setStartdatetime(start_time)
    # handle.setPatientName(charlist2str(extra_data['header_mac']))
    edf._export(handle)
    convert_config_clear()
if __name__ == '__main__':
    conver_name = r'C:\Users\fengxinan\Downloads\14705_1705387031317.eeg.eeg'
    convert(conver_name, 'tst2')



    