"""规范数据文件读取模块"""

import numpy as np
from dataclasses import dataclass
from pathlib import Path
import struct


CUBAN_19_CHANNELS = [
    'Fp1', 'Fp2', 'F3', 'F4', 'C3', 'C4', 'P3', 'P4', 'O1', 'O2',
    'F7', 'F8', 'T3', 'T4', 'T5', 'T6', 'Fz', 'Cz', 'Pz'
]


@dataclass
class NormsBroadBand:
    """宽带模型规范数据"""
    state: int
    pg_correct: int
    freq_resolution: float
    band_index: np.ndarray
    n_channels: int
    n_bands: int
    mean_pa: np.ndarray
    std_pa: np.ndarray
    mean_pr: np.ndarray
    std_pr: np.ndarray
    mean_fm: np.ndarray
    std_fm: np.ndarray


@dataclass
class NormsNarrowBand:
    """窄带模型规范数据"""
    state: int
    pg_correct: int
    freq_resolution: float
    frequencies: np.ndarray
    n_channels: int
    n_freqs: int
    mean_coef: np.ndarray
    std_coef: np.ndarray


def _int2real(e, minr, maxr):
    """将整数[0:255]转换为实数[minr:maxr]"""
    return minr + e.astype(np.float32) * (maxr - minr) / 255.0


def _descomp(minv, maxv, firstv, cdif):
    """解压缩差分编码的数据"""
    nf, nc = cdif.shape
    nc = nc + 1
    X = np.zeros((nf, nc), dtype=np.float32)
    
    X[:, 0] = firstv
    
    for k in range(nf):
        X[k, 1:nc] = _int2real(cdif[k, :], minv[k], maxv[k])
    
    for k in range(1, nc):
        X[:, k] = X[:, k-1] + X[:, k]
    
    return X


def _find_closest_age_index(ages, target_age):
    """找到最接近目标年龄的索引"""
    log_age = np.log(target_age)
    return int(np.argmin(np.abs(ages - log_age)))


def read_norms_broadband(filepath, age):
    """读取宽带模型规范数据文件"""
    with open(filepath, 'rb') as f:
        header = f.read(100).decode('latin-1').strip('\x00')
        
        expected = 'QEEGT Norms. Broad Band Model. Kernel Coefficients. Version 1.0'
        if not header.startswith(expected):
            raise ValueError(f"Invalid file type. Expected '{expected}', got '{header[:50]}'")
        
        v = struct.unpack('<6h', f.read(12))
        state = v[0]
        pg_correct = v[1]
        n_var = v[2]
        n_ages = v[3]
        n_bands = v[4]
        ncols_band_index = v[5]
        
        band_index = np.frombuffer(
            f.read(n_bands * ncols_band_index * 2), 
            dtype='<i2'
        ).reshape(n_bands, ncols_band_index)
        
        freq_res = struct.unpack('<f', f.read(4))[0]
        
        ages = np.frombuffer(f.read(n_ages * 4), dtype='<f4')
        
        age_index = _find_closest_age_index(ages, age)
        
        ptrbase = f.tell()
        
        record_size = ((3 * n_bands - 1) * n_var * 4) * 2
        ptr = ptrbase + age_index * record_size
        
        f.seek(ptr)
        
        mean_pa = np.frombuffer(f.read(n_var * n_bands * 4), dtype='<f4').reshape(n_var, n_bands)
        std_pa = np.frombuffer(f.read(n_var * n_bands * 4), dtype='<f4').reshape(n_var, n_bands)
        mean_pr = np.frombuffer(f.read(n_var * (n_bands-1) * 4), dtype='<f4').reshape(n_var, n_bands-1)
        std_pr = np.frombuffer(f.read(n_var * (n_bands-1) * 4), dtype='<f4').reshape(n_var, n_bands-1)
        mean_fm = np.frombuffer(f.read(n_var * n_bands * 4), dtype='<f4').reshape(n_var, n_bands)
        std_fm = np.frombuffer(f.read(n_var * n_bands * 4), dtype='<f4').reshape(n_var, n_bands)
    
    return NormsBroadBand(
        state=state,
        pg_correct=pg_correct,
        freq_resolution=freq_res,
        band_index=band_index,
        n_channels=n_var,
        n_bands=n_bands,
        mean_pa=mean_pa,
        std_pa=std_pa,
        mean_pr=mean_pr,
        std_pr=std_pr,
        mean_fm=mean_fm,
        std_fm=std_fm,
    )


