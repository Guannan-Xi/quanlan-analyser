(() => {
  const ARCHITECTURE_SOURCE = {
    localDocument: "D:/Quanlan/Codes/Python/quanlan-analyser-official/docs/online_paid_platform_architecture.md",
    feishuDocument: "https://quanland.feishu.cn/wiki/LB03w1WMTizruikhudUcSUXknZb?fromScene=spaceOverview",
    version: "v1-research-paid-platform",
  };

  const DOMAIN_OBJECTS = [
    "User",
    "Organization",
    "Project",
    "Subject",
    "Session",
    "EEGFile",
    "Wallet",
    "RechargeOrder",
    "AnalysisOrder",
    "LedgerEntry",
    "WorkflowTemplate",
    "AnalysisTask",
    "Artifact",
    "Report",
    "AuditLog",
  ];

  const WORKFLOW_STEPS = [
    { id: "metadata", label: "Metadata", contract: "read sampling rate, channels, duration, annotations/events" },
    { id: "preview", label: "Preview", contract: "show raw signal and event distribution before analysis" },
    { id: "preprocess", label: "Preprocess", contract: "filter, rereference, resample, bad channels, ICA when applicable" },
    { id: "analysis", label: "Analysis", contract: "PSD, ERP, time-frequency, connectivity according to workflow template" },
    { id: "visualization", label: "Visualization", contract: "figures must have labels, units, legends, and reproducibility trace" },
    { id: "report", label: "Report Package", contract: "HTML/report, tables, methods, manifest, and package artifacts" },
  ];

  const FILE_STATUS = {
    uploaded: "uploaded",
    metadataReady: "metadata_ready",
    previewReady: "preview_ready",
    processing: "processing",
    archived: "archived",
    deleted: "deleted",
  };

  const TASK_STATUS = {
    draft: "draft",
    priced: "priced",
    frozen: "balance_frozen",
    queued: "queued",
    running: "running",
    completed: "completed",
    failed: "failed",
    delivered: "delivered",
  };

  const ARTIFACT_TYPES = {
    figure: "figure",
    table: "table",
    methods: "methods",
    manifest: "manifest",
    package: "package",
    raw: "raw",
  };

  const PLATFORM_LAYERS = [
    ["Browser Frontend", "Customer workspace, admin console, billing center, workflow designer"],
    ["Backend API", "Auth, projects, EEG files, billing, tasks, artifacts, reports"],
    ["Task Queue / Worker", "Metadata, preview, preprocess, PSD, ERP, ICA, report package"],
    ["EEG Core", "MNE-Python engine and EEGLAB-compatible workflows"],
    ["Storage", "Original files, derivatives, reports, database, audit logs"],
  ];

  function makeId(prefix) {
    return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 7)}`;
  }

  function createProject(input = {}) {
    const now = input.createdAt || new Date().toLocaleString("zh-CN", { hour12: false });
    return {
      objectType: "Project",
      id: input.id || makeId("project"),
      organizationId: input.organizationId || "local-org",
      ownerId: input.ownerId || "local-user",
      name: input.name || "Untitled EEG project",
      status: input.status || "draft",
      createdAt: now,
      updatedAt: input.updatedAt || now,
      subjectIds: input.subjectIds || [],
      sessionIds: input.sessionIds || [],
      eegFileIds: input.eegFileIds || [],
      taskIds: input.taskIds || [],
      artifactIds: input.artifactIds || [],
    };
  }

  function createEegFile(input = {}) {
    return {
      objectType: "EEGFile",
      id: input.id || makeId("eeg-file"),
      projectId: input.projectId || "",
      filename: input.filename || input.name || "",
      format: input.format || input.type || "EEG",
      sizeBytes: input.sizeBytes || 0,
      samplingRateHz: input.samplingRateHz || null,
      channelCount: input.channelCount || null,
      durationSec: input.durationSec || null,
      eventSummary: input.eventSummary || null,
      status: input.status || FILE_STATUS.uploaded,
      source: input.source || "customer_upload",
      storageKey: input.storageKey || input.filename || input.name || "",
      locked: Boolean(input.locked),
    };
  }

  function createAnalysisTask(input = {}) {
    return {
      objectType: "AnalysisTask",
      id: input.id || makeId("task"),
      projectId: input.projectId || "",
      workflowTemplate: input.workflowTemplate || "ERP",
      status: input.status || TASK_STATUS.queued,
      estimatedCost: Number(input.estimatedCost || 0),
      frozenAmount: Number(input.frozenAmount || 0),
      finalCost: Number(input.finalCost || 0),
      createdAt: input.createdAt || new Date().toLocaleString("zh-CN", { hour12: false }),
      inputFileIds: input.inputFileIds || [],
      artifactIds: input.artifactIds || [],
      manifestId: input.manifestId || "",
      trace: input.trace || {},
    };
  }

  function createLedgerEntry(input = {}) {
    return {
      objectType: "LedgerEntry",
      id: input.id || makeId("ledger"),
      customer: input.customer || "local customer",
      type: input.type || "analysis_charge",
      amount: Number(input.amount || 0),
      status: input.status || "pending",
      source: input.source || "",
      projectId: input.projectId || "",
      taskId: input.taskId || "",
      createdAt: input.createdAt || new Date().toLocaleString("zh-CN", { hour12: false }),
      handler: input.handler || "system",
    };
  }

  function createArtifact(input = {}) {
    return {
      objectType: "Artifact",
      id: input.id || makeId("artifact"),
      projectId: input.projectId || "",
      taskId: input.taskId || "",
      type: input.type || ARTIFACT_TYPES.figure,
      label: input.label || input.filename || "",
      href: input.href || "",
      format: input.format || "",
      previewRequired: input.previewRequired !== false,
      trace: input.trace || {},
    };
  }

  function architectureChecklist(state = {}) {
    const activeProject = Array.isArray(state.projects)
      ? state.projects.find((project) => project.id === state.activeProjectId)
      : null;
    const projectFiles = activeProject && Array.isArray(activeProject.files) ? activeProject.files : [];
    const result = activeProject?.result || {};
    return [
      { id: "project", label: "Project object exists", ok: Boolean(activeProject) },
      { id: "eeg-file", label: "EEG files attach to project", ok: projectFiles.some((file) => /EDF|BDF|SET|FIF/.test(file.type || file.format || "")) },
      { id: "events", label: "Events come from annotations/events", ok: Boolean(result.trace?.events || state?.localSample?.eventSummary) },
      { id: "billing", label: "Billing ledger records charge/recharge", ok: Array.isArray(state.orders) && state.orders.length > 0 },
      { id: "artifacts", label: "Artifacts require preview before download", ok: Boolean(result.downloads?.length || result.figures?.length) },
      { id: "manifest", label: "Result package has reproducibility manifest", ok: Boolean(result.trace?.archive || result.downloads?.some((item) => /manifest/i.test(item.href || item.label || ""))) },
    ];
  }

  window.QLANALYSER_ARCHITECTURE = {
    source: ARCHITECTURE_SOURCE,
    domainObjects: DOMAIN_OBJECTS,
    workflowSteps: WORKFLOW_STEPS,
    fileStatus: FILE_STATUS,
    taskStatus: TASK_STATUS,
    artifactTypes: ARTIFACT_TYPES,
    platformLayers: PLATFORM_LAYERS,
    createProject,
    createEegFile,
    createAnalysisTask,
    createLedgerEntry,
    createArtifact,
    architectureChecklist,
  };
  document.documentElement.dataset.architectureModel = ARCHITECTURE_SOURCE.version;
})();
