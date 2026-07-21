class IChannelInfo:
    @staticmethod
    def gene_desc(label:str, dimension:str, sample_rate:int, physical_max:int, physical_min:int, digital_max:int, digital_min:int, transducer :str= '', prefilter:str = '') -> None:
        desc = {
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
        return desc
    def __init__(self) -> None:
        self.data = []
        self.desc = {
                'label': None,
                'dimension': None,
                'sample_rate': None,
                'physical_max': None,
                'physical_min': None,
                'digital_max': None,
                'digital_min': None,
                'transducer': None,
                'prefilter': None
            }
        
class IDataFormat:
    def __init__(self) -> None:
        self.start_time = 0
        self.channels = [] #type: list[IChannelInfo]
    def set_start_time(self,  start_time:float) -> None:
        self.start_time = start_time
    def add_channel(self, data, desc):
        ch = IChannelInfo()
        ch.data = data
        ch.desc = desc
        self.channels.append(ch)


