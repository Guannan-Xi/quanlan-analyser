
import numpy as np
import pyedflib

from datetime import datetime
import struct
# signal label/waveform  amplitude    f       sf
# ---------------------------------------------------
#    1    squarewave        100 uV    0.1Hz   200 Hz
#    2    ramp              100 uV    1 Hz    200 Hz
#    3    pulse 1           100 uV    1 Hz    200 Hz
#    4    pulse 2           100 uV    1 Hz    256 Hz
#    5    pulse 3           100 uV    1 Hz    217 Hz
#    6    noise             100 uV    - Hz    200 Hz
#    7    sine 1 Hz         100 uV    1 Hz    200 Hz
#    8    sine 8 Hz         100 uV    8 Hz    200 Hz
#    9    sine 8.1777 Hz    100 uV    8.25 Hz 200 Hz
#    10    sine 8.5 Hz       100 uV    8.5Hz   200 Hz
#    11    sine 15 Hz        100 uV   15 Hz    200 Hz
#    12    sine 17 Hz        100 uV   17 Hz    200 Hz
#    13    sine 50 Hz        100 uV   50 Hz    200 Hz


class DataParser:
    @staticmethod
    def parse_points(in_file, split_char = ','):
        with open(in_file, 'r') as f:
            temp = f.read()
            if '[' in temp:
                temp = temp.replace('][', split_char)
                temp = temp.replace(']', '')
                temp = temp.replace('[', '')
            temp = temp.replace('%s%s' % (split_char,split_char), split_char)
            temp = temp.split(split_char)

            if temp[-1] == '':
                temp.pop(-1)
        temp = [int(v) for v in temp]
        if max(temp) > 15000:
            return [ v/3 for v in temp]
        else:
            return temp

    @staticmethod
    def parse_dat(in_file, byte_len, start_offset, byteorder = 'little', signed = False):
        with open(in_file, 'rb') as f:
            temp = f.read()
            header = temp[:start_offset]
            temp = temp[start_offset:]
        
        data_list = []
        order_map = {'little':'<', 'big':'>'}
        signed_map = {1:'b', 2:'h', 4:'i'}
        unsigned_map = {1:'B', 2:'H', 4:'I'}
        is_sign_map = {True:signed_map, False: unsigned_map}
        cmd = order_map[byteorder] + str(int(len(temp)/2)) + is_sign_map[signed][byte_len]
        data_list = struct.unpack(cmd ,temp)

        return data_list

    @staticmethod
    def parse_rsa32_header(header: bytes, byteorder):
        info = {}
        order_map = {'little':'<', 'big':'>'}
        ch_id, rate, phy_max, phy_min, value_max, value_min, data_len, signed = struct.unpack('%sIIiiiiBB' % order_map[byteorder], header[:26])
        header = header[26:]
        info['channel_id'] = ch_id + 1 
        info['sample_rate'] = rate
        info['phy_max'] = phy_max
        info['phy_min'] = phy_min
        info['value_max'] = value_max
        info['value_min'] = value_min
        info['data_len'] = data_len
        info['signed'] = False if signed == 0 else True
        info['dimension'] = header[:header.index(0)].decode()
        header = header[10:]
        time_str = header[:header.index(0)].decode()
        info['start_time'] = datetime.strptime(time_str, '%Y_%m_%d_%H_%M_%S')
        return info


class EdfHandle:
    class EdfOriChannel:
        def __init__(self, ori_dict):
            self.ch_dict = ori_dict
        def set_data(self, in_data):
            self.__data_list = in_data
        def get_data(self):
            data = self.__data_list
            del self.__data_list
            return data
        
    class ChannelInfo:
        def __init__(self, label:str, dimension:str, sample_rate:int, physical_max:int, physical_min:int, digital_max:int, digital_min:int, transducer :str= '', prefilter:str = '') -> None:
            self.ch_dict = {
                'label': label,
                'dimension': dimension,
                'sample_rate': sample_rate,
                'physical_max': physical_max,
                'physical_min': physical_min,
                'digital_max': digital_max,
                'digital_min': digital_min,
                'transducer': transducer,
                'prefilter': prefilter
                }
            
        def set_data(self, in_data):
            # mut = ( self.ch_dict['physical_max'] - self.ch_dict['physical_min']) / (self.ch_dict['digital_max'] - self.ch_dict['digital_min'])
            # sub = self.ch_dict['digital_min']
            # offset = self.ch_dict['physical_min'] - sub*mut
            # def convert(i):
            #     return i * mut + offset
            # for i in range(len(in_data)):
            #     in_data[i] = convert(in_data[i])
            # if(any( [ i < ]))
            self.__data_list = in_data
        def get_data(self):
            data = self.__data_list
            del self.__data_list
            return data

    def __init__(self) -> None:
        self.chennel_list = []
        self.annotation = []
        self.__start_time = None
        pass
    
    def from_reader(self, reader:pyedflib.EdfReader):
        len_count = len(reader.getSampleFrequencies())
        for i in range(len_count):
            ch_info = self.EdfOriChannel(reader.getSignalHeader(i))
            self.chennel_list.append(ch_info)
            ch_info.set_data(reader.readSignal(i, digital=True))

    def add_channel(self, label:str, dimension:str, sample_rate:int, physical_max:int, 
                    physical_min:int, digital_max:int, digital_min:int, transducer :str= '', prefilter:str = ''):
        ch_info = self.ChannelInfo(label, dimension, sample_rate, physical_max, physical_min, digital_max, digital_min, transducer, prefilter)
        self.chennel_list.append(ch_info)
        return ch_info

    def _export(self, handle, start_time = None):
        channel_info_list = [info.ch_dict for info in self.chennel_list]
        handle.setSignalHeaders(channel_info_list)
        data_list = [info.get_data() for info in self.chennel_list]
        if start_time is not None:
            handle.setStartdatetime(start_time)
        handle.writeSamples(data_list, digital=True)
        for anno in self.annotation:
            handle.writeAnnotation(*anno)
        handle.close()

    def get_edf_handle(self, filename) ->pyedflib.EdfWriter:
        handle = pyedflib.EdfWriter('%s.edf' %filename,
                           len(self.chennel_list),
                           file_type=pyedflib.FILETYPE_EDFPLUS)
        return handle
    
    def export_edf(self, filename, start_time = None):
        handle = pyedflib.EdfWriter('%s.edf' %filename,
                           len(self.chennel_list),
                           file_type=pyedflib.FILETYPE_EDFPLUS)
        return self._export(handle, start_time)
    def export(self, filename, start_time = None):
        handle = pyedflib.EdfWriter(filename,
                           len(self.chennel_list),
                           file_type=pyedflib.FILETYPE_EDFPLUS)
        return self._export(handle, start_time)

    def add_annotation(self, onset_in_seconds, duration_in_seconds, description, str_format='utf_8'):
        self.annotation.append([onset_in_seconds, duration_in_seconds, description])

    def export_bdf(self, filename, start_time = None):
        handle = pyedflib.EdfWriter('%s.bdf' %filename,
                           len(self.chennel_list),
                           file_type=pyedflib.FILETYPE_BDFPLUS)
        return self._export(handle, start_time)


if __name__ == '__main__':
    import numpy
    edf = pyedflib.EdfReader(r'C:\Users\loudly\Desktop\20221129201246_part4.bdf')
    a = edf.getSampleFrequencies()
    b = edf.readAnnotations()
    c = edf.getStartdatetime()
    d = edf.getNSamples()
    e = edf.getPhysicalDimension(1)
    f = edf.readSignal(0)
    print()





