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
def convert_config_clear():
    global convert_config
    convert_config = {}

def convert(conver_name, export_name):
    if 'sampleRate' in convert_config.keys():
        sample_rate = convert_config['sampleRate']
    else:
        sample_rate = get_qle_sample_rate(conver_name)

    print('real sp', sample_rate)
    qle_data_size = os.path.getsize(conver_name)
    qle_data = open(conver_name, 'rb')
    header_data = qle_data.read(x7qledef.STHeader.sizeof_struct())
    extra_data = qle_data.read(x7qledef.T_RecoderFileExtraData.sizeof_struct())

    header_data = x7qledef.STHeader.unpack(header_data)
    extra_data = x7qledef.T_RecoderFileExtraData.unpack(extra_data)
    print(header_data)
    magic = charlist2str(header_data['magic'][:3])
    channel_num = header_data['channel'][0]
    assert channel_num in [3, 7]
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
    DataTotal = []
    for i in range(pkg_count):
        PackageT = qle_data.read(PackageDataLength)
        index = int.from_bytes(PackageT[10:14], byteorder = 'little', signed=False)
        time_ms = int.from_bytes(PackageT[2:10], byteorder = 'little', signed=False)
        if i > 1:
            d_i = index - last_index
            d_t = time_ms - last_time_ms
            if (d_i > 3 or d_i < 1) or d_t > 600:
                time_ms_mis += d_t
                real_index = i + (time_ms_mis) / 1000 *  (sample_rate / header_data['points_pre_package'])
                anno.append(pkgIndex2edfonset(i, real_index, d_t))

        last_index = index
        last_time_ms = time_ms
        PackageT = PackageT[pre_offset:]
        for j in range(int(len(PackageT) // Resolution)):
            DataT = int.from_bytes(PackageT[j * Resolution:j * Resolution + Resolution], byteorder='little',
                                    signed=False)
            DataTotal.append(DataT)

    DataTotal = np.array(DataTotal).reshape(-1, channel_num).T
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
                phy_max = int(charlist2str(extra_data['phy_max']))
                phy_min = int(charlist2str(extra_data['phy_min']))
                if extra_data['header_type'] == 0x2C:
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
        ch = edf.add_channel(f'{magic}{i}', dimension, int(sample_rate), phy_max, phy_min, dig_max, dig_min)
        data = DataTotal[i]
        if rejust_v != 0:
            data -= rejust_v
        ch.set_data(data)
        del data
    handle = edf.get_edf_handle(export_name)
    handle.setEquipment(charlist2str(extra_data['box_mac']) + '_' + charlist2str(extra_data['header_mac']))
    # handle.setPatientName(charlist2str(extra_data['header_mac']))
    edf._export(handle, datetime.fromtimestamp(header_data['start_time']/1000))
    convert_config_clear()
    
if __name__ == '__main__':
    conver_name = r'C:\Users\fengxinan\Downloads\14705_1705387031317.eeg.eeg'
    convert(conver_name, 'tst2')



    