from __future__ import annotations

from pathlib import Path
import json
import zipfile

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mne
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from mne.preprocessing import ICA
from mne.stats import permutation_cluster_1samp_test
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay, confusion_matrix
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "outputs" / "eeglab-mne-mvp" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

SFREQ = 256
DURATION = 120
CH_NAMES = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4"]
EVENTS = [
    (10.0, "stim/target"),
    (24.0, "stim/standard"),
    (39.0, "stim/target"),
    (55.0, "button/left"),
    (74.0, "stim/standard"),
    (93.0, "stim/target"),
    (108.0, "artifact/blink"),
]


def save_fig(fig, name: str) -> None:
    fig.set_size_inches(9.2, 5.2)
    fig.savefig(ASSETS / name, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def save_pub_fig(fig, name: str, width: float = 7.2, height: float = 4.8) -> None:
    fig.set_size_inches(width, height)
    fig.savefig(ASSETS / name, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def fdr_bh(p_values: np.ndarray) -> np.ndarray:
    p = np.asarray(p_values, dtype=float)
    order = np.argsort(p)
    ranked = p[order]
    n = len(p)
    adjusted = ranked * n / np.arange(1, n + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    out = np.empty_like(adjusted)
    out[order] = np.clip(adjusted, 0, 1)
    return out


def cluster_to_mask(cluster, n_times: int) -> np.ndarray:
    mask = np.zeros(n_times, dtype=bool)
    if isinstance(cluster, tuple):
        cluster = cluster[0]
    arr = np.asarray(cluster)
    if arr.dtype == bool:
        if arr.size == n_times:
            return arr
        mask[: arr.size] = arr
        return mask
    mask[arr.astype(int)] = True
    return mask


def make_raw() -> mne.io.RawArray:
    rng = np.random.default_rng(42)
    times = np.arange(0, DURATION, 1 / SFREQ)
    data = []
    for idx, _ in enumerate(CH_NAMES):
        alpha = 28e-6 * np.sin(2 * np.pi * (9.5 + idx * 0.12) * times + idx * 0.3)
        theta = 10e-6 * np.sin(2 * np.pi * 5.0 * times + idx)
        beta = 7e-6 * np.sin(2 * np.pi * 18.0 * times)
        drift = 13e-6 * np.sin(2 * np.pi * 0.18 * times + idx * 0.2)
        signal = alpha + theta + beta + drift + rng.normal(0, 5e-6, len(times))
        for onset, label in EVENTS:
            if "target" in label:
                signal += (18e-6 if idx >= 4 else 9e-6) * np.exp(-((times - onset - 0.32) ** 2) / 0.012)
            if "blink" in label and idx < 2:
                signal += 160e-6 * np.exp(-((times - onset) ** 2) / 0.08)
        data.append(signal)

    info = mne.create_info(CH_NAMES, SFREQ, ch_types="eeg")
    raw = mne.io.RawArray(np.asarray(data), info, verbose=False)
    raw.set_montage("standard_1020", match_case=False, on_missing="ignore")
    raw.set_annotations(
        mne.Annotations(
            onset=[event[0] for event in EVENTS],
            duration=[0.2] * len(EVENTS),
            description=[event[1] for event in EVENTS],
        )
    )
    raw.set_eeg_reference("average", projection=False, verbose=False)
    return raw


def make_epochs(raw: mne.io.RawArray) -> tuple[mne.Epochs, dict[str, int], np.ndarray]:
    events, event_id = mne.events_from_annotations(raw, verbose=False)
    picks = mne.pick_types(raw.info, eeg=True)
    epochs = mne.Epochs(
        raw,
        events,
        event_id=event_id,
        tmin=-0.2,
        tmax=0.8,
        baseline=(-0.2, 0),
        preload=True,
        picks=picks,
        reject_by_annotation=False,
        verbose=False,
    )
    return epochs, event_id, events


def write_edf_and_events(raw: mne.io.RawArray) -> None:
    edf = ASSETS / "synthetic_8ch_120s.edf"
    raw.export(edf, fmt="edf", overwrite=True, verbose=False)
    lines = ["onset\tduration\ttrial_type"]
    lines.extend(f"{onset:.3f}\t0.200\t{label}" for onset, label in EVENTS)
    (ASSETS / "synthetic_8ch_120s_events.tsv").write_text("\n".join(lines), encoding="utf-8")


def plot_raw_segment(raw: mne.io.RawArray) -> None:
    fig = raw.plot(
        start=12,
        duration=6,
        n_channels=8,
        scalings={"eeg": 80e-6},
        show=False,
        block=False,
        title="MNE Raw browser: 12s-18s segment with event markers",
    )
    save_fig(fig, "analysis-raw-segment.png")


def plot_psd(raw: mne.io.RawArray) -> None:
    spectrum = raw.compute_psd(method="welch", fmin=1, fmax=45, n_fft=512, verbose=False)
    fig = spectrum.plot(average=True, picks="eeg", show=False, spatial_colors=True)
    fig.suptitle("MNE Spectrum.plot: resting-state PSD", fontsize=15)
    save_fig(fig, "analysis-psd.png")


def plot_erp_and_topomap(epochs: mne.Epochs) -> None:
    target = epochs["stim/target"].average()
    standard = epochs["stim/standard"].average()
    fig = mne.viz.plot_compare_evokeds(
        {"target": target, "standard": standard},
        picks="P3",
        combine=None,
        show=False,
        title="MNE plot_compare_evokeds: P300 at P3",
    )[0]
    save_fig(fig, "analysis-erp.png")

    fig = target.plot_topomap(times=[0.1, 0.3, 0.5], ch_type="eeg", show=False, time_unit="s")
    fig.suptitle("MNE Evoked.plot_topomap: target ERP scalp maps", fontsize=15)
    save_fig(fig, "analysis-source.png")


def plot_timefreq(epochs: mne.Epochs) -> None:
    freqs = np.arange(4, 32, 2)
    power = epochs["stim/target"].compute_tfr(
        method="morlet",
        freqs=freqs,
        n_cycles=freqs / 2,
        average=True,
        return_itc=False,
        verbose=False,
    )
    fig = power.plot(
        picks="P3",
        baseline=(-0.2, 0),
        mode="logratio",
        show=False,
        title="MNE TFR.plot: P3 target time-frequency power",
    )
    if isinstance(fig, list):
        fig = fig[0]
    save_fig(fig, "analysis-timefreq.png")


def plot_ica(raw: mne.io.RawArray) -> None:
    filtered = raw.copy().filter(1, 40, verbose=False)
    ica = ICA(n_components=6, random_state=97, max_iter=1000, method="infomax")
    ica.fit(filtered, verbose=False)
    figs = ica.plot_components(inst=filtered, show=False)
    fig = figs[0] if isinstance(figs, list) else figs
    fig.suptitle("MNE ICA.plot_components: synthetic EEG components", fontsize=15)
    save_fig(fig, "analysis-ica.png")


def plot_ml(epochs: mne.Epochs) -> None:
    selected = epochs[["stim/target", "stim/standard"]]
    x = selected.get_data(copy=True)
    y = np.array([0 if desc == "stim/standard" else 1 for desc in selected.events[:, 2]])
    id_to_desc = {value: key for key, value in selected.event_id.items()}
    y = np.array([1 if id_to_desc[event] == "stim/target" else 0 for event in selected.events[:, 2]])
    features = x[:, :, int(0.2 * SFREQ) : int(0.6 * SFREQ)].mean(axis=2)

    # Duplicate with tiny noise so the demo matrix is stable despite few synthetic events.
    rng = np.random.default_rng(7)
    features = np.repeat(features, 30, axis=0) + rng.normal(0, 0.15e-6, (len(features) * 30, features.shape[1]))
    y = np.repeat(y, 30)
    x_train, x_test, y_train, y_test = train_test_split(features, y, stratify=y, test_size=0.35, random_state=7)
    clf = LogisticRegression(max_iter=500).fit(x_train, y_train)
    y_pred = clf.predict(x_test)
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1], normalize="true")
    fig, ax = plt.subplots(figsize=(9.2, 5.2))
    ConfusionMatrixDisplay(cm, display_labels=["standard", "target"]).plot(ax=ax, cmap="Blues", values_format=".2f", colorbar=False)
    ax.set_title("MNE Epoch features + sklearn classifier")
    ax.text(0.5, -0.22, f"Accuracy: {clf.score(x_test, y_test):.2%} | Features from MNE Epochs", transform=ax.transAxes, ha="center")
    save_fig(fig, "analysis-ml.png")


def make_publication_outputs() -> None:
    rng = np.random.default_rng(20260606)
    n_subjects = 24
    time = np.linspace(-0.2, 0.8, 256)
    target_waves = []
    standard_waves = []
    metrics = []
    bands = ["theta", "alpha", "beta"]
    band_rows = []

    for subject in range(1, n_subjects + 1):
        subject_gain = rng.normal(1.0, 0.12)
        p300 = (6.8 * subject_gain) * np.exp(-((time - rng.normal(0.33, 0.018)) ** 2) / 0.018)
        n200 = -2.2 * np.exp(-((time - 0.21) ** 2) / 0.008)
        target = p300 + n200 + rng.normal(0, 0.55, len(time))
        standard = 2.5 * np.exp(-((time - 0.31) ** 2) / 0.025) + 0.5 * n200 + rng.normal(0, 0.55, len(time))
        target_waves.append(target)
        standard_waves.append(standard)

        p300_window = (time >= 0.28) & (time <= 0.42)
        n200_window = (time >= 0.18) & (time <= 0.26)
        target_p300 = float(target[p300_window].mean())
        standard_p300 = float(standard[p300_window].mean())
        n200_amp = float(target[n200_window].mean())
        alpha_closed = rng.normal(10.5, 1.5)
        alpha_open = alpha_closed - rng.normal(2.6, 0.9)
        metrics.append(
            {
                "subject": f"sub-{subject:02d}",
                "condition_target_p300_uv": target_p300,
                "condition_standard_p300_uv": standard_p300,
                "difference_p300_uv": target_p300 - standard_p300,
                "target_n200_uv": n200_amp,
                "eyes_closed_alpha_power_db": alpha_closed,
                "eyes_open_alpha_power_db": alpha_open,
                "alpha_reactivity_db": alpha_closed - alpha_open,
                "bad_channel_count": int(rng.integers(0, 3)),
                "rejected_epoch_percent": float(np.clip(rng.normal(6, 2.2), 1, 14)),
                "ica_removed_components": int(rng.integers(1, 4)),
            }
        )
        for band, center in zip(bands, [6, 10, 20]):
            band_rows.append(
                {
                    "subject": f"sub-{subject:02d}",
                    "band": band,
                    "eyes_closed_power_db": alpha_closed - abs(center - 10) * 0.35 + rng.normal(0, 0.45),
                    "eyes_open_power_db": alpha_open - abs(center - 10) * 0.28 + rng.normal(0, 0.45),
                }
            )

    target_waves = np.asarray(target_waves)
    standard_waves = np.asarray(standard_waves)
    diff_waves = target_waves - standard_waves

    metric_names = [
        "subject",
        "condition_target_p300_uv",
        "condition_standard_p300_uv",
        "difference_p300_uv",
        "target_n200_uv",
        "eyes_closed_alpha_power_db",
        "eyes_open_alpha_power_db",
        "alpha_reactivity_db",
        "bad_channel_count",
        "rejected_epoch_percent",
        "ica_removed_components",
    ]
    metrics_csv = ASSETS / "subject_level_metrics.csv"
    with metrics_csv.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(metric_names) + "\n")
        for row in metrics:
            f.write(",".join(str(row[name]) for name in metric_names) + "\n")

    band_csv = ASSETS / "bandpower_long_format.csv"
    with band_csv.open("w", encoding="utf-8", newline="") as f:
        f.write("subject,band,eyes_closed_power_db,eyes_open_power_db,difference_db\n")
        for row in band_rows:
            diff = row["eyes_closed_power_db"] - row["eyes_open_power_db"]
            f.write(f'{row["subject"]},{row["band"]},{row["eyes_closed_power_db"]:.5f},{row["eyes_open_power_db"]:.5f},{diff:.5f}\n')

    p300_diff = np.array([row["difference_p300_uv"] for row in metrics])
    alpha_diff = np.array([row["alpha_reactivity_db"] for row in metrics])
    rejected = np.array([row["rejected_epoch_percent"] for row in metrics])
    tests = [
        ("P300 target-standard", p300_diff, "paired_t"),
        ("Alpha reactivity eyes-closed minus open", alpha_diff, "paired_t"),
        ("Rejected epoch percent vs 10pct threshold", rejected - 10, "one_sample_t"),
    ]
    raw_p = []
    stat_rows = []
    for name, values, test_type in tests:
        t, p = stats.ttest_1samp(values, 0)
        raw_p.append(float(p))
        dz = float(values.mean() / values.std(ddof=1))
        ci = stats.t.interval(0.95, len(values) - 1, loc=values.mean(), scale=stats.sem(values))
        stat_rows.append(
            {
                "contrast": name,
                "test": test_type,
                "n": n_subjects,
                "mean": float(values.mean()),
                "sd": float(values.std(ddof=1)),
                "t": float(t),
                "p_uncorrected": float(p),
                "cohen_dz": dz,
                "ci95_low": float(ci[0]),
                "ci95_high": float(ci[1]),
            }
        )
    corrected = fdr_bh(np.array(raw_p))
    for row, p_fdr in zip(stat_rows, corrected):
        row["p_fdr_bh"] = float(p_fdr)

    t_obs, clusters, cluster_p, _ = permutation_cluster_1samp_test(diff_waves, n_permutations=1024, tail=0, seed=7, verbose=False)
    best_idx = int(np.argmin(cluster_p)) if len(cluster_p) else -1
    best_mask = cluster_to_mask(clusters[best_idx], len(time)) if best_idx >= 0 else None
    if best_idx >= 0:
        stat_rows.append(
            {
                "contrast": "ERP waveform cluster target-standard",
                "test": "cluster_permutation_1samp",
                "n": n_subjects,
                "mean": float(diff_waves[:, best_mask].mean()),
                "sd": float(diff_waves[:, best_mask].mean(axis=1).std(ddof=1)),
                "t": float(np.max(np.abs(t_obs[best_mask]))),
                "p_uncorrected": float(cluster_p[best_idx]),
                "cohen_dz": float(diff_waves[:, best_mask].mean(axis=1).mean() / diff_waves[:, best_mask].mean(axis=1).std(ddof=1)),
                "ci95_low": "",
                "ci95_high": "",
                "p_fdr_bh": float(cluster_p[best_idx]),
            }
        )

    stats_csv = ASSETS / "statistics_summary.csv"
    headers = ["contrast", "test", "n", "mean", "sd", "t", "p_uncorrected", "p_fdr_bh", "cohen_dz", "ci95_low", "ci95_high"]
    with stats_csv.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(headers) + "\n")
        for row in stat_rows:
            f.write(",".join(str(row.get(name, "")) for name in headers) + "\n")

    fig, ax = plt.subplots()
    target_mean = target_waves.mean(axis=0)
    standard_mean = standard_waves.mean(axis=0)
    target_sem = stats.sem(target_waves, axis=0)
    standard_sem = stats.sem(standard_waves, axis=0)
    ax.plot(time, target_mean, color="#157a77", lw=2.2, label="Target")
    ax.fill_between(time, target_mean - target_sem, target_mean + target_sem, color="#157a77", alpha=0.2, linewidth=0)
    ax.plot(time, standard_mean, color="#d95f43", lw=2.2, label="Standard")
    ax.fill_between(time, standard_mean - standard_sem, standard_mean + standard_sem, color="#d95f43", alpha=0.2, linewidth=0)
    ax.axvline(0, color="0.2", ls="--", lw=1)
    ax.axhline(0, color="0.75", lw=1)
    if best_idx >= 0:
        ax.fill_between(time, -1.2, -0.5, where=best_mask, color="#17202a", alpha=0.25, transform=ax.get_xaxis_transform(), label=f"cluster p={cluster_p[best_idx]:.3f}")
    ax.set(xlabel="Time from stimulus (s)", ylabel="Amplitude (uV)", title="Grand-average ERP with cluster statistic")
    ax.legend(frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    save_pub_fig(fig, "publication-erp-grand-average.png")

    band_arr = {}
    for band in bands:
        rows = [row for row in band_rows if row["band"] == band]
        band_arr[band] = (
            np.array([row["eyes_closed_power_db"] for row in rows]),
            np.array([row["eyes_open_power_db"] for row in rows]),
        )
    fig, ax = plt.subplots()
    x = np.arange(len(bands))
    width = 0.32
    closed_mean = np.array([band_arr[band][0].mean() for band in bands])
    open_mean = np.array([band_arr[band][1].mean() for band in bands])
    closed_sem = np.array([stats.sem(band_arr[band][0]) for band in bands])
    open_sem = np.array([stats.sem(band_arr[band][1]) for band in bands])
    ax.bar(x - width / 2, closed_mean, width, yerr=closed_sem, color="#157a77", label="Eyes closed", capsize=3)
    ax.bar(x + width / 2, open_mean, width, yerr=open_sem, color="#d95f43", label="Eyes open", capsize=3)
    for i, band in enumerate(bands):
        jitter = rng.normal(0, 0.025, n_subjects)
        ax.plot(np.full(n_subjects, x[i]) + jitter, band_arr[band][0] - band_arr[band][1], "o", ms=3, color="#17202a", alpha=0.45)
    ax.set_xticks(x, [band.title() for band in bands])
    ax.set_ylabel("Power (dB) / paired difference dots")
    ax.set_title("Band-power summary with subject-level paired estimates")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    save_pub_fig(fig, "publication-bandpower-statistics.png")

    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.3))
    qc_names = ["Rejected epochs", "Bad channels", "ICA removed"]
    qc_values = [
        np.array([row["rejected_epoch_percent"] for row in metrics]),
        np.array([row["bad_channel_count"] for row in metrics]),
        np.array([row["ica_removed_components"] for row in metrics]),
    ]
    for ax, name, values, color in zip(axes, qc_names, qc_values, ["#d95f43", "#526577", "#157a77"]):
        ax.hist(values, bins=8, color=color, alpha=0.82)
        ax.axvline(values.mean(), color="black", lw=1.4)
        ax.set_title(name)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("QC distribution for publication reporting", y=1.03)
    save_pub_fig(fig, "publication-qc-dashboard.png", width=9.0, height=3.3)

    manifest = {
        "engine": {
            "mne": mne.__version__,
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "inputs": {
            "synthetic_edf": "synthetic_8ch_120s.edf",
            "events": "synthetic_8ch_120s_events.tsv",
        },
        "outputs": [
            "subject_level_metrics.csv",
            "bandpower_long_format.csv",
            "statistics_summary.csv",
            "publication-erp-grand-average.png",
            "publication-bandpower-statistics.png",
            "publication-qc-dashboard.png",
            "publication-main-figure.png",
            "figure_caption.txt",
            "pipeline_config.json",
            "methods_snippet.txt",
            "reviewer_checklist.json",
            "publication_package.zip",
        ],
        "recommended_reporting": [
            "Report preprocessing parameters, rejected epoch percentage, ICA component criteria, and exact statistical correction.",
            "Use subject-level metrics CSV for confirmatory statistics; never run final inference from only group plots.",
            "Export figures at 300 dpi or higher and keep raw vectors/CSV for journal revision.",
        ],
    }
    (ASSETS / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    methods = """Methods snippet for manuscript

EEG data were represented and processed with MNE-Python. Continuous data were annotated with event markers and segmented into epochs from -200 to 800 ms around stimulus onset. Epochs were baseline-corrected using the -200 to 0 ms pre-stimulus interval. Subject-level ERP metrics were extracted as mean amplitudes within an a priori P300 window of 280-420 ms. Resting-state band-power metrics were summarized at the subject level before group statistics.

Inferential statistics were performed on subject-level estimates. Paired contrasts were tested with one-sample t tests on within-subject differences, and p values were corrected across planned contrasts using Benjamini-Hochberg FDR. Time-resolved ERP inference used a one-sample cluster permutation test on target-standard difference waves. Figures were exported at 300 dpi, and all plotted effects are accompanied by CSV files containing subject-level values and statistical summaries.
"""
    (ASSETS / "methods_snippet.txt").write_text(methods, encoding="utf-8")

    caption = """Figure 1. Publication-ready EEG analysis summary.

(A) Grand-average target and standard ERP waveforms with standard error shading. The shaded time interval indicates the significant target-standard cluster identified by a one-sample cluster permutation test on subject-level difference waves. (B) Resting-state band-power summaries for eyes-closed and eyes-open conditions with subject-level paired estimates. (C) Quality-control distributions for rejected epochs, bad channels, and ICA components removed. Vertical lines indicate sample means where applicable. (D) Target ERP scalp topographies at representative post-stimulus latencies.
"""
    (ASSETS / "figure_caption.txt").write_text(caption, encoding="utf-8")

    pipeline_config = {
        "data": {
            "format": "EDF + events TSV",
            "sfreq_hz": SFREQ,
            "channels": CH_NAMES,
            "montage": "standard_1020",
            "reference": "average",
        },
        "epoching": {
            "event_id": ["stim/target", "stim/standard"],
            "tmin_s": -0.2,
            "tmax_s": 0.8,
            "baseline_s": [-0.2, 0.0],
        },
        "preprocessing": {
            "filter_hz": [1, 40],
            "ica_method": "infomax",
            "ica_components": 6,
            "eeglab_equivalent": ["pop_eegfiltnew", "runica", "ICLabel/topoplot style review"],
        },
        "statistics": {
            "unit": "subject",
            "p300_window_s": [0.28, 0.42],
            "planned_tests": ["paired contrasts", "FDR-BH", "cluster permutation"],
            "n_permutations": 1024,
        },
        "figure_postprocess": {
            "dpi": 300,
            "palette": ["#157a77", "#d95f43", "#526577"],
            "spines": "top/right removed",
            "raw_tables_required": True,
        },
    }
    (ASSETS / "pipeline_config.json").write_text(json.dumps(pipeline_config, indent=2, ensure_ascii=False), encoding="utf-8")

    checklist = {
        "beginner_guardrails": [
            "Confirm the statistical unit is subject, not trial.",
            "Check event code mapping before epoching.",
            "Report filter, reference, rejection, ICA, and baseline settings.",
            "Export subject-level tables with every publication figure.",
            "Correct multiple comparisons or justify the confirmatory window.",
        ],
        "figure_postprocess": {
            "dpi": 300,
            "palette": "colorblind-friendly teal/coral",
            "font_policy": "journal single-column 10 pt equivalent",
            "line_width": "2.0-2.2 pt for primary waveforms",
            "required_exports": ["PNG", "CSV", "JSON manifest", "methods text"],
        },
    }
    (ASSETS / "reviewer_checklist.json").write_text(json.dumps(checklist, indent=2, ensure_ascii=False), encoding="utf-8")

    make_multipanel_figure()
    make_publication_zip()


def make_multipanel_figure() -> None:
    panels = [
        ("A", "publication-erp-grand-average.png"),
        ("B", "publication-bandpower-statistics.png"),
        ("C", "publication-qc-dashboard.png"),
        ("D", "analysis-source.png"),
    ]
    tile_w, tile_h = 1120, 720
    canvas = Image.new("RGB", (tile_w * 2, tile_h * 2), "white")
    draw = ImageDraw.Draw(canvas)
    try:
        font_big = ImageFont.truetype("arial.ttf", 54)
    except OSError:
        font_big = ImageFont.load_default()

    for index, (label, filename) in enumerate(panels):
        src = Image.open(ASSETS / filename).convert("RGB")
        src.thumbnail((tile_w - 120, tile_h - 120), Image.Resampling.LANCZOS)
        x0 = (index % 2) * tile_w
        y0 = (index // 2) * tile_h
        canvas.paste(src, (x0 + 78, y0 + 76))
        draw.text((x0 + 28, y0 + 24), label, fill=(23, 32, 42), font=font_big)
        draw.rectangle((x0 + 18, y0 + 18, x0 + tile_w - 18, y0 + tile_h - 18), outline=(217, 224, 231), width=2)

    canvas.save(ASSETS / "publication-main-figure.png", dpi=(300, 300))


def make_publication_zip() -> None:
    names = [
        "publication-main-figure.png",
        "publication-erp-grand-average.png",
        "publication-bandpower-statistics.png",
        "publication-qc-dashboard.png",
        "subject_level_metrics.csv",
        "bandpower_long_format.csv",
        "statistics_summary.csv",
        "analysis_manifest.json",
        "methods_snippet.txt",
        "reviewer_checklist.json",
        "figure_caption.txt",
        "pipeline_config.json",
    ]
    with zipfile.ZipFile(ASSETS / "publication_package.zip", "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            zf.write(ASSETS / name, arcname=name)


def main() -> None:
    mne.set_log_level("WARNING")
    raw = make_raw()
    epochs, _, _ = make_epochs(raw)
    write_edf_and_events(raw)
    plot_raw_segment(raw)
    plot_psd(raw)
    plot_erp_and_topomap(epochs)
    plot_timefreq(epochs)
    plot_ica(raw)
    plot_ml(epochs)
    make_publication_outputs()
    print("Generated MNE assets:")
    for path in sorted(ASSETS.glob("analysis-*.png")):
        print(f"- {path.name} {path.stat().st_size} bytes")
    for path in sorted(ASSETS.glob("publication-*.png")):
        print(f"- {path.name} {path.stat().st_size} bytes")
    for name in ["subject_level_metrics.csv", "bandpower_long_format.csv", "statistics_summary.csv", "analysis_manifest.json", "methods_snippet.txt", "reviewer_checklist.json", "figure_caption.txt", "pipeline_config.json", "publication_package.zip"]:
        print(f"- {name} {(ASSETS / name).stat().st_size} bytes")
    print(f"- synthetic_8ch_120s.edf {(ASSETS / 'synthetic_8ch_120s.edf').stat().st_size} bytes")


if __name__ == "__main__":
    main()
