from .pystruct import CStruct, CNameSpace
name_space = CNameSpace()
CHannelInfo = CStruct('''
    char label[20];
    char phy_max[32];
    char phy_min[32];
    char phy_unit[20];
    int32_t digital_max;
    int32_t digital_min;
    int32_t sample_rate;
''', struct_name='ChannelInfo', group=name_space)
STHeader = CStruct('''
    uint8_t  magic[4];           //fedf
    uint32_t fileVersion;
    uint32_t header_len;
    uint8_t descr_magic[12];
    char reserve[1024];
    uint32_t bype_per_point;
    uint32_t packet_ms;
    int64_t start_time;
    int64_t end_time;
    uint32_t pack_count;
    uint8_t channel_count;
    uint32_t dataOffset;
    ChannelInfo info[];
''', struct_name='STHeader', group=name_space)

PkgHeader = CStruct('''
    int type;
    int len;
''')

F_Annotation = CStruct('''
    int64_t anno_ns;
    int64_t duration;
    char anno[40];
''')



