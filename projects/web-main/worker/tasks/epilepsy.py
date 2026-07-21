from eeg_core.analysis.epilepsy import run_epilepsy


def run_task(input_path, output_dir, parameters=None):
    return run_epilepsy(input_path, output_dir, parameters or {})
