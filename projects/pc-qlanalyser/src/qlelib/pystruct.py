import binascii
import re
import binascii
def removeCCppComment( text :str):

    def blotOutNonNewlines( strIn ):  # Return a string containing only the newline chars contained in strIn
        return "" + ("\n" * strIn.count('\n'))

    def replacer( match ):
        s = match.group(0)
        if s.startswith('/'):  # Matched string is //...EOL or /*...*/  ==> Blot out all non-newline chars
            return blotOutNonNewlines(s)
        else:                  # Matched string is '...' or "..."  ==> Keep unchanged
            return s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )

    return re.sub(pattern, replacer, text)

class MyStruct:
    type_dict =  {'uint8_t' : 'B', 'char':  'c', 'unsinged char':  'B', 'int8_t':  'b',
                'uint16_t' : 'H', 'int16_t': 'h', 'short': 'h',
                'uint32_t': 'I', 'int32_t': 'i', 'int': 'i' , 'long': 'i',
                'uint64_t': 'Q', 'long long': 'q', 'int64_t':'q', 'bytes': 's'}

    struct_dict = {'c': (1, True), 'b': (1, True), 'B': (1, False), 'h': (2, True), 'H': (2, False), 
                  'i': (4, True), 'I':(4, False), 'q': (8, True), 'Q': (8, False), 's': (1, None)}
    @staticmethod
    def unpack(format: str, in_data:bytes) ->list:
        assert isinstance(in_data, bytes) or isinstance(in_data, bytearray)
        format, byte_order, res = MyStruct.check(format)
        ret_value = []
        all_data_len = len(in_data)
        use_len = 0
        
        for count, s_type in res:
            try:
                t_len = int(s_type)
            except:
                t_len = MyStruct.struct_dict[s_type][0]
                if s_type == 's':
                    func = lambda : in_data[use_len: use_len + t_len]
                else:
                    func = lambda : int.from_bytes(in_data[use_len: use_len + t_len], byteorder = byte_order, signed=MyStruct.struct_dict[s_type][1])
            else:
                func = lambda : in_data[use_len: use_len + t_len]
            if count == '':
                ret_value.append(func())
                use_len += t_len
            else:
                count = int(count)
                ret_tmp = []
                for i in range(count):
                   ret_tmp.append(func())
                   use_len += t_len
                ret_value.append(ret_tmp)
        assert use_len == all_data_len
        return ret_value

    @staticmethod
    def check(format):
        if format.startswith('little'):
            byte_order = 'little'
            format = format[6:]
        elif format.startswith('big'):
            byte_order = 'big'
            format = format[3:]
        else:
            byte_order = 'little'

        res = re.findall(r'(\d*)([\<a-zA-Z])', format)
        res2 = re.findall(r'<(\d+)>', format)
        assert [ r[1] for r in res].count('<') == len(res2)
        index2 = 0
        for i in range(len(res)):
            if res[i][1] == '<':
                res[i] = (res[i][0], res2[index2])
                index2 += 1
        return format, byte_order, res
    
    @staticmethod
    def pack(format :str, *args) ->bytearray:
        format, byte_order, res = MyStruct.check(format)
        arg_list = list(args)
        ret_byte = bytearray()
        index = 0
        assert len(arg_list) == len(res)
        for count, s_type in res:
            try:
                t_len = int(s_type)
            except:
                t_len = MyStruct.struct_dict[s_type][0]
                if s_type == 's':
                    func = lambda _: bytearray(_)
                else:
                    func = lambda _: int.to_bytes(_, t_len, byteorder=byte_order, signed = MyStruct.struct_dict[s_type][1])
            else:
                func = lambda _: bytearray(_)
            
            if count == '':
                ret_byte += func(arg_list[index])
            else:
                count = int(count)
                assert len(arg_list[index]) == count
                for i in range(count):
                    a = func(arg_list[index][i])
                    ret_byte += a
            index += 1

        return ret_byte      

