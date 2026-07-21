from . import tdyqle2edf
from . import qle2edf
from . import x7eeg2edf
from . import data2edf
from pyedflib import EdfReader, EdfWriter
import os
import uuid
def get_randam_name():
    return uuid.uuid4().hex

def merge_edf(edf_list, out_put_name):
    if len(edf_list) == 0:
        return
    edf_readers = []
    for i in edf_list:
        edf_readers.append(EdfReader(i))
    edf_writer = data2edf.EdfHandle()
    for r in edf_readers:
        edf_writer.from_reader(r)
    handle = edf_writer.get_edf_handle(out_put_name)
    handle.setEquipment(edf_readers[0].getEquipment())
    start_time = edf_readers[0].getStartdatetime()
    edf_writer._export(handle, start_time)
    

def convert(conver_name, export_name = None):
    base_name = os.path.basename(conver_name)
    base_name, t = os.path.splitext(base_name)
    if export_name is None:
        export_name = f'{os.path.dirname(conver_name)}/{base_name}'
        if export_name[0] == '/':
            export_name = export_name[1:]        
        
    t # type: str
    if t.endswith('qle'):
        qle2edf.convert(conver_name, export_name)
    elif t.endswith('fedf'):
        tdyqle2edf.covert(conver_name, export_name)
    else:
        f =  open(conver_name, 'rb')
        f.seek(8, 0)
        _ = int.from_bytes(f.read(4), byteorder='little', signed=False)
        f.close()
        if _ > 300:
            qle2edf.convert(conver_name, export_name)
        else:
            x7eeg2edf.convert(conver_name, export_name)
    return export_name + '.edf'

if __name__ == '__main__':
    merge_edf([r'C:\Users\fengxinan\Downloads\13408_eeg.eeg',r'C:\Users\fengxinan\Downloads\13408_acc.acc'], r'C:\Users\fengxinan\Downloads\13408')
        
    