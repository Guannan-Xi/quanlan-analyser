from .IDataFormat import IDataFormat, IChannelInfo
import numpy as np
import os
import time
from datetime import datetime
from .data2edf import EdfHandle

config = {
    'acc':(3,5, 50),
    'eeg':(2,50,500),
    'emg':(8,10,88)
}

def decode_data(path:str)->IDataFormat:
    ret = IDataFormat()
    f =  open(path, 'rb')
    f.seek(21, 0)
    SampleRate = int.from_bytes(f.read(4), byteorder='little', signed=False)
    f.seek(30, 0)
    ST_Y = int.from_bytes(f.read(2), byteorder='little', signed=False)
    ST_M = int.from_bytes(f.read(1), byteorder='little', signed=False)
    ST_D = int.from_bytes(f.read(1), byteorder='little', signed=False)
    ST_H = int.from_bytes(f.read(1), byteorder='little', signed=False)
    ST_Min = int.from_bytes(f.read(1), byteorder='little', signed=False)
    ST_S = int.from_bytes(f.read(1), byteorder='little', signed=False)
    ST_ms = int.from_bytes(f.read(2), byteorder='little', signed=False)
    ST = [ST_Y, ST_M, ST_D, ST_H, ST_Min, ST_S, ST_ms, 0, 0]
    StartTime = list(ST)
    secs = time.mktime(tuple(StartTime))
    
    if path.endswith('.acc'):
        def trans_func(v:int):
            return v - 0x7FFF
            # return v if v & 0xF000 == 0 else v - 65536
        
        type = config['acc']
        channel_count = type[0]
        channel_info = [IChannelInfo() for i in range(channel_count)]
        label = ['x', 'y', 'z']
        for i in range(len(channel_info)):
            channel_info[i].desc = IChannelInfo.gene_desc(label[i], 'mG', SampleRate, 4096, -4096, 2047*4, -2048*4)
    elif path.endswith('.eeg'):
        def trans_func(v:int):
            return v - 0x7FFF
        type = config['eeg']
        channel_count = type[0]
        channel_info = [IChannelInfo() for i in range(channel_count)]
        for i in range(len(channel_info)):
            channel_info[i].desc = IChannelInfo.gene_desc(str(i), 'uV', SampleRate, 13000, -13000, 32767, -32768)
    elif path.endswith('.emg'):
        def trans_func(v:int):
            return v - 0x7FFF
        type = config['emg']
        channel_count = type[0]
        channel_info = [IChannelInfo() for i in range(channel_count)]
        for i in range(len(channel_info)):
            channel_info[i].desc = IChannelInfo.gene_desc(str(i), 'uV', type[2], 13000, -13000, 32767, -32768)
    else:
        raise Exception('not support trans')
    
    ch_count = channel_count

    f.seek(0x5A, 0)
    offset = np.fromfile(f, dtype='<u4', count=1)
    f.seek(int(offset[0]))
    data_all = f.read()
    pkg_size = 8 + 2 * ch_count * type[1]
    print('pkg count ', len(data_all)/pkg_size)
    ch_data = [[] for i in range(ch_count)]
    base_data = []
    for i in range(0, len(data_all), pkg_size):
        buf = data_all[i + 8:i + pkg_size]
        # one_data = np.frombuffer(buf, dtype='<u2')
        one_data = [trans_func(int.from_bytes(buf[i:i + 2], byteorder='little', signed=False)) for i in range(0, len(buf), 2)]
        base_data += one_data
    time_start = time.time()
    val = np.array(base_data, dtype='i2').reshape(int(len(base_data)/ch_count) , ch_count).T
    ch_data = []
    for i in range(ch_count):
        ch_data.append(list(val[i]))
    time_use = time.time() - time_start
    ret = IDataFormat()
    ret.start_time = datetime.fromtimestamp(secs)
    for i in range(ch_count):
        channel_info[i].data = ch_data[i]
        ret.channels.append(channel_info[i])
    return ret


def write_edf(data:IDataFormat, out_name):
    handle = EdfHandle()
    for ch in data.channels:
        c = handle.add_channel(**ch.desc)
        c.set_data(np.array(ch.data))
    handle.export_edf(out_name, data.start_time)
    
def convert(conver_name, export_name):

    write_edf(decode_data(conver_name), export_name)