from eeg_core.analysis.epilepsy_ml import run_epilepsy_ml


def run_task(input_path, output_dir, parameters=None):
    return run_epilepsy_ml(input_path, output_dir, parameters or {})
