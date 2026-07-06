"""
Generate multiple teaching scenario EEG demo files for QLanalyser

This script creates 5 different 10-minute teaching scenarios:
1. Normal sleep cycle - Complete sleep progression
2. Multiple epilepsy events - Several seizure episodes
3. Insomnia pattern - Frequent awakenings
4. REM behavior disorder - High EMG during REM
5. Mixed artifacts - Various noise and artifact types
"""

import numpy as np
import mne
from pathlib import Path
import sys

# Import the main generation functions
sys.path.append(str(Path(__file__).parent))
from generate_teaching_demo_10min import (
    generate_wake_eeg, generate_nrem12_eeg, generate_nrem3_eeg,
    generate_rem_eeg, generate_seizure_eeg, generate_postictal_eeg,
    generate_emg, generate_wake_acc, generate_sleep_acc
)


def generate_normal_sleep_demo(output_dir='data/teaching'):
    """
    Scenario 1: Normal sleep cycle
    Complete progression through sleep stages with good sleep architecture
    """
    sfreq = 250
    duration = 600
    n_samples = int(sfreq * duration)
    times = np.arange(n_samples) / sfreq
    
    print("🛌 Generating: Normal Sleep Cycle Demo")
    
    eeg3 = np.zeros(n_samples)
    eeg1_emg = np.zeros(n_samples)
    acc_x = np.zeros(n_samples)
    acc_y = np.zeros(n_samples)
    acc_z = np.zeros(n_samples)
    
    # Smooth progression: Wake -> NREM1-2 -> NREM3 -> NREM2 -> REM
    segments = [
        (0, 60, 'wake', 70),
        (60, 180, 'nrem12', 40),
        (180, 360, 'nrem3', 15),
        (360, 480, 'nrem12', 25),
        (480, 600, 'rem', 8)
    ]
    
    for start, end, stage, emg_amp in segments:
        mask = (times >= start) & (times < end)
        
        if stage == 'wake':
            eeg3[mask] = generate_wake_eeg(times[mask], sfreq)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_wake_acc(times[mask], sfreq)
        elif stage == 'nrem12':
            eeg3[mask] = generate_nrem12_eeg(times[mask], sfreq)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_sleep_acc(times[mask], 0.01)
        elif stage == 'nrem3':
            eeg3[mask] = generate_nrem3_eeg(times[mask], sfreq)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_sleep_acc(times[mask], 0.005)
        elif stage == 'rem':
            eeg3[mask] = generate_rem_eeg(times[mask], sfreq)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_sleep_acc(times[mask], 0.001)
        
        eeg1_emg[mask] = generate_emg(times[mask], emg_amp, sfreq)
    
    return save_demo(eeg3, eeg1_emg, acc_x, acc_y, acc_z, sfreq, 
                     'teaching_demo_normal_sleep.edf', output_dir,
                     "Normal sleep cycle with smooth stage transitions")


def generate_epilepsy_multiple_demo(output_dir='data/teaching'):
    """
    Scenario 2: Multiple epilepsy events
    Baseline with 3 distinct seizure events throughout recording
    """
    sfreq = 250
    duration = 600
    n_samples = int(sfreq * duration)
    times = np.arange(n_samples) / sfreq
    
    print("⚡ Generating: Multiple Epilepsy Events Demo")
    
    eeg3 = np.zeros(n_samples)
    eeg1_emg = np.zeros(n_samples)
    
    # Baseline: NREM sleep
    eeg3[:] = generate_nrem3_eeg(times, sfreq)
    eeg1_emg[:] = generate_emg(times, 20, sfreq)
    
    # Insert 3 seizure events
    seizure_times = [(100, 115), (300, 320), (500, 525)]
    
    for start, end in seizure_times:
        mask_seizure = (times >= start) & (times < end)
        eeg3[mask_seizure] = generate_seizure_eeg(times[mask_seizure], sfreq)
        
        # Post-ictal suppression
        mask_post = (times >= end) & (times < end + 10)
        if mask_post.any():
            eeg3[mask_post] = generate_postictal_eeg(times[mask_post], sfreq)
    
    acc_x, acc_y, acc_z = generate_sleep_acc(times, 0.005)
    
    return save_demo(eeg3, eeg1_emg, acc_x, acc_y, acc_z, sfreq,
                     'teaching_demo_epilepsy_multiple.edf', output_dir,
                     "Multiple seizure events with post-ictal periods")


