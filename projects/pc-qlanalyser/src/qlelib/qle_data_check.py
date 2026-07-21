import numpy as np
from datetime import datetime
import struct
from . import x7qledef
import os
from datetime import datetime


def charlist2str(c_list):
    if 0 in c_list:
        return bytes(c_list[:c_list.index(0)]).decode()
    else:
        return bytes(c_list).decode()


def qle_data_check(conver_name, export_name = None):
    repair_data = bytearray()
    ret_err_list = []
    qle_data_size = os.path.getsize(conver_name)
    qle_data = open(conver_name, 'rb')
    header_data = qle_data.read(x7qledef.STHeader.sizeof_struct())
    extra_data = qle_data.read(x7qledef.T_RecoderFileExtraData.sizeof_struct())
    header_data_ori = header_data
    extra_data_ori = extra_data
    header_data = x7qledef.STHeader.unpack(header_data)
    extra_data = x7qledef.T_RecoderFileExtraData.unpack(extra_data)
    print(header_data)
    magic = charlist2str(header_data['magic'][:3])
    channel_num = header_data['channel'][0]
    assert channel_num in [3, 7, 0xF], 'channel_num should be 3 or 7'
    channel_num = bin(channel_num).count('1')
    assert extra_data['prefix_data_offset'] == 18, 'prefix_data_offset should be 18'
    PackageDataLength = extra_data['prefix_data_offset'] + channel_num * header_data['points_pre_package'] * header_data['bype_per_point']
    pkg_count = (qle_data_size - header_data['header_len'])/ PackageDataLength
    if pkg_count % 1 != 0:
        ret_err_list.append('Package count is not integer')
    pkg_count = int(pkg_count)

    repair_data += header_data_ori
    repair_data += extra_data_ori
    find_state = 0
    expect_i = 0
    i = 0
    while True:
        while find_state != 3:
            _ = qle_data.read(1)
            if len(_) == 0:
                break
            if find_state == 0:
                if _[0] == 0xA5:
                    find_state = 2
                else:
                    ret_err_list.append('Package header not found0 %d' % (qle_data.tell()))
                    find_state = 1
            elif find_state == 1:
                if _[0] == 0xA5:
                    find_state = 2

            elif find_state == 2:
                if _[0] == 0x5A:
                    find_state = 3
                else:
                    ret_err_list.append('Package header not found1 %d' % (qle_data.tell()))
                    find_state = 0
        find_state = 0
        data_len = extra_data['prefix_data_offset'] - 2
        PackageT = qle_data.read(data_len)
        if len(PackageT) != data_len:
            if len(_) > 0:
                ret_err_list.append('Package header found but not enough, need %d, real %d' % (data_len, len(PackageT)))
            break
        time_ms = int.from_bytes(PackageT[0:8], byteorder = 'little', signed=False)
        file_pkg_id = int.from_bytes(PackageT[12:16], byteorder = 'little', signed=False)
        if expect_i > 0:
            if file_pkg_id != expect_i:
                ret_err_list.append(f'Package id is not continuous file_pkg_id:{file_pkg_id}, expect_i:{expect_i}')
                expect_i = -1
                continue
            
        if time_ms > (1000*3600*24*30):
            ret_err_list.append('Time is not in range %d' % (qle_data.tell()))
            continue
        data_len = PackageDataLength - extra_data['prefix_data_offset']
        _ = qle_data.read(data_len)
        if len(_) != data_len:
            ret_err_list.append('data is not enough, need %d, real %d' % (data_len, len(_)))
            continue
        expect_i = file_pkg_id + 1
        repair_data.append(0xA5)
        repair_data.append(0x5A)
        repair_data += PackageT[0:12]
        repair_data += int.to_bytes(i, 4, byteorder = 'little', signed=False)
        repair_data += _
        i += 1
    if i != pkg_count:
        ret_err_list.append('Package count is not enough, need %d, real %d' % (pkg_count, i))
    qle_data.close()
    del qle_data
    if export_name is not None:
        with open(export_name, 'wb') as f:
            f.write(repair_data)
    return repair_data, ret_err_list

if __name__ == '__main__':
    qle_data_check('')

