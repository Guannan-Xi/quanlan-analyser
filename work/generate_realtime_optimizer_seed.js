const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const outDir = path.join(root, "outputs", "eeglab-mne-dev", "assets", "realtime_optimizer");
fs.mkdirSync(outDir, { recursive: true });

const statePath = path.join(outDir, "optimizer_state.json");
const existingState = fs.existsSync(statePath)
  ? JSON.parse(fs.readFileSync(statePath, "utf8").replace(/^\uFEFF/, ""))
  : {};

const sources = [
  {
    id: "mne-overview",
    title: "Overview of MEG/EEG analysis with MNE-Python",
    url: "https://mne.tools/stable/auto_tutorials/intro/10_overview.html",
    type: "official tutorial",
    focus: ["Raw", "Epochs", "Evoked", "SourceEstimate", "time-frequency", "PSD"],
  },
  {
    id: "mne-python-paper",
    title: "MEG and EEG data analysis with MNE-Python",
    url: "https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2013.00267/full",
    type: "paper",
    focus: ["MNE-Python", "event-related analysis", "source estimates"],
  },
  {
    id: "prep-pipeline",
    title: "The PREP pipeline: standardized preprocessing for large-scale EEG analysis",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC4471356/",
    type: "paper",
    focus: ["line noise", "bad channels", "robust reference", "large-scale preprocessing"],
  },
  {
    id: "artifact-review",
    title: "Removal of Artifacts from EEG Signals: A Review",
    url: "https://pmc.ncbi.nlm.nih.gov/articles/PMC6427454/",
    type: "review",
    focus: ["EOG", "ECG", "EMG", "ICA", "wavelet", "artifact removal"],
  },
  {
    id: "signal-processing-review",
    title: "Electroencephalography Signal Processing: A Comprehensive Review and Analysis of Methods and Techniques",
    url: "https://pubmed.ncbi.nlm.nih.gov/37514728/",
    type: "review",
    focus: ["preprocessing", "feature extraction", "classification", "time-frequency"],
  },
  {
    id: "eegdash-p300",
    title: "EEGDash / OpenNeuro P300 datasets",
    url: "https://eegdash.org/",
    type: "open dataset catalog",
    focus: ["P300", "visual oddball", "MNE Raw", "BIDS"],
  },
  {
    id: "moabb",
    title: "MOABB-compatible open EEG datasets",
    url: "https://neuropeek.com/datasets/moabb",
    type: "open dataset catalog",
    focus: ["motor imagery", "P300", "SSVEP", "resting state"],
  },
  {
    id: "mne-time-frequency",
    title: "Frequency and time-frequency sensor analysis",
    url: "https://mne.tools/stable/auto_tutorials/time-freq/20_sensors_time_frequency.html",
    type: "official tutorial",
    focus: ["TFR", "Morlet", "multitaper", "Stockwell", "ITC", "memory reduction"],
  },
  {
    id: "mne-decoding-mvpa",
    title: "Decoding (MVPA)",
    url: "https://mne.tools/stable/auto_tutorials/machine-learning/50_decoding.html",
    type: "official tutorial",
    focus: ["CSP", "motor imagery", "cross validation", "linear models", "overfitting risk"],
  },
];

const workflows = [
  ["raw-qc", "After uploading EDF, how can a user confirm sampling rate, channel units, bad channels, and event alignment?", ["Raw", "Events", "Visualization"]],
  ["prep", "If a paper requires PREP-style preprocessing, can the platform guide line-noise removal, bad-channel handling, and robust reference?", ["Filtering", "Bad channels", "Reference/CSD"]],
  ["ica-artifact", "When eye-movement and ECG artifacts are obvious, how can the platform help a novice understand ICA component selection risk?", ["Artifacts", "ICA", "Reports"]],
  ["p300", "Using an open P300/oddball dataset, can the platform reproduce target-standard ERP and expose a P300 window plus subject-level CSV?", ["Epochs", "Evoked/ERP", "Statistics"]],
  ["rest-psd", "Can resting eyes-open/eyes-closed data produce low-cost alpha peak, bandpower, and QC reports?", ["Spectrum/PSD", "Reports"]],
  ["tf-ersp", "Can Stroop or motor-imagery tasks produce ERSP/ITC/ERD and explain baseline choices?", ["Time-frequency", "Statistics"]],
  ["decoding", "Can a BCI user complete CSP/decoding cross-validation and see overfitting and cost warnings?", ["Decoding", "Reports"]],
  ["connectivity", "Can connectivity analysis clearly separate sensor-space, source-space, and volume-conduction risks?", ["Connectivity", "Source modeling"]],
  ["publication", "Can a publication user obtain methods, captions, manifests, and figure/table downloads from real results?", ["Reports", "Visualization"]],
  ["platform-cost", "Can routine analyses use fewer parameters and less compute without losing essential QC?", ["cost", "simplicity", "platform"]],
];