class CStruct:
    type_dict =   MyStruct.type_dict

    struct_dict = MyStruct.struct_dict
    
    def __init__(self, c_struct : str, struct_name = None, byteorder = 'little', group = None) -> None:
        order_dict = {'little': 'little', 'big': 'big'}
        assert byteorder in order_dict.keys()
        self.name = struct_name
        self.byteorder = order_dict[byteorder]
        self.offset_map = {}
        self.size_info_map = {}
        if group is None:
            self.group = CNameSpace() 
        else:
            self.group = group # type: CNameSpace
            if self.name is not None:
                self.group.regist(self)
        self.py_dict = self.__cstruct_dict(c_struct)
        size = 0
        for name, value in self.py_dict.items():
            self.offset_map[name] = size
            if value[0] in self.struct_dict:
                len_info = self.struct_dict[value[0]][0]
            else:
                len_info = value[0].sizeof_struct()
            if value[1] is None:
                all_len = len_info
            else:
                all_len = len_info * value[1]
            size += all_len
            self.size_info_map[name] = all_len
        self.__cstruct_size = size
    
    def offsetof(self, name):
        import sys
        assert sys.version_info.major >= 3
        return self.offset_map[name]
    
    def using_group(self, group):
        self.group = group # type: CNameSpace
        if self.name is not None:
            self.group.regist(self)

    def unpack(self, in_bytes: bytes, muti_count = None) :#-> dict[str]
        if muti_count is not None:
            if muti_count == 0:
                muti_count = len(in_bytes)
                # muti_count = len(in_bytes) // self.sizeof_struct()
                # assert len(in_bytes) % self.sizeof_struct()  == 0
            assert isinstance(muti_count, int)
            ret = []
            for i in range(muti_count):
                # tmp = in_bytes[:self.sizeof_struct()]
                # in_bytes = in_bytes[self.sizeof_struct():]
                ret.append(self.unpack(in_bytes[i], None))
            return ret

        assert isinstance(in_bytes, bytes) or isinstance(in_bytes, bytearray) 
        ret_name_value_dict = {}
        value_list = list(self.py_dict.values())
        key_list = list(self.py_dict.keys())

        unpack_str = self.__gene_unpack_str(value_list, len(in_bytes))

        unpack_values = MyStruct.unpack( unpack_str, in_bytes) # type: tuple[bytes]
        assert len(unpack_values) == len(key_list)
        for i in range(len(unpack_values)):
            if isinstance(value_list[i][0], CStruct):
                c_struct = value_list[i][0] # type: CStruct
                ret_name_value_dict[key_list[i]] = c_struct.unpack(unpack_values[i], value_list[i][1])
            else:   
                ret_name_value_dict[key_list[i]] = unpack_values[i]

        return ret_name_value_dict
        
    def pack(self, in_dict, add_crc_cb = None) -> bytes:
        if isinstance(in_dict, tuple):
            ret = [self.pack(i) for i in in_dict]
            return (b'').join(ret)
        else:
            info_list = list(self.py_dict.values())
            value_list = []
            size = 0
            for name, value in self.py_dict.items():
                if value[0] in self.struct_dict:
                    len_info = self.struct_dict[value[0]][0]
                else:
                    len_info = value[0].sizeof_struct()
                if isinstance(self.py_dict[name], CStruct):
                    this_value = self.py_dict[name].pack(in_dict[name])
                else:
                    this_value = in_dict[name]
                    
                value_list.append(this_value)
                if value[1] is None:
                    size += len_info * 1
                elif value[1] > 0:
                    size += len_info * value[1]
                else:
                    cur_len = len(in_dict[name])
                    size += len_info * cur_len

            unpack_str = self.__gene_unpack_str(info_list, size)
            ret_bytes = MyStruct.pack(unpack_str, *value_list)
            test_str = binascii.hexlify(ret_bytes)
            if add_crc_cb is not None:
                ret_bytes += add_crc_cb(ret_bytes)
            return ret_bytes

    def sizeof_struct(self, name = None) -> int:
        if name is None:
            return self.__cstruct_size
        else:
            return self.size_info_map[name]

    def __gene_unpack_str(self, in_list, in_byte_len) -> str:
        ret_str = self.byteorder
        use_len = 0
        for i, count in in_list:
            if i in self.struct_dict.keys():
                per_len = self.struct_dict[i][0]
                if count is None:
                    ret_str += str(i)
                    count = 1
                else:
                    if count == 0:
                        count = (in_byte_len - use_len) // per_len
                        assert (in_byte_len - use_len) % per_len == 0
                    ret_str += str(count) + str(i)

            elif isinstance(i, CStruct):
                per_len = i.sizeof_struct()
                if count is None:
                    ret_str += '<%s>' % per_len
                    count = 1
                else:
                    if count == 0:
                        count = (in_byte_len - use_len) // per_len
                        assert (in_byte_len - use_len) % per_len == 0
                    ret_str += '%s<%s>' % (count, per_len)
            else:
                raise Exception()


            use_len += count * per_len
 
        return ret_str

    def __cstruct_dict(self, c_struct: str) : #-> dict[str, tuple]
        c_struct = removeCCppComment(c_struct)
        c_struct = re.sub(r'[\r\n\t]', '', c_struct)
        while '  ' in c_struct:
            c_struct = c_struct.replace('  ', ' ')
        c_struct = re.sub(r'\s*;\s*', ';', c_struct)
        type_name = c_struct.split(';')
        py_dict = {}
        for item in type_name:
            if len(item) == 0:
                continue
            item = re.sub(r'^\s*', '',item)
            item = re.sub(r'\s*$', '', item)
            aa = item.split(' ', 1)
            ty, name = item.split(' ', 1)
            if name in py_dict.keys():
                raise Exception()
            else:
                py_dict[name] = ty
        ret_py_dict = {}

        for name, value in py_dict.items():
            res = re.search(r'([\w_]+)([^\s]*)', name)
            if res is None:
                raise Exception()
            te_name = res.group(1) #name

            value = self.group.eval_with_macro(value)

            if value in self.group.group.keys():
                te_len = self.group.group[value]

            elif value in self.type_dict.keys():
                te_len = self.type_dict[value] # type
            else:
                raise Exception()

            if len(res.group(2)) > 0:
                res2 = re.search(r'\[([^\]]*)\]', res.group(2))
                if res2 is None:
                    raise Exception()
                arr_len = res2.group(1)
                if len(arr_len) > 0:
                    te_count = self.group.eval_with_macro(res2.group(1))
                else:
                    te_count = 0
            else:
                te_count = None
            ret_py_dict[te_name] = (te_len, te_count)

        return ret_py_dict
            
