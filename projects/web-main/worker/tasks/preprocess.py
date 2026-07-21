from eeg_core.preprocess.quality import run_quality_check


def run_task(input_path, output_dir, parameters=None):
    return run_quality_check(input_path, output_dir, parameters or {})

