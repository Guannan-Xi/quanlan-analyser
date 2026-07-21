import numpy as np
from datetime import datetime
import struct
from . import x7qledef
import os
from datetime import datetime

class SampRateCal:
    def __init__(self, start_stamp):
        self.start_stamp = start_stamp
        self.last_index = None
        self.pkg = []
        self.pkg_list = []

    def get_time_str(self, ms) ->str:
        from datetime import datetime
        t = datetime.fromtimestamp(  (self.start_stamp + ms) / 1000)
        return t

    def add_index(self, index, time_ms):
        if self.last_index == None:
            self.last_index = index
            self.pkg = [[index, time_ms]]
            self.pkg_list = []
        else:
            if index - self.last_index != 1:
                self.pkg_list.append(self.pkg)
                self.pkg = []
            self.pkg.append([index, time_ms])
            self.last_index = index

    def get_sp_list(self):
        if len(self.pkg) > 0:
            self.pkg_list.append(self.pkg)
            self.pkg = []
        self.sp_list = []
        for pkg in self.pkg_list:
            sub_len = 10*600
            for i in range(0, len(pkg) - sub_len, sub_len):
                sub_data = pkg[i:i+sub_len]
                pkg_count = sub_data[-1][0] - sub_data[0][0]
                assert pkg_count == len(sub_data) - 1
                pkg_time = sub_data[-1][1] - sub_data[0][1]
                self.sp_list.append([self.get_time_str(sub_data[0][1]) ,pkg_count/pkg_time * 1000])
        return self.sp_list

def charlist2str(c_list):
    if 0 in c_list:
        return bytes(c_list[:c_list.index(0)]).decode()
    else:
        return bytes(c_list).decode()

def get_qle_box_header_mac(conver_name):
    qle_data = open(conver_name, 'rb')
    header_data = qle_data.read(x7qledef.STHeader.sizeof_struct())
    extra_data = qle_data.read(x7qledef.T_RecoderFileExtraData.sizeof_struct())
    header_data = x7qledef.STHeader.unpack(header_data)
    extra_data = x7qledef.T_RecoderFileExtraData.unpack(extra_data)
    qle_data.close()
    return extra_data['header_type'], charlist2str(extra_data['box_mac']), charlist2str(extra_data['header_mac'])

def get_qle_sample_rate(conver_name, draw = False):

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

    pkg_count = (qle_data_size - header_data['header_len'])/ (extra_data['prefix_data_offset'] + channel_num * header_data['bype_per_point'] * header_data['points_pre_package'])
    pkg_count = int(pkg_count)
    sp_cal = SampRateCal(header_data['start_time'])
    time_ms_l = []
    for i in range(pkg_count):
        _ = qle_data.read( extra_data['prefix_data_offset'])
        index = int.from_bytes(_[10:14], byteorder = 'little', signed=False)
        time_ms = int.from_bytes(_[2:10], byteorder = 'little', signed=False)
        time_ms_l.append(time_ms)
        if i > 1:
            sp_cal.add_index(index, time_ms)
        __ = header_data['points_pre_package'] * channel_num * header_data['bype_per_point']
        qle_data.read(__)
    qle_data.close()
    del qle_data

    sp_rates = [p for p in sp_cal.get_sp_list()]
    t = [v[0] for v in sp_rates]
    sp = [v[1] for v in sp_rates]
    if draw:
        import matplotlib.pyplot as plt
        plt.plot(t, sp)
        plt.show()
    
    if len(sp) > 0:
        return np.mean(sp) * header_data['points_pre_package']
    else:
        if extra_data['header_type'] == 0x2C:
            return 515
        else:
            return 500


if __name__ == '__main__':
    conver_name = r'C:\Users\fengxinan\Downloads\13312_eeg.eeg'
    sp = get_qle_box_header_mac(conver_name)
    print(sp)

