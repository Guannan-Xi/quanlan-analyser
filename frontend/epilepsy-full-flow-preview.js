(function () {
  "use strict";

  const FLOW_SCHEMA = "qlanalyser.epilepsy.full_flow_preview.v1";
  const REVIEW_SCHEMA = "qlanalyser.epilepsy.manual_correction_preview.v1";
  const REVIEW_SESSION_SCHEMA = "epilepsy_review_session.v1";
  const REPORT_SCHEMA = "qlanalyser.epilepsy.report_preview.v1";
  const REVIEW_STORAGE_KEY = "qlanalyser.epilepsy.review_preview.latest";
  const FLOW_STORAGE_KEY = "qlanalyser.epilepsy.full_flow.latest";
  const SAFE_SAMPLE_FOLDER = "work/sample_data/epilepsy/";
  const REQUEST_TIMEOUT_MS = 30_000;
  const LONG_REQUEST_TIMEOUT_MS = 75_000;
  const MAX_WAVEFORM_CACHE_ITEMS = 12;
  const API_BASE = resolveApiBase();
  const DEMO_PREVIEW_MODE = new URLSearchParams(window.location.search).get("demo") === "1";
  const STEPS = ["upload", "preflight", "candidates", "review", "adversarial", "report"];

  const STEP_LABEL = {
    upload: "上传样本",
    preflight: "数据预检",
    candidates: "筛出候选",
    review: "候选复核",
    adversarial: "边界检查",
    report: "草稿输出",
  };

  const TYPE_LABEL = {
    ied: "癫痫样放电候选",
    seizure_like: "节律性片段候选（待复核）",
    rhythmic: "节律性片段候选（待复核）",
    artifact_suspect: "伪迹候选",
    candidate_window: "候选窗口",
  };

  const STATUS_LABEL = {
    confirmed: "纳入草稿候选",
    rejected: "不纳入草稿",
    needs_review: "存疑/需二次复核",
    unreviewed: "未复核",
  };

  const EVENT_TYPE_EXPORT_LABEL = {
    ied: "棘波样候选",
    seizure_like: "节律性片段候选",
    rhythmic: "节律性候选",
    artifact_suspect: "伪迹候选",
    candidate_window: "候选窗口",
  };

  function eventTypeLabel(type) {
    return TYPE_LABEL[type] || type || "未标注候选类型";
  }

  const STATUS_COLOR = {
    confirmed: "#17803d",
    rejected: "#b42318",
    needs_review: "#b7791f",
    unreviewed: "#728294",
  };

  const SAMPLE_RECORDS = [
    {
      id: "he-105",
      file_id: "local_he_105_edf",
      filename: "HE-105.edf",
      size_bytes: 2009769280,
      duration_sec: 69.78 * 3600,
      sfreq: 1000,
      channels: ["EEG1", "EEG2", "EMG", "ACC"],
      safe_source_path: `${SAFE_SAMPLE_FOLDER}HE-105.edf`,
      candidates: [
        candidate("HE105-E001", 14 * 60 + 18.4, 1.7, "ied", "high", ["EEG1", "EEG2"], 0.86),
        candidate("HE105-E002", 4 * 3600 + 26 * 60 + 8.2, 12.6, "seizure_like", "high", ["EEG1", "EEG2"], 0.91),
        candidate("HE105-E003", 8 * 3600 + 6 * 60 + 12.0, 1.2, "ied", "medium", ["EEG1"], 0.7),
        candidate("HE105-E004", 17 * 3600 + 44 * 60 + 30.2, 7.8, "rhythmic", "medium", ["EEG2"], 0.72),
        candidate("HE105-E005", 28 * 3600 + 11 * 60 + 2.4, 0.9, "artifact_suspect", "low", ["EEG1", "EMG"], 0.55),
        candidate("HE105-E006", 41 * 3600 + 32 * 60 + 18.7, 2.1, "ied", "medium", ["EEG1", "EEG2"], 0.76),
        candidate("HE105-E007", 58 * 3600 + 5 * 60 + 44.0, 15.1, "seizure_like", "high", ["EEG2"], 0.88),
        candidate("HE105-E008", 67 * 3600 + 19 * 60 + 6.5, 1.5, "ied", "low", ["EEG1"], 0.62),
      ],
    },
    {
      id: "he-106",
      file_id: "local_he_106_edf",
      filename: "HE-106.edf",
      size_bytes: 2009961280,
      duration_sec: 69.8 * 3600,
      sfreq: 1000,
      channels: ["EEG1", "EEG2", "EMG", "ACC"],
      safe_source_path: `${SAFE_SAMPLE_FOLDER}HE-106.edf`,
      candidates: [
        candidate("HE106-E001", 1 * 3600 + 10 * 60 + 4.5, 6.9, "rhythmic", "high", ["EEG2"], 0.81),
        candidate("HE106-E002", 6 * 3600 + 49 * 60 + 2.0, 1.1, "ied", "medium", ["EEG1"], 0.69),
        candidate("HE106-E003", 13 * 3600 + 28 * 60 + 51.3, 2.4, "ied", "medium", ["EEG1", "EEG2"], 0.74),
        candidate("HE106-E004", 21 * 3600 + 9 * 60 + 13.1, 9.6, "seizure_like", "high", ["EEG1", "EEG2"], 0.9),
        candidate("HE106-E005", 35 * 3600 + 18 * 60 + 42.9, 1.0, "artifact_suspect", "low", ["EMG"], 0.51),
        candidate("HE106-E006", 49 * 3600 + 10 * 60 + 2.2, 2.2, "rhythmic", "low", ["EEG2"], 0.6),
        candidate("HE106-E007", 61 * 3600 + 52 * 60 + 24.4, 1.8, "ied", "medium", ["EEG1"], 0.71),
      ],
    },
    {
      id: "he-118",
      file_id: "local_he_118_edf",
      filename: "HE-118.edf",
      size_bytes: 2007833280,
      duration_sec: 69.72 * 3600,
      sfreq: 1000,
      channels: ["EEG1", "EEG2", "EMG", "ACC"],
      safe_source_path: `${SAFE_SAMPLE_FOLDER}HE-118.edf`,
      candidates: [
        candidate("HE118-E001", 38 * 60 + 14.1, 1.4, "ied", "medium", ["EEG1"], 0.66),
        candidate("HE118-E002", 3 * 3600 + 22 * 60 + 7.4, 11.4, "seizure_like", "high", ["EEG1", "EEG2"], 0.87),
        candidate("HE118-E003", 12 * 3600 + 8 * 60 + 37.5, 1.6, "ied", "high", ["EEG2"], 0.83),
        candidate("HE118-E004", 19 * 3600 + 47 * 60 + 54.0, 8.0, "rhythmic", "medium", ["EEG1", "EEG2"], 0.73),
        candidate("HE118-E005", 31 * 3600 + 40 * 60 + 9.6, 0.8, "artifact_suspect", "low", ["ACC"], 0.49),
        candidate("HE118-E006", 52 * 3600 + 2 * 60 + 30.2, 13.2, "seizure_like", "high", ["EEG2"], 0.85),
        candidate("HE118-E007", 64 * 3600 + 56 * 60 + 16.8, 1.3, "ied", "medium", ["EEG1"], 0.7),
      ],
    },
  ];

  const dom = {};
  const state = {
    currentStep: "upload",
    selectedRecordId: null,
    uploadedRecord: null,
    backendAvailable: false,
    backendError: "",
    backendRecords: [],
    backendRoot: "",
    preflightDone: false,
    preflightLimitedUpload: false,
    candidatesGenerated: false,
    candidateProgress: 0,
    activeEventIndex: 0,
    reviews: {},
    gates: [],
    audit: [],
    reviewSaved: false,
    waveformCache: {},
    candidateCache: {},
    candidateTimers: [],
    operationSeq: 0,
    candidateOperationId: null,
    reviewVersion: 0,
    backendReviewSession: null,
    busy: {
      preflight: false,
      candidates: false,
      saveReview: false,
    },
    lastError: "",
  };

  function candidate(event_id, start_sec, duration_sec, event_type, priority, channels, score) {
    const previewScore = Number.isFinite(Number(score)) ? Number(score) : 0.5;
    return {
      event_id,
      start_sec,
      duration_sec,
      end_sec: start_sec + duration_sec,
      event_type,
      priority,
      channels,
      score: previewScore,
      preview_rms_ptp_rank_score: previewScore,
      score_kind: "preview_seeded_rank_not_probability",
      source: "frontend_seeded_time_synthetic_preview",
      event_type_scope: "candidate_label_only",
    };
  }

  function normalizeCandidateEvent(event) {
    const sourceEvent = event || {};
    const score = Number(sourceEvent.preview_rms_ptp_rank_score ?? sourceEvent.score ?? 0.5);
    const start = Number(sourceEvent.start_sec ?? 0);
    const duration = Number(sourceEvent.duration_sec ?? Math.max(0.1, Number(sourceEvent.end_sec ?? start + 1) - start));
    return {
      ...sourceEvent,
      event_id: sourceEvent.event_id || sourceEvent.id || "candidate",
      start_sec: start,
      duration_sec: duration,
      end_sec: Number(sourceEvent.end_sec ?? start + duration),
      channels: Array.isArray(sourceEvent.channels) ? sourceEvent.channels : [],
      score: Number.isFinite(score) ? score : 0.5,
      preview_rms_ptp_rank_score: Number.isFinite(score) ? score : 0.5,
      score_kind: sourceEvent.score_kind || "preview_rank_not_probability",
      score_note: sourceEvent.score_note || "复核优先级排序值不是临床概率、检测置信度或诊断结论。",
      source: sourceEvent.source || "preview_candidate_package",
      event_type_scope: sourceEvent.event_type_scope || "candidate_label_only",
    };
  }

  function resolveApiBase() {
    const params = new URLSearchParams(window.location.search);
    const explicit = params.get("api");
    if (explicit && isLocalPage() && isLocalApiBase(explicit)) return explicit.replace(/\/$/, "");
    if (window.location.port === "8001") return `${window.location.origin}/api`;
    if (!isLocalPage()) return `${window.location.origin}/api`;
    return "http://127.0.0.1:8001/api";
  }

  function isLocalPage() {
    const host = window.location.hostname;
    return !host || host === "localhost" || host === "127.0.0.1" || host === "::1" || host === "[::1]";
  }

  function isLocalApiBase(value) {
    try {
      const url = new URL(value, window.location.origin);
      return ["localhost", "127.0.0.1", "::1", "[::1]"].includes(url.hostname);
    } catch {
      return false;
    }
  }

  async function apiFetch(path, options = {}) {
    const { timeoutMs = REQUEST_TIMEOUT_MS, ...fetchOptions } = options;
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${API_BASE}${path}`, {
        ...fetchOptions,
        signal: controller.signal,
        headers: {
          Accept: "application/json",
          ...(fetchOptions.headers || {}),
        },
      });
      if (!response.ok) {
        const detail = await response.text().catch(() => "");
        throw new Error(`${response.status} ${response.statusText} ${detail}`.trim());
      }
      if (response.status === 204) return null;
      const text = await response.text();
      return text ? JSON.parse(text) : null;
    } catch (error) {
      if (error?.name === "AbortError") {
        throw new Error(`请求超过 ${Math.round(timeoutMs / 1000)} 秒未返回，请稍后重试或检查本地处理任务。`);
      }
      throw error;
    } finally {
      window.clearTimeout(timer);
    }
  }

  async function loadBackendRecords() {
    try {
      const data = await apiFetch("/lab/epilepsy-full-flow/records");
      state.backendRecords = Array.isArray(data.records) ? data.records.map(normalizeBackendRecord) : [];
      state.backendRoot = data.root || data.safe_root || SAFE_SAMPLE_FOLDER;
      state.backendAvailable = state.backendRecords.length > 0;
      state.backendError = "";
      if (state.backendAvailable) {
        addAudit("backend_records_loaded", `已发现 ${state.backendRecords.length} 个 HE 示例 EDF。`);
      }
    } catch (error) {
      state.backendRecords = [];
      state.backendRoot = "";
      state.backendAvailable = false;
      state.backendError = "示例数据未就绪。请联系部署人员或重新连接示例数据。";
      addAudit(
        "backend_records_unavailable",
        DEMO_PREVIEW_MODE
          ? "示例数据未就绪；当前仅显示界面预览样本。"
          : "示例数据未就绪；已阻止预览样本自动冒充真实分析。"
      );
    }
    setSampleFolder();
  }

  function normalizeBackendRecord(record) {
    const fallback = SAMPLE_RECORDS.find((item) => item.id === record.id);
    return {
      ...(fallback || {}),
      ...record,
      backend_record: true,
      source_path_display: record.source_path_display || record.safe_source_path || `${SAFE_SAMPLE_FOLDER}${record.filename}`,
      safe_source_path: record.safe_source_path || `${SAFE_SAMPLE_FOLDER}${record.filename}`,
      candidates: Array.isArray(record.candidates)
        ? record.candidates.map(normalizeCandidateEvent)
        : (fallback?.candidates || []).map(normalizeCandidateEvent),
    };
  }

  function availableRecords() {
    if (state.backendAvailable) return state.backendRecords;
    return DEMO_PREVIEW_MODE ? SAMPLE_RECORDS : [];
  }

  function replaceAvailableRecord(record) {
    if (record?.backend_record) {
      state.backendRecords = state.backendRecords.map((item) => (item.id === record.id ? { ...item, ...record } : item));
    } else if (state.uploadedRecord && record?.id === state.uploadedRecord.id) {
      state.uploadedRecord = { ...state.uploadedRecord, ...record };
    }
  }

  function restoreFlowState() {
    let raw = "";
    try {
      raw = window.localStorage.getItem(FLOW_STORAGE_KEY) || window.sessionStorage.getItem(FLOW_STORAGE_KEY) || "";
    } catch {
      raw = "";
    }
    if (!raw) return false;
    let snapshot = null;
    try {
      snapshot = JSON.parse(raw);
    } catch {
      return false;
    }
    if (!snapshot || snapshot.schema_version !== FLOW_SCHEMA || !snapshot.selected_record_id) return false;
    const snapshotRecord = snapshot.current_record && typeof snapshot.current_record === "object" ? snapshot.current_record : null;
    const selected = availableRecords().find((record) => record.id === snapshot.selected_record_id)
      || (snapshotRecord?.id === snapshot.selected_record_id ? snapshotRecord : null);
    if (!selected) return false;
    if (Array.isArray(snapshot.backend_records) && state.backendAvailable) {
      state.backendRecords = snapshot.backend_records.map(normalizeBackendRecord);
    }
    const restoredRecord = {
      ...selected,
      ...(snapshot.current_record || {}),
      candidates: Array.isArray(snapshot.candidates)
        ? snapshot.candidates.map(normalizeCandidateEvent)
        : selected.candidates,
    };
    if (restoredRecord.backend_record && state.backendAvailable) {
      replaceAvailableRecord(normalizeBackendRecord(restoredRecord));
    } else if (!state.backendAvailable) {
      state.uploadedRecord = {
        ...restoredRecord,
        backend_record: false,
        restored_from_snapshot: true,
      };
    }
    state.selectedRecordId = snapshot.selected_record_id;
    state.preflightDone = Boolean(snapshot.preflight_done);
    state.preflightLimitedUpload = Boolean(snapshot.preflight_limited_upload);
    state.candidatesGenerated = Boolean(snapshot.candidates_generated);
    state.currentStep = STEPS.includes(snapshot.current_step) ? snapshot.current_step : "upload";
    state.reviews = snapshot.reviews && typeof snapshot.reviews === "object" ? snapshot.reviews : {};
    state.reviewSaved = Boolean(snapshot.review_saved);
    state.backendReviewSession = snapshot.backend_review_session || null;
    state.gates = Array.isArray(snapshot.gates) ? snapshot.gates : [];
    state.audit = Array.isArray(snapshot.audit) ? snapshot.audit.slice(-80) : state.audit;
    state.activeEventIndex = 0;
    state.reviewVersion += 1;
    const reviewMerged = mergeLatestReviewPayloadIntoFlow();
    addAudit("flow_state_restored", reviewMerged ? "已恢复候选复核流程进度，并同步最新人工状态。" : "已恢复上次候选复核流程进度。");
    return true;
  }

  function mergeLatestReviewPayloadIntoFlow() {
    const payload = latestStoredReviewPayload();
    if (!payload || !Array.isArray(payload.reviewed_events) || !payload.reviewed_events.length) return false;
    const record = currentRecord();
    if (!record || !sameReviewRecord(record, payload.record || {})) return false;
    const incoming = payload.reviewed_events.map(candidateFromReviewPayloadEvent).filter(Boolean);
    if (!incoming.length) return false;
    const currentIds = new Set((record.candidates || []).map((event) => event.event_id || event.id));
    if (!record.candidates?.length || incoming.some((event) => !currentIds.has(event.event_id))) {
      record.candidates = incoming.map(normalizeCandidateEvent);
      replaceAvailableRecord(record.backend_record ? normalizeBackendRecord(record) : record);
    }
    state.selectedRecordId = record.id;
    state.preflightDone = true;
    state.candidatesGenerated = true;
    state.reviews = { ...state.reviews };
    payload.reviewed_events.forEach((event) => {
      if (!event?.event_id) return;
      state.reviews[event.event_id] = reviewFromPayloadEvent(event);
    });
    state.reviewSaved = true;
    state.backendReviewSession = payload.backend_review_session || state.backendReviewSession;
    state.reviewVersion += 1;
    return true;
  }

  function latestStoredReviewPayload() {
    try {
      const raw = window.sessionStorage.getItem(REVIEW_STORAGE_KEY) || window.localStorage.getItem(REVIEW_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || parsed.schema_version !== REVIEW_SCHEMA) return null;
      return parsed;
    } catch {
      return null;
    }
  }

  function sameReviewRecord(record, reviewRecord) {
    const keys = ["id", "file_id", "filename"];
    return keys.some((key) => record?.[key] && reviewRecord?.[key] && String(record[key]) === String(reviewRecord[key]));
  }

  function candidateFromReviewPayloadEvent(event) {
    const start = numberOr(event.original_start_sec, numberOr(event.candidate_start_sec, event.start_sec));
    const end = Math.max(start + 0.1, numberOr(event.original_end_sec, numberOr(event.candidate_end_sec, event.end_sec)));
    const score = Number(event.preview_rms_ptp_rank_score ?? event.score ?? 0.5);
    return normalizeCandidateEvent({
      event_id: event.event_id,
      id: event.event_id,
      start_sec: start,
      end_sec: end,
      duration_sec: round1(end - start),
      event_type: event.ai_type || event.event_type || event.reviewed_type || "candidate_window",
      priority: event.priority || "medium",
      channels: Array.isArray(event.channels) ? event.channels : [],
      score: Number.isFinite(score) ? score : 0.5,
      preview_rms_ptp_rank_score: Number.isFinite(score) ? score : 0.5,
      score_kind: event.score_kind || "preview_rank_not_probability",
      score_note: event.score_note || "复核优先级排序值不是临床概率、检测置信度或诊断结论。",
      source: event.event_source || event.source || "review_payload",
      event_type_scope: event.event_type_scope || "candidate_label_only",
    });
  }

  function reviewFromPayloadEvent(event) {
    const start = numberOr(event.reviewed_start_sec, event.start_sec);
    const end = Math.max(start + 0.1, numberOr(event.reviewed_end_sec, event.end_sec));
    return {
      status: normalizeFlowReviewStatus(event.status || event.backend_status || event.review_status),
      event_type: event.event_type || event.reviewed_type || event.ai_type || "candidate_window",
      evidence_grade: event.evidence_grade || event.grade || "",
      adjusted_start_sec: round1(start),
      adjusted_end_sec: round1(end),
      note: event.review_note || event.note || "",
      reviewer: event.reviewer || "",
      reviewed_at: event.reviewed_at || "",
    };
  }

  function normalizeFlowReviewStatus(status) {
    const value = String(status || "unreviewed");
    if (value === "kept") return "confirmed";
    if (value === "excluded") return "rejected";
    if (value === "uncertain") return "needs_review";
    if (["confirmed", "rejected", "needs_review", "unreviewed"].includes(value)) return value;
    return "unreviewed";
  }

  async function init() {
    cacheDom();
    bindEvents();
    setSampleFolder();
    addAudit("flow_opened", "打开癫痫样候选事件全流程预览。");
    runAdversarialReview({ silent: true });
    render();
    await loadBackendRecords();
    if (!restoreFlowState()) {
      const first = availableRecords()[0];
      if (first) selectRecord(first.id, { silent: true });
    }
    runAdversarialReview({ silent: true });
    render();
    syncIcons();
    window.addEventListener("resize", debounce(redrawVisibleFigures, 120));
  }

  function cacheDom() {
    [
      "copyFlowBtn",
      "openReviewBtn",
      "openReportBtn",
      "chooseEdfBtn",
      "edfInput",
      "sampleSourceText",
      "sampleFolderText",
      "copyFolderBtn",
      "sampleGrid",
      "contextRecord",
      "contextQc",
      "contextCandidates",
      "contextReview",
      "contextReport",
      "runPreflightBtn",
      "qcGrid",
      "generateCandidatesBtn",
      "candidateRunner",
      "candidateStrip",
      "autoReviewBtn",
      "saveReviewBtn",
      "eventList",
      "activeEventTitle",
      "reviewWaveform",
      "reviewHandoffFacts",
      "reviewNoteInput",
      "runAdversarialBtn",
      "gateGrid",
      "issueLedger",
      "exportCsvBtn",
      "exportReportJsonBtn",
      "reportPreview",
      "reportStatusBadge",
      "reportSummary",
      "timelineFigure",
      "funnelFigure",
      "densityFigure",
      "qcFigure",
      "reportInterpretation",
      "reportMethods",
      "reportEventRows",
      "nextActionTitle",
      "nextActionText",
      "nextActionBtn",
      "gateSummary",
      "auditList",
      "toast",
    ].forEach((id) => {
      dom[id] = document.getElementById(id);
    });
    dom.steps = Array.from(document.querySelectorAll("[data-step]"));
    dom.stages = Array.from(document.querySelectorAll("[data-stage]"));
  }

  function bindEvents() {
    dom.steps.forEach((button) => {
      button.addEventListener("click", () => setStep(button.dataset.step));
    });
    dom.copyFolderBtn.addEventListener("click", () => copyText(sampleSourceTraceForCopy(), "已复制示例数据来源说明。"));
    dom.copyFlowBtn.addEventListener("click", copyFlowJson);
    dom.openReviewBtn?.addEventListener("click", openDetailedReview);
    dom.openReportBtn.addEventListener("click", openStandaloneReport);
    dom.chooseEdfBtn.addEventListener("click", () => {
      if (isFlowBusy()) {
        toast("当前流程正在运行，请等待本步完成后再选择文件。");
        return;
      }
      dom.edfInput.click();
    });
    dom.edfInput.addEventListener("change", handleFileSelect);
    dom.runPreflightBtn.addEventListener("click", runPreflight);
    dom.generateCandidatesBtn.addEventListener("click", generateCandidates);
    dom.autoReviewBtn.addEventListener("click", fillExampleReview);
    dom.saveReviewBtn.addEventListener("click", saveReviewLayer);
    document.querySelectorAll("[data-flow-status]").forEach((button) => {
      button.addEventListener("click", () => markInlineReviewStatus(button.dataset.flowStatus));
    });
    document.querySelectorAll("[data-flow-note]").forEach((button) => {
      button.addEventListener("click", () => appendInlineReviewNote(button.dataset.flowNote || ""));
    });
    dom.reviewNoteInput.addEventListener("change", syncInlineReviewNote);
    dom.runAdversarialBtn.addEventListener("click", () => runAdversarialReview());
    dom.exportCsvBtn.addEventListener("click", exportEventsCsv);
    dom.exportReportJsonBtn.addEventListener("click", exportReportJson);
    dom.nextActionBtn.addEventListener("click", runNextAction);
  }

  function setSampleFolder() {
    const sourceStatus = sampleSourceStatus();
    if (dom.sampleSourceText) dom.sampleSourceText.textContent = sourceStatus.title;
    dom.sampleFolderText.textContent = sourceStatus.detail;
  }

  function isLocalHost() {
    return isLocalPage();
  }

  function sampleFolderForDisplay() {
    if (state.backendRoot) return state.backendRoot;
    return SAFE_SAMPLE_FOLDER;
  }

  function sampleSourceStatus() {
    if (state.backendAvailable) {
      return {
        title: "示例数据已由试用环境提供",
        detail: "数据来源说明：真实 EDF 元数据和波形窗口已连接",
      };
    }
    if (DEMO_PREVIEW_MODE) {
      return {
        title: "当前为界面预览模式",
        detail: "数据来源说明：仅展示界面样式，不能作为真实分析证据",
      };
    }
    if (state.backendError) {
      return {
        title: "示例数据未就绪",
        detail: "请联系部署人员或重新连接示例数据",
      };
    }
    return {
      title: "正在连接示例数据",
      detail: "数据来源说明：等待试用环境返回数据状态",
    };
  }

  function sampleSourceTraceForCopy() {
    const sourceStatus = sampleSourceStatus();
    return [
      "QLanalyser 示例数据来源说明",
      `状态：${sourceStatus.title}`,
      `说明：${sourceStatus.detail}`,
      `数据标识：${sampleFolderForDisplay()}`,
      `API：${API_BASE}`,
    ].join("\n");
  }

  function currentRecord() {
    if (state.uploadedRecord && state.selectedRecordId === state.uploadedRecord.id) return state.uploadedRecord;
    return availableRecords().find((record) => record.id === state.selectedRecordId) || null;
  }

  function effectiveDurationSec(record) {
    return Number.isFinite(record?.duration_sec) && record.duration_sec > 0 ? record.duration_sec : 70 * 3600;
  }

  function isFlowBusy() {
    return state.busy.preflight || state.busy.candidates || state.busy.saveReview;
  }

  function isCurrentOperation(opId, recordId) {
    return opId === state.operationSeq && recordId === state.selectedRecordId;
  }

  function selectRecord(recordId, options = {}) {
    if (isFlowBusy() && !options.force) {
      toast("当前步骤正在运行，请等待完成后再切换记录。");
      return;
    }
    clearCandidateTimers();
    state.operationSeq += 1;
    state.busy.preflight = false;
    state.busy.candidates = false;
    state.busy.saveReview = false;
    state.candidateOperationId = null;
    state.selectedRecordId = recordId;
    state.preflightDone = false;
    state.preflightLimitedUpload = false;
    state.candidatesGenerated = false;
    state.candidateProgress = 0;
    state.activeEventIndex = 0;
    state.reviews = {};
    state.waveformCache = {};
    state.reviewSaved = false;
    state.reviewVersion += 1;
    if (!options.silent) {
      addAudit("record_selected", `选择记录 ${currentRecord()?.filename || recordId}。`);
      setStep("preflight");
      runAdversarialReview({ silent: true });
      toast("已选择记录，请运行数据预检。");
    }
    render();
  }

  function clearCandidateTimers() {
    state.candidateTimers.forEach((timer) => window.clearTimeout(timer));
    state.candidateTimers = [];
  }

  function finishCandidateRun(opId) {
    if (state.candidateOperationId !== opId) return;
    state.busy.candidates = false;
    state.candidateOperationId = null;
    renderActions();
  }

  function handleFileSelect(event) {
    if (isFlowBusy()) {
      event.target.value = "";
      toast("当前流程正在运行，请等待完成后再选择文件。");
      return;
    }
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    state.uploadedRecord = {
      id: `uploaded_${Date.now()}`,
      file_id: "browser_uploaded_edf_preview",
      filename: file.name,
      size_bytes: file.size,
      duration_sec: null,
      sfreq: null,
      channels: [],
      source_path_display: file.name,
      safe_source_path: file.name,
      upload_only: true,
      candidates: [],
    };
    selectRecord(state.uploadedRecord.id);
    state.preflightDone = false;
    state.preflightLimitedUpload = false;
    state.candidatesGenerated = false;
    addAudit("browser_file_selected", `浏览器选择文件 ${file.name}，大小 ${formatBytes(file.size)}；尚未读取 EDF 记录信息，不能套用 HE 示例候选。`);
    toast("已选择本地 EDF，但需要先读取记录信息，才能生成候选片段包。");
  }

  async function runPreflight() {
    if (state.busy.preflight) return;
    if (!currentRecord()) {
      toast("请先选择 HE 示例或导入 EDF。");
      setStep("upload");
      return;
    }
    const record = currentRecord();
    const opId = ++state.operationSeq;
    const recordId = record.id;
    state.busy.preflight = true;
    renderActions();
    try {
      if (record.upload_only) {
        if (!isCurrentOperation(opId, recordId)) return;
        state.preflightDone = true;
        state.preflightLimitedUpload = true;
        state.reviewSaved = false;
        addAudit("upload_preflight_limited", "导入文件只完成文件名和大小登记；尚未读取 EDF 元数据。");
        runAdversarialReview({ silent: true });
        state.currentStep = "preflight";
        render();
        toast("导入文件尚未完成 EDF 读取，已停留在预检页等待正式分析任务。");
        return;
      }
      if (record.backend_record) {
        try {
          const data = await apiFetch(`/lab/epilepsy-full-flow/records/${encodeURIComponent(record.id)}/preflight`);
          if (!isCurrentOperation(opId, recordId)) return;
          replaceAvailableRecord(normalizeBackendRecord({ ...record, ...data }));
          addAudit("backend_preflight_loaded", `已读取 ${record.filename} 元数据。`);
        } catch (error) {
          if (!isCurrentOperation(opId, recordId)) return;
          addAudit("backend_preflight_failed", "数据预检失败，当前记录未取得新的元数据。");
          toast("数据预检失败，已降级使用预览元数据。");
        }
      }
      if (!isCurrentOperation(opId, recordId)) return;
      state.preflightDone = true;
      state.preflightLimitedUpload = false;
      state.reviewSaved = false;
      addAudit("preflight_complete", "完成格式、规模、通道和窗口读取策略预检。");
      runAdversarialReview({ silent: true });
      setStep("candidates");
      render();
      toast("预检完成，可以生成待人工查看的候选片段包。");
    } finally {
      if (isCurrentOperation(opId, recordId)) {
        state.busy.preflight = false;
        renderActions();
      }
    }
  }

  async function generateCandidates() {
    if (state.busy.candidates) return;
    if (!state.preflightDone) {
      toast("请先运行数据预检。");
      setStep("preflight");
      return;
    }
    const record = currentRecord();
    if (record?.upload_only) {
      state.candidatesGenerated = false;
      addAudit("uploaded_candidates_blocked", "导入文件尚未完成 EDF 读取，已阻断示例候选套用。");
      runAdversarialReview({ silent: true });
      render();
      toast("导入文件不能套用 HE 示例候选，请接入正式分析任务或选择 HE 示例。");
      return;
    }
    clearCandidateTimers();
    const opId = ++state.operationSeq;
    const recordId = record?.id;
    state.busy.candidates = true;
    state.candidateOperationId = opId;
    state.candidateProgress = 12;
    state.candidatesGenerated = false;
    renderCandidateRunner("读取预检结果，准备生成候选片段包", 12);
    renderActions();
    if (record?.backend_record) {
      try {
        renderCandidateRunner("正在分段查看长时程记录，并按波形变化筛出需要人工查看的片段，首次可能需要 20-60 秒", 38);
        const data = state.candidateCache[record.id] || await apiFetch(
          `/lab/epilepsy-full-flow/records/${encodeURIComponent(record.id)}/candidates`,
          { method: "POST", timeoutMs: LONG_REQUEST_TIMEOUT_MS }
        );
        if (!isCurrentOperation(opId, recordId)) {
          finishCandidateRun(opId);
          return;
        }
        state.candidateCache[record.id] = data;
        const nextRecord = normalizeBackendRecord({
          ...record,
          ...(data.record || {}),
          candidates: Array.isArray(data.candidates) ? data.candidates : record.candidates,
          backend_candidate_source: data.candidate_source,
          backend_algorithm_status: data.algorithm_status,
          backend_limitations: data.candidate_boundary_notes || data.limitations || [],
        });
        replaceAvailableRecord(nextRecord);
        state.candidateProgress = 100;
        state.candidatesGenerated = true;
        state.activeEventIndex = 0;
        state.reviews = {};
        state.waveformCache = {};
        state.reviewSaved = false;
        addAudit("backend_candidates_generated", `已标出 ${candidates().length} 个待人工查看的候选片段，并计算每段的波形变化指标。`);
        runAdversarialReview({ silent: true });
        setStep("review");
        render();
        toast("候选片段包已生成，可在当前页复核。");
        finishCandidateRun(opId);
        return;
      } catch (error) {
        if (!isCurrentOperation(opId, recordId)) {
          finishCandidateRun(opId);
          return;
        }
        addAudit("backend_candidates_failed", "候选片段包生成失败，未生成新的候选列表。");
        toast("候选片段包生成失败，未自动降级为示例候选。");
        finishCandidateRun(opId);
        return;
      }
    }
    state.candidateTimers.push(window.setTimeout(() => {
      if (opId === state.operationSeq && recordId === state.selectedRecordId) renderCandidateRunner("构建 70 小时记录的候选时间轴", 48);
    }, 160));
    state.candidateTimers.push(window.setTimeout(() => {
      if (opId === state.operationSeq && recordId === state.selectedRecordId) renderCandidateRunner("生成事件队列和证据占位", 78);
    }, 320));
    state.candidateTimers.push(window.setTimeout(() => {
      if (!isCurrentOperation(opId, recordId)) {
        finishCandidateRun(opId);
        return;
      }
      state.candidateProgress = 100;
      state.candidatesGenerated = true;
      state.activeEventIndex = 0;
      state.reviews = {};
      state.reviewSaved = false;
      state.reviewVersion += 1;
      addAudit("candidate_package_generated", `生成 ${candidates().length} 个候选片段；排序值不是概率，不能用于正式结论。`);
      runAdversarialReview({ silent: true });
      setStep("review");
      render();
      toast("候选片段包已生成，可在当前页复核。");
      finishCandidateRun(opId);
    }, 520));
  }

  function renderCandidateRunner(label, progress) {
    state.candidateProgress = progress;
    const bar = dom.candidateRunner.querySelector("b");
    const progressEl = dom.candidateRunner.querySelector(".ep-flow-progress");
    dom.candidateRunner.querySelector("span").textContent = label;
    bar.style.width = `${progress}%`;
    progressEl.setAttribute("aria-valuenow", String(Math.round(progress)));
    progressEl.setAttribute("aria-valuetext", `${label}，${Math.round(progress)}%`);
  }

  function candidates() {
    return state.candidatesGenerated && currentRecord() ? currentRecord().candidates : [];
  }

  function candidateSourceLabel(event) {
    if (event?.source === "seeded_time_real_edf_window_metrics") {
      return "示例时间点 + 原始波形片段；用于复核优先级";
    }
    if (event?.source === "bounded_full_record_window_scan_metrics" || event?.source === "bounded_full_record_window_scan_rms_ptp_v1") {
      return "有限 EDF 窗口抽样后按波形幅度变化排序，供人工复核优先级使用";
    }
    if (event?.score_kind?.includes("not_probability")) {
      return "预览候选；用于复核优先级";
    }
    return "预览候选；正式交付需接入真实波形追溯";
  }

  function priorityLabel(priority) {
    return {
      high: "高",
      medium: "中",
      low: "低",
    }[String(priority || "").toLowerCase()] || priority || "未记录";
  }

  function activeCandidate() {
    const list = candidates();
    return list[Math.max(0, Math.min(state.activeEventIndex, list.length - 1))] || null;
  }

  function reviewFor(event) {
    if (!event) return null;
    return state.reviews[event.event_id] || null;
  }

  function statusFor(event) {
    return reviewFor(event)?.status || "unreviewed";
  }

  function fillExampleReview() {
    if (isFlowBusy()) {
      toast("当前流程正在运行，请等待完成后再复核候选。");
      return;
    }
    if (!candidates().length) {
      toast("请先生成候选片段包。");
      setStep("candidates");
      return;
    }
    const statuses = ["confirmed", "confirmed", "rejected", "needs_review", "rejected", "confirmed", "needs_review", "confirmed"];
    candidates().forEach((event, index) => {
      const status = statuses[index % statuses.length];
      state.reviews[event.event_id] = {
        status,
        event_type: status === "rejected" ? "artifact_suspect" : event.event_type,
        evidence_grade: status === "confirmed" ? "B" : status === "needs_review" ? "C" : "X",
        adjusted_start_sec: round1(event.start_sec + (status === "confirmed" ? -0.2 : 0)),
        adjusted_end_sec: round1(event.end_sec + (status === "confirmed" ? 0.3 : 0)),
        note: exampleNote(status, event),
        reviewer: "preview_reviewer",
        reviewed_at: new Date().toISOString(),
      };
    });
    state.reviewSaved = false;
    state.reviewVersion += 1;
    addAudit("demo_review_filled", "填充预览复核结果，仅用于端到端流程试跑，不能用于正式报告。");
    runAdversarialReview({ silent: true });
    render();
    toast("示例复核已填充，可同步记录并检查边界。");
  }

  function exampleNote(status, event) {
    if (status === "confirmed") return `${eventTypeLabel(event.event_type)}，EEG 双通道证据较一致；需正式报告替换真实波形证据。`;
    if (status === "needs_review") return "形态边界或伪迹解释仍需专家复核，暂不进入最终结论。";
    return "EMG/ACC 或信号质量提示伪迹风险，本预览中排除出统计。";
  }

  function defaultInlineReview(event) {
    return {
      status: "unreviewed",
      event_type: event.event_type,
      evidence_grade: "",
      adjusted_start_sec: round1(event.start_sec),
      adjusted_end_sec: round1(event.end_sec),
      note: "",
      reviewer: "preview_reviewer",
      reviewed_at: "",
    };
  }

  function ensureInlineReview(event) {
    if (!event) return null;
    if (!state.reviews[event.event_id]) {
      state.reviews[event.event_id] = defaultInlineReview(event);
    }
    return state.reviews[event.event_id];
  }

  function markInlineReviewStatus(status) {
    if (!["confirmed", "rejected", "needs_review"].includes(status)) return;
    if (isFlowBusy()) {
      toast("当前流程正在运行，请等待完成后再标注候选。");
      return;
    }
    const event = activeCandidate();
    if (!event) {
      toast("请先生成候选片段包。");
      setStep("candidates");
      return;
    }
    const review = ensureInlineReview(event);
    const noteText = dom.reviewNoteInput.value.trim();
    review.status = status;
    review.event_type = status === "rejected" ? "artifact_suspect" : (review.event_type || event.event_type);
    review.evidence_grade = review.evidence_grade || (status === "confirmed" ? "B" : status === "needs_review" ? "C" : "X");
    review.note = noteText || review.note || exampleNote(status, event);
    review.reviewer = review.reviewer || "preview_reviewer";
    review.reviewed_at = new Date().toISOString();
    state.reviewSaved = false;
    state.reviewVersion += 1;
    addAudit("inline_review_status", `${event.event_id} 标注为 ${STATUS_LABEL[status]}。`);
    runAdversarialReview({ silent: true });
    render();
    toast(`${event.event_id} 已标注为${STATUS_LABEL[status]}。`);
  }

  function syncInlineReviewNote(options = {}) {
    const event = activeCandidate();
    if (!event) return;
    const review = ensureInlineReview(event);
    const nextNote = dom.reviewNoteInput.value.trim();
    if ((review.note || "") === nextNote) return;
    review.note = nextNote;
    review.reviewer = review.reviewer || "preview_reviewer";
    if (review.status !== "unreviewed") review.reviewed_at = new Date().toISOString();
    state.reviewSaved = false;
    state.reviewVersion += 1;
    addAudit("inline_review_note", `${event.event_id} 更新复核备注。`);
    runAdversarialReview({ silent: true });
    if (options.renderAfter !== false) render();
  }

  function appendInlineReviewNote(text) {
    if (!text) return;
    const event = activeCandidate();
    if (!event) {
      toast("请先选择候选事件。");
      return;
    }
    const existing = dom.reviewNoteInput.value.trim();
    dom.reviewNoteInput.value = existing ? `${existing}\n${text}` : text;
    syncInlineReviewNote();
  }

  async function saveReviewLayer() {
    if (state.busy.saveReview) return false;
    if (!candidates().length) {
      toast("请先生成候选片段包。");
      setStep("candidates");
      return false;
    }
    syncInlineReviewNote({ renderAfter: false });
    state.busy.saveReview = true;
    const saveVersion = state.reviewVersion;
    const saveRecordId = state.selectedRecordId;
    renderActions();
    const payload = buildReviewPayload();
    try {
      window.sessionStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(payload));
      window.localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(payload));
      if (currentRecord()?.backend_record) {
        try {
          const saved = await apiFetch("/lab/epilepsy-full-flow/review-sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          state.backendReviewSession = saved;
          payload.backend_review_session = saved;
          payload.context = { ...(payload.context || {}), review_session_id: saved.session_id };
          window.sessionStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(payload));
          window.localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(payload));
          addAudit("backend_review_session_saved", `复核记录已保存：${saved.session_id}。`);
        } catch (error) {
          state.backendReviewSession = null;
          addAudit("backend_review_session_failed", "复核结果保存失败，已保留浏览器本地记录。");
        }
      }
      if (saveVersion !== state.reviewVersion || saveRecordId !== state.selectedRecordId) {
        addAudit("review_layer_stale_save_ignored", "保存期间复核结果或记录已改变，已忽略旧保存结果。");
        return false;
      }
      state.reviewSaved = true;
      addAudit("review_layer_saved", "候选与复核上下文已保存，可供草稿预览页读取。");
      runAdversarialReview({ silent: true });
      window.sessionStorage.setItem(FLOW_STORAGE_KEY, JSON.stringify(buildFlowState()));
      window.localStorage.setItem(FLOW_STORAGE_KEY, JSON.stringify(buildFlowState()));
      render();
      toast("候选与复核上下文已保存。");
      return true;
    } catch {
      toast("浏览器阻止 sessionStorage，请先修复会话存储权限再导出草稿包。");
      return false;
    } finally {
      state.busy.saveReview = false;
      renderActions();
    }
  }

  function runAdversarialReview(options = {}) {
    const stats = reviewStats();
    const record = currentRecord();
    const gates = [];

    gates.push(makeGate("input", "输入与隐私", record && !record.upload_only ? "pass" : record ? "warn" : "fail", [
      record ? `已选择 ${record.filename}。` : "未选择 EDF 数据。",
      "前端默认只显示安全相对路径；导出包会移除 source_path/local_source_path/root 等绝对路径字段。",
      record?.upload_only ? "导入文件仅登记文件名和大小，尚未完成 EDF 读取。" : "HE 示例由试用环境中的真实 EDF 或界面预览样本提供。",
    ], record ? (record.upload_only ? ["P1：导入文件尚未读取记录信息，不能生成候选片段包或报告。"] : []) : ["阻断：必须先选择 HE 示例或导入 EDF。"]));

    gates.push(makeGate("preflight", "数据预检", state.preflightDone ? (record?.upload_only ? "warn" : "pass") : "fail", [
      state.preflightDone
        ? record?.upload_only
          ? "仅完成导入文件名和大小登记，尚未读取 EDF 元数据。"
          : "已确认文件规模、通道策略和长记录处理边界。"
        : "尚未运行预检。",
      "70 小时 EDF 不在浏览器全量读取，正式态需使用窗口化数据读取。",
      record?.upload_only ? "导入 EDF 的采样率、通道和时长当前为未知，不能写入正式交付材料。" : "HE 样本元数据由预检或界面预览给出。",
    ], state.preflightDone
      ? record?.upload_only ? ["P1：导入文件还未读取 EDF 元数据，不能生成候选片段包或报告。"] : []
      : ["阻断：生成候选片段包前必须完成预检。"]));

    gates.push(makeGate("candidate", "候选片段包", state.candidatesGenerated ? "warn" : "fail", [
      state.candidatesGenerated ? `已标出 ${candidates().length} 个待人工查看的候选片段。` : "尚未生成候选片段包。",
      record?.backend_candidate_source ? `候选生成边界：${candidateSourceLabel({ source: record.backend_candidate_source })}。` : "预览候选只用于流程试用，不声明算法外部验证性能。",
      "正式报告需记录算法版本、参数、候选表校验信息和证据来源；当前不是经外部验证的检测器输出。",
    ], state.candidatesGenerated ? ["正式交付限制：当前为候选复核草稿，正式交付需接入已验证算法产物和真实波形追溯。"] : ["阻断：复核前必须有候选包。"]));

    gates.push(makeGate("review", "人工复核", reviewGateStatus(stats), [
      `${stats.reviewed}/${stats.total} 个候选已有人工状态；其中 ${stats.needs_review} 个存疑/需二次复核。`,
      `${stats.confirmed} 个候选纳入草稿，${stats.rejected} 个不纳入草稿，${stats.needs_review} 个存疑/需二次复核，${stats.unreviewed} 个未复核。`,
      "仅纳入草稿候选进入预览候选密度；不纳入草稿和存疑/需二次复核候选进入操作记录或待确认清单。",
    ], reviewBlocks(stats)));

    gates.push(makeGate("report", "草稿与证据", reportGateStatus(stats), [
      state.reviewSaved ? "候选与复核上下文已保存，可被草稿预览页读取。" : "人工复核结果尚未保存。",
      "图表来自候选复核草稿；代表波形示意需正式接入 EDF 窗口数据。",
      "草稿措辞保持科研筛查支持，不使用确诊、排除疾病或治疗建议。",
    ], reportBlocks(stats)));

    state.gates = gates;
    if (!options.silent) {
      addAudit("adversarial_review_run", `完成 ${gates.length} 个关键节点对抗性评审。`);
      toast("对抗性评审已更新。");
    }
  }

  function makeGate(id, title, status, evidence, blocks) {
    return { id, title, status, evidence, blocks };
  }

  function reviewGateStatus(stats) {
    if (!state.candidatesGenerated) return "fail";
    if (stats.reviewed === 0) return "fail";
    if (stats.unreviewed > 0 || stats.needs_review > 0) return "warn";
    return "pass";
  }

  function reportGateStatus(stats) {
    if (!state.candidatesGenerated || stats.reviewed === 0) return "fail";
    if (!state.reviewSaved || stats.unreviewed > 0 || stats.needs_review > 0) return "warn";
    return "warn";
  }

  function reviewBlocks(stats) {
    const blocks = [];
    if (!state.candidatesGenerated) blocks.push("阻断：候选包缺失。");
    if (stats.reviewed === 0 && state.candidatesGenerated) blocks.push("阻断：没有任何人工复核记录。");
    if (stats.unreviewed > 0) blocks.push("P1：仍有未复核候选，只能生成部分复核草稿。");
    if (stats.needs_review > 0) blocks.push("P1：存疑候选不能写成结论，需要单列待确认。");
    return blocks;
  }

  function reportBlocks(stats) {
    const blocks = [];
    if (!state.reviewSaved) blocks.push("P1：人工复核结果未保存，外部报告页无法复现当前结果。");
    if (stats.reviewed === 0) blocks.push("阻断：没有人工复核结果，不能生成复核草稿结论。");
    if (stats.unreviewed + stats.needs_review > 0) blocks.push("P1：报告状态必须标为部分复核草稿。");
    blocks.push("正式交付限制：正式交付材料需替换真实 EDF 窗口示意图，并生成追溯清单和操作记录。");
    return blocks;
  }

  function setStep(step) {
    if (!STEPS.includes(step)) return;
    if (!canEnterStep(step)) {
      toast(stepLockReason(step));
      return;
    }
    state.currentStep = step;
    render();
    window.requestAnimationFrame(redrawVisibleFigures);
  }

  function canEnterStep(step) {
    const stats = reviewStats();
    if (step === "upload") return true;
    if (step === "preflight") return Boolean(currentRecord());
    if (step === "candidates") return state.preflightDone && !currentRecord()?.upload_only;
    if (step === "review") return state.candidatesGenerated;
    if (step === "adversarial") return stats.reviewed > 0;
    if (step === "report") return state.reviewSaved && stats.reviewed > 0 && !hasFailingGate();
    return false;
  }

  function stepLockReason(step) {
    if (step === "preflight") return "请先选择 HE 示例或导入 EDF。";
    if (step === "candidates") return "请先完成数据预检。";
    if (step === "review") return "请先生成候选片段包。";
    if (step === "adversarial") return "请先完成至少一条人工复核。";
    if (step === "report") return "请先保存工作台复核记录，并通过阻断项检查。";
    return "当前步骤还未解锁。";
  }

  async function runNextAction() {
    if (isFlowBusy()) {
      toast("当前流程正在运行，请等待本步完成。");
      return;
    }
    const next = nextAction();
    if (next.action === "reload_backend") {
      await loadBackendRecords();
      const first = availableRecords()[0];
      if (first) selectRecord(first.id, { silent: true });
      render();
    }
    if (next.action === "select_sample") {
      const first = availableRecords()[0];
      if (first) selectRecord(first.id);
      else toast(state.backendError || "当前没有可选择的示例记录。");
    }
    if (next.action === "preflight") await runPreflight();
    if (next.action === "candidates") await generateCandidates();
    if (next.action === "review") setStep("review");
    if (next.action === "open_review") setStep("review");
    if (next.action === "auto_review") fillExampleReview();
    if (next.action === "save_review") await saveReviewLayer();
    if (next.action === "adversarial") {
      setStep("adversarial");
      runAdversarialReview();
      render();
    }
    if (next.action === "report") setStep("report");
    if (next.action === "export_report") await exportReportJson();
  }

  function nextAction() {
    const stats = reviewStats();
    if (!currentRecord() && !state.backendAvailable && !DEMO_PREVIEW_MODE) {
      return {
        action: "reload_backend",
        title: "连接示例数据",
        text: "需要读取真实 HE EDF 后才能继续；未就绪时不会用界面预览样本代替真实分析。",
        label: "重新连接",
      };
    }
    if (!currentRecord()) return { action: "select_sample", title: "选择 HE 示例数据", text: "选择 HE-105、HE-106、HE-118，或登记 EDF 文件。", label: "选择 HE-105" };
    if (!state.preflightDone) return { action: "preflight", title: "运行数据预检", text: "先确认文件规模、通道和长记录读取策略，再生成候选片段包。", label: "运行预检" };
    if (currentRecord()?.upload_only && state.preflightDone) return { action: "select_sample", title: "导入文件待读取记录信息", text: "当前导入文件不能套用 HE 示例候选；请选择 HE 示例，或先完成 EDF 读取后再生成候选片段包。", label: "选择 HE 示例" };
    if (!state.candidatesGenerated) return { action: "candidates", title: "生成候选片段包", text: "从长记录中筛出需要人工查看的片段；HE 示例首次读取原始波形可能需要 20-40 秒。", label: "生成候选片段包" };
    if (stats.reviewed === 0) return { action: "review", title: "在当前页复核候选", text: "选择左侧候选，在右侧标注是否纳入草稿；不需要再打开新的工作台。", label: "开始复核" };
    if (stats.unreviewed === 0 && !state.reviewSaved) return { action: "save_review", title: "同步复核记录", text: "保存当前页的人工判断，供复核草稿读取。", label: "同步记录" };
    if (state.reviewSaved && stats.unreviewed === 0 && !hasFailingGate()) return { action: "report", title: stats.needs_review > 0 ? "查看部分复核草稿" : "查看复核草稿预览", text: "存疑候选会保留为草稿风险提示，不会升级为正式结论。", label: "查看草稿" };
    if (stats.needs_review > 0) return { action: "review", title: `处理 ${stats.needs_review} 个存疑候选`, text: "存疑候选必须单列待确认，不能进入正式结论。", label: "回到复核" };
    if (stats.unreviewed > 0) return { action: "review", title: "补齐未复核候选", text: "未复核候选不能进入最终报告结论。", label: "回到复核" };
    if (!state.reviewSaved) return { action: "save_review", title: "同步复核记录", text: "保存当前页的人工判断，供复核草稿读取。", label: "同步记录" };
    if (hasFailingGate()) return { action: "adversarial", title: "完成结果边界检查", text: "重新检查输入、候选片段、人工复核和草稿结论是否越界。", label: "运行检查" };
    if (state.currentStep !== "report") return { action: "report", title: "查看复核草稿预览", text: "草稿包含摘要、图表、事件表、方法、限制和追溯信息；仍不是正式科研结论。", label: "查看复核草稿" };
    return { action: "export_report", title: "下载草稿数据", text: "下载当前草稿数据；正式报告还需要 PDF/HTML、图表、追溯清单和审计记录。", label: "下载草稿数据" };
  }

  function render() {
    renderStepper();
    renderTopActions();
    renderSamples();
    renderContext();
    renderQc();
    renderCandidates();
    renderReview();
    renderGates();
    renderReport();
    renderNextAction();
    renderAudit();
    syncIcons();
  }

  function renderActions() {
    renderTopActions();
    renderNextAction();
    renderStepper();
    syncIcons();
  }

  function renderTopActions() {
    const stats = reviewStats();
    const busy = isFlowBusy();
    const canOpenReview = state.candidatesGenerated && !busy;
    const canOpenReport = state.reviewSaved && stats.reviewed > 0 && !hasFailingGate() && !busy;
    dom.chooseEdfBtn.disabled = busy;
    dom.edfInput.disabled = busy;
    if (dom.openReviewBtn) {
      dom.openReviewBtn.disabled = !canOpenReview;
      dom.openReviewBtn.title = canOpenReview ? "打开详细复核页" : busy ? "当前流程正在运行" : "请先生成候选片段包";
    }
    dom.openReportBtn.disabled = !canOpenReport;
    dom.openReportBtn.title = canOpenReport ? "打开草稿预览页" : busy ? "当前流程正在运行" : "请先保存工作台复核记录并处理阻断项";
    dom.runPreflightBtn.disabled = state.busy.preflight || !currentRecord();
    dom.generateCandidatesBtn.disabled = state.busy.candidates || !state.preflightDone || Boolean(currentRecord()?.upload_only);
    dom.autoReviewBtn.disabled = busy || !state.candidatesGenerated;
    dom.saveReviewBtn.disabled = state.busy.saveReview || !canOpenReview;
    dom.saveReviewBtn.title = canOpenReview ? "同步当前页复核记录" : busy ? "当前流程正在运行" : "请先生成候选片段包";
    dom.exportCsvBtn.disabled = busy || hasFailingGate() || !state.reviewSaved;
    dom.exportCsvBtn.title = dom.exportCsvBtn.disabled ? "存在阻断项或复核结果未保存，不能导出事件表。" : "导出草稿事件表。";
    dom.exportReportJsonBtn.disabled = busy || hasFailingGate() || !state.reviewSaved;
    dom.exportReportJsonBtn.title = dom.exportReportJsonBtn.disabled ? "存在阻断项或复核结果未保存，不能下载草稿数据。" : "下载草稿数据。";
  }

  function renderStepper() {
    const activeIndex = STEPS.indexOf(state.currentStep);
    dom.steps.forEach((button, index) => {
      button.classList.toggle("is-active", button.dataset.step === state.currentStep);
      button.classList.toggle("is-done", index < activeIndex || stepComplete(button.dataset.step));
      button.disabled = !canEnterStep(button.dataset.step);
      button.title = button.disabled ? stepLockReason(button.dataset.step) : "";
      button.setAttribute("aria-disabled", String(button.disabled));
      if (button.dataset.step === state.currentStep) {
        button.setAttribute("aria-current", "step");
      } else {
        button.removeAttribute("aria-current");
      }
    });
    dom.stages.forEach((stage) => {
      stage.classList.toggle("is-active", stage.dataset.stage === state.currentStep);
    });
  }

  function stepComplete(step) {
    const stats = reviewStats();
    if (step === "upload") return Boolean(currentRecord());
    if (step === "preflight") return state.preflightDone;
    if (step === "candidates") return state.candidatesGenerated;
    if (step === "review") return stats.reviewed > 0;
    if (step === "adversarial") return state.gates.length > 0 && !hasFailingGate();
    if (step === "report") return state.reviewSaved;
    return false;
  }

  function renderSamples() {
    const rows = [...availableRecords(), ...(state.uploadedRecord ? [state.uploadedRecord] : [])];
    const busy = isFlowBusy();
    if (!rows.length) {
      dom.sampleGrid.innerHTML = `
        <article class="ep-flow-sample-card ep-flow-sample-card-empty" aria-live="polite">
          <strong>示例数据未就绪</strong>
          <small>${h(state.backendError || "请联系部署人员或重新连接示例数据。")}</small>
          <small>未就绪时不会用界面预览样本代替真实分析。</small>
        </article>
      `;
      return;
    }
    dom.sampleGrid.innerHTML = rows.map((record) => `
      <button class="ep-flow-sample-card ${record.id === state.selectedRecordId ? "is-selected" : ""}" type="button" data-record-id="${h(record.id)}" ${busy ? "disabled" : ""} aria-current="${record.id === state.selectedRecordId ? "true" : "false"}" title="${busy ? "当前流程正在运行，完成后可切换记录。" : "选择该记录"}">
        <strong>${h(record.filename)}</strong>
          <small>${formatBytes(record.size_bytes)} · ${record.duration_sec ? `${formatHours(record.duration_sec)} h` : "待读取"} · ${h((record.channels || []).join(" / ") || "通道待解析")}</small>
          <small>${record.upload_only ? "导入文件：仅登记，未分析" : record.backend_record ? "真实 EDF 示例：元数据和波形窗口已连接" : "界面预览样本，不作为真实分析证据"}</small>
        </button>
    `).join("");
    dom.sampleGrid.querySelectorAll("[data-record-id]").forEach((button) => {
      button.addEventListener("click", () => selectRecord(button.dataset.recordId));
    });
  }

  function renderContext() {
    const record = currentRecord();
    const stats = reviewStats();
    dom.contextRecord.textContent = record ? record.filename : "尚未选择";
    dom.contextQc.textContent = state.preflightLimitedUpload ? "待读取元数据" : state.preflightDone ? "已完成" : "待预检";
    dom.contextCandidates.textContent = state.candidatesGenerated ? String(candidates().length) : "0";
    dom.contextReview.textContent = `${Math.round((stats.reviewed / Math.max(1, stats.total)) * 100)}%`;
    dom.contextReport.textContent = reportStatusLabel(stats);
  }

  function renderQc() {
    const record = currentRecord();
    const checks = preflightChecks(record);
    dom.qcGrid.innerHTML = checks.map((check) => `
      <article class="ep-flow-qc-card">
        <span>${h(check.label)}</span>
        <strong>${h(check.value)}</strong>
        <p>${h(check.detail)}</p>
      </article>
    `).join("");
  }

  function preflightChecks(record) {
    if (!record) {
      return [
        { label: "文件", value: "待选择", detail: "请先选择 HE 示例或导入 EDF。" },
        { label: "读取方式", value: "未确认", detail: "长时程记录需要按时间窗分段查看。" },
      ];
    }
    return [
      { label: "文件格式", value: record.filename.toLowerCase().endsWith(".edf") ? "EDF" : "待确认", detail: `${record.filename} · ${formatBytes(record.size_bytes)}` },
      { label: "记录规模", value: record.duration_sec ? `${formatHours(record.duration_sec)} h` : "待解析", detail: "约 70 小时记录需要分段处理，不能一次性全量加载。" },
      { label: "采样率", value: record.sfreq ? `${record.sfreq} Hz` : "待解析", detail: "HE 示例预期为 1000 Hz；导入文件以实际读取结果为准。" },
      { label: "通道", value: (record.channels || []).join(" / ") || "待解析", detail: "EEG 通道用于候选展示，EMG/ACC 只能作为伪迹线索，不能单独决定是否纳入草稿。" },
      { label: "隐私路径", value: "安全相对路径", detail: record.safe_source_path || SAFE_SAMPLE_FOLDER },
      { label: "代表波形", value: "原始记录片段", detail: "正式报告代表图必须来自真实 EDF 时间窗。" },
    ];
  }

  function renderCandidates() {
    const list = candidates();
    const runnerText = state.candidatesGenerated ? "候选片段包已生成" : state.candidateProgress > 0 ? "正在生成候选片段包" : "等待运行";
    dom.candidateRunner.querySelector("span").textContent = runnerText;
    dom.candidateRunner.querySelector("b").style.width = `${state.candidateProgress}%`;
    const progressEl = dom.candidateRunner.querySelector(".ep-flow-progress");
    progressEl.setAttribute("aria-valuenow", String(Math.round(state.candidateProgress)));
    progressEl.setAttribute("aria-valuetext", `${runnerText}，${Math.round(state.candidateProgress)}%`);
    dom.candidateStrip.innerHTML = list.length
      ? list.map((event) => `
        <article class="ep-flow-candidate-mini">
          <strong>${h(event.event_id)} · ${h(eventTypeLabel(event.event_type))}</strong>
          <span>${formatClock(event.start_sec)} · ${event.duration_sec.toFixed(1)} s · ${h(event.channels.join(" / "))}</span>
          <span>复核优先级：${h(priorityLabel(event.priority))} · 排序值仅作复核优先级参考</span>
          <span>${h(candidateSourceLabel(event))}</span>
        </article>
      `).join("")
      : `<article class="ep-flow-candidate-mini"><strong>暂无候选</strong><span>完成预检后会列出需要人工查看的候选片段。</span></article>`;
  }

  function renderReview() {
    const list = candidates();
    dom.eventList.innerHTML = list.length
      ? list.map((event, index) => `
        <button class="ep-flow-event-card ${index === state.activeEventIndex ? "is-active" : ""}" type="button" data-event-index="${index}" aria-current="${index === state.activeEventIndex ? "true" : "false"}" aria-selected="${index === state.activeEventIndex ? "true" : "false"}">
          <strong><span>${h(event.event_id)}</span><span>${h(STATUS_LABEL[statusFor(event)])}</span></strong>
          <span>${formatClock(event.start_sec)} · ${event.duration_sec.toFixed(1)} s · ${h(eventTypeLabel(event.event_type))}</span>
          <span>${h(event.channels.join(" / "))} · 复核优先级：${h(priorityLabel(event.priority))}</span>
          <span>${h(candidateSourceLabel(event))}</span>
        </button>
      `).join("")
      : `<article class="ep-flow-event-card"><strong><span>暂无候选</span></strong><span>生成候选片段包后在这里查看候选队列。</span></article>`;
    dom.eventList.querySelectorAll("[data-event-index]").forEach((button) => {
      button.addEventListener("click", () => {
        state.activeEventIndex = Number(button.dataset.eventIndex);
        renderReview();
      });
    });
    renderReviewForm();
  }

  function renderReviewForm() {
    const event = activeCandidate();
    const review = reviewFor(event);
    if (!event) {
      dom.activeEventTitle.textContent = "请选择候选事件";
      dom.reviewWaveform.setAttribute("aria-label", "暂无候选片段波形；生成候选片段包后显示只读概览。");
      drawEmptyCanvas(dom.reviewWaveform, "生成候选片段包后显示只读概览");
      renderReviewHandoffFacts(null, null);
      renderInlineReviewControls(null, null);
      return;
    }
    dom.activeEventTitle.textContent = `${event.event_id} · ${eventTypeLabel(event.event_type)}`;
    dom.reviewWaveform.setAttribute(
      "aria-label",
      `${event.event_id}，${eventTypeLabel(event.event_type)}，起始 ${formatClock(event.start_sec)}，时长 ${event.duration_sec.toFixed(1)} 秒，通道 ${event.channels.join(" / ")}，状态 ${STATUS_LABEL[review?.status || "unreviewed"]}。`
    );
    renderReviewHandoffFacts(event, review);
    renderInlineReviewControls(event, review);
    drawWaveformPreview(event, review);
  }

  function renderInlineReviewControls(event, review) {
    const disabled = !event || isFlowBusy();
    document.querySelectorAll("[data-flow-status]").forEach((button) => {
      const active = Boolean(event && review?.status === button.dataset.flowStatus);
      button.classList.toggle("is-active", active);
      button.disabled = disabled;
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    if (dom.reviewNoteInput) {
      dom.reviewNoteInput.value = event ? (review?.note || "") : "";
      dom.reviewNoteInput.disabled = disabled;
    }
    document.querySelectorAll("[data-flow-note]").forEach((button) => {
      button.disabled = disabled;
    });
  }

  function renderReviewHandoffFacts(event, review) {
    if (!dom.reviewHandoffFacts) return;
    const stats = reviewStats();
    const facts = [
      `候选 ${stats.total}`,
      `已有人工状态 ${stats.reviewed}/${stats.total}`,
    ];
    if (event) {
      facts.push(`${formatClock(event.start_sec)} · ${event.duration_sec.toFixed(1)} s`);
      facts.push(STATUS_LABEL[review?.status || "unreviewed"]);
    }
    dom.reviewHandoffFacts.innerHTML = facts.map((item) => `<span>${h(item)}</span>`).join("");
  }

  function renderGates() {
    const gates = state.gates.length ? state.gates : [];
    dom.gateGrid.innerHTML = gates.map(gateCardHtml).join("");
    dom.gateSummary.innerHTML = gates.map((gate) => `
      <div class="ep-flow-gate-summary-item">
        <strong>${h(gate.title)}</strong>
        <span class="ep-flow-status ${h(gate.status)}">${h(gate.status.toUpperCase())}</span>
      </div>
    `).join("");
    dom.issueLedger.innerHTML = issueLedgerHtml(gates);
  }

  function gateCardHtml(gate) {
    return `
      <article class="ep-flow-gate-card ${h(gate.status)}">
        <header>
          <h3>${h(gate.title)}</h3>
          <span class="ep-flow-status ${h(gate.status)}">${h(gate.status.toUpperCase())}</span>
        </header>
        <p>${gate.evidence.map(h).join("<br>")}</p>
        ${gate.blocks.length ? `<p><strong>阻断/风险：</strong>${gate.blocks.map(h).join("；")}</p>` : `<p><strong>评审：</strong>当前节点无阻断项。</p>`}
      </article>
    `;
  }

  function issueLedgerHtml(gates) {
    const issues = gates.flatMap((gate) => gate.blocks.map((block) => ({
      gate: gate.title,
      severity: block.startsWith("阻断") ? "P0" : block.startsWith("P1") ? "P1" : block.startsWith("正式交付限制") ? "限制" : "P2",
      issue: block,
    })));
    if (!issues.length) {
      return `<div class="ep-flow-callout"><p>当前评审未发现阻断项。</p></div>`;
    }
    return `
      <table>
        <thead><tr><th>节点</th><th>级别</th><th>问题</th><th>处理</th></tr></thead>
        <tbody>
          ${issues.map((item) => `
            <tr>
              <td>${h(item.gate)}</td>
              <td>${h(item.severity)}</td>
              <td>${h(item.issue)}</td>
              <td>${h(issueFix(item.issue))}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    `;
  }

  function issueFix(issue) {
    if (issue.includes("选择")) return "回到上传样本步骤。";
    if (issue.includes("预检")) return "运行数据预检。";
    if (issue.includes("候选") || issue.includes("疑似")) return "生成候选片段包。";
    if (issue.includes("未复核")) return "回到当前页候选复核区完成标注。";
    if (issue.includes("保存")) return "同步当前页复核记录。";
    if (issue.includes("waveform")) return "正式态接入真实证据图。";
    return "保留为报告限制或待办。";
  }

  function renderReport() {
    const payload = buildReportPayload();
    const stats = payload.summary;
    dom.reportStatusBadge.textContent = reportStatusLabel(stats);
    dom.reportStatusBadge.classList.toggle("ready", stats.report_status === "review_draft_ready");
    dom.reportStatusBadge.classList.toggle("partial", stats.report_status === "partial_review_draft");
    dom.reportSummary.innerHTML = [
      ["候选事件", stats.auto_candidates, "候选总数"],
      ["已有人工状态", stats.reviewed, "人工处理覆盖"],
      ["纳入草稿", stats.confirmed, "进入预览统计"],
      ["存疑/未复核", stats.needs_review + stats.unreviewed, "不写作结论"],
      ["纳入草稿候选数", `${stats.confirmed_candidate_rate_per_hour.toFixed(3)} 个/记录小时`, "预览归一化统计，非疾病负荷"],
    ].map(([label, value, hint]) => `
      <article>
        <span>${h(label)}</span>
        <strong>${h(String(value))}</strong>
        <small>${h(hint)}</small>
      </article>
    `).join("");
    dom.reportInterpretation.textContent = payload.interpretation;
    dom.reportMethods.textContent = payload.methods;
    dom.reportEventRows.innerHTML = payload.events.length
      ? payload.events.map((event) => `
        <tr>
          <td><strong>${h(event.event_id)}</strong></td>
          <td>${h(formatClock(event.start_sec))}<br><small>${h(event.duration_sec.toFixed(1))} s</small></td>
          <td>${h(eventTypeLabel(event.event_type))}</td>
          <td>${h(event.channels.join(" / "))}</td>
          <td>${h(event.evidence_grade || "-")}<br><small>复核优先级：${h(priorityLabel(event.priority))}</small></td>
          <td>${h(STATUS_LABEL[event.status] || event.status)}</td>
          <td>${h(event.review_note || "-")}</td>
        </tr>
      `).join("")
      : `<tr><td colspan="7">生成候选片段包，并在当前页完成人工状态标注后生成事件表。</td></tr>`;
    window.requestAnimationFrame(drawReportFigures);
  }

  function renderNextAction() {
    const next = nextAction();
    dom.nextActionTitle.textContent = next.title;
    dom.nextActionText.textContent = next.text;
    dom.nextActionBtn.querySelector("span").textContent = next.label;
    dom.nextActionBtn.disabled = isFlowBusy();
    dom.nextActionBtn.title = isFlowBusy() ? "当前流程正在运行" : next.label;
  }

  function renderAudit() {
    dom.auditList.innerHTML = state.audit.slice(-8).reverse().map((item) => `
      <li><strong>${h(auditActionLabel(item.action))}</strong><br>${h(item.detail)}<br><small>${h(formatDateTime(item.at))}</small></li>
    `).join("");
  }

  function auditActionLabel(action) {
    return {
      backend_records_loaded: "示例数据已载入",
      backend_records_unavailable: "示例数据未连接",
      backend_preflight_loaded: "数据预检完成",
      backend_preflight_failed: "数据预检失败",
      backend_candidates_generated: "候选已生成",
      backend_candidates_failed: "候选生成失败",
      backend_review_session_saved: "复核记录已保存",
      backend_review_session_failed: "复核记录保存失败",
      backend_export_package_loaded: "草稿材料已生成",
      backend_export_package_failed: "草稿材料生成失败",
      backend_csv_export_failed: "事件表生成失败",
      backend_waveform_failed: "波形窗口读取失败",
      draft_json_exported: "草稿记录已下载",
      draft_csv_exported: "事件表已下载",
      candidate_package_generated: "候选已生成",
      demo_review_filled: "预览复核已填充",
      upload_preflight_limited: "导入文件待分析",
      uploaded_candidates_blocked: "候选生成已阻断",
      adversarial_review_run: "边界检查完成",
    }[action] || "流程记录";
  }

  function reviewStats() {
    const list = candidates();
    const stats = { total: list.length, reviewed: 0, confirmed: 0, rejected: 0, needs_review: 0, unreviewed: 0 };
    list.forEach((event) => {
      const status = statusFor(event);
      stats[status] += 1;
      if (status !== "unreviewed") stats.reviewed += 1;
    });
    return stats;
  }

  function buildReviewPayload() {
    const record = currentRecord();
    const events = candidates().map((event) => normalizedEvent(event));
    return {
      schema_version: REVIEW_SCHEMA,
      review_session_schema_version: REVIEW_SESSION_SCHEMA,
      non_medical_scope: "research_screening_support_only",
      created_at: new Date().toISOString(),
      record: {
        id: record?.id || "",
        file_id: record?.file_id || "",
        filename: record?.filename || "",
        duration_sec: effectiveDurationSec(record),
        sfreq: record?.sfreq || null,
        channels: record?.channels || [],
        safe_source_path: record?.safe_source_path || `${SAFE_SAMPLE_FOLDER}${record?.filename || ""}`,
        path_visibility: "safe_relative",
        backend_record: Boolean(record?.backend_record),
      },
      metadata: {
        review_event_source: "reviewed_events",
        has_full_candidate_set: true,
        has_explicit_candidate_denominator: true,
        candidate_denominator: events.length,
        candidate_set_scope: "current_preview_candidate_package",
        denominator_note: "本复核记录包含当前工作台已载入的预览候选包；这不是全记录完整检测器的事件负荷估计。",
      },
      context: {
        workflow_id: "epilepsy_full_flow_preview",
        task_id: `preview_${record?.id || "none"}`,
        input_file_id: record?.file_id || "",
        review_session_id: `preview_session_${record?.id || "none"}`,
        source_algorithm_artifact_id: record?.backend_candidate_source || "preview_candidate_package",
        source_page: "epilepsy-full-flow-preview",
        api_base: API_BASE,
        backend_record: Boolean(record?.backend_record),
      },
      model: {
        detector_version: record?.backend_algorithm_status || "preview_candidate_package_he_v1",
        threshold: null,
        note: "候选包用于产品流程验证；当前不是外部验证过的癫痫检测器输出。",
      },
      summary: reviewStats(),
      event_reviews: Object.fromEntries(events.map((event) => [event.event_id, {
        status: event.status,
        reviewed_type: event.event_type,
        evidence_grade: event.evidence_grade,
        evidence_grade_scope: event.evidence_grade_scope,
        adjusted_start_sec: event.start_sec,
        adjusted_end_sec: event.end_sec,
        note: event.review_note,
        reviewer: event.reviewer,
        reviewed_at: event.reviewed_at,
      }])),
      reviewed_events: events,
      actions: state.audit,
    };
  }

  function buildReportPayload() {
    const record = currentRecord();
    const events = candidates().map((event) => normalizedEvent(event));
    const stats = reviewStats();
    const hours = effectiveDurationSec(record) / 3600;
    const report_status = stats.reviewed === 0
      ? "not_ready"
      : stats.unreviewed + stats.needs_review > 0
        ? "partial_review_draft"
        : "review_draft_ready";
    return {
      schema_version: REPORT_SCHEMA,
      source_review_schema_version: REVIEW_SCHEMA,
      export_class: "review_draft_only",
      non_medical_scope: "research_screening_support_only",
      delivery_readiness: {
        can_export_draft_json: !hasFailingGate() && state.reviewSaved,
        formal_pdf_html_ready: false,
        manifest_required: true,
        clinical_use_allowed: false,
      },
      record: {
        filename: record?.filename || "",
        duration_sec: effectiveDurationSec(record),
        sfreq: record?.sfreq || null,
        channels: record?.channels || [],
        safe_source_path: record?.safe_source_path || `${SAFE_SAMPLE_FOLDER}${record?.filename || ""}`,
        path_visibility: "safe_relative",
      },
      summary: {
        ...stats,
        auto_candidates: stats.total,
        confirmed_candidate_rate_per_hour: stats.confirmed / Math.max(0.01, hours),
        report_status,
      },
      interpretation: interpretationText(stats, record),
      methods: methodsText(record, stats),
      figure_manifest: figureManifest(),
      provenance: provenanceManifest(),
      gates: state.gates,
      events,
      review_payload: buildReviewPayload(),
    };
  }

  function normalizedEvent(event) {
    const review = reviewFor(event);
    const start = numberOr(review?.adjusted_start_sec, event.start_sec);
    const end = Math.max(start + 0.1, numberOr(review?.adjusted_end_sec, event.end_sec));
    return {
      event_id: event.event_id,
      status: review?.status || "unreviewed",
      event_type: review?.event_type || event.event_type,
      start_sec: round1(start),
      end_sec: round1(end),
      duration_sec: round1(end - start),
      original_start_sec: event.start_sec,
      original_end_sec: event.end_sec,
      priority: event.priority,
      preview_rms_ptp_rank_score: event.preview_rms_ptp_rank_score ?? event.score,
      score_kind: event.score_kind || "preview_rank_not_probability",
      score_note: event.score_note || "复核优先级排序值不是临床概率、检测置信度或诊断结论。",
      event_source: event.source || "preview_candidate_package",
      event_type_scope: event.event_type_scope || "candidate_label_only",
      channels: event.channels,
      evidence_grade: review?.evidence_grade || "",
      evidence_grade_scope: "展示证据充分度，不代表临床证据等级或诊断确定性。",
      review_note: review?.note || "",
      reviewer: review?.reviewer || "",
      reviewed_at: review?.reviewed_at || "",
    };
  }

  function interpretationText(stats, record) {
    if (!record) return "尚未选择记录。";
    if (stats.reviewed === 0) {
      return `记录 ${record.filename} 已进入预览流程，但尚无人工复核结果；不能形成草稿摘要。`;
    }
    const pending = stats.needs_review + stats.unreviewed;
    const base = `在 ${record.filename} 的候选复核草稿中，${stats.confirmed} 个癫痫样候选被纳入草稿，${stats.rejected} 个候选不纳入草稿。`;
    if (pending > 0) {
      return `${base} 仍有 ${pending} 个存疑或未复核候选，本草稿只能作为部分复核记录，不能代表完整记录的事件负荷。`;
    }
    return `${base} 当前所有候选均已有人工状态；纳入草稿候选数（预览，按记录小时归一化）只表示已有人工状态候选的预览统计，不代表发作频率、疾病活动度或完整事件负荷。`;
  }

  function methodsText(record, stats) {
    if (!record) return "尚未选择输入数据。";
    const sfreq = record.sfreq ? `${record.sfreq} Hz` : "待读取";
    const candidateSource = record.backend_candidate_source?.startsWith("fallback_")
      ? "候选片段来自示例时间点；系统读取对应原始波形片段，并计算波形变化指标。该指标只用于复核优先级，不是概率。"
      : record.backend_candidate_source
        ? "候选片段来自长记录分段筛查；系统读取原始波形片段，并计算波形变化指标。该指标只用于复核优先级，不是概率。"
        : "当前页面使用界面预览候选试跑产品流程，不表示候选算法或科研结论已验证。";
    return `输入为 ${record.filename}，通道为 ${(record.channels || []).join("、") || "待读取"}，采样率 ${sfreq}，记录时长约 ${formatHours(effectiveDurationSec(record))} 小时。${candidateSource} 正式分析应记录算法版本、阈值、预处理、窗口长度、人工复核标准和导出追溯清单。证据等级 A/B/C/X 仅表示当前界面展示的证据是否足够复核，不是临床证据等级；不纳入草稿原因包括肌电、运动、接触不良、断线、饱和、噪声、重复候选或非癫痫样生理活动。本草稿不估计敏感性或特异性，不确认或排除癫痫发作。`;
  }

  function figureManifest() {
    return [
      { id: "timelineFigure", title: "候选事件时间轴", source: "preview_review_layer", provenance: "preview_only", limitation: "正式报告需绑定真实 EDF 波形追溯。" },
      { id: "funnelFigure", title: "复核漏斗", source: "manual_review_layer", provenance: "review_state" },
      { id: "densityFigure", title: "纳入草稿候选数（预览，按记录小时归一化）", source: "manual_review_layer", provenance: "review_state", limitation: "仅为已有人工状态候选的预览统计，不代表发作频率、疾病活动度或完整事件负荷。" },
      { id: "qcFigure", title: "通道参与概览", source: "preview_candidates", provenance: "preview_only" },
    ];
  }

  function provenanceManifest() {
    return {
      generated_at: new Date().toISOString(),
      generated_by: "epilepsy-full-flow-preview",
      path_visibility: "safe_relative",
      review_saved_to: state.reviewSaved ? REVIEW_STORAGE_KEY : null,
      backend_review_session_id: state.backendReviewSession?.session_id || null,
      backend_review_session_source: state.backendReviewSession?.source || null,
      boundary: "research_screening_support_only",
    };
  }

  function buildFlowState() {
    return {
      schema_version: FLOW_SCHEMA,
      current_step: state.currentStep,
      selected_record_id: state.selectedRecordId,
      current_record: currentRecord(),
      backend_records: state.backendRecords,
      candidates: candidates(),
      reviews: state.reviews,
      preflight_done: state.preflightDone,
      preflight_limited_upload: state.preflightLimitedUpload,
      candidates_generated: state.candidatesGenerated,
      review_saved: state.reviewSaved,
      backend_review_session: state.backendReviewSession,
      gates: state.gates,
      audit: state.audit,
      report: buildReportPayload(),
    };
  }

  function buildCustomerFlowRecord() {
    const record = currentRecord();
    const stats = reviewStats();
    return {
      记录类型: "癫痫样候选事件流程记录",
      生成时间: new Date().toISOString(),
      使用边界: "仅用于科研筛查和人工复核支持；不作为临床诊断、治疗或用药依据。",
      当前步骤: STEP_LABEL[state.currentStep] || state.currentStep,
      记录: {
        文件名: record?.filename || "尚未选择",
        记录时长秒: round1(effectiveDurationSec(record)),
        采样率Hz: record?.sfreq || "",
        通道: record?.channels || [],
      },
      进度: {
        已完成预检: state.preflightDone ? "是" : "否",
        已生成候选: state.candidatesGenerated ? "是" : "否",
        已保存复核记录: state.reviewSaved ? "是" : "否",
      },
      复核摘要: {
        候选总数: stats.total,
        已复核: stats.reviewed,
        纳入草稿候选: stats.confirmed,
        不纳入草稿候选: stats.rejected,
        存疑: stats.needs_review,
        未复核: stats.unreviewed,
        草稿状态: reportStatusLabel(stats),
      },
      边界检查: state.gates.map((gate) => ({
        环节: gate.title,
        状态: gate.status,
        说明: gate.evidence,
        待处理: gate.blocks,
      })),
      操作记录: state.audit.slice(-20).map((item) => ({
        时间: item.at,
        操作: auditActionLabel(item.action),
        说明: item.detail,
      })),
    };
  }

  function copyFlowJson() {
    if (hasFailingGate()) {
      toast("存在阻断项，不能复制完整流程记录；请先查看边界检查。");
      setStep("adversarial");
      return;
    }
    copyText(JSON.stringify(buildCustomerFlowRecord(), null, 2), "已复制候选复核流程记录。");
  }

  async function openDetailedReview() {
    if (!await saveReviewLayer()) return;
    window.location.href = linkedPreviewUrl("./epilepsy-review-preview.html", "full-flow-preview");
  }

  async function openStandaloneReport() {
    if (!await saveReviewLayer()) return;
    window.location.href = linkedPreviewUrl("./epilepsy-report-preview.html", "full-flow-preview");
  }

  function linkedPreviewUrl(path, source) {
    const params = new URLSearchParams({ source });
    if (isLocalPage() && API_BASE) params.set("api", API_BASE);
    return `${path}?${params.toString()}`;
  }

  async function exportReportJson() {
    if (hasFailingGate() || !state.reviewSaved) {
      toast("存在阻断项或复核结果未保存，不能下载草稿数据。");
      setStep(hasFailingGate() ? "adversarial" : "review");
      return;
    }
    let reportPayload = buildReportPayload();
    let backendExport = null;
    if (state.backendReviewSession?.session_id) {
      try {
        const sessionId = encodeURIComponent(state.backendReviewSession.session_id);
        const [exportPackage, reportPackage] = await Promise.all([
          apiFetch(`/lab/epilepsy-full-flow/review-sessions/${sessionId}/exports`, { method: "POST" }),
          apiFetch(`/lab/epilepsy-full-flow/review-sessions/${sessionId}/report`),
        ]);
        reportPayload = normalizeBackendReportForCustomer(reportPackage, reportPayload);
        backendExport = exportPackage;
        addAudit("backend_export_package_loaded", `研究草稿材料已生成：${state.backendReviewSession.session_id}。`);
      } catch (error) {
        addAudit("backend_export_package_failed", "复核草稿生成失败，已回退为浏览器本地草稿数据。");
      }
    }
    const payload = buildCustomerDraftPackage(reportPayload, backendExport);
    saveBlob(JSON.stringify(payload, null, 2), "复核草稿记录.json", "application/json;charset=utf-8");
    addAudit("draft_json_exported", state.backendReviewSession?.session_id ? "下载复核草稿记录。" : "下载浏览器本地候选复核草稿记录。");
    toast("草稿数据已下载。");
    renderAudit();
  }

  function normalizeBackendReportForCustomer(reportPackage, fallback) {
    if (!reportPackage || typeof reportPackage !== "object") return fallback;
    const record = reportPackage.record || fallback.record || {};
    const summary = reportPackage.summary || fallback.summary || {};
    const events = Array.isArray(reportPackage.all_reviewed_events)
      ? reportPackage.all_reviewed_events
      : Array.isArray(reportPackage.reviewed_events)
        ? reportPackage.reviewed_events
        : fallback.events || [];
    return {
      ...fallback,
      record: { ...fallback.record, ...record },
      summary: { ...fallback.summary, ...summary },
      events: events.map((item) => ({
        ...item,
        start_sec: Number(item.start_sec ?? item.reviewed_start_sec ?? item.original_start_sec ?? 0),
        end_sec: Number(item.end_sec ?? item.reviewed_end_sec ?? item.original_end_sec ?? 0),
        duration_sec: Number(item.duration_sec ?? Math.max(0, Number(item.end_sec ?? 0) - Number(item.start_sec ?? 0))),
        status: item.status || item.review_status || item.backend_status || "unreviewed",
        event_type: item.event_type || item.reviewed_type || item.ai_type || "candidate_window",
        review_note: item.review_note || item.note || "",
      })),
      interpretation: reportPackage.interpretation || fallback.interpretation,
      methods: reportPackage.methods || fallback.methods,
    };
  }

  function buildCustomerDraftPackage(reportPayload, backendExport) {
    const record = reportPayload.record || {};
    const stats = reportPayload.summary || {};
    const events = Array.isArray(reportPayload.events) ? reportPayload.events : [];
    return {
      草稿类型: "癫痫样候选事件复核草稿",
      生成时间: new Date().toISOString(),
      使用边界: "仅用于科研筛查和人工复核支持；不作为临床诊断、治疗或用药依据。",
      记录: {
        文件名: record.filename || "",
        记录时长秒: round1(record.duration_sec || 0),
        采样率Hz: record.sfreq || "",
        通道: record.channels || [],
      },
      摘要: {
        候选总数: stats.auto_candidates ?? stats.total ?? events.length,
        已复核: stats.reviewed ?? 0,
        纳入草稿候选: stats.confirmed ?? 0,
        不纳入草稿候选: stats.rejected ?? 0,
        存疑: stats.needs_review ?? 0,
        未复核: stats.unreviewed ?? 0,
        草稿状态: reportStatusLabel(stats),
        纳入草稿候选数每记录小时: Number(stats.confirmed_candidate_rate_per_hour || 0),
      },
      事件表: events.map(customerEventRow),
      摘要文字: reportPayload.interpretation || "",
      方法与限制: reportPayload.methods || "",
      图表说明: [
        "时间轴、复核漏斗、候选密度和通道概览来自当前复核草稿。",
        "代表波形当前可能为版式示意；正式交付需接入真实 EDF 波形窗口。",
      ],
      追溯: {
        复核记录编号: state.backendReviewSession?.session_id || "浏览器本地记录",
        草稿材料来源: backendExport ? "试用环境生成" : "当前页面记录",
      },
    };
  }

  function customerEventRow(event) {
    return {
      事件编号: event.event_id || "",
      复核状态: STATUS_LABEL[event.status] || event.status || "未复核",
      起始秒: round1(event.start_sec || 0),
      结束秒: round1(event.end_sec || Number(event.start_sec || 0) + Number(event.duration_sec || 0)),
      时长秒: round1(event.duration_sec || 0),
      候选类型: EVENT_TYPE_EXPORT_LABEL[event.event_type] || eventTypeLabel(event.event_type),
      通道: Array.isArray(event.channels) ? event.channels : [],
      展示证据等级: event.evidence_grade || "",
      复核优先级: priorityLabel(event.priority),
      复核备注: event.review_note || event.note || "",
      伪迹原因: artifactLabel(event.artifact_reason || ""),
    };
  }

  function artifactLabel(reason) {
    return {
      emg: "肌电增高",
      motion_acc: "体动 / ACC 同步",
      electrode: "电极接触不良",
      saturation: "饱和 / 截幅",
      unreadable: "不可判读",
      duplicate: "重复候选",
      physiological: "非目标生理活动",
    }[reason] || reason || "";
  }

  async function exportEventsCsv() {
    if (hasFailingGate() || !state.reviewSaved) {
      toast("存在阻断项或复核结果未保存，不能导出事件表。");
      setStep(hasFailingGate() ? "adversarial" : "review");
      return;
    }
    if (state.backendReviewSession?.session_id) {
      try {
        const sessionId = encodeURIComponent(state.backendReviewSession.session_id);
        const exportPackage = await apiFetch(`/lab/epilepsy-full-flow/review-sessions/${sessionId}/exports`, { method: "POST" });
        const eventCsv = exportPackage?.candidate_review_state_csv || exportPackage?.final_review_events_csv;
        if (eventCsv) {
          saveBlob(eventCsv, "复核草稿事件表.csv", "text/csv;charset=utf-8");
          addAudit("draft_csv_exported", `下载复核事件表：${state.backendReviewSession.session_id}。`);
          toast("事件表已下载。");
          renderAudit();
          return;
        }
      } catch (error) {
        addAudit("backend_csv_export_failed", "事件表生成失败，已回退为浏览器本地事件表。");
      }
    }
    const rows = [
      ["导出类型", "癫痫样候选事件复核草稿"],
      ["临床用途", "不允许作为临床诊断、治疗或用药依据"],
      ["使用边界", "科研筛查和人工复核支持"],
      [],
      ["事件编号", "人工状态", "起始秒", "时长秒", "候选类型", "通道", "展示证据等级", "证据等级说明", "复核优先级", "候选来源", "候选类型说明", "复核备注"],
      ...candidates().map((event) => {
        const item = normalizedEvent(event);
        return [
          item.event_id,
          STATUS_LABEL[item.status] || item.status,
          item.start_sec,
          item.duration_sec,
          EVENT_TYPE_EXPORT_LABEL[item.event_type] || eventTypeLabel(item.event_type),
          item.channels.join("|"),
          item.evidence_grade,
          item.evidence_grade_scope,
          priorityLabel(item.priority),
          candidateSourceLabel({ source: item.event_source }),
          item.event_type_scope,
          item.review_note,
        ];
      }),
    ];
    const csv = `\ufeff${rows.map((row) => row.map(csvCell).join(",")).join("\r\n")}\r\n`;
    saveBlob(csv, "复核草稿事件表.csv", "text/csv;charset=utf-8");
    addAudit("draft_event_csv_exported", "导出候选复核草稿事件表。");
    toast("草稿事件表已导出。");
    renderAudit();
  }

  function drawWaveformPreview(event, review) {
    const record = currentRecord();
    const cacheKey = waveformCacheKey(record?.id, event.event_id);
    const cached = state.waveformCache[cacheKey];
    if (cached?.status === "ready") {
      cached.at = Date.now();
      drawRealWaveformPreview(event, review, cached.payload);
      return;
    }
    if (!cached && record?.backend_record) {
      loadBackendWaveform(event, record.id, cacheKey);
    }
    const canvas = dom.reviewWaveform;
    const ctx = prepareCanvas(canvas, 300);
    if (!ctx) return;
    const { width, height } = canvas._epSize;
    ctx.clearRect(0, 0, width, height);
    drawCanvasTitle(ctx, "候选事件波形概览（合成示意，正式报告需真实 EDF 窗口）", width);
    const channels = ["EEG1", "EEG2", "EMG", "ACC"];
    const left = 54;
    const right = width - 18;
    const top = 42;
    const rowH = (height - top - 28) / channels.length;
    const status = review?.status || "unreviewed";
    channels.forEach((channel, row) => {
      const yMid = top + row * rowH + rowH / 2;
      ctx.strokeStyle = "#e3eaf0";
      ctx.beginPath();
      ctx.moveTo(left, yMid);
      ctx.lineTo(right, yMid);
      ctx.stroke();
      ctx.fillStyle = "#536273";
      ctx.font = "12px Segoe UI, sans-serif";
      ctx.fillText(channel, 12, yMid + 4);
      ctx.strokeStyle = channel.startsWith("EEG") ? "#2563eb" : channel === "EMG" ? "#b7791f" : "#64748b";
      ctx.lineWidth = 1.3;
      ctx.beginPath();
      for (let x = left; x <= right; x += 2) {
        const t = (x - left) / Math.max(1, right - left);
        const burst = event.score * Math.exp(-Math.pow((t - 0.48) / 0.08, 2));
        const base = Math.sin(t * 56 + row) * 0.32 + Math.sin(t * 145 + row * 0.7) * 0.08;
        const motion = channel === "ACC" && status === "rejected" ? Math.sin(t * 30) * 0.28 : 0;
        const emg = channel === "EMG" && status === "rejected" ? Math.sin(t * 180) * 0.18 : 0;
        const signal = base + burst * (channel.startsWith("EEG") ? 0.52 : 0.12) + motion + emg;
        const y = yMid - signal * rowH * 0.55;
        if (x === left) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });
    const start = left + 0.42 * (right - left);
    const end = left + 0.58 * (right - left);
    ctx.fillStyle = "rgba(15, 118, 110, 0.08)";
    ctx.fillRect(start, top - 4, end - start, height - top - 18);
    ctx.strokeStyle = STATUS_COLOR[status] || "#728294";
    ctx.setLineDash([4, 4]);
    [start, end].forEach((x) => {
      ctx.beginPath();
      ctx.moveTo(x, top - 4);
      ctx.lineTo(x, height - 20);
      ctx.stroke();
    });
    ctx.setLineDash([]);
  }

  function waveformCacheKey(recordId, eventId) {
    return `${recordId || "no-record"}:${eventId || "no-event"}`;
  }

  async function loadBackendWaveform(event, recordId, cacheKey) {
    const record = currentRecord();
    if (!record?.backend_record || record.id !== recordId || !event?.event_id) return;
    state.waveformCache[cacheKey] = { status: "loading", at: Date.now() };
    pruneWaveformCache();
    try {
      const start = Math.max(0, (event.start_sec || 0) - 10);
      const duration = Math.min(60, (event.duration_sec || 0) + 20);
      const params = new URLSearchParams({
        start_sec: String(start),
        duration_sec: String(duration),
        channels: "EEG1,EEG2,EMG,ACC",
        max_points: "1800",
      });
      const payload = await apiFetch(`/lab/epilepsy-full-flow/records/${encodeURIComponent(record.id)}/waveform-window?${params.toString()}`, { timeoutMs: REQUEST_TIMEOUT_MS });
      if (state.selectedRecordId !== recordId) return;
      state.waveformCache[cacheKey] = { status: "ready", payload, at: Date.now() };
      pruneWaveformCache();
      if (currentRecord()?.id === recordId && activeCandidate()?.event_id === event.event_id && state.currentStep === "review") {
        drawRealWaveformPreview(event, reviewFor(event), payload);
      }
    } catch (error) {
      if (state.selectedRecordId !== recordId) return;
      state.waveformCache[cacheKey] = { status: "failed", error: error.message, at: Date.now() };
      pruneWaveformCache();
      addAudit("backend_waveform_failed", `${event.event_id} 波形窗口读取失败，保留示意波形。`);
    }
  }

  function pruneWaveformCache() {
    const entries = Object.entries(state.waveformCache);
    if (entries.length <= MAX_WAVEFORM_CACHE_ITEMS) return;
    entries
      .sort(([, a], [, b]) => (a.at || 0) - (b.at || 0))
      .slice(0, entries.length - MAX_WAVEFORM_CACHE_ITEMS)
      .forEach(([key]) => {
        delete state.waveformCache[key];
      });
  }

  function drawRealWaveformPreview(event, review, payload) {
    const canvas = dom.reviewWaveform;
    const ctx = prepareCanvas(canvas, 300);
    if (!ctx) return;
    const { width, height } = canvas._epSize;
    ctx.clearRect(0, 0, width, height);
    drawCanvasTitle(ctx, "真实 EDF 窗口概览（uV，数据读取）", width);
    const channels = Array.isArray(payload.channels) ? payload.channels : [];
    if (!channels.length) {
      drawEmptyCanvas(canvas, "窗口未返回通道数据");
      return;
    }
    const left = 58;
    const right = width - 18;
    const top = 42;
    const rowH = (height - top - 28) / channels.length;
    const status = review?.status || "unreviewed";
    channels.forEach((channel, row) => {
      const values = Array.isArray(channel.values) ? channel.values.map(Number).filter(Number.isFinite) : [];
      const yMid = top + row * rowH + rowH / 2;
      ctx.strokeStyle = "#e3eaf0";
      ctx.beginPath();
      ctx.moveTo(left, yMid);
      ctx.lineTo(right, yMid);
      ctx.stroke();
      ctx.fillStyle = "#536273";
      ctx.font = "12px Segoe UI, sans-serif";
      ctx.fillText(String(channel.name || `CH${row + 1}`).slice(0, 12), 10, yMid + 4);
      if (!values.length) return;
      const scale = robustScale(values);
      ctx.strokeStyle = String(channel.name || "").toUpperCase().startsWith("EEG") ? "#2563eb" : "#b7791f";
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      values.forEach((value, index) => {
        const x = left + (index / Math.max(1, values.length - 1)) * (right - left);
        const y = yMid - Math.max(-1.8, Math.min(1.8, value / scale)) * rowH * 0.28;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
    });
    const eventStart = event.start_sec || payload.start_sec || 0;
    const eventEnd = event.end_sec || eventStart + (event.duration_sec || 1);
    const payloadStart = payload.start_sec || 0;
    const payloadDuration = payload.duration_sec || 1;
    const startX = left + ((eventStart - payloadStart) / payloadDuration) * (right - left);
    const endX = left + ((eventEnd - payloadStart) / payloadDuration) * (right - left);
    ctx.fillStyle = "rgba(15, 118, 110, 0.08)";
    ctx.fillRect(startX, top - 4, Math.max(2, endX - startX), height - top - 18);
    ctx.strokeStyle = STATUS_COLOR[status] || "#728294";
    ctx.setLineDash([4, 4]);
    [startX, endX].forEach((x) => {
      ctx.beginPath();
      ctx.moveTo(x, top - 4);
      ctx.lineTo(x, height - 20);
      ctx.stroke();
    });
    ctx.setLineDash([]);
  }

  function robustScale(values) {
    const sorted = [...values].map((value) => Math.abs(value)).filter(Number.isFinite).sort((a, b) => a - b);
    if (!sorted.length) return 1;
    const index = Math.max(0, Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95)));
    return Math.max(sorted[index], 1);
  }

  function drawReportFigures() {
    if (state.currentStep !== "report") return;
    drawTimelineFigure();
    drawFunnelFigure();
    drawDensityFigure();
    drawQcFigure();
  }

  function redrawVisibleFigures() {
    if (state.currentStep === "review") renderReviewForm();
    if (state.currentStep === "report") drawReportFigures();
  }

  function drawTimelineFigure() {
    const ctx = prepareCanvas(dom.timelineFigure, 250);
    if (!ctx) return;
    const { width, height } = dom.timelineFigure._epSize;
    const list = candidates().map(normalizedEvent);
    const duration = effectiveDurationSec(currentRecord());
    ctx.clearRect(0, 0, width, height);
    drawCanvasTitle(ctx, "当前候选包时间轴", width);
    const left = 54;
    const right = width - 28;
    const y = height / 2;
    ctx.strokeStyle = "#cfd9e3";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(right, y);
    ctx.stroke();
    for (let hIndex = 0; hIndex <= 70; hIndex += 10) {
      const x = left + (hIndex * 3600 / duration) * (right - left);
      ctx.strokeStyle = "#e6edf2";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, y - 46);
      ctx.lineTo(x, y + 46);
      ctx.stroke();
      ctx.fillStyle = "#64748b";
      ctx.font = "11px Segoe UI, sans-serif";
      ctx.fillText(`${hIndex}h`, x - 10, y + 66);
    }
    list.forEach((event, index) => {
      const x = left + (event.start_sec / duration) * (right - left);
      const offset = (index % 4 - 1.5) * 14;
      ctx.fillStyle = STATUS_COLOR[event.status] || STATUS_COLOR.unreviewed;
      ctx.beginPath();
      ctx.arc(x, y + offset, 5.5, 0, Math.PI * 2);
      ctx.fill();
    });
    drawLegend(ctx, [
      ["纳入草稿", STATUS_COLOR.confirmed],
      ["存疑", STATUS_COLOR.needs_review],
      ["不纳入", STATUS_COLOR.rejected],
      ["未复核", STATUS_COLOR.unreviewed],
    ], left, 48);
  }

  function drawFunnelFigure() {
    const ctx = prepareCanvas(dom.funnelFigure, 250);
    if (!ctx) return;
    const { width, height } = dom.funnelFigure._epSize;
    const stats = reviewStats();
    const values = [
      ["候选", stats.total, "#2563eb"],
      ["已有人工状态", stats.reviewed, "#0f766e"],
      ["纳入草稿", stats.confirmed, STATUS_COLOR.confirmed],
    ];
    drawBarChart(ctx, width, height, "复核漏斗", values, Math.max(1, stats.total));
  }

  function drawDensityFigure() {
    const ctx = prepareCanvas(dom.densityFigure, 250);
    if (!ctx) return;
    const { width, height } = dom.densityFigure._epSize;
    const duration = effectiveDurationSec(currentRecord());
    const bins = new Array(10).fill(0);
    candidates().map(normalizedEvent).filter((event) => event.status === "confirmed").forEach((event) => {
      const index = Math.min(bins.length - 1, Math.floor((event.start_sec / duration) * bins.length));
      bins[index] += 1;
    });
    const values = bins.map((value, index) => [`${index * 7}-${(index + 1) * 7}h`, value, "#0f766e"]);
    drawBarChart(ctx, width, height, "纳入草稿候选数（预览）", values, Math.max(1, ...bins), { compactLabels: true });
  }

  function drawQcFigure() {
    const ctx = prepareCanvas(dom.qcFigure, 250);
    if (!ctx) return;
    const { width, height } = dom.qcFigure._epSize;
    const channels = ["EEG1", "EEG2", "EMG", "ACC"];
    const counts = channels.map((channel) => candidates().filter((event) => event.channels.includes(channel)).length);
    const values = channels.map((channel, index) => [channel, counts[index], channel.startsWith("EEG") ? "#2563eb" : "#b7791f"]);
    drawBarChart(ctx, width, height, "通道参与候选数", values, Math.max(1, ...counts));
  }

  function drawBarChart(ctx, width, height, title, values, maxValue, options = {}) {
    ctx.clearRect(0, 0, width, height);
    drawCanvasTitle(ctx, title, width);
    const left = 46;
    const right = width - 18;
    const bottom = height - 34;
    const top = 50;
    const gap = 8;
    const barW = Math.max(10, (right - left - gap * (values.length - 1)) / values.length);
    ctx.strokeStyle = "#d9e2ea";
    ctx.beginPath();
    ctx.moveTo(left, top);
    ctx.lineTo(left, bottom);
    ctx.lineTo(right, bottom);
    ctx.stroke();
    values.forEach(([label, value, color], index) => {
      const x = left + index * (barW + gap);
      const hgt = (value / maxValue) * (bottom - top);
      ctx.fillStyle = color;
      ctx.fillRect(x, bottom - hgt, barW, hgt);
      ctx.fillStyle = "#12212f";
      ctx.font = "12px Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(String(value), x + barW / 2, bottom - hgt - 6);
      ctx.fillStyle = "#64748b";
      ctx.font = "11px Segoe UI, sans-serif";
      const text = options.compactLabels ? label.replace("-", "–") : label;
      ctx.fillText(text, x + barW / 2, bottom + 18);
      ctx.textAlign = "left";
    });
  }

  function drawCanvasTitle(ctx, title, width) {
    ctx.fillStyle = "#12212f";
    ctx.font = "600 14px Segoe UI, sans-serif";
    ctx.fillText(title, 14, 24);
    ctx.fillStyle = "#64748b";
    ctx.font = "11px Segoe UI, sans-serif";
    ctx.fillText("只读概览", width - 74, 24);
  }

  function drawLegend(ctx, items, x, y) {
    let cursor = x;
    items.forEach(([label, color]) => {
      ctx.fillStyle = color;
      ctx.fillRect(cursor, y - 8, 9, 9);
      ctx.fillStyle = "#536273";
      ctx.font = "11px Segoe UI, sans-serif";
      ctx.fillText(label, cursor + 14, y);
      cursor += 78;
    });
  }

  function drawEmptyCanvas(canvas, text) {
    const ctx = prepareCanvas(canvas, 300);
    if (!ctx) return;
    const { width, height } = canvas._epSize;
    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#64748b";
    ctx.font = "14px Segoe UI, sans-serif";
    ctx.fillText(text, 18, height / 2);
  }

  function prepareCanvas(canvas, fallbackHeight) {
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const cssWidth = Math.max(260, Math.round(rect.width || canvas.parentElement?.clientWidth || canvas.width || 600));
    const cssHeight = Math.max(180, Math.round(rect.height || fallbackHeight));
    const dpr = Math.max(1, Math.min(2, window.devicePixelRatio || 1));
    canvas.width = Math.round(cssWidth * dpr);
    canvas.height = Math.round(cssHeight * dpr);
    canvas.style.height = `${cssHeight}px`;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    canvas._epSize = { width: cssWidth, height: cssHeight };
    return ctx;
  }

  function reportStatusLabel(stats) {
    const value = stats.report_status || buildReportPayload().summary.report_status;
    if (stats.report_status_label) return stats.report_status_label;
    if (value === "review_draft_ready") return "当前候选包状态已补齐（仍为研究草稿）";
    if (value === "partial_review_draft") return "部分复核草稿";
    return "未生成";
  }

  function hasFailingGate() {
    return state.gates.some((gate) => gate.status === "fail");
  }

  function addAudit(action, detail) {
    state.audit.push({ action, detail, at: new Date().toISOString() });
    if (state.audit.length > 80) state.audit = state.audit.slice(-80);
  }

  function copyText(text, message) {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(() => toast(message)).catch(() => fallbackCopy(text, message));
    } else {
      fallbackCopy(text, message);
    }
  }

  function fallbackCopy(text, message) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "readonly");
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand("copy");
      toast(message);
    } catch {
      toast("复制失败，请手动选择文本。");
    }
    textarea.remove();
  }

  function saveBlob(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function toast(message) {
    dom.toast.textContent = message;
    dom.toast.classList.add("is-visible");
    window.clearTimeout(toast._timer);
    toast._timer = window.setTimeout(() => dom.toast.classList.remove("is-visible"), 2200);
  }

  function syncIcons() {
    if (window.lucide) window.lucide.createIcons();
  }

  function h(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function csvCell(value) {
    let text = String(value ?? "");
    if (/^[=+\-@]/.test(text)) text = `'${text}`;
    if (/[",\r\n]/.test(text)) text = `"${text.replace(/"/g, '""')}"`;
    return text;
  }

  function numberOr(value, fallback) {
    if (value === null || value === undefined || value === "") return fallback;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
  }

  function round1(value) {
    return Math.round(Number(value) * 10) / 10;
  }

  function formatBytes(bytes) {
    if (!Number.isFinite(bytes)) return "-";
    const gb = bytes / (1024 ** 3);
    return `${gb.toFixed(2)} GB`;
  }

  function formatHours(seconds) {
    return (seconds / 3600).toFixed(1);
  }

  function formatClock(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const hPart = Math.floor(total / 3600);
    const mPart = Math.floor((total % 3600) / 60);
    const sPart = total % 60;
    return `${String(hPart).padStart(2, "0")}:${String(mPart).padStart(2, "0")}:${String(sPart).padStart(2, "0")}`;
  }

  function formatDateTime(iso) {
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleString("zh-CN", { hour12: false });
  }

  function debounce(fn, delay) {
    let timer = 0;
    return function debounced() {
      window.clearTimeout(timer);
      timer = window.setTimeout(fn, delay);
    };
  }

  document.addEventListener("DOMContentLoaded", init);
})();
