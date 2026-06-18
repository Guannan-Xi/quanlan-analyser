ANALYSIS_TEMPLATES = [
    {
        "id": "metadata_qc",
        "name": "Metadata and signal QC",
        "module": "qc",
        "engine": "MNE-Python raw readers + NumPy signal checks",
        "outputs": ["reproducibility/qc_summary.json", "reproducibility/parameters.json", "reproducibility/software_versions.json", "reproducibility/workflow.json"],
        "production_status": "v01_required",
        "enabled": True,
        "prerequisites": ["Readable non-empty EEG file", "Supported EEG format"],
    },
    {
        "id": "resting_psd",
        "name": "Resting-state PSD / band power",
        "module": "psd",
        "engine": "MNE Raw.compute_psd(method='welch')",
        "outputs": ["tables/band_power.csv", "tables/channel_band_power.csv", "reproducibility/psd_summary.json", "reproducibility/parameters.json"],
        "production_status": "v01_enabled",
        "enabled": True,
        "prerequisites": ["Readable EEG file", "At least one usable EEG channel", "QC reviewed before interpretation"],
    },
    {
        "id": "erp_p300",
        "name": "ERP / P300 component metrics",
        "module": "erp",
        "engine": "MNE events_from_annotations + Epochs + Evoked",
        "outputs": ["tables/erp_metrics.csv", "reproducibility/erp_summary.json", "reproducibility/parameters.json"],
        "production_status": "v01_enabled_when_events_exist",
        "enabled": True,
        "prerequisites": ["Readable EEG file", "Verified event markers/annotations", "Condition semantics reviewed"],
    },
    {
        "id": "tfr_ersp_itc",
        "name": "Time-frequency / ERSP / ITC",
        "module": "tfr",
        "engine": "Planned MNE time-frequency methods",
        "outputs": [],
        "production_status": "planned_not_enabled_in_v01",
        "enabled": False,
        "prerequisites": ["Epoch design", "Baseline strategy", "Artifact rejection", "Multiple-comparison/statistical plan"],
    },
    {
        "id": "pac_cfc",
        "name": "PAC / cross-frequency coupling",
        "module": "pac",
        "engine": "Planned coupling pipeline with surrogate statistics",
        "outputs": [],
        "production_status": "planned_not_enabled_in_v01",
        "enabled": False,
        "prerequisites": ["Artifact controls", "Surrogate/null distribution", "Frequency-band justification", "Edge-effect handling"],
    },
    {
        "id": "connectivity",
        "name": "Connectivity",
        "module": "connectivity",
        "engine": "Planned connectivity pipeline",
        "outputs": [],
        "production_status": "planned_not_enabled_in_v01",
        "enabled": False,
        "prerequisites": ["Reference strategy", "Volume-conduction controls", "Connectivity metric selection", "Statistical validation"],
    },
]

PARADIGMS = [
    {
        "id": "resting_state",
        "name": "Resting state / eyes open-closed",
        "recommended_templates": ["metadata_qc", "resting_psd"],
        "notes": "Start with QC and PSD. Interpret band power with reference, artifacts, and individual alpha peak variability.",
    },
    {
        "id": "oddball_p300",
        "name": "Oddball / P300 ERP",
        "recommended_templates": ["metadata_qc", "erp_p300"],
        "notes": "Requires verified event markers and condition semantics before ERP interpretation.",
    },
]

RECOMMENDATION_RULES = [
    {
        "key": "event_marked_erp",
        "template_id": "erp_p300",
        "reason": "Files with valid event annotations can run ERP/P300 metrics after QC.",
        "parameters": {"tmin": -0.2, "tmax": 0.8, "baseline": [None, 0.0]},
    },
    {
        "key": "continuous_rest",
        "template_id": "resting_psd",
        "reason": "Continuous resting or eyes-open/eyes-closed data should start with PSD and band power after QC.",
        "parameters": {"fmin": 1, "fmax": 40},
    },
]