def generate_insomnia_demo(output_dir='data/teaching'):
    """
    Scenario 3: Insomnia pattern
    Frequent awakenings and difficulty maintaining sleep
    """
    sfreq = 250
    duration = 600
    n_samples = int(sfreq * duration)
    times = np.arange(n_samples) / sfreq
    
    print("😫 Generating: Insomnia Pattern Demo")
    
    eeg3 = np.zeros(n_samples)
    eeg1_emg = np.zeros(n_samples)
    acc_x = np.zeros(n_samples)
    acc_y = np.zeros(n_samples)
    acc_z = np.zeros(n_samples)
    
    # Fragmented sleep pattern
    segments = [
        (0, 80, 'wake', 70),
        (80, 140, 'nrem12', 40),
        (140, 180, 'wake', 75),  # Awakening
        (180, 280, 'nrem12', 35),
        (280, 320, 'wake', 70),  # Awakening
        (320, 420, 'nrem3', 20),
        (420, 460, 'nrem12', 30),
        (460, 500, 'wake', 65),  # Awakening
        (500, 600, 'nrem12', 35)
    ]
    
    for start, end, stage, emg_amp in segments:
        mask = (times >= start) & (times < end)
        
        if stage == 'wake':
            eeg3[mask] = generate_wake_eeg(times[mask], sfreq)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_wake_acc(times[mask], sfreq)
        elif stage == 'nrem12':
            eeg3[mask] = generate_nrem12_eeg(times[mask], sfreq)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_sleep_acc(times[mask], 0.02)
        elif stage == 'nrem3':
            eeg3[mask] = generate_nrem3_eeg(times[mask], sfreq)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_sleep_acc(times[mask], 0.01)
        
        eeg1_emg[mask] = generate_emg(times[mask], emg_amp, sfreq)
    
    return save_demo(eeg3, eeg1_emg, acc_x, acc_y, acc_z, sfreq,
                     'teaching_demo_insomnia.edf', output_dir,
                     "Insomnia pattern with frequent awakenings")


def generate_rem_behavior_demo(output_dir='data/teaching'):
    """
    Scenario 4: REM behavior disorder
    Normal REM sleep but with abnormally high muscle tone (EMG)
    """
    sfreq = 250
    duration = 600
    n_samples = int(sfreq * duration)
    times = np.arange(n_samples) / sfreq
    
    print("🏃 Generating: REM Behavior Disorder Demo")
    
    eeg3 = np.zeros(n_samples)
    eeg1_emg = np.zeros(n_samples)
    acc_x = np.zeros(n_samples)
    acc_y = np.zeros(n_samples)
    acc_z = np.zeros(n_samples)
    
    segments = [
        (0, 120, 'nrem3', 15),
        (120, 240, 'nrem12', 30),
        (240, 420, 'rem', 60),  # High EMG during REM (abnormal)
        (420, 600, 'rem', 55)   # Continued high EMG
    ]
    
    for start, end, stage, emg_amp in segments:
        mask = (times >= start) & (times < end)
        
        if stage == 'nrem12':
            eeg3[mask] = generate_nrem12_eeg(times[mask], sfreq)
        elif stage == 'nrem3':
            eeg3[mask] = generate_nrem3_eeg(times[mask], sfreq)
        elif stage == 'rem':
            eeg3[mask] = generate_rem_eeg(times[mask], sfreq)
            # Add movement artifacts during REM (abnormal)
            acc_x[mask], acc_y[mask], acc_z[mask] = generate_sleep_acc(times[mask], 0.05)
        
        eeg1_emg[mask] = generate_emg(times[mask], emg_amp, sfreq)
    
    return save_demo(eeg3, eeg1_emg, acc_x, acc_y, acc_z, sfreq,
                     'teaching_demo_rem_behavior.edf', output_dir,
                     "REM behavior disorder with elevated muscle tone")


