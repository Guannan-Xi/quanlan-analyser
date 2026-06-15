from eeg_core.analysis.erp import run_erp


def run_task(input_path, output_dir, parameters=None):
    return run_erp(input_path, output_dir, parameters or {})

