from eeg_core.preprocess.quality import summarize_quality


def run_preprocess(path, parameters=None):
    return summarize_quality(path, parameters or {})

