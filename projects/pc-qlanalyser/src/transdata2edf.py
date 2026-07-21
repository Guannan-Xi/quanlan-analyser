from .qlelib import qldata2edf,qle2edf,qle_data_check
import time
import os
from .decode_data import eegIsX8


repair = qle_data_check

def find_file(root, func, find_dir = False,  recursion = True):
    ret = []
    for f in os.listdir(root):
        full_name = root + '/' + f
        if(os.path.isfile(full_name)):
            if func(full_name):
                ret.append(full_name)
        else:
            if find_dir:
               if func(full_name):
                    ret.append(full_name)
            if recursion:
                ret += find_file(full_name, func, find_dir, recursion)
    return ret

def is_dir_all_file(root):
    for f in os.listdir(root):
        full_name = root + '/' + f
        if(os.path.isdir(full_name)):
            return False
    return True

def repair_err_data(data_p):
    if eegIsX8(data_p):
        with open(data_p, 'rb') as f:
            f.seek(41)
            data = f.read(8)
        end_ms = int.from_bytes(data, byteorder='little', signed=True)
        if end_ms == 0:
            dir_ = os.path.dirname(data_p)
            base_name = data_p[len(dir_) + 1:]
            repair_name = dir_ + '/repair_' + base_name
            data, err_list = repair.qle_data_check(data_p, repair_name, force_write=False)
            if len(err_list) > 0:
                data_p = repair_name
    return data_p
#单个文件转换方法(输入的是文件名)
def data_translate_edf(data_p):
    data_p = repair_err_data(data_p)
    qldata2edf.convert(data_p)
#多个文件转换方法(输入的是文件夹)
def data_translate_edf_path(data_p:str):
    def func(path:str):
        return path.endswith('.eeg') or path.endswith('eeg.qle')
    eeg_p = find_file(data_p, func, recursion=False)
    print(4444)
    if len(eeg_p) == 1:
        eeg_p = eeg_p[0]
        if eegIsX8(eeg_p):
            acc_p = find_file(data_p, lambda _: _.endswith('.acc') or _.endswith('acc.qle'), recursion=False)
            tri_p = find_file(data_p, lambda _: _.endswith('tri.tri') or _.endswith('tri.dat'), recursion=False)
            sw_p = find_file(data_p, lambda _: _.endswith('sti.log'), recursion=False)
            dir_info = {'EEG':eeg_p}
            if len(acc_p) == 1:
                dir_info['ACC'] = acc_p[0]
            if len(tri_p) == 1:
                dir_info['TRI'] = tri_p[0]
            if len(sw_p) == 1:
                dir_info['SW'] = sw_p[0]
            print(55555)
            qle2edf.convert_dir(dir_info, os.path.join(data_p, os.path.basename(data_p)))
            return
    def func(path:str):
        return path.endswith('.eeg') or path.endswith('.acc') or path.endswith('.qle')
    all_file = find_file(data_p, func, recursion=False)
    print(666666)
    for f in all_file:
        qldata2edf.convert(f)

#    data_translate_edf_path(r'C:\Users\evian\Desktop\QL\ExampleData\ECG\10248')
#    data_translate_edf(r'C:\Users\evian\Desktop\QL\ExampleData\ECG\10248\acc.acc')