
from .qlelib.IDataFormat import IDataFormat, IChannelInfo
import numpy as np
from datetime import datetime, timedelta
import os
from .qlelib.qle_sp_cal import get_qle_sample_rate,get_qle_box_header_mac

config = {
    'acc':(3,5, 50),
    'eeg':(2,50,500),
    'emg':(8,10,88)
}

ref_map = {
    'AR2':2000000,
    'AR4':2000000,
    'X8':2500000,
    'X7':2500000
}
'''
def decode_dataX8(path:str)->IDataFormat:
    ret = IDataFormat()
    if path.endswith('.acc'):
        def trans_func(v:int):
            return v - 0x7FFF
            # return v if v & 0xF000 == 0 else v - 65536

        type = config['acc']
        channel_count = type[0]
        channel_info = [IChannelInfo() for i in range(channel_count)]
        for i in range(len(channel_info)):
            channel_info[i].desc = IChannelInfo.gene_desc('acc%d' % (i + 1), 'mG', type[2], 4096, -4096, 2047, -2048)
    elif path.endswith('.eeg'):
        def trans_func(v:int):
            return v - 0x7FFF
        type = config['eeg']
        channel_count = type[0]
        channel_info = [IChannelInfo() for i in range(channel_count)]
        for i in range(len(channel_info)):
            channel_info[i].desc = IChannelInfo.gene_desc('eeg%d' % (i + 1), 'uV', type[2], 13000*ref_map[head_type]/2500000, -13000*ref_map[head_type]/2500000, 32767, -32768)
    else:
        raise Exception('not support trans')
    ch_count = channel_count
    DataType = path.split('.')[-1]

    with open(path, 'rb') as f:
        TotalLen =  f.seek(0, os.SEEK_END)
        f.seek(0, 0)
        f.seek(17, 0)
        PackageCount = int.from_bytes(f.read(4), byteorder='little', signed=False)
        pointPerPkg = int.from_bytes(f.read(4), byteorder='little', signed=False)
        f.seek(16, 0)
        Resolution = int.from_bytes(f.read(1), byteorder='little', signed=False)

        f.seek(29, 0)
        SampleRate = int.from_bytes(f.read(4), byteorder='little', signed=False)
        st_stamp = int.from_bytes(f.read(8), byteorder='little', signed=False)
        et_stamp = int.from_bytes(f.read(8), byteorder='little', signed=False)

        PackageCount = 0
        et_stamp = 0
        f.seek(49, 0)
        channel_num = int.from_bytes(f.read(4), byteorder='little', signed=False)
        channel_num = bin(channel_num).count('1')
        f.seek(81, 0)
        DataOffSet = int.from_bytes(f.read(4), byteorder='little', signed=True)
        f.seek(93, 0)
        pre_offset = int.from_bytes(f.read(4), byteorder='little', signed=True)
        PackageDataLength = pre_offset + channel_num * pointPerPkg * Resolution
        if PackageCount == 0:
            PackageCount = (TotalLen - DataOffSet)/PackageDataLength
            PackageCount = int(PackageCount)

        ms_per_pkg = pointPerPkg/SampleRate*1000
        ms_new = 0
        f.seek(DataOffSet, 0)
        DataTotal = []
        for i in range(PackageCount):
  
            PackageT = f.read(PackageDataLength)
            PackageID = int.from_bytes(PackageT[10:14], byteorder='little', signed=False)
            ms_new = int.from_bytes(PackageT[2:10], byteorder='little', signed=False)
  

            PackageT = PackageT[pre_offset:]
            for j in range(int(len(PackageT) // Resolution)):
                DataT = int.from_bytes(PackageT[j * Resolution:j * Resolution + Resolution], byteorder='little',
                                        signed=False)
                DataTotal.append(DataT)
        if DataType== 'eeg':
            DataTotal = (np.array(DataTotal)-32768)*(ref_map[head_type] / 48/4/32768)
            DataTotal = DataTotal[0:len(DataTotal) // 2 * 2]
            DataTotal_T = DataTotal.reshape(-1, 2)
            DataTotal = []
            DataTotal.append(DataTotal_T[:, 0])
            DataTotal.append(DataTotal_T[:, 1])

        elif DataType == 'acc':
            DataTotal = np.array(DataTotal)
            DataTotal = DataTotal[0:len(DataTotal) // 3 * 3]
            DataTotal_T = DataTotal.reshape(-1, 3)
            DataTotal = []
            DataTotal.append(DataTotal_T[:, 0])
            DataTotal.append(DataTotal_T[:, 1])
            DataTotal.append(DataTotal_T[:, 2])
        


    ret = IDataFormat()
    for i in range(ch_count):
        channel_info[i].data = DataTotal[i]
        ret.channels.append(channel_info[i])
    return ret

def decode_dataX7(path:str)->IDataFormat:
    head_type = 'X7'
    ret = IDataFormat()
    if path.endswith('.acc'):
        def trans_func(v:int):
            return v - 0x7FFF
            # return v if v & 0xF000 == 0 else v - 65536

        type = config['acc']
        channel_count = type[0]
        channel_info = [IChannelInfo() for i in range(channel_count)]
        for i in range(len(channel_info)):
            channel_info[i].desc = IChannelInfo.gene_desc('acc%d' % (i + 1), 'mG', type[2], 4096, -4096, 2047, -2048)
    elif path.endswith('.eeg'):
        def trans_func(v:int):
            return v - 0x7FFF
        type = config['eeg']
        channel_count = type[0]
        channel_info = [IChannelInfo() for i in range(channel_count)]
        for i in range(len(channel_info)):
            channel_info[i].desc = IChannelInfo.gene_desc('eeg%d' % (i + 1), 'uV', type[2], 13000*ref_map[head_type]/2500000, -13000*ref_map[head_type]/2500000, 32767, -32768)
    else:
        raise Exception('not support trans')
    ch_count = channel_count
    f =  open(path, 'rb')
    f.read(0x5A)
    offset = np.fromfile(f, dtype='<u4', count=1)
    f.seek(int(offset[0]))
    data_all = f.read()
    pkg_size = 8 + 2 * ch_count * type[1]
    print('pkg count ', len(data_all)/pkg_size)
    ch_data = [[] for i in range(ch_count)]
    import time
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
    for i in range(ch_count):
        channel_info[i].data = ch_data[i]
        ret.channels.append(channel_info[i])
    return ret
    
'''


