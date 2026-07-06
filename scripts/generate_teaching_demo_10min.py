"""
Generate 10-minute high-quality teaching demonstration EEG data for QLanalyser

This script creates realistic EEG data with multiple waveform scenarios:
- Wake state (0-120s): Alpha + Beta waves
- NREM Stage 1-2 (120-240s): Theta waves with Sleep Spindles and K-complexes
- NREM Stage 3 (240-360s): High-amplitude Delta waves (deep sleep)
- REM sleep (360-480s): Theta waves with rapid eye movements
- Seizure events (480-600s): High-frequency high-amplitude spikes

Target: Teaching mode demonstration with clear, distinct features
"""

import numpy as np
import mne
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))


def generate_teaching_demo_eeg(output_dir='data/teaching'):
    """
    Generate 10-minute teaching demonstration EEG data
    
    Parameters
    ----------
    output_dir : str
        Directory to save the generated EDF file
        
    Returns
    -------
    raw : mne.io.Raw
        MNE Raw object containing the generated data
    """
    
    # Parameters
    sfreq = 250  # Hz - sampling frequency
    duration = 600  # seconds (10 minutes)
    n_samples = int(sfreq * duration)
    
    print(f"🎓 Generating teaching demo EEG data...")
    print(f"   Duration: {duration}s ({duration/60:.1f} minutes)")
    print(f"   Sampling rate: {sfreq} Hz")
    print(f"   Total samples: {n_samples}")
    
    # Time axis
    times = np.arange(n_samples) / sfreq
    
    # Initialize 5 channels
    eeg3 = np.zeros(n_samples)
    eeg1_emg = np.zeros(n_samples)
    acc_x = np.zeros(n_samples)
    acc_y = np.zeros(n_samples)
    acc_z = np.zeros(n_samples)
    
    print("\n📊 Generating waveforms:")
    
    # === Segment 1: Wake state (0-120s) ===
    print("   ⏰ 0-120s: Wake state (Alpha + Beta)")
    mask_wake = (times >= 0) & (times < 120)
    eeg3[mask_wake] = generate_wake_eeg(times[mask_wake], sfreq)
    eeg1_emg[mask_wake] = generate_emg(times[mask_wake], amplitude=75, sfreq=sfreq)
    acc_x[mask_wake], acc_y[mask_wake], acc_z[mask_wake] = generate_wake_acc(times[mask_wake], sfreq)
    
    # === Segment 2: NREM Stage 1-2 (120-240s) with Spindles and K-complexes ===
    print("   😴 120-240s: NREM 1-2 (Theta + Spindles + K-complexes)")
    mask_nrem12 = (times >= 120) & (times < 240)
    eeg3[mask_nrem12] = generate_nrem12_eeg(times[mask_nrem12], sfreq)
    eeg1_emg[mask_nrem12] = generate_emg(times[mask_nrem12], amplitude=40, sfreq=sfreq)
    acc_x[mask_nrem12], acc_y[mask_nrem12], acc_z[mask_nrem12] = generate_sleep_acc(times[mask_nrem12], movement_prob=0.02)
    
    # === Segment 3: NREM Stage 3 - Deep sleep (240-360s) ===
    print("   💤 240-360s: NREM 3 (Deep sleep - high amplitude Delta)")
    mask_nrem3 = (times >= 240) & (times < 360)
    eeg3[mask_nrem3] = generate_nrem3_eeg(times[mask_nrem3], sfreq)
    eeg1_emg[mask_nrem3] = generate_emg(times[mask_nrem3], amplitude=15, sfreq=sfreq)
    acc_x[mask_nrem3], acc_y[mask_nrem3], acc_z[mask_nrem3] = generate_sleep_acc(times[mask_nrem3], movement_prob=0.005)
    
    # === Segment 4: REM sleep (360-480s) ===
    print("   👁️  360-480s: REM sleep (Theta + eye movements)")
    mask_rem = (times >= 360) & (times < 480)
    eeg3[mask_rem] = generate_rem_eeg(times[mask_rem], sfreq)
    eeg1_emg[mask_rem] = generate_emg(times[mask_rem], amplitude=8, sfreq=sfreq)
    acc_x[mask_rem], acc_y[mask_rem], acc_z[mask_rem] = generate_sleep_acc(times[mask_rem], movement_prob=0.001)
    
    # === Segment 5: Epilepsy events (480-600s) ===
    print("   ⚡ 480-500s: Baseline NREM")
    mask_baseline = (times >= 480) & (times < 500)
    eeg3[mask_baseline] = generate_nrem3_eeg(times[mask_baseline], sfreq)
    
    print("   ⚡ 500-520s: Seizure event (high-frequency spikes)")
    mask_seizure = (times >= 500) & (times < 520)
    eeg3[mask_seizure] = generate_seizure_eeg(times[mask_seizure], sfreq)
    
    print("   ⚡ 520-530s: Post-ictal suppression")
    mask_postictal = (times >= 520) & (times < 530)
    eeg3[mask_postictal] = generate_postictal_eeg(times[mask_postictal], sfreq)
    
    print("   ⚡ 530-600s: Recovery to normal")
    mask_recovery = (times >= 530) & (times < 600)
    eeg3[mask_recovery] = generate_nrem3_eeg(times[mask_recovery], sfreq)
    
    # EMG for epilepsy segment
    eeg1_emg[(times >= 480) & (times < 600)] = generate_emg(
        times[(times >= 480) & (times < 600)], amplitude=15, sfreq=sfreq
    )
    
    # Assemble data (5 channels)
    data = np.array([eeg3, eeg1_emg, acc_x, acc_y, acc_z])
    
    # Create MNE Raw object
    ch_names = ['EEG3', 'EEG1', 'ACC_X', 'ACC_Y', 'ACC_Z']
    ch_types = ['eeg', 'emg', 'misc', 'misc', 'misc']
    info = mne.create_info(ch_names, sfreq, ch_types)
    raw = mne.io.RawArray(data * 1e-6, info)  # Convert µV to V
    
    # Add annotations
    print("\n📝 Adding annotations...")
    annotations = create_annotations()
    raw.set_annotations(annotations)
    
    # Save as EDF
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / 'teaching_demo_10min.edf'
    
    print(f"\n💾 Saving to {output_file}...")
    raw.export(output_file, fmt='edf', overwrite=True)
    
    # Print summary
    file_size = output_file.stat().st_size / 1024
    print(f"\n✅ Teaching demo data generated successfully!")
    print(f"   📁 File: {output_file}")
    print(f"   ⏱️  Duration: {duration}s ({duration/60:.1f} minutes)")
    print(f"   📊 Sampling rate: {sfreq} Hz")
    print(f"   📺 Channels: {len(ch_names)} ({', '.join(ch_names)})")
    print(f"   📦 File size: {file_size:.1f} KB")
    print(f"   📋 Annotations: {len(annotations)} events")
    print(f"\n🎯 Scenarios included:")
    print(f"   • Wake state (Alpha/Beta waves)")
    print(f"   • NREM sleep stages (Theta/Delta waves)")
    print(f"   • Sleep spindles and K-complexes")
    print(f"   • REM sleep with eye movements")
    print(f"   • Seizure event with post-ictal suppression")
    
    return raw