class CNameSpace:
    type_dict =   MyStruct.type_dict
    struct_dict = MyStruct.struct_dict
    all_name_space = {} #type: dict[str, CNameSpace]
    def __init__(self, name= None, code=None) -> None:
        self.group = {}#type: dict[str, CStruct]
        self.cmacro_value_dict = {} #type: dict[str, str]
        self.name = name
        if self.name is not None:
            self.all_name_space[self.name] = self
        if code is not None:
            self.parse_c_code(code)

    def using_namespace(self, name_space):

        if isinstance(name_space, str):
            if name_space in self.all_name_space.keys():
                space = self.all_name_space[name_space]
                self.update(space)
            else:
                self.parse_c_code(name_space)
        else:
            self.update(space)

    def regist(self, c_struct: CStruct) -> None:
        assert c_struct.name is not None
        self.group[c_struct.name] = c_struct

    def update(self, name_space):
        self.group.update(name_space.group)
        self.cmacro_value_dict.update(name_space.cmacro_value_dict)

    def define(self, macro, value) -> None:
        self.cmacro_value_dict[macro] = value

    def undef(self, macro):
        if macro in self.cmacro_value_dict.keys():
            self.cmacro_value_dict.pop(macro)
    
    def type_def(self, dst_type, src_type):
        self.cmacro_value_dict[src_type] = dst_type
    
    def parse_c_code(self, c_code:str):
        code = removeCCppComment(c_code)
        sub_compile = re.compile(r'\\\s*\r*\n')
        code = re.sub(sub_compile, '', code)
        macro = re.findall(r'^\s*#define\s+([\w_]+)\s+([\(\)\+\-\*/\^&|!%\s\w_]*)$', code, re.MULTILINE)
        for s, d in macro:
            d = self.eval_with_macro(d)
            self.define(s, d)
        
        type_def = re.findall(r'^\s*typedef\s+([\w_]+)\s+([\w_]*);\s*$', code, re.MULTILINE)
        for d, s in type_def:
            self.define(s, d)
        using = re.findall(r'^\s*using\s+namespace\s+([\w_]+)\s*;\s*', code, re.MULTILINE)
        for space in using:
            space = self.cmacro_value_dict.get(space, space)
            self.using_namespace(space)

    def eval_with_macro(self, in_str: str):
        if in_str.startswith('0x'):
            return int(in_str, 16)
        else:
            try:
                ret = int(in_str)
            except:
                pass
            else:
                return ret

        def sub_cb(res):
            value = res.group(0)
            var = res.group(1)
            while var in self.cmacro_value_dict.keys():
                var  = self.cmacro_value_dict[var]
            value = value.replace(res.group(1), str(var))
            
            return value
            
        sub_com = re.compile(r'(?<=[\+\-\*/\s\(\^&|%!])*([\w_]+)(?=[\+\-\*/\s\(\^&|%])*')
        final_str = re.sub(sub_com,  sub_cb, in_str)
        try:
            ret = eval(final_str)
        except:
            ret = final_str
        if  not isinstance(ret, str):
            ret = ret.__name__

        assert ret in MyStruct.type_dict.keys() or ret in self.group.keys() or self.all_name_space.keys()

        return ret

def sizeof(s: CStruct, name=None):
    return s.sizeof_struct(name)

def offsetof(s: CStruct, name):
    return s.offsetof(name)

if __name__ == '__main__':
    root_struct = CStruct('''
        uint16_t start;                // header 0xA55A
        uint8_t pkgType;            //
        uint8_t devType;            //
        uint32_t ID;                    // device ID(can be part of mac address
        uint32_t length;            // pkg length
        uint16_t CMD;
        uint8_t data[];''')
    print(offsetof(root_struct, 'data'))
    name_space1 = CNameSpace(name = 'space1', code = '#define abcd space1')
    name_space2 = CNameSpace(code='using namespace space1;')
    print()
    

