"""
Streaming EDF Reader for Large File Support

Provides chunked data loading to handle very large EEG files (e.g., 44+ hours)
without loading the entire dataset into memory.

Author: QLanalyser Team
Created: 2026-07-02
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

import numpy as np

from eeg_core.io.readers import read_raw


logger = logging.getLogger(__name__)


class StreamingEDFReader:
    """
    Streaming EDF reader that loads data in time-based chunks.
    
    This reader is designed for very large EEG files (e.g., 44+ hour recordings)
    where loading the full dataset into memory would cause OOM errors.
    
    Key features:
    - Lazy loading: Only loads requested time chunks
    - Memory efficient: Releases chunks after yielding
    - Compatible with MNE Raw objects
    - Supports all MNE-compatible formats (EDF, BDF, etc.)
    
    Example:
        >>> reader = StreamingEDFReader("large_file.edf", chunk_duration_sec=7200)
        >>> for chunk_info in reader.iter_chunks(channel="EEG Fpz-Cz"):
        ...     start_sec, end_sec, data = chunk_info
        ...     # Process data chunk (e.g., extract features)
        ...     process(data)
    """
    
    def __init__(
        self,
        file_path: str | Path,
        chunk_duration_sec: float = 7200.0,  # 2 hours default
        overlap_sec: float = 30.0,  # Overlap to avoid edge effects
    ):
        """
        Initialize streaming reader.
        
        Args:
            file_path: Path to EEG file (EDF, BDF, etc.)
            chunk_duration_sec: Duration of each chunk in seconds (default: 2 hours)
            overlap_sec: Overlap between chunks to handle edge cases (default: 30s)
        """
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"EEG file not found: {self.file_path}")
        
        # Load header only (preload=False)
        self.raw = read_raw(self.file_path, preload=False)
        self.chunk_duration = float(chunk_duration_sec)
        self.overlap_sec = float(overlap_sec)
        
        # Get metadata
        self.sfreq = float(self.raw.info["sfreq"])
        self.total_duration = float(self.raw.times[-1])
        self.n_times = len(self.raw.times)
        self.ch_names = self.raw.ch_names
        
        # Calculate chunk info
        self.chunk_count = int(np.ceil(self.total_duration / self.chunk_duration))
        
        logger.info(
            f"Initialized StreamingEDFReader: {self.file_path.name}, "
            f"duration={self.total_duration:.1f}s ({self.total_duration/3600:.1f}h), "
            f"sfreq={self.sfreq}Hz, chunks={self.chunk_count}"
        )
    
    def iter_chunks(
        self, 
        channel: str | list[str] | None = None,
        use_overlap: bool = True
    ) -> Iterator[tuple[float, float, np.ndarray]]:
        """
        Iterate over data chunks.
        
        Args:
            channel: Channel name(s) to load. If None, loads all channels.
            use_overlap: Whether to include overlap between chunks (default: True)
        
        Yields:
            tuple: (start_sec, end_sec, data)
                - start_sec: Chunk start time in seconds
                - end_sec: Chunk end time in seconds
                - data: Data array, shape (n_channels, n_samples) or (n_samples,) for single channel
        """
        current = 0.0
        chunk_idx = 0
        
        while current < self.total_duration:
            # Calculate chunk boundaries
            chunk_start = current
            chunk_end = min(current + self.chunk_duration, self.total_duration)
            
            # Add overlap for next chunk (except last chunk)
            if use_overlap and chunk_end < self.total_duration:
                chunk_end = min(chunk_end + self.overlap_sec, self.total_duration)
            
            # Load chunk
            try:
                raw_chunk = self.raw.copy().crop(tmin=chunk_start, tmax=chunk_end, include_tmax=False)
                raw_chunk.load_data()
                
                # Extract data for specified channel(s)
                if channel is None:
                    data = raw_chunk.get_data()
                elif isinstance(channel, str):
                    data = raw_chunk.get_data(picks=[channel])[0]
                else:
                    data = raw_chunk.get_data(picks=channel)
                
                logger.debug(
                    f"Loaded chunk {chunk_idx + 1}/{self.chunk_count}: "
                    f"[{chunk_start:.1f}s - {chunk_end:.1f}s], "
                    f"shape={data.shape}, memory={data.nbytes / 1024**2:.1f}MB"
                )
                
                yield (chunk_start, chunk_end, data)
                
                # Explicitly release memory
                del raw_chunk
                del data
                
            except Exception as e:
                logger.error(f"Failed to load chunk {chunk_idx + 1} [{chunk_start:.1f}s - {chunk_end:.1f}s]: {e}")
                raise RuntimeError(
                    f"Chunk loading failed at {chunk_start:.1f}s: {e}"
                ) from e
            
            # Move to next chunk (without overlap for positioning)
            current += self.chunk_duration
            chunk_idx += 1
    
    def get_chunk(
        self,
        start_sec: float,
        end_sec: float,
        channel: str | list[str] | None = None
    ) -> np.ndarray:
        """
        Get a specific time chunk.
        
        Args:
            start_sec: Start time in seconds
            end_sec: End time in seconds
            channel: Channel name(s) to load
        
        Returns:
            Data array for the specified time range
        """
        if start_sec < 0 or end_sec > self.total_duration:
            raise ValueError(
                f"Invalid time range [{start_sec}s - {end_sec}s], "
                f"valid range: [0s - {self.total_duration}s]"
            )
        
        if start_sec >= end_sec:
            raise ValueError(f"start_sec ({start_sec}) must be < end_sec ({end_sec})")
        
        raw_chunk = self.raw.copy().crop(tmin=start_sec, tmax=end_sec, include_tmax=False)
        raw_chunk.load_data()
        
        if channel is None:
            return raw_chunk.get_data()
        elif isinstance(channel, str):
            return raw_chunk.get_data(picks=[channel])[0]
        else:
            return raw_chunk.get_data(picks=channel)
    
    def estimate_memory_usage(self, channel: str | list[str] | None = None) -> dict[str, float]:
        """
        Estimate memory usage for different loading strategies.
        
        Args:
            channel: Channel(s) to estimate for
        
        Returns:
            Dictionary with memory estimates in MB:
                - full_load: Memory for loading entire file
                - single_chunk: Memory for one chunk
                - peak_chunked: Peak memory during chunked processing
        """
        if channel is None:
            n_channels = len(self.ch_names)
        elif isinstance(channel, str):
            n_channels = 1
        else:
            n_channels = len(channel)
        
        # Assume float64 (8 bytes per sample)
        bytes_per_sample = 8
        
        full_samples = self.n_times * n_channels
        full_load_mb = (full_samples * bytes_per_sample) / (1024 ** 2)
        
        chunk_samples = int(self.chunk_duration * self.sfreq * n_channels)
        single_chunk_mb = (chunk_samples * bytes_per_sample) / (1024 ** 2)
        
        # Peak memory: 2x chunk (current + processing overhead)
        peak_chunked_mb = single_chunk_mb * 2
        
        return {
            "full_load_mb": round(full_load_mb, 2),
            "single_chunk_mb": round(single_chunk_mb, 2),
            "peak_chunked_mb": round(peak_chunked_mb, 2),
            "chunk_count": self.chunk_count,
            "memory_reduction_ratio": round(full_load_mb / peak_chunked_mb, 2)
        }
    
    def __repr__(self) -> str:
        return (
            f"StreamingEDFReader(file={self.file_path.name}, "
            f"duration={self.total_duration/3600:.1f}h, "
            f"sfreq={self.sfreq}Hz, "
            f"chunks={self.chunk_count})"
        )


def iter_channel_chunks(
    file_path: str | Path,
    channel: str,
    chunk_duration_sec: float = 7200.0,
    overlap_sec: float = 30.0
) -> Iterator[tuple[float, float, np.ndarray]]:
    """
    Convenience function to iterate over chunks of a single channel.
    
    Args:
        file_path: Path to EEG file
        channel: Channel name to load
        chunk_duration_sec: Duration of each chunk in seconds
        overlap_sec: Overlap between chunks in seconds
    
    Yields:
        tuple: (start_sec, end_sec, data) for each chunk
    
    Example:
        >>> for start, end, data in iter_channel_chunks("file.edf", "EEG Fpz-Cz"):
        ...     features = extract_features(data)
    """
    reader = StreamingEDFReader(file_path, chunk_duration_sec, overlap_sec)
    yield from reader.iter_chunks(channel=channel, use_overlap=overlap_sec > 0)