def generate_wake_eeg(times, sfreq):
    """Generate wake state EEG: Alpha + Beta waves"""
    # Alpha waves (8-12 Hz) - dominant in relaxed wake state
    alpha = 30 * np.sin(2 * np.pi * 10 * times)
    
    # Beta waves (12-30 Hz) - present during alert state
    beta = 15 * np.sin(2 * np.pi * 20 * times + np.random.rand() * 2 * np.pi)
    
    # Background noise
    noise = 10 * np.random.randn(len(times))
    
    return alpha + beta + noise


def generate_nrem12_eeg(times, sfreq):
    """Generate NREM Stage 1-2: Theta waves + Sleep Spindles + K-complexes"""
    # Theta waves (4-8 Hz) - characteristic of light sleep
    theta = 40 * np.sin(2 * np.pi * 6 * times)
    
    # Delta waves (light presence)
    delta = 20 * np.sin(2 * np.pi * 2 * times)
    
    # Background noise
    noise = 8 * np.random.randn(len(times))
    
    eeg = theta + delta + noise
    
    # Add Sleep Spindles (12-14 Hz, 0.5-1.0 second duration)
    # Spindles occur at specific times in this segment
    spindle_times = [20, 45, 80]  # Relative to segment start
    for t in spindle_times:
        mask = (times >= times[0] + t) & (times < times[0] + t + 1.0)
        if mask.any():
            t_spindle = times[mask] - times[0] - t
            spindle = 60 * np.sin(2 * np.pi * 13 * t_spindle)
            # Gaussian envelope for smooth spindle
            envelope = np.exp(-((t_spindle - 0.5) ** 2) / 0.1)
            eeg[mask] += spindle * envelope
    
    # Add K-complexes (large amplitude slow waves)
    kcomplex_times = [60, 100]
    for t in kcomplex_times:
        mask = (times >= times[0] + t) & (times < times[0] + t + 0.8)
        if mask.any():
            t_kcomplex = times[mask] - times[0] - t
            kcomplex = -150 * np.sin(2 * np.pi * 1.5 * t_kcomplex)
            eeg[mask] += kcomplex
    
    return eeg


