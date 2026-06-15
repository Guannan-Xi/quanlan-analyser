from eeg_core.analysis.psd import run_psd


def run_task(input_path, output_dir, parameters=None):
    return run_psd(input_path, output_dir, parameters or {})