def eegIsX8(path):
    with open(path, 'rb') as f:
        f.seek(8, 0)
        _ = int.from_bytes(f.read(4), byteorder='little', signed=False)
        return _ > 300

g_BoxMac = ''
def get_box_mac():
    return g_BoxMac

class ShortList:
    def __init__(self, max_len, dtype):
        self.max_len = max_len
        self.dtype = dtype
        self.data = np.zeros(max_len, dtype=dtype)
        self.index = 0

    def append(self, data):
        self.data[self.index] = data
        self.index += 1

    def __isub__(self, other):
        if isinstance(other, int):
            self.data -= other
            return self
        else:
            raise Exception()

    def __iadd__(self, other):
        if isinstance(other, int):
            self.data += other
            return self
        else:
            raise Exception()
    def __imul__(self, other):
        if isinstance(other, int) or isinstance(other, float):
            self.data *= other
            return self
        else:
            raise Exception()
    def reshape(self, *args, **kwargs):
        return self.data.reshape(*args, **kwargs)
       
    def __len__(self):
        return self.index
    
    def __getitem__(self, item):
        return self.data[item]
    
    def __setitem__(self, key, value):
        self.data[key] = value

    def __iter__(self):
        return iter(self.data[:self.index])
    

def DataloaderX8(path:str, signed=False):  # for ACC-36727, the sign is False
    global g_BoxMac

    DataType = path.split('.')[-1]
    SampleRate = get_qle_sample_rate(path)
    type_int, box_mac, header_mac = get_qle_box_header_mac(path)
    SampleRate = int(SampleRate)
    print(box_mac, header_mac)
    g_BoxMac = box_mac + '_' + header_mac
    head_type = 'X8'

    if type_int == 0x2C:
        head_type = 'AR2'
        print('ar2 modify')
    elif type_int == 0x66:
        head_type = 'AR4'
        print('ar2 modify')

    with open(path, 'rb') as f:
        TotalLen =  f.seek(0, os.SEEK_END)
        f.seek(0, 0)
        f.seek(17, 0)
        PackageCount = int.from_bytes(f.read(4), byteorder='little', signed=False)
        pointPerPkg = int.from_bytes(f.read(4), byteorder='little', signed=False)
        f.seek(16, 0)
        Resolution = int.from_bytes(f.read(1), byteorder='little', signed=False)



        f.seek(29, 0)
        int.from_bytes(f.read(4), byteorder='little', signed=False)
        st_stamp = int.from_bytes(f.read(8), byteorder='little', signed=False)
        et_stamp = int.from_bytes(f.read(8), byteorder='little', signed=False)
        st_stamp = datetime.fromtimestamp(st_stamp/1000)

        PackageCount = 0
        et_stamp = 0
        def stamp2matarray(stamp:datetime):
            ST_Y = int(stamp.strftime('%Y'))
            ST_M = int(stamp.strftime('%m'))
            ST_D = int(stamp.strftime('%d'))
            ST_H = int(stamp.strftime('%H'))
            ST_Min = int(stamp.strftime('%M'))
            ST_S = int(stamp.strftime('%S'))
            ST_ms = int(stamp.strftime('%f'))/1000
            return np.array([ST_Y, ST_M, ST_D, ST_H, ST_Min, ST_S, ST_ms])
        ST = stamp2matarray(st_stamp)
        f.seek(49, 0)
        channel_num = int.from_bytes(f.read(4), byteorder='little', signed=False)
        channel_num = bin(channel_num).count('1')
        f.seek(81, 0)
        DataOffSet = int.from_bytes(f.read(4), byteorder='little', signed=True)
        f.seek(93, 0)
        pre_offset = int.from_bytes(f.read(4), byteorder='little', signed=True)
        PackageDataLength = pre_offset + channel_num * pointPerPkg * Resolution
        if PackageCount == 0:
            PackageCount = (TotalLen - DataOffSet)/PackageDataLength
            PackageCount = int(PackageCount)

        f.seek(DataOffSet, 0)
        ms_per_pkg = pointPerPkg/SampleRate*1000
        ms_new = 0
        DataTotal = ShortList(PackageCount * channel_num * pointPerPkg, dtype=np.float32)
        PackageIDs = ShortList(PackageCount, dtype=np.uint32)
        for i in range(PackageCount):
  
            PackageT = f.read(PackageDataLength)
            PackageID = int.from_bytes(PackageT[10:14], byteorder='little', signed=False)
            ms_new = int.from_bytes(PackageT[2:10], byteorder='little', signed=False)
  

            PackageT = PackageT[pre_offset:]
            for j in range(int(len(PackageT) // Resolution)):
                DataT = int.from_bytes(PackageT[j * Resolution:j * Resolution + Resolution], byteorder='little',
                                        signed=signed)
                DataTotal.append(DataT)
            PackageIDs.append(PackageID)
        if DataType== 'eeg':
            DataTotal -= 32768
            DataTotal *= (ref_map[head_type] / 48/4/32768)
            # DataTotal = DataTotal[0:len(DataTotal) // 2 * 2]
            DataTotal_T = DataTotal.reshape(-1, channel_num)
            DataTotal = []
            for i in range(channel_num):
                DataTotal.append(DataTotal_T[:, i])

        elif DataType == 'acc':
            DataTotal_T = DataTotal.reshape(-1, 3)
            DataTotal = []
            DataTotal.append(DataTotal_T[:, 0])
            DataTotal.append(DataTotal_T[:, 1])
            DataTotal.append(DataTotal_T[:, 2])
        else:
            DataTotal = DataTotal.data
        PackageIDs = PackageIDs.data
        if et_stamp == 0:
            et_stamp = st_stamp + timedelta(milliseconds=ms_new)
        else:
            et_stamp =  datetime.fromtimestamp(et_stamp/1000)
        ET = stamp2matarray(et_stamp)
        package_loss = (ms_per_pkg * PackageCount)/(et_stamp.timestamp() - st_stamp.timestamp())/1000

    return DataTotal, PackageIDs, SampleRate, ST, ET, package_loss

def DataloaderX7(path:str, signed=False):  # for ACC-36727, the sign is False
    global g_BoxMac
    head_type = 'X7'
    DataTotal = []
    PackageIDs = []
    g_BoxMac = ''
    DataType = path.split('.')[-1]

    with open(path, 'rb') as f:
        TotalLen = len(f.read())
        f.seek(0, 0)
        # DataType = f.read(3)
        f.seek(12, 0)
        PackageCount = int.from_bytes(f.read(4), byteorder='little', signed=False)
        f.seek(16, 0)
        Resolution = int.from_bytes(f.read(1), byteorder='little', signed=False)

        f.seek(21, 0)
        SampleRate = int.from_bytes(f.read(4), byteorder='little', signed=False)
        f.seek(81, 0)
        ChannelDataLenth = int.from_bytes(f.read(4), byteorder='little', signed=False)

        f.seek(30, 0)
        ST_Y = int.from_bytes(f.read(2), byteorder='little', signed=False)
        ST_M = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ST_D = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ST_H = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ST_Min = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ST_S = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ST_ms = int.from_bytes(f.read(2), byteorder='little', signed=False)

        f.seek(40, 0)
        ET_Y = int.from_bytes(f.read(2), byteorder='little', signed=False)
        ET_M = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ET_D = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ET_H = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ET_Min = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ET_S = int.from_bytes(f.read(1), byteorder='little', signed=False)
        ET_ms = int.from_bytes(f.read(2), byteorder='little', signed=False)

        ST = np.array([ST_Y, ST_M, ST_D, ST_H, ST_Min, ST_S, ST_ms])
        ET = np.array([ET_Y, ET_M, ET_D, ET_H, ET_Min, ET_S, ET_ms])
        # package_sent= (ET - ST)*np.array([365*24*60*60*1000,30*24*60*60*1000,24*60*60*1000,60*60*1000,60*1000,1000,0])/100 # 100 means package send frequency
        # package_loss = PacketCount/sum(package_sent)*100

        f.seek(90, 0)
        DataOffSet = int.from_bytes(f.read(4), byteorder='little', signed=signed)
        # PackageOffSet = 8


        if DataType == 'eeg':
            PackageDataLength = 208 # for 10 Hz
            # PackageDataLength = 138 # for 15 Hz
            # PackageDataLength = 28 # for 100 Hz
            # PackageDataLength = 48 # for 100 Hz

        elif DataType == 'acc':
            PackageDataLength = 38

        elif DataType == 'sti':
            PackageDataLength = 12

        elif DataType == 'emg':
            PackageDataLength = 168
        elif DataType == 'delay':
            PackageDataLength = 16
            Resolution = 8

        if not PackageCount:
            PackageCount = int((TotalLen - DataOffSet) / PackageDataLength)
        # else:
        #     PackageDataLength = int((TotalLen - DataOffSet) / PackageCount)


        f.seek(DataOffSet, 0)
        for i in range(PackageCount):
            PackageT = f.read(PackageDataLength)

            # if DataType == 'EMG':

            PackageID = int.from_bytes(PackageT[0:8], byteorder='little', signed=signed)
            PackageT = PackageT[8:]
            for j in range(int(len(PackageT) // Resolution)):
                DataT = int.from_bytes(PackageT[j * Resolution:j * Resolution + Resolution], byteorder='little',
                                        signed=signed)
                DataTotal.append(DataT)
            PackageIDs.append(PackageID)
        PackageIDs = np.array(PackageIDs)

        if DataType== 'eeg':
            DataTotal = (np.array(DataTotal)-32768)*(ref_map[head_type] / 48/4/32768)
            DataTotal = DataTotal[0:len(DataTotal) // 2 * 2]
            DataTotal_T = DataTotal.reshape(-1, 2)
            DataTotal = []
            DataTotal.append(DataTotal_T[:, 0])
            DataTotal.append(DataTotal_T[:, 1])

        elif DataType == 'acc':
            DataTotal = np.array(DataTotal)
            DataTotal = DataTotal[0:len(DataTotal) // 3 * 3]
            DataTotal_T = DataTotal.reshape(-1, 3)
            DataTotal = []
            DataTotal.append(DataTotal_T[:, 0])
            DataTotal.append(DataTotal_T[:, 1])
            DataTotal.append(DataTotal_T[:, 2])

        elif DataType == 'emg':
            DataTotal = np.array(DataTotal)
            DataTotal = DataTotal[0:len(DataTotal) // 8 * 8]
            DataTotal_T = DataTotal.reshape(-1, 8)
            DataTotal = []
            DataTotal.append(DataTotal_T[:, 0])
            DataTotal.append(DataTotal_T[:, 1])
            DataTotal.append(DataTotal_T[:, 2])
            DataTotal.append(DataTotal_T[:, 3])
            DataTotal.append(DataTotal_T[:, 4])
            DataTotal.append(DataTotal_T[:, 5])
            DataTotal.append(DataTotal_T[:, 6])
            DataTotal.append(DataTotal_T[:, 7])
        elif DataType== 'delay':
            DataTotal = np.array(DataTotal)
            # DataTotal = DataTotal[0:len(DataTotal) // 1 * 1]
            # DataTotal_T = DataTotal.reshape(-1, 1)
            # DataTotal = []
            # DataTotal.append(DataTotal_T[:, 0])




        package_loss = (sum(PackageIDs[2:-1] - PackageIDs[1:-2] - 100) / 100) / (
                    sum(PackageIDs[2:-1] - PackageIDs[1:-2] - 100) / 100 + PackageCount)


        # package_loss =[]

    return DataTotal, PackageIDs, SampleRate, ST, ET, package_loss

if __name__ == '__main__':

    ret = DataloaderX8(r'C:\Users\fengxinan\Downloads\14222_1705232999217.eeg.eeg')
    print(ret)