def generate_nrem3_eeg(times, sfreq):
    """Generate NREM Stage 3: High-amplitude Delta waves (deep sleep)"""
    # Delta waves (0.5-4 Hz) - dominant in deep sleep
    delta1 = 120 * np.sin(2 * np.pi * 1.5 * times)
    delta2 = 80 * np.sin(2 * np.pi * 0.8 * times + 0.5)
    
    # Minimal noise
    noise = 5 * np.random.randn(len(times))
    
    return delta1 + delta2 + noise


def generate_rem_eeg(times, sfreq):
    """Generate REM sleep: Theta waves + mixed frequencies + eye movements"""
    # Theta waves (5-7 Hz) - sawtooth waves characteristic of REM
    theta = 35 * np.sin(2 * np.pi * 6 * times)
    
    # Mixed frequency - Beta activity during REM
    beta = 20 * np.sin(2 * np.pi * 18 * times + np.random.rand() * 2 * np.pi)
    
    # Some alpha activity
    alpha = 15 * np.sin(2 * np.pi * 9 * times)
    
    eeg = theta + beta + alpha + 10 * np.random.randn(len(times))
    
    # Add rapid eye movement artifacts (low frequency, high amplitude)
    rem_times = [20, 50, 90]  # Relative times
    for t in rem_times:
        mask = (times >= times[0] + t) & (times < times[0] + t + 0.3)
        if mask.any():
            t_rem = times[mask] - times[0] - t
            eye_movement = 100 * np.sin(2 * np.pi * 2 * t_rem)
            eeg[mask] += eye_movement
    
    return eeg


def generate_seizure_eeg(times, sfreq):
    """Generate seizure event: High-frequency high-amplitude spikes"""
    # Fast spikes (15-25 Hz)
    spike_freq = 20
    spikes = 300 * np.sin(2 * np.pi * spike_freq * times)
    
    # Underlying slow wave
    slow_wave = 100 * np.sin(2 * np.pi * 3 * times)
    
    # Amplitude modulation (seizure intensity variation)
    t_rel = times - times[0]
    modulation = 0.5 + 0.5 * np.sin(2 * np.pi * 0.1 * t_rel)
    
    # Add noise
    noise = 20 * np.random.randn(len(times))
    
    return (spikes + slow_wave) * modulation + noise


def generate_postictal_eeg(times, sfreq):
    """Generate post-ictal suppression: Low-amplitude slow waves"""
    # Very slow delta waves with reduced amplitude
    delta = 30 * np.sin(2 * np.pi * 1 * times)
    noise = 5 * np.random.randn(len(times))
    return delta + noise


