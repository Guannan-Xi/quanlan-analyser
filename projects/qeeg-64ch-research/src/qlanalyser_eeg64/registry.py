"""Machine-readable restoration status for every historical report method."""

METHOD_REGISTRY = {
    "io": {"status": "implemented", "scope": "BDF/EDF/SET/VHDR/FIF/CNT input with SHA256 provenance"},
    "preprocessing": {"status": "implemented", "scope": "50 Hz notch, 0.5-45 Hz band-pass, average reference and 250 Hz resampling"},
    "automatic_qc": {"status": "implemented_with_optional_dependency", "scope": "bad-channel screen/interpolation, extended Infomax ICA, optional ICLabel, epoch screen and safety gate"},
    "spectral": {"status": "implemented", "scope": "Welch PSD, absolute/relative bandpower, PAF, TBR and FAA"},
    "gfp_gmd": {"status": "implemented", "scope": "full-record GFP and polarity-invariant GMD"},
    "microstates": {"status": "implemented_algorithm_recovered", "scope": "A-F maps, full-record labels, temporal statistics and transitions"},
    "complexity": {"status": "implemented_algorithm_recovered", "scope": "Hjorth, entropy, fractal and multiscale measures"},
    "spatial_complexity": {"status": "implemented_algorithm_recovered", "scope": "Omega complexity from full-record channel-correlation eigenvalue entropy"},
    "connectivity": {"status": "implemented_algorithm_recovered", "scope": "ImCoh, wPLI2, ciPLV, PPC, coherence, PLV, PLI and AEC"},
    "pac_cfc": {"status": "implemented_algorithm_recovered", "scope": "Tort PAC, mean-vector length and n:m phase-locking"},
    "aperiodic_specparam": {"status": "implemented_optional_dependency", "scope": "Specparam full-record spectrum peak and aperiodic fitting"},
    "erp": {"status": "pending_event_contract", "scope": "requires verified event markers and experimental timing"},
    "clinical_report_renderer": {"status": "implemented", "scope": "bound two-page HTML report, visual manifest and structured CSV exports"},
}