const pigQuestions = workflows.flatMap(([id, question, coverage], index) => [
  {
    id: `pig-${String(index * 3 + 1).padStart(3, "0")}`,
    workflow: id,
    question,
    expectedBehavior: "Pig assistant should first identify data type, research question, events/channels/sampling rate, then provide executable QL platform steps.",
    platformTest: "Use the development UI to complete the flow and record missing controls, misleading copy, complex parameters, and cost risk.",
    coverage,
  },
  {
    id: `pig-${String(index * 3 + 2).padStart(3, "0")}`,
    workflow: id,
    question: `Rewrite this as a novice user's plain-language Chinese question: ${question}`,
    expectedBehavior: "Pig assistant should give a short explanation and next-step style guidance without fabricating results.",
    platformTest: "Check whether the development UI supports this novice entry point; otherwise record a UX backlog item.",
    coverage,
  },
  {
    id: `pig-${String(index * 3 + 3).padStart(3, "0")}`,
    workflow: id,
    question: `Review from paper/tutorial reproduction perspective: ${question}`,
    expectedBehavior: "Pig assistant should cite method points and separate known facts, platform-supported actions, and user-supplied data needs.",
    platformTest: "Check that the result area shows only real generated content and remains empty when no real result exists.",
    coverage,
  },
]);

const optimizerState = {
  generatedAt: new Date().toISOString(),
  modePolicy: {
    conversationActive: "Listen for user-reported bugs and requirement changes first; fix confirmed issues in development and generate a release candidate only after validation.",
    conversationIdle: "Collect public EEG/MNE/paper/open-dataset materials, generate pig-assistant training questions, and use them to test QL EEG development.",
    releaseRule: "Release promotion requires idle release tasks and passing validation; customer UI must not expose internal training, review, or fake results.",
  },
  goals: [
    "Cover common EEG and MNE workflows as broadly as possible.",
    "Keep entry points and parameters simple.",
    "Prefer low-cost, reproducible, interpretable analysis paths.",
    "Record issues that require backend capability, real data, or user-supplied materials.",
    "Prevent pig assistant or platform UI from fabricating analysis results.",
  ],
  sources,
  workflows: workflows.map(([id, prompt, coverage]) => ({ id, prompt, coverage, status: "seeded" })),
  pigQuestions,
  issueBacklog: existingState.issueBacklog || [],
  needsUserMaterials: existingState.needsUserMaterials || [],
  trainingLog: [
    ...(existingState.trainingLog || []),
    {
      at: new Date().toISOString(),
      action: "seed-refresh",
      sources: sources.length,
      workflows: workflows.length,
      pigQuestions: pigQuestions.length,
    },
  ].slice(-200),
};

fs.writeFileSync(statePath, JSON.stringify(optimizerState, null, 2), "utf8");

const markdown = [
  "# Real-Time Optimizer",
  "",
  "This is internal development material for QL EEG and pig assistant. Do not expose it in the release UI.",
  "",
  "## Modes",
  "",
  "- Conversation active: listen for user-reported bugs and optimize the development version.",
  "- Conversation idle: collect public EEG/MNE/paper/open-dataset material, generate pig-assistant training questions, and test the QL EEG development version.",
  "- Release: promote only when idle and validated.",
  "",
  "## Seed Sources",
  "",
  ...sources.map((source) => `- ${source.title}: ${source.url}`),
  "",
  "## Seed Questions",
  "",
  ...pigQuestions.slice(0, 12).map((item) => `- ${item.id}: ${item.question}`),
  "",
  "Full queue: `optimizer_state.json`.",
];

fs.writeFileSync(path.join(outDir, "README.md"), markdown.join("\n"), "utf8");
console.log(`Generated ${sources.length} sources, ${workflows.length} workflows, ${pigQuestions.length} pig-assistant questions.`);