def generate_emg(times, amplitude, sfreq):
    """Generate EMG signal (electromyography)"""
    # High-frequency random noise (muscle activity)
    emg = amplitude * np.random.randn(len(times))
    
    # Simple bandpass filter simulation (20-200 Hz)
    # Use basic filtering without scipy
    # Generate frequency-appropriate noise directly
    n = len(times)
    freqs = np.fft.fftfreq(n, 1/sfreq)
    fft = np.fft.fft(emg)
    
    # Zero out frequencies outside 20-200 Hz
    mask = (np.abs(freqs) < 20) | (np.abs(freqs) > 200)
    fft[mask] = 0
    
    emg_filtered = np.real(np.fft.ifft(fft))
    
    return emg_filtered


def generate_wake_acc(times, sfreq):
    """Generate accelerometer data for wake state: Occasional movements"""
    n = len(times)
    acc_x = 0.1 * np.random.randn(n)
    acc_y = 0.1 * np.random.randn(n)
    acc_z = 1000 + 0.1 * np.random.randn(n)  # Gravity component
    
    # Add body movements every ~20 seconds
    for t in range(0, int(times[-1] - times[0]), 20):
        mask = (times >= times[0] + t) & (times < times[0] + t + 2)
        if mask.any():
            t_move = times[mask] - times[0] - t
            acc_x[mask] += 500 * np.sin(2 * np.pi * 2 * t_move)
            acc_y[mask] += 300 * np.cos(2 * np.pi * 2 * t_move)
    
    return acc_x, acc_y, acc_z


def generate_sleep_acc(times, movement_prob):
    """Generate accelerometer data for sleep state: Minimal movement"""
    n = len(times)
    acc_x = 0.05 * np.random.randn(n)
    acc_y = 0.05 * np.random.randn(n)
    acc_z = 1000 + 0.05 * np.random.randn(n)  # Gravity component
    
    # Occasional micro-movements
    if np.random.rand() < movement_prob * len(times) / 250:
        idx = np.random.randint(0, max(1, n - 250))
        acc_x[idx:idx+250] += 100 * np.random.randn(250)
    
    return acc_x, acc_y, acc_z


def create_annotations():
    """Create event annotations for the demo data"""
    from mne import Annotations
    
    onset = []
    duration = []
    description = []
    
    # Sleep stage annotations (every 4 seconds = 1 epoch)
    epoch_duration = 4  # seconds
    n_epochs = 150  # 600 seconds / 4 = 150 epochs
    
    for i in range(n_epochs):
        onset.append(i * epoch_duration)
        duration.append(epoch_duration)
        
        # Assign stage based on time
        t = i * epoch_duration
        if t < 120:
            description.append('Wake')
        elif t < 240:
            description.append('NREM')
        elif t < 360:
            description.append('NREM')
        elif t < 480:
            description.append('REM')
        else:
            description.append('NREM')
    
    # Special event annotations
    # Sleep Spindles
    onset.extend([140, 165, 200])
    duration.extend([1.0, 1.0, 1.0])
    description.extend(['Spindle', 'Spindle', 'Spindle'])
    
    # K-complexes
    onset.extend([180, 220])
    duration.extend([0.8, 0.8])
    description.extend(['K-complex', 'K-complex'])
    
    # Rapid eye movements
    onset.extend([380, 410, 450])
    duration.extend([0.3, 0.3, 0.3])
    description.extend(['REM', 'REM', 'REM'])
    
    # Seizure event
    onset.append(500)
    duration.append(20)
    description.append('Seizure')
    
    # Post-ictal suppression
    onset.append(520)
    duration.append(10)
    description.append('Post-ictal')
    
    return Annotations(onset, duration, description)


if __name__ == '__main__':
    import sys
    
    # Allow custom output directory from command line
    output_dir = sys.argv[1] if len(sys.argv) > 1 else 'data/teaching'
    
    try:
        raw = generate_teaching_demo_eeg(output_dir=output_dir)
        print("\n🎉 Generation complete! Ready for teaching mode.")
    except Exception as e:
        print(f"\n❌ Error generating teaching demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