def generate_mixed_artifacts_demo(output_dir='data/teaching'):
    """
    Scenario 5: Mixed artifacts
    Various types of noise and artifacts for teaching recognition
    """
    sfreq = 250
    duration = 600
    n_samples = int(sfreq * duration)
    times = np.arange(n_samples) / sfreq
    
    print("🎭 Generating: Mixed Artifacts Demo")
    
    eeg3 = generate_nrem12_eeg(times, sfreq)
    eeg1_emg = generate_emg(times, 30, sfreq)
    acc_x, acc_y, acc_z = generate_sleep_acc(times, 0.01)
    
    # Add various artifacts
    
    # 1. Eye blinks (60-80s)
    mask = (times >= 60) & (times < 80)
    for t in [62, 65, 68, 72, 76]:
        blink_mask = (times >= t) & (times < t + 0.2)
        if blink_mask.any():
            eeg3[blink_mask] += 150 * np.exp(-5 * (times[blink_mask] - t))
    
    # 2. 50/60 Hz electrical noise (150-200s)
    mask = (times >= 150) & (times < 200)
    eeg3[mask] += 20 * np.sin(2 * np.pi * 50 * times[mask])
    
    # 3. Electrode pop artifact (280s)
    mask = (times >= 280) & (times < 280.5)
    if mask.any():
        eeg3[mask] += 500 * np.exp(-10 * (times[mask] - 280))
    
    # 4. Movement artifacts (400-420s)
    mask = (times >= 400) & (times < 420)
    eeg3[mask] += 100 * np.sin(2 * np.pi * 1.5 * times[mask]) * np.random.rand(mask.sum())
    acc_x[mask], acc_y[mask], acc_z[mask] = generate_wake_acc(times[mask], sfreq)
    
    # 5. Muscle tension artifact (500-550s)
    mask = (times >= 500) & (times < 550)
    eeg1_emg[mask] += generate_emg(times[mask], 80, sfreq)
    
    return save_demo(eeg3, eeg1_emg, acc_x, acc_y, acc_z, sfreq,
                     'teaching_demo_mixed_artifacts.edf', output_dir,
                     "Various artifacts for teaching recognition")


def save_demo(eeg3, eeg1_emg, acc_x, acc_y, acc_z, sfreq, filename, output_dir, description):
    """Helper function to save demo data"""
    data = np.array([eeg3, eeg1_emg, acc_x, acc_y, acc_z])
    
    ch_names = ['EEG3', 'EEG1', 'ACC_X', 'ACC_Y', 'ACC_Z']
    ch_types = ['eeg', 'emg', 'misc', 'misc', 'misc']
    info = mne.create_info(ch_names, sfreq, ch_types)
    raw = mne.io.RawArray(data * 1e-6, info)
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / filename
    
    raw.export(output_file, fmt='edf', overwrite=True)
    
    file_size = output_file.stat().st_size / 1024
    print(f"   ✅ Saved: {filename} ({file_size:.1f} KB)")
    print(f"   📝 {description}")
    
    return raw


def main():
    """Generate all teaching demo scenarios"""
    output_dir = sys.argv[1] if len(sys.argv) > 1 else 'data/teaching'
    
    print("🎓 Generating Multiple Teaching Demo Scenarios")
    print("=" * 60)
    
    demos = [
        generate_normal_sleep_demo,
        generate_epilepsy_multiple_demo,
        generate_insomnia_demo,
        generate_rem_behavior_demo,
        generate_mixed_artifacts_demo
    ]
    
    for i, demo_func in enumerate(demos, 1):
        print(f"\n[{i}/5] ", end="")
        try:
            demo_func(output_dir)
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🎉 All teaching demos generated successfully!")
    print(f"📁 Location: {output_dir}/")
    print("\n📋 Available demos:")
    print("   1. teaching_demo_normal_sleep.edf - Normal sleep cycle")
    print("   2. teaching_demo_epilepsy_multiple.edf - Multiple seizure events")
    print("   3. teaching_demo_insomnia.edf - Insomnia with awakenings")
    print("   4. teaching_demo_rem_behavior.edf - REM behavior disorder")
    print("   5. teaching_demo_mixed_artifacts.edf - Various artifacts")


if __name__ == '__main__':
    main()
