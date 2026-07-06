(function () {
  "use strict";

  const CONTRACT_VERSION = "qlanalyser.epilepsy.manual_correction_preview.v1";
  const REVIEW_SESSION_VERSION = "epilepsy_review_session.v1";
  const STATUS_LABEL = {
    unreviewed: "未审",
    kept: "保留",
    excluded: "排除",
    uncertain: "存疑",
  };
  const STATUS_TO_BACKEND = {
    unreviewed: "unreviewed",
    kept: "confirmed",
    excluded: "rejected",
    uncertain: "needs_review",
  };
  const TYPE_LABEL = {
    ied: "IED / 尖慢波",
    seizure_like: "发作样节律",
    rhythmic: "节律性放电",
    artifact_suspect: "伪迹疑似",
  };
  const PRIORITY_WEIGHT = { high: 0, medium: 1, low: 2 };

  const records = [
    {
      id: "he-105",
      file_id: "local_he_105_edf",
      filename: "HE-105.edf",
      duration_sec: 69.78 * 3600,
      sfreq: 1000,
      channels: ["EEG1", "EEG2", "EMG", "ACC"],
      source_path_hint: "D:\\Quanlan\\Data\\HE脑电\\HE脑电\\HE-105.edf",
      model: {
        workflow_id: "epilepsy_ml_xgboost",
        detector_version: "preview-local-he-v1",
        threshold: 0.72,
      },
      candidates: [
        makeCandidate("HE105-E001", 14 * 60 + 18.4, 14 * 60 + 20.1, "high", "ied", ["EEG1", "EEG2"], 0.91, "双导同步尖慢波"),
        makeCandidate("HE105-E002", 42 * 60 + 6.2, 42 * 60 + 9.7, "high", "seizure_like", ["EEG1"], 0.88, "短程节律增强"),
        makeCandidate("HE105-E003", 2 * 3600 + 31 * 60 + 11.5, 2 * 3600 + 31 * 60 + 13.0, "medium", "artifact_suspect", ["EEG2"], 0.67, "EMG/ACC 同步增高"),
        makeCandidate("HE105-E004", 5 * 3600 + 8 * 60 + 45.0, 5 * 3600 + 8 * 60 + 46.8, "medium", "ied", ["EEG1"], 0.73, "单导尖波候选"),
        makeCandidate("HE105-E005", 11 * 3600 + 2 * 60 + 28.4, 11 * 3600 + 2 * 60 + 32.2, "low", "rhythmic", ["EEG1", "EEG2"], 0.61, "边界节律事件"),
        makeCandidate("HE105-E006", 20 * 3600 + 17 * 60 + 9.1, 20 * 3600 + 17 * 60 + 11.8, "high", "ied", ["EEG2"], 0.84, "高幅尖慢波"),
        makeCandidate("HE105-E007", 36 * 3600 + 3 * 60 + 4.6, 36 * 3600 + 3 * 60 + 7.4, "medium", "artifact_suspect", ["EEG1", "EEG2"], 0.69, "体动同步疑似"),
        makeCandidate("HE105-E008", 61 * 3600 + 22 * 60 + 39.3, 61 * 3600 + 22 * 60 + 40.4, "low", "ied", ["EEG1"], 0.58, "低置信单发"),
      ],
    },
    {
      id: "he-106",
      file_id: "local_he_106_edf",
      filename: "HE-106.edf",
      duration_sec: 69.79 * 3600,
      sfreq: 1000,
      channels: ["EEG1", "EEG2", "EMG", "ACC"],
      source_path_hint: "D:\\Quanlan\\Data\\HE脑电\\HE脑电\\HE-106.edf",
      model: {
        workflow_id: "epilepsy_ml_xgboost",
        detector_version: "preview-local-he-v1",
        threshold: 0.72,
      },
      candidates: [
        makeCandidate("HE106-E001", 8 * 60 + 36.8, 8 * 60 + 39.6, "high", "seizure_like", ["EEG1", "EEG2"], 0.9, "发作样短程节律"),
        makeCandidate("HE106-E002", 1 * 3600 + 6 * 60 + 12.0, 1 * 3600 + 6 * 60 + 13.2, "medium", "ied", ["EEG1"], 0.7, "单发尖慢波"),
        makeCandidate("HE106-E003", 4 * 3600 + 44 * 60 + 4.5, 4 * 3600 + 44 * 60 + 6.9, "high", "artifact_suspect", ["EEG2"], 0.81, "EMG 同步突增"),
        makeCandidate("HE106-E004", 13 * 3600 + 28 * 60 + 51.3, 13 * 3600 + 28 * 60 + 53.0, "medium", "ied", ["EEG1", "EEG2"], 0.74, "双导短暂异常"),
        makeCandidate("HE106-E005", 49 * 3600 + 10 * 60 + 2.2, 49 * 3600 + 10 * 60 + 4.4, "low", "rhythmic", ["EEG2"], 0.6, "低置信节律"),
      ],
    },
    {
      id: "he-118",
      file_id: "local_he_118_edf",
      filename: "HE-118.edf",
      duration_sec: 69.72 * 3600,
      sfreq: 1000,
      channels: ["EEG1", "EEG2", "EMG", "ACC"],
      source_path_hint: "D:\\Quanlan\\Data\\HE脑电\\HE脑电\\HE-118.edf",
      model: {
        workflow_id: "epilepsy_ml_xgboost",
        detector_version: "preview-local-he-v1",
        threshold: 0.72,
      },
      candidates: [
        makeCandidate("HE118-E001", 19 * 60 + 12.1, 19 * 60 + 13.6, "medium", "ied", ["EEG1"], 0.71, "局灶尖波"),
        makeCandidate("HE118-E002", 2 * 3600 + 18 * 60 + 31.6, 2 * 3600 + 18 * 60 + 35.8, "high", "seizure_like", ["EEG1", "EEG2"], 0.89, "双导节律演变"),
        makeCandidate("HE118-E003", 7 * 3600 + 52 * 60 + 24.0, 7 * 3600 + 52 * 60 + 26.2, "medium", "artifact_suspect", ["EEG2"], 0.64, "ACC 同步变化"),
        makeCandidate("HE118-E004", 28 * 3600 + 4 * 60 + 55.0, 28 * 3600 + 4 * 60 + 57.0, "low", "ied", ["EEG1", "EEG2"], 0.59, "边界尖波"),
        makeCandidate("HE118-E005", 63 * 3600 + 7 * 60 + 8.4, 63 * 3600 + 7 * 60 + 11.1, "high", "ied", ["EEG2"], 0.86, "高优先尖慢波"),
      ],
    },
  ];

  const state = {
    recordIndex: 0,
    selectedId: "",
    filter: "all",
    viewDuration: 40,
    viewStart: 0,
    sortPriorityFirst: true,
    audit: [],
    history: [],
    drag: null,
  };

  const dom = {};

  function makeCandidate(id, startSec, endSec, priority, aiType, channels, score, qcHint) {
    return {
      id,
      start_sec: round1(startSec),
      end_sec: round1(endSec),
      peak_sec: round1((startSec + endSec) / 2),
      priority,
      ai_type: aiType,
      channels,
      score,
      qc_hint: qcHint,
      emg_sync: aiType === "artifact_suspect" ? "present" : "absent",
      acc_motion: aiType === "artifact_suspect" ? "possible" : "absent",
      review: {
        status: "unreviewed",
        grade: aiType === "artifact_suspect" ? "C" : priority === "high" ? "B" : "C",
        artifact_reason: aiType === "artifact_suspect" ? "motion_acc" : "",
        note: "",
        event_type: aiType,
        adjusted_start_sec: null,
        adjusted_end_sec: null,
        include_in_report: false,
        representative: false,
        reviewer: "local-user",
        reviewed_at: null,
      },
    };
  }

  function init() {
    cacheDom();
    populateRecords();
    selectRecord(0);
    bindEvents();
    resizeCanvases();
    window.addEventListener("resize", resizeCanvases);
    syncIcons();
  }

  function cacheDom() {
    [
      "recordSelect",
      "copyJsonBtn",
      "reportPreviewBtn",
      "exportJsonBtn",
      "durationMetric",
      "candidateMetric",
      "reviewedMetric",
      "keptMetric",
      "candidateList",
      "eventTitle",
      "waveformCanvas",
      "timelineCanvas",
      "eventBand",
      "startHandle",
      "endHandle",
      "prevEventBtn",
      "nextEventBtn",
      "zoomInBtn",
      "zoomOutBtn",
      "sortBtn",
      "statusPill",
      "eventTypeSelect",
      "gradeSelect",
      "artifactReasonSelect",
      "startInput",
      "endInput",
      "noteInput",
      "undoBtn",
      "applyNextBtn",
      "auditList",
      "contractName",
    ].forEach((id) => {
      dom[id] = document.getElementById(id);
    });
  }

  function populateRecords() {
    dom.recordSelect.innerHTML = records
      .map((record, index) => `<option value="${index}">${h(record.filename)} · ${formatDuration(record.duration_sec)}</option>`)
      .join("");
  }

  function bindEvents() {
    dom.recordSelect.addEventListener("change", () => selectRecord(Number(dom.recordSelect.value) || 0));
    dom.copyJsonBtn.addEventListener("click", copyJson);
    dom.reportPreviewBtn.addEventListener("click", openReportPreview);
    dom.exportJsonBtn.addEventListener("click", exportJson);
    dom.prevEventBtn.addEventListener("click", () => stepCandidate(-1));
    dom.nextEventBtn.addEventListener("click", () => stepCandidate(1));
    dom.zoomInBtn.addEventListener("click", () => setViewDuration(Math.max(12, state.viewDuration * 0.65)));
    dom.zoomOutBtn.addEventListener("click", () => setViewDuration(Math.min(180, state.viewDuration * 1.45)));
    dom.sortBtn.addEventListener("click", () => {
      state.sortPriorityFirst = !state.sortPriorityFirst;
      renderQueue();
    });
    document.querySelectorAll("[data-filter]").forEach((button) => {
      button.addEventListener("click", () => {
        state.filter = button.dataset.filter || "all";
        document.querySelectorAll("[data-filter]").forEach((item) => item.classList.toggle("is-active", item === button));
        renderQueue();
      });
    });
    document.querySelectorAll("[data-status]").forEach((button) => {
      button.addEventListener("click", () => markStatus(button.dataset.status || "unreviewed"));
    });
    document.querySelectorAll("[data-note]").forEach((button) => {
      button.addEventListener("click", () => appendNoteTemplate(button.dataset.note || ""));
    });
    [dom.eventTypeSelect, dom.gradeSelect, dom.artifactReasonSelect].forEach((input) => {
      input.addEventListener("change", syncFormToCandidate);
    });
    dom.noteInput.addEventListener("change", syncFormToCandidate);
    dom.startInput.addEventListener("change", syncTimeInputs);
    dom.endInput.addEventListener("change", syncTimeInputs);
    dom.undoBtn.addEventListener("click", undoLast);
    dom.applyNextBtn.addEventListener("click", saveAndNext);
    dom.startHandle.addEventListener("pointerdown", (event) => startDrag(event, "start"));
    dom.endHandle.addEventListener("pointerdown", (event) => startDrag(event, "end"));
    window.addEventListener("pointermove", onDragMove);
    window.addEventListener("pointerup", endDrag);
  }

  function selectRecord(index) {
    state.recordIndex = Math.max(0, Math.min(records.length - 1, index));
    state.audit = [];
    state.history = [];
    const first = sortedCandidates().find((item) => item.priority === "high" && item.review.status === "unreviewed") || sortedCandidates()[0];
    state.selectedId = first ? first.id : "";
    addAudit("open_record", "打开记录", `载入 ${currentRecord().filename}`);
    fitViewToCandidate();
    renderAll();
  }

  function currentRecord() {
    return records[state.recordIndex];
  }

  function selectedCandidate() {
    return currentRecord().candidates.find((candidate) => candidate.id === state.selectedId) || currentRecord().candidates[0];
  }

  function sortedCandidates() {
    const candidates = [...currentRecord().candidates];
    if (state.sortPriorityFirst) {
      candidates.sort((a, b) => {
        const priority = (PRIORITY_WEIGHT[a.priority] ?? 9) - (PRIORITY_WEIGHT[b.priority] ?? 9);
        if (priority !== 0) return priority;
        return a.start_sec - b.start_sec;
      });
    } else {
      candidates.sort((a, b) => a.start_sec - b.start_sec);
    }
    return candidates;
  }

  function filteredCandidates() {
    return sortedCandidates().filter((candidate) => {
      if (state.filter === "all") return true;
      if (state.filter === "unreviewed") return candidate.review.status === "unreviewed";
      if (state.filter === "high") return candidate.priority === "high";
      if (state.filter === "artifact_suspect") return candidate.ai_type === "artifact_suspect" || candidate.review.artifact_reason;
      return true;
    });
  }

  function renderAll() {
    renderSummary();
    renderQueue();
    renderReviewPanel();
    renderAudit();
    drawWaveform();
    drawTimeline();
    updateHandles();
    syncIcons();
  }

  function renderSummary() {
    const record = currentRecord();
    const candidates = record.candidates;
    const reviewed = candidates.filter((item) => item.review.status !== "unreviewed").length;
    const kept = candidates.filter((item) => item.review.status === "kept").length;
    dom.durationMetric.textContent = formatDuration(record.duration_sec);
    dom.candidateMetric.textContent = String(candidates.length);
    dom.reviewedMetric.textContent = `${reviewed}/${candidates.length}`;
    dom.keptMetric.textContent = String(kept);
    dom.contractName.textContent = CONTRACT_VERSION;
  }

  function renderQueue() {
    const candidates = filteredCandidates();
    if (!candidates.length) {
      dom.candidateList.innerHTML = `<div class="er-candidate-meta">当前筛选下没有候选。</div>`;
      return;
    }
    dom.candidateList.innerHTML = candidates
      .map((candidate) => {
        const review = candidate.review;
        const start = review.adjusted_start_sec ?? candidate.start_sec;
        const end = review.adjusted_end_sec ?? candidate.end_sec;
        return `
          <button class="er-candidate priority-${h(candidate.priority)} ${candidate.id === state.selectedId ? "is-active" : ""}" type="button" data-candidate-id="${h(candidate.id)}">
            <div class="er-candidate-top">
              <strong>${h(formatClock(start))}</strong>
              <span class="er-tag ${h(review.status)}">${h(STATUS_LABEL[review.status] || review.status)}</span>
            </div>
            <div class="er-candidate-meta">
              <span>${h(TYPE_LABEL[review.event_type] || TYPE_LABEL[candidate.ai_type] || candidate.ai_type)} · ${round1(end - start)}s</span>
              <span class="er-tag ${h(candidate.priority)}">${priorityLabel(candidate.priority)}</span>
            </div>
            <div class="er-candidate-meta">
              <span>${h(candidate.channels.join("/"))}</span>
              <span>${Math.round(candidate.score * 100)}%</span>
            </div>
          </button>
        `;
      })
      .join("");
    dom.candidateList.querySelectorAll("[data-candidate-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.selectedId = button.dataset.candidateId || "";
        fitViewToCandidate();
        renderAll();
      });
    });
  }

  function renderReviewPanel() {
    const candidate = selectedCandidate();
    if (!candidate) return;
    const review = candidate.review;
    const start = review.adjusted_start_sec ?? candidate.start_sec;
    const end = review.adjusted_end_sec ?? candidate.end_sec;
    dom.eventTitle.textContent = `${candidate.id} · ${TYPE_LABEL[review.event_type] || TYPE_LABEL[candidate.ai_type]}`;
    dom.statusPill.textContent = STATUS_LABEL[review.status] || review.status;
    dom.statusPill.className = `er-status-pill ${review.status}`;
    dom.eventTypeSelect.value = review.event_type || candidate.ai_type;
    dom.gradeSelect.value = review.grade || "C";
    dom.artifactReasonSelect.value = review.artifact_reason || "";
    dom.startInput.value = round1(start);
    dom.endInput.value = round1(end);
    dom.noteInput.value = review.note || "";
    document.querySelectorAll("[data-status]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.status === review.status);
    });
  }

  function renderAudit() {
    const items = state.audit.slice(-4).reverse();
    if (!items.length) {
      dom.auditList.innerHTML = `<li><strong>等待操作</strong>尚未产生人工矫正记录。</li>`;
      return;
    }
    dom.auditList.innerHTML = items
      .map((item) => `<li><strong>${h(item.label)}</strong>${h(item.detail)}<br />${h(formatAuditTime(item.created_at))}</li>`)
      .join("");
  }

  function markStatus(status) {
    const candidate = selectedCandidate();
    if (!candidate) return;
    withHistory("event_review", () => {
      candidate.review.status = status;
      candidate.review.include_in_report = status === "kept";
      candidate.review.reviewed_at = new Date().toISOString();
      candidate.review.reviewer = "local-user";
      if (status === "excluded" && !candidate.review.artifact_reason && candidate.ai_type === "artifact_suspect") {
        candidate.review.artifact_reason = "motion_acc";
      }
    });
    addAudit("event_review", STATUS_LABEL[status] || status, `${candidate.id} · ${STATUS_TO_BACKEND[status] || status}`);
    renderAll();
  }

  function syncFormToCandidate() {
    const candidate = selectedCandidate();
    if (!candidate) return;
    withHistory("review_fields", () => {
      candidate.review.event_type = dom.eventTypeSelect.value;
      candidate.review.grade = dom.gradeSelect.value;
      candidate.review.artifact_reason = dom.artifactReasonSelect.value;
      candidate.review.note = dom.noteInput.value.trim();
      candidate.review.reviewed_at = candidate.review.status === "unreviewed" ? candidate.review.reviewed_at : new Date().toISOString();
    });
    addAudit("review_fields", "更新字段", `${candidate.id} · 等级 ${candidate.review.grade}`);
    renderAll();
  }

  function syncTimeInputs() {
    const candidate = selectedCandidate();
    if (!candidate) return;
    const start = Number(dom.startInput.value);
    const end = Number(dom.endInput.value);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
      showToast("起止时间无效");
      renderReviewPanel();
      return;
    }
    withHistory("adjust_event_interval", () => {
      candidate.review.adjusted_start_sec = round1(start);
      candidate.review.adjusted_end_sec = round1(end);
    });
    addAudit("adjust_event_interval", "调整边界", `${candidate.id} · ${round1(start)}-${round1(end)}s`);
    fitViewToCandidate(false);
    renderAll();
  }

  function appendNoteTemplate(text) {
    const candidate = selectedCandidate();
    if (!candidate || !text) return;
    withHistory("note_template", () => {
      const existing = candidate.review.note ? `${candidate.review.note}\n` : "";
      candidate.review.note = `${existing}${text}`;
      dom.noteInput.value = candidate.review.note;
    });
    addAudit("note_template", "添加备注", candidate.id);
    renderAll();
  }

  function saveAndNext() {
    syncFormToCandidate();
    stepCandidate(1);
  }

  function stepCandidate(delta) {
    const candidates = filteredCandidates();
    if (!candidates.length) return;
    const currentIndex = Math.max(0, candidates.findIndex((item) => item.id === state.selectedId));
    const next = candidates[(currentIndex + delta + candidates.length) % candidates.length];
    state.selectedId = next.id;
    fitViewToCandidate();
    renderAll();
  }

  function setViewDuration(value) {
    state.viewDuration = round1(value);
    fitViewToCandidate(false);
    renderAll();
  }

  function fitViewToCandidate(resetDuration = true) {
    const candidate = selectedCandidate();
    if (!candidate) return;
    if (resetDuration) state.viewDuration = 40;
    const start = candidate.review.adjusted_start_sec ?? candidate.start_sec;
    const end = candidate.review.adjusted_end_sec ?? candidate.end_sec;
    const center = (start + end) / 2;
    const record = currentRecord();
    state.viewStart = clamp(center - state.viewDuration * 0.38, 0, Math.max(0, record.duration_sec - state.viewDuration));
  }

  function resizeCanvases() {
    [dom.waveformCanvas, dom.timelineCanvas].forEach((canvas) => {
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    });
    drawWaveform();
    drawTimeline();
    updateHandles();
  }

  function drawWaveform() {
    const canvas = dom.waveformCanvas;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const hgt = rect.height;
    const candidate = selectedCandidate();
    if (!candidate || w <= 0 || hgt <= 0) return;

    ctx.clearRect(0, 0, w, hgt);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, hgt);

    const layout = waveformLayout(w, hgt);
    drawGrid(ctx, layout, candidate);

    const record = currentRecord();
    const rowH = layout.plotH / record.channels.length;
    record.channels.forEach((channel, index) => {
      const yCenter = layout.top + rowH * (index + 0.5);
      const color = channelColor(channel);
      ctx.strokeStyle = "#eef2ea";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(layout.left, yCenter);
      ctx.lineTo(layout.rightX, yCenter);
      ctx.stroke();

      ctx.fillStyle = "#2d352f";
      ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(channel, 18, yCenter + 4);

      ctx.strokeStyle = color;
      ctx.lineWidth = candidate.channels.includes(channel) ? 1.9 : 1.25;
      ctx.beginPath();
      const points = Math.max(260, Math.floor(w * 1.25));
      for (let i = 0; i <= points; i += 1) {
        const x = layout.left + (i / points) * layout.plotW;
        const t = timeFromX(x, layout);
        const value = waveformValue(channel, t, candidate);
        const scale = channel === "ACC" ? rowH * 0.18 : channel === "EMG" ? rowH * 0.2 : rowH * 0.28;
        const y = yCenter - value * scale;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.stroke();

      if (channel === "EMG" || channel === "ACC") {
        ctx.fillStyle = "rgba(104, 115, 107, 0.78)";
        ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
        const cue = channel === "EMG" ? emgLabel(candidate) : accLabel(candidate);
        ctx.fillText(cue, layout.rightX - 112, yCenter + 4);
      }
    });

    drawEventLabel(ctx, layout, candidate);
  }

  function drawGrid(ctx, layout, candidate) {
    ctx.strokeStyle = "#edf1ea";
    ctx.lineWidth = 1;
    ctx.fillStyle = "#68736b";
    ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
    for (let i = 0; i <= 8; i += 1) {
      const x = layout.left + (i / 8) * layout.plotW;
      const t = state.viewStart + (i / 8) * state.viewDuration;
      ctx.beginPath();
      ctx.moveTo(x, layout.top);
      ctx.lineTo(x, layout.bottomY);
      ctx.stroke();
      ctx.fillText(`${round1(t - candidate.peak_sec)}s`, x - 14, layout.bottomY + 26);
    }
    ctx.strokeStyle = "#dce2d7";
    ctx.beginPath();
    ctx.rect(layout.left, layout.top, layout.plotW, layout.plotH);
    ctx.stroke();
  }

  function drawEventLabel(ctx, layout, candidate) {
    const start = candidate.review.adjusted_start_sec ?? candidate.start_sec;
    const end = candidate.review.adjusted_end_sec ?? candidate.end_sec;
    const x1 = xFromTime(start, layout);
    const x2 = xFromTime(end, layout);
    ctx.fillStyle = "rgba(178, 65, 61, 0.1)";
    ctx.fillRect(x1, layout.top, Math.max(3, x2 - x1), layout.plotH);
    ctx.strokeStyle = "rgba(178, 65, 61, 0.75)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x1, layout.top);
    ctx.lineTo(x1, layout.bottomY);
    ctx.moveTo(x2, layout.top);
    ctx.lineTo(x2, layout.bottomY);
    ctx.stroke();

    ctx.fillStyle = "#18201c";
    ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
    ctx.fillText(`${candidate.id} · ${round1(end - start)}s · score ${Math.round(candidate.score * 100)}%`, layout.left, 25);
    ctx.fillStyle = "#68736b";
    ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
    ctx.fillText(`${candidate.qc_hint} · ${candidate.channels.join("/")}`, layout.left, 43);
  }

  function drawTimeline() {
    const canvas = dom.timelineCanvas;
    const ctx = canvas.getContext("2d");
    const rect = canvas.getBoundingClientRect();
    const w = rect.width;
    const hgt = rect.height;
    const record = currentRecord();
    if (w <= 0 || hgt <= 0) return;
    ctx.clearRect(0, 0, w, hgt);
    ctx.fillStyle = "#f9faf6";
    ctx.fillRect(0, 0, w, hgt);

    const left = 54;
    const right = 18;
    const y = 42;
    const width = w - left - right;
    ctx.strokeStyle = "#cbd5c5";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(left, y);
    ctx.lineTo(left + width, y);
    ctx.stroke();

    ctx.fillStyle = "#68736b";
    ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
    for (let i = 0; i <= 7; i += 1) {
      const x = left + (i / 7) * width;
      const hour = (record.duration_sec / 3600) * (i / 7);
      ctx.fillText(`${hour.toFixed(0)}h`, x - 10, y + 32);
      ctx.strokeStyle = "#dce2d7";
      ctx.beginPath();
      ctx.moveTo(x, y - 8);
      ctx.lineTo(x, y + 8);
      ctx.stroke();
    }

    record.candidates.forEach((candidate) => {
      const x = left + (candidate.start_sec / record.duration_sec) * width;
      const color = candidate.review.status === "kept"
        ? "#2f7d55"
        : candidate.review.status === "excluded"
          ? "#b2413d"
          : candidate.review.status === "uncertain"
            ? "#a86513"
            : candidate.priority === "high"
              ? "#b2413d"
              : "#2f659f";
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(x, y, candidate.id === state.selectedId ? 6 : 4, 0, Math.PI * 2);
      ctx.fill();
    });

    const viewX = left + (state.viewStart / record.duration_sec) * width;
    const viewW = Math.max(8, (state.viewDuration / record.duration_sec) * width);
    ctx.strokeStyle = "#18201c";
    ctx.fillStyle = "rgba(24, 32, 28, 0.08)";
    ctx.lineWidth = 1.5;
    ctx.fillRect(viewX, y - 22, viewW, 44);
    ctx.strokeRect(viewX, y - 22, viewW, 44);

    ctx.fillStyle = "#18201c";
    ctx.font = "700 12px Inter, Microsoft YaHei, sans-serif";
    ctx.fillText("70h 记录概览", 14, 18);
  }

  function updateHandles() {
    const candidate = selectedCandidate();
    if (!candidate) return;
    const shell = dom.waveformCanvas.parentElement;
    const rect = dom.waveformCanvas.getBoundingClientRect();
    const layout = waveformLayout(rect.width, rect.height);
    const start = candidate.review.adjusted_start_sec ?? candidate.start_sec;
    const end = candidate.review.adjusted_end_sec ?? candidate.end_sec;
    const x1 = clamp(xFromTime(start, layout), layout.left, layout.rightX);
    const x2 = clamp(xFromTime(end, layout), layout.left, layout.rightX);
    const shellRect = shell.getBoundingClientRect();
    const canvasOffsetLeft = rect.left - shellRect.left;
    const left = canvasOffsetLeft + x1;
    const right = canvasOffsetLeft + x2;
    dom.eventBand.style.left = `${left}px`;
    dom.eventBand.style.width = `${Math.max(4, right - left)}px`;
    dom.startHandle.style.left = `${left}px`;
    dom.endHandle.style.left = `${right}px`;
  }

  function startDrag(event, handle) {
    const candidate = selectedCandidate();
    if (!candidate) return;
    event.preventDefault();
    state.drag = {
      handle,
      candidateId: candidate.id,
      before: snapshotCandidates(),
    };
    event.currentTarget.setPointerCapture?.(event.pointerId);
  }

  function onDragMove(event) {
    if (!state.drag) return;
    const candidate = selectedCandidate();
    if (!candidate || candidate.id !== state.drag.candidateId) return;
    const rect = dom.waveformCanvas.getBoundingClientRect();
    const layout = waveformLayout(rect.width, rect.height);
    const x = event.clientX - rect.left;
    const t = clamp(timeFromX(x, layout), state.viewStart, state.viewStart + state.viewDuration);
    const currentStart = candidate.review.adjusted_start_sec ?? candidate.start_sec;
    const currentEnd = candidate.review.adjusted_end_sec ?? candidate.end_sec;
    if (state.drag.handle === "start") {
      candidate.review.adjusted_start_sec = round1(Math.min(t, currentEnd - 0.2));
    } else {
      candidate.review.adjusted_end_sec = round1(Math.max(t, currentStart + 0.2));
    }
    renderReviewPanel();
    drawWaveform();
    drawTimeline();
    updateHandles();
  }

  function endDrag() {
    if (!state.drag) return;
    const candidate = selectedCandidate();
    if (candidate && candidate.id === state.drag.candidateId) {
      state.history.push({ label: "adjust_event_interval", before: state.drag.before });
      const start = candidate.review.adjusted_start_sec ?? candidate.start_sec;
      const end = candidate.review.adjusted_end_sec ?? candidate.end_sec;
      addAudit("adjust_event_interval", "拖动边界", `${candidate.id} · ${round1(start)}-${round1(end)}s`);
    }
    state.drag = null;
    renderAll();
  }

  function withHistory(label, mutator) {
    const before = snapshotCandidates();
    mutator();
    state.history.push({ label, before });
    if (state.history.length > 40) state.history.shift();
  }

  function undoLast() {
    const item = state.history.pop();
    if (!item) {
      showToast("没有可撤销操作");
      return;
    }
    currentRecord().candidates = item.before;
    if (!selectedCandidate()) state.selectedId = currentRecord().candidates[0]?.id || "";
    addAudit("undo", "撤销", item.label);
    fitViewToCandidate(false);
    renderAll();
  }

  function snapshotCandidates() {
    return JSON.parse(JSON.stringify(currentRecord().candidates));
  }

  function addAudit(type, label, detail) {
    state.audit.push({
      action_id: `epact_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`,
      type,
      label,
      detail,
      source: "epilepsy-review-preview",
      created_at: new Date().toISOString(),
    });
    if (state.audit.length > 80) state.audit.shift();
  }

  function reviewPayload() {
    const record = currentRecord();
    return {
      schema_version: CONTRACT_VERSION,
      review_session_schema_version: REVIEW_SESSION_VERSION,
      generated_at: new Date().toISOString(),
      non_medical_scope: "research_screening_support_only",
      record: {
        id: record.id,
        file_id: record.file_id,
        filename: record.filename,
        duration_sec: round1(record.duration_sec),
        sfreq: record.sfreq,
        channels: record.channels,
        source_path_hint: record.source_path_hint,
      },
      context: {
        workflow_id: record.model.workflow_id,
        task_id: "preview_local_task",
        input_file_id: record.file_id,
        data_preparation_plan_id: "preview_he_plan",
        data_preparation_revision: 1,
        data_preparation_contract_version: "preview.v1",
        source: "standalone_review_page",
      },
      model: record.model,
      summary: {
        auto_candidates: record.candidates.length,
        reviewed: record.candidates.filter((item) => item.review.status !== "unreviewed").length,
        confirmed: record.candidates.filter((item) => item.review.status === "kept").length,
        rejected: record.candidates.filter((item) => item.review.status === "excluded").length,
        needs_review: record.candidates.filter((item) => item.review.status === "uncertain").length,
      },
      event_reviews: Object.fromEntries(
        record.candidates.map((candidate) => [
          candidate.id,
          {
            event_id: candidate.id,
            status: STATUS_TO_BACKEND[candidate.review.status] || "unreviewed",
            note: candidate.review.note || "",
            reviewer: candidate.review.reviewer || "local-user",
            reviewed_at: candidate.review.reviewed_at,
            ui_review: candidate.review,
          },
        ]),
      ),
      reviewed_events: record.candidates.map((candidate) => {
        const start = candidate.review.adjusted_start_sec ?? candidate.start_sec;
        const end = candidate.review.adjusted_end_sec ?? candidate.end_sec;
        return {
          event_id: candidate.id,
          original_start_sec: candidate.start_sec,
          original_end_sec: candidate.end_sec,
          reviewed_start_sec: round1(start),
          reviewed_end_sec: round1(end),
          duration_sec: round1(end - start),
          ai_type: candidate.ai_type,
          reviewed_type: candidate.review.event_type,
          priority: candidate.priority,
          score: candidate.score,
          channels: candidate.channels,
          review_status: candidate.review.status,
          backend_status: STATUS_TO_BACKEND[candidate.review.status],
          evidence_grade: candidate.review.grade,
          artifact_reason: candidate.review.artifact_reason,
          include_in_report: candidate.review.include_in_report,
        };
      }),
      actions: state.audit,
    };
  }

  async function copyJson() {
    const text = JSON.stringify(reviewPayload(), null, 2);
    try {
      await navigator.clipboard.writeText(text);
      showToast("复核 JSON 已复制");
    } catch (error) {
      showToast("浏览器未允许复制，已改为下载");
      saveBlob(text, `${currentRecord().id}_epilepsy_review_preview.json`, "application/json;charset=utf-8");
    }
  }

  function exportJson() {
    const text = JSON.stringify(reviewPayload(), null, 2);
    saveBlob(text, `${currentRecord().id}_epilepsy_review_preview.json`, "application/json;charset=utf-8");
    showToast("复核 JSON 已导出");
  }

  function openReportPreview() {
    try {
      window.localStorage.setItem("qlanalyser.epilepsy.review_preview.latest", JSON.stringify(reviewPayload()));
    } catch {
      // The report page still has its sample fallback if localStorage is unavailable.
    }
    window.location.href = "./epilepsy-report-preview.html?source=review-preview";
  }

  function saveBlob(text, filename, type) {
    const blob = new Blob([text], { type });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  function showToast(message) {
    const existing = document.querySelector(".er-toast");
    existing?.remove();
    const toast = document.createElement("div");
    toast.className = "er-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.remove(), 2200);
  }

  function waveformLayout(w, hgt) {
    const left = 74;
    const right = 22;
    const top = 58;
    const bottom = 58;
    return {
      left,
      right,
      top,
      bottom,
      rightX: w - right,
      bottomY: hgt - bottom,
      plotW: Math.max(1, w - left - right),
      plotH: Math.max(1, hgt - top - bottom),
    };
  }

  function xFromTime(time, layout) {
    return layout.left + ((time - state.viewStart) / state.viewDuration) * layout.plotW;
  }

  function timeFromX(x, layout) {
    return state.viewStart + ((x - layout.left) / layout.plotW) * state.viewDuration;
  }

  function waveformValue(channel, t, candidate) {
    const seed = hash(`${candidate.id}:${channel}`);
    const base = Math.sin(t * 2.2 + seed) * 0.22 + Math.sin(t * 7.7 + seed * 0.21) * 0.08;
    const noise = Math.sin(t * 31.1 + seed * 1.7) * 0.035 + Math.sin(t * 53.3 + seed * 0.41) * 0.018;
    const start = candidate.review.adjusted_start_sec ?? candidate.start_sec;
    const end = candidate.review.adjusted_end_sec ?? candidate.end_sec;
    const center = (start + end) / 2;
    const inEvent = t >= start && t <= end;
    const envelope = Math.exp(-Math.pow((t - center) / Math.max(0.18, (end - start) / 2.4), 2));
    const isEvidenceChannel = candidate.channels.includes(channel);

    if (channel === "EMG") {
      const burst = candidate.ai_type === "artifact_suspect" ? 1.1 * envelope * (1 + Math.sin(t * 72) * 0.25) : 0.18 * envelope;
      return base * 0.45 + noise * 3.4 + burst;
    }
    if (channel === "ACC") {
      const motion = candidate.ai_type === "artifact_suspect" ? 1.05 * envelope + (inEvent ? Math.sin(t * 9.5) * 0.18 : 0) : 0.08 * envelope;
      return Math.sin(t * 0.34 + seed) * 0.28 + motion;
    }
    if (!isEvidenceChannel) return base + noise;

    if (candidate.ai_type === "seizure_like" || candidate.ai_type === "rhythmic") {
      const rhythm = inEvent ? Math.sin((t - start) * Math.PI * 7.5) * 0.88 * envelope : 0;
      const slow = envelope * 0.28;
      return base + noise + rhythm + slow;
    }
    if (candidate.ai_type === "artifact_suspect") {
      return base + noise + envelope * 0.45 + Math.sin(t * 45) * envelope * 0.18;
    }
    const spike = Math.exp(-Math.pow((t - center) / 0.045, 2)) * 1.45;
    const slowWave = -Math.exp(-Math.pow((t - (center + 0.22)) / 0.22, 2)) * 0.7;
    return base + noise + spike + slowWave;
  }

  function hash(text) {
    let value = 0;
    for (let i = 0; i < text.length; i += 1) value = (value * 31 + text.charCodeAt(i)) >>> 0;
    return value / 1000;
  }

  function channelColor(channel) {
    if (channel === "EMG") return "#a86513";
    if (channel === "ACC") return "#2f7d55";
    return channel === "EEG1" ? "#2f659f" : "#6f5aa8";
  }

  function emgLabel(candidate) {
    return candidate.emg_sync === "present" ? "EMG 同步" : "EMG 未同步";
  }

  function accLabel(candidate) {
    return candidate.acc_motion === "possible" ? "ACC 提示体动" : "ACC 稳定";
  }

  function priorityLabel(priority) {
    if (priority === "high") return "高";
    if (priority === "medium") return "中";
    return "低";
  }

  function formatDuration(seconds) {
    const hours = seconds / 3600;
    return `${hours.toFixed(1)} h`;
  }

  function formatClock(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const h24 = Math.floor(total / 3600);
    const min = Math.floor((total % 3600) / 60);
    const sec = total % 60;
    return `${String(h24).padStart(2, "0")}:${String(min).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
  }

  function formatAuditTime(iso) {
    const date = new Date(iso);
    return date.toLocaleTimeString("zh-CN", { hour12: false });
  }

  function round1(value) {
    return Math.round(Number(value) * 10) / 10;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  function h(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[char]));
  }

  function syncIcons() {
    if (window.lucide) window.lucide.createIcons();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