def read_norms_narrowband(filepath, age):
    """读取窄带模型规范数据文件"""
    with open(filepath, 'rb') as f:
        header = f.read(100).decode('latin-1').strip('\x00')
        
        expected = 'QEEGT Norms. Kernel Coefficients. Version 1.0'
        if not header.startswith(expected):
            raise ValueError(f"Invalid file type. Expected '{expected}', got '{header[:50]}'")
        
        v = struct.unpack('<5h', f.read(10))
        state = v[0]
        pg_correct = v[1]
        n_var = v[2]
        n_ages = v[3]
        n_freqs = v[4]
        
        freq_res = struct.unpack('<f', f.read(4))[0]
        
        ages = np.frombuffer(f.read(n_ages * 4), dtype='<f4')
        
        freqs_hz = np.frombuffer(f.read(n_freqs * 4), dtype='<f4')
        
        ptrbase = f.tell()
        
        age_index = _find_closest_age_index(ages, age)
        
        ptr = ptrbase + age_index * n_var * 4
        f.seek(ptr)
        minmed = np.frombuffer(f.read(n_var * 4), dtype='<f4')
        
        ptr = ptrbase + n_ages * n_var * 4 + age_index * n_var * 4
        f.seek(ptr)
        maxmed = np.frombuffer(f.read(n_var * 4), dtype='<f4')
        
        ptr = ptrbase + 2 * n_ages * n_var * 4 + age_index * n_var * 4
        f.seek(ptr)
        minstd = np.frombuffer(f.read(n_var * 4), dtype='<f4')
        
        ptr = ptrbase + 3 * n_ages * n_var * 4 + age_index * n_var * 4
        f.seek(ptr)
        maxstd = np.frombuffer(f.read(n_var * 4), dtype='<f4')
        
        ptr = ptrbase + 4 * n_ages * n_var * 4 + age_index * n_var * 4
        f.seek(ptr)
        firstvmed = np.frombuffer(f.read(n_var * 4), dtype='<f4')
        
        ptr = ptrbase + 5 * n_ages * n_var * 4 + age_index * n_var * 4
        f.seek(ptr)
        firstvstd = np.frombuffer(f.read(n_var * 4), dtype='<f4')
        
        ptr = ptrbase + 6 * n_ages * n_var * 4 + 2 * age_index * n_var * (n_freqs - 1)
        f.seek(ptr)
        cdifmed = np.frombuffer(f.read(n_var * (n_freqs - 1)), dtype='uint8').reshape(n_var, n_freqs - 1)
        cdifstd = np.frombuffer(f.read(n_var * (n_freqs - 1)), dtype='uint8').reshape(n_var, n_freqs - 1)
        
        mean_coef = _descomp(minmed, maxmed, firstvmed, cdifmed)
        std_coef = _descomp(minstd, maxstd, firstvstd, cdifstd)
    
    return NormsNarrowBand(
        state=state,
        pg_correct=pg_correct,
        freq_resolution=freq_res,
        frequencies=freqs_hz,
        n_channels=n_var,
        n_freqs=n_freqs,
        mean_coef=mean_coef,
        std_coef=std_coef,
    )


def get_norms_filepath(norms_dir, state='eyes_open', model='broadband', pg_correct=True, reference='average'):
    """获取规范数据文件路径"""
    state_prefix = 'A' if state == 'eyes_open' else 'B'
    ref = 'AVR'
    pg = 'PG' if pg_correct else 'RD'
    model_suffix = 'BB' if model == 'broadband' else 'NB'
    
    filename = f"{state_prefix}_{ref}_{pg}_{model_suffix}_.NRM"
    
    return str(Path(norms_dir) / filename)
