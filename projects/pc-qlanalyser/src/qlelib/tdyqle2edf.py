import numpy as np
import pyedflib
from datetime import datetime
import struct
from .data2edf import EdfHandle
from .pystruct import CStruct
from . import tdyqledef as qledef
import os
from datetime import datetime

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

def parser0(data_list, anno_list, data):
    index = data[:8]
    data_list[0].append(int.from_bytes(data[8:10], byteorder='little', signed=True))
    data_list[1].append(int.from_bytes(data[10:12], byteorder='little', signed=True))
    data_list[2].append(int.from_bytes(data[12:14], byteorder='little', signed=True))


def parser1(data_list, anno_list, data):
    anno = qledef.F_Annotation.unpack(data)
    anno_list.append((anno['anno_ns']/100/1000, -1, charlist2str(anno['anno'])))

def parser(data_list, anno_list, t, data):
    parser_map = {0:parser0, 1:parser1}
    parser_map[t](data_list, anno_list, data)

def covert(name, out_name = None):
    conver_name = name
    base_name = os.path.basename(conver_name)
    base_name, t = os.path.splitext(base_name)

    qle_data_size = os.path.getsize(conver_name)
    qle_data = open(conver_name, 'rb')
    header_data = qle_data.read(qledef.STHeader.sizeof_struct())
    tmp = qledef.STHeader.unpack(header_data)
    header_data += qle_data.read(tmp['header_len'] - len(header_data))
    header_data = qledef.STHeader.unpack(header_data)
    magic = charlist2str(header_data['magic'][:3])
    edf_handle = EdfHandle()
    channel_num = header_data['channel_count']

    edf = EdfHandle()
    edf_ch = []
    if header_data['start_time'] == 0:
        import re, time
        res = re.search(r'acc_(\d{6}_\d{6})\.fedf', conver_name)
        t = time.strptime('20' + res.group(1), '%Y%m%d_%H%M%S')
        t1 = time.mktime(t)
        t2 = time.gmtime(t1)
        header_data['start_time'] =  int(t1*1000)
        header_data['end_time'] += int(t1*1000)
    for i in range(channel_num):
        extra_data = header_data['info'][i]
        phy_max = int(float(charlist2str(extra_data['phy_max'])))
        phy_min = int(float(charlist2str(extra_data['phy_min'])))
        rejust_v = int( (extra_data['digital_max'] + 1 + extra_data['digital_min']) / 2)
        dig_max = extra_data['digital_max'] - rejust_v
        dig_min = extra_data['digital_min'] - rejust_v
        dimension = 'mG' #'charlist2str(extra_data['phy_unit'])'
        sample_rate = extra_data['sample_rate']
        ch = edf.add_channel(f'{magic}{i}', dimension, sample_rate, phy_max, phy_min, dig_max, dig_min)
        edf_ch.append(ch)
    pkg_size = int(sum([header_data['bype_per_point'] * header_data['packet_ms'] * extra_data['sample_rate']/1000 for extra_data in header_data['info']]))
    data_list = [[],[],[]]
    anno_list = []
    while True:
        def cal_bytes_match(ori:bytes, dst:bytes):
            res = ori[:]
            while True:
                try:
                    p = res.index(dst[0])
                except ValueError:
                    break
                else:
                    res = res[p:]
                    if res == dst[:len(res)]:
                        return res
                    else:
                        res = res[1:]
            return b''
                
        raw_bytes = qle_data.read(8)
        if len(raw_bytes) == 0:
            break
        t = int.from_bytes(raw_bytes[:4], byteorder='little', signed=False)
        pkg_len = int.from_bytes(raw_bytes[4:], byteorder='little', signed=False)
        if t == 1:
            print()
        flag1 = t == 0 and pkg_len != 0x16
        flag2 = t == 1 and pkg_len > 100
        flag3 = t != 1 and t != 0
        if flag1 or flag2 or flag3:
                end_flag = False
                while True:
                    res = cal_bytes_match(raw_bytes, b'\x00\x00\x00\x00\x16\x00\x00\x00')
                    if len(res) == 8:
                        t = int.from_bytes(raw_bytes[:4], byteorder='little', signed=False)
                        pkg_len = int.from_bytes(raw_bytes[4:], byteorder='little', signed=False)
                        break
                    else:
                        raw_bytes = raw_bytes[1:]
                        _ = qle_data.read(1)
                        if len(_) == 0:
                            end_flag = True
                            break
                        raw_bytes += _
                if end_flag:
                    break
                        
                        
            

        data = qle_data.read(pkg_len - 8)
        parser(data_list, anno_list, t, data)


    for i,ch in enumerate(edf_ch):
        ch.set_data(np.array(data_list[i], dtype=np.int16))
    for anno in anno_list:
        edf.add_annotation(anno[0]/10000, -1, anno[2])
    if out_name is None:
        export_name = f'{os.path.dirname(conver_name)}/{base_name}'
        if export_name[0] == '/':
            export_name = export_name[1:]
    else:
        export_name = out_name
    edf.export_edf(export_name, datetime.fromtimestamp(header_data['start_time']/1000))
    return export_name + '.edf'

def main():
    out_name = covert(r'D:\Downloads\11acc_230919_185802.fedf')
    print(f"export {out_name} success!")
     
if __name__ == '__main__':
    import sys
    if len(sys.argv) > 2:
        raise Exception("invailed argv!")
    elif len(sys.argv) == 2:
        print(f"start convert {sys.argv[1]}")
        out_name = covert(sys.argv[1])
        print(f"export {out_name} success!")
    else:
        raise Exception("no argv")
    