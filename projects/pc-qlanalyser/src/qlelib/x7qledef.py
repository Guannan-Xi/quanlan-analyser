from . import pystruct
CStruct = pystruct.CStruct
T_QlX7FileAcquisitionInfo = CStruct('''
    int32_t type;
    char version[33];
    char mac[65];
    char phy_max[30];
    char phy_min[30];
    char phy_unit[30];
    int32_t digital_max;
    int32_t digital_min;''', struct_name='T_QlX7FileAcquisitionInfo')

T_QlX7FileRecorderInfo = CStruct('''
    int32_t type;
    char version[33];
    char mac[65];
''', struct_name = 'T_QlX7FileRecorderInfo')

T_QlX7FileUserInfo = CStruct('''
    int32_t type;
    char version[33];
    char user_name[65];
''', struct_name='T_QlX7FileUserInfo')

T_RecoderFileExtraData = CStruct('''
    int32_t start_record_reason;
    int32_t stop_record_reason;
    int32_t prefix_data_offset;
    int32_t header_type;
    char header_version[33];
    char header_mac[65];
    char phy_max[30];
    char phy_min[30];
    char phy_unit[30];
    int32_t digital_max;
    int32_t digital_min;

    int32_t box_type;
    char box_version[33];
    char box_mac[65];
    char box_name[33];

    int32_t app_type;
    char app_version[33];
    char user_id[65];
''', struct_name='T_RecoderFileExtraData')

STHeader = CStruct('''
    int8_t  magic[4];           //eeg(eeg文件) acc(acc文件) sti(音频刺激文件) 魔数 4个字节
    uint32_t fileVersion;
    uint32_t header_len;
    uint32_t dev_type;
    uint8_t bype_per_point;
    uint32_t packetCount;
    uint32_t points_pre_package;
    uint32_t originalRate;
    uint32_t sampleRate;
    int64_t start_time;
    int64_t end_time;
    uint8_t channel[32];
    uint32_t dataOffset;         //数据偏移 真实数据位置 从dataOffset 位置可以读到真实文件数据
''', struct_name='STHeader')