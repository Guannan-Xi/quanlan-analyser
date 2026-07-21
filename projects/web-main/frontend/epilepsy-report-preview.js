(function () {
  "use strict";

  const REPORT_SCHEMA = "qlanalyser.epilepsy.report_preview.v1";
  const REVIEW_SCHEMA = "qlanalyser.epilepsy.manual_correction_preview.v1";
  const REVIEW_STORAGE_KEY = "qlanalyser.epilepsy.review_preview.latest";
  const API_BASE = resolveApiBase();
  const STATUS_LABEL = {
    confirmed: "纳入草稿候选",
    kept: "纳入草稿候选",
    rejected: "不纳入草稿",
    excluded: "不纳入草稿",
    needs_review: "存疑/需二次复核",
    uncertain: "存疑/需二次复核",
    unreviewed: "未复核",
  };
  const STATUS_ORDER = {
    confirmed: 0,
    kept: 0,
    needs_review: 1,
    uncertain: 1,
    unreviewed: 2,
    rejected: 3,
    excluded: 3,
  };
  const TYPE_LABEL = {
    ied: "棘波样候选",
    seizure_like: "节律性片段候选（待复核）",
    rhythmic: "节律性放电候选",
    artifact_suspect: "伪迹候选",
    candidate_window: "候选窗口 / 未分类",
    unknown: "未分类候选",
  };

  const state = {
    payload: emptyReviewPayload(),
  };

  const dom = {};

  function init() {
    cacheDom();
    hydrateFromReviewPreview();
    bindEvents();
    renderReport();
    updateReturnLink();
    resizeFigures();
    window.addEventListener("resize", resizeFigures);
    syncIcons();
  }

  function hydrateFromReviewPreview() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "1") {
      state.payload = sampleReviewPayload();
      return;
    }
    try {
      const raw = window.sessionStorage.getItem(REVIEW_STORAGE_KEY) || window.localStorage.getItem(REVIEW_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && (parsed.schema_version === REVIEW_SCHEMA || parsed.reviewed_events || parsed.all_reviewed_events || parsed.confirmed_events || parsed.event_reviews)) {
        state.payload = parsed;
      }
    } catch (error) {
      state.payload = emptyReviewPayload("复核记录无法自动读取。请重新从候选波形复核台打开，或手动载入复核记录。");
    }
  }

  function cacheDom() {
    [
      "reviewJsonInput",
      "returnFromReportBtn",
      "exportReportBtn",
      "copySummaryBtn",
      "copyMethodsBtn",
      "redrawBtn",
      "exportCsvBtn",
      "overallStatement",
      "recordName",
      "recordMeta",
      "confirmedMetric",
      "eventRateMetric",
      "pendingMetric",
      "coverageMetric",
      "coverageHint",
      "interpretationText",
      "dataMethodText",
      "reviewMethodText",
      "eventTableBody",
      "auditList",
      "contractLabel",
      "timelineFigure",
      "waveformFigure",
      "funnelFigure",
      "densityFigure",
      "qcFigure",
    ].forEach((id) => {
      dom[id] = document.getElementById(id);
    });
    dom.reportBanner = document.querySelector(".ep-report-banner");
  }

  function bindEvents() {
    dom.reviewJsonInput.addEventListener("change", loadReviewJson);
    dom.exportReportBtn.addEventListener("click", exportReportJson);
    dom.exportCsvBtn.addEventListener("click", exportEventsCsv);
    dom.copySummaryBtn.addEventListener("click", () => copyText(summaryText()));
    dom.copyMethodsBtn.addEventListener("click", () => copyText(methodsText()));
    dom.redrawBtn.addEventListener("click", resizeFigures);
    document.querySelectorAll(".ep-report-nav a").forEach((link) => {
      link.addEventListener("click", () => {
        document.querySelectorAll(".ep-report-nav a").forEach((item) => item.classList.toggle("is-active", item === link));
      });
    });
  }

  function updateReturnLink() {
    if (!dom.returnFromReportBtn) return;
    const params = new URLSearchParams(window.location.search);
    const source = params.get("source") || "";
    const target = source === "full-flow-preview"
      ? "./epilepsy-full-flow-preview.html"
      : "./epilepsy-review-preview.html";
    dom.returnFromReportBtn.href = linkedPreviewUrl(target, "report-preview");
    const label = dom.returnFromReportBtn.querySelector("span");
    if (label) label.textContent = source === "full-flow-preview" ? "返回全流程" : "返回复核";
  }

  async function loadReviewJson(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const raw = JSON.parse(text);
      const normalized = normalizePayload(raw);
      const validation = validatePayloadForStandaloneLoad(normalized);
      if (!validation.accepted) throw new Error(validation.reason);
      state.payload = normalized;
      persistReviewPayload(normalized);
      renderReport();
      resizeFigures();
      showToast(`已载入 ${file.name}`);
    } catch (error) {
      showToast("复核记录无法读取，请确认文件是本工作台导出的复核记录。");
    } finally {
      event.target.value = "";
    }
  }

  function normalizePayload(raw) {
    const record = raw.record || {};
    const preservedMetadata = raw.metadata || {};
    const eventSource = preservedMetadata.review_event_source || reviewEventSource(raw);
    const reviewedEvents = Array.isArray(raw.reviewed_events)
      ? raw.reviewed_events
      : eventSource ? raw[eventSource] : [];
    const eventReviews = raw.event_reviews || {};
    const events = reviewedEvents.map((item, index) => {
      const id = String(item.event_id || item.id || `event_${index + 1}`);
      const review = eventReviews[id] || {};
      const uiReview = review.ui_review || {};
      const status = normalizeStatus(item.backend_status || item.review_status || item.status || review.status || uiReview.status || "unreviewed");
      const originalStart = numberOr(item.original_start_sec, item.candidate_start_sec, item.start_sec, item.reviewed_start_sec, 0);
      const originalEnd = numberOr(item.original_end_sec, item.candidate_end_sec, item.end_sec, item.reviewed_end_sec, originalStart + numberOr(item.duration_sec, 1));
      const start = numberOr(item.reviewed_start_sec, item.start_sec, item.original_start_sec, 0);
      const end = numberOr(item.reviewed_end_sec, item.end_sec, item.original_end_sec, start + numberOr(item.duration_sec, 1));
      return {
        event_id: id,
        original_start_sec: round1(originalStart),
        original_end_sec: round1(Math.max(originalEnd, originalStart + 0.1)),
        start_sec: round1(start),
        end_sec: round1(Math.max(end, start + 0.1)),
        duration_sec: round1(Math.max(0.1, end - start)),
        event_type: normalizeEventType(item.reviewed_type || item.event_type || uiReview.event_type || item.ai_type),
        channels: Array.isArray(item.channels) ? item.channels : splitChannels(item.channels),
        evidence_grade: item.evidence_grade || uiReview.grade || "C",
        artifact_reason: item.artifact_reason || uiReview.artifact_reason || "",
        status,
        preview_rms_ptp_rank_score: Number(item.preview_rms_ptp_rank_score || item.score || 0),
        score_kind: item.score_kind || "preview_rank_not_probability",
        score_note: item.score_note || "复核优先级排序值不是候选为真实事件的概率或检测置信度。",
        note: item.note || review.note || uiReview.note || "",
        reviewer: item.reviewer || review.reviewer || uiReview.reviewer || "",
        evidence_window: item.evidence_window || null,
        reviewed_at: item.reviewed_at || review.reviewed_at || uiReview.reviewed_at || "",
        source_artifact_id: item.source_artifact_id || item.source_algorithm_artifact_id || "",
        window_id: item.window_id || item.evidence_window_id || "",
      };
    });
    const explicitDenominator = explicitCandidateDenominator(raw);
    const hasFullCandidateSet = typeof preservedMetadata.has_full_candidate_set === "boolean"
      ? preservedMetadata.has_full_candidate_set
      : false;
    const hasExplicitCandidateDenominator = typeof preservedMetadata.has_explicit_candidate_denominator === "boolean"
      ? preservedMetadata.has_explicit_candidate_denominator
      : Number.isFinite(explicitDenominator);
    const preservedDenominator = Number(preservedMetadata.candidate_denominator);
    const candidateDenominator = Math.max(
      events.length,
      Number.isFinite(preservedDenominator) ? preservedDenominator : events.length,
      hasExplicitCandidateDenominator ? explicitDenominator : events.length,
    );
    return {
      schema_version: raw.schema_version || REVIEW_SCHEMA,
      generated_at: raw.generated_at || new Date().toISOString(),
      non_medical_scope: raw.non_medical_scope || "research_screening_support_only",
      metadata: {
        ...preservedMetadata,
        review_event_source: eventSource || "none",
        has_full_candidate_set: hasFullCandidateSet,
        has_explicit_candidate_denominator: hasExplicitCandidateDenominator,
        candidate_denominator: candidateDenominator,
        candidate_set_scope: preservedMetadata.candidate_set_scope || (hasFullCandidateSet ? "current_preview_candidate_package" : "unknown"),
        denominator_note: hasFullCandidateSet
          ? "复核记录包含当前已载入的预览候选包；这不是完整检测器的全记录负荷估计。"
          : hasExplicitCandidateDenominator
            ? "复核记录提供了候选总数，但候选明细可能不是完整列表。"
            : "候选总数未知，当前记录不能作为可下载复核草稿。",
      },
      record: {
        id: record.id || record.file_id || "unknown_record",
        file_id: record.file_id || "",
        filename: record.filename || record.file_name || "未命名记录",
        duration_sec: numberOr(record.duration_sec, 0),
        sfreq: numberOr(record.sfreq, 0),
        channels: Array.isArray(record.channels) ? record.channels : ["EEG1", "EEG2", "EMG", "ACC"],
      },
      context: raw.context || {},
      model: raw.model || {},
      backend_review_session: raw.backend_review_session || null,
      reviewed_events: events,
      actions: Array.isArray(raw.actions) ? raw.actions : [],
    };
  }

  function reviewEventSource(raw) {
    if (Array.isArray(raw.reviewed_events)) return "reviewed_events";
    if (Array.isArray(raw.all_reviewed_events)) return "all_reviewed_events";
    if (Array.isArray(raw.confirmed_events)) return "confirmed_events";
    return "";
  }

  function explicitCandidateDenominator(raw) {
    const candidates = [
      raw.candidate_denominator,
      raw.total_candidates,
      raw.candidate_count,
      raw.summary?.auto_candidates,
      raw.summary?.total,
      raw.summary?.candidate_count,
    ];
    for (const value of candidates) {
      const number = Number(value);
      if (Number.isFinite(number) && number >= 0) return number;
    }
    return NaN;
  }

  function normalizeEventType(type) {
    const value = String(type || "candidate_window");
    if (value === "candidate_window" || value === "unknown" || !TYPE_LABEL[value]) return "candidate_window";
    return value;
  }

  function validatePayloadForStandaloneLoad(payload) {
    if (!payload.reviewed_events.length) {
      return { accepted: false, reason: "复核记录为空，不能生成复核草稿。" };
    }
    return { accepted: true, reason: "" };
  }

  function persistReviewPayload(payload) {
    try {
      window.sessionStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(payload));
      window.localStorage.setItem(REVIEW_STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // Returning to the review page may fall back to its built-in sample if storage is blocked.
    }
  }

  function renderReport() {
    state.payload = normalizePayload(state.payload);
    renderSummary();
    renderTexts();
    renderEventTable();
    renderAudit();
    renderExportState();
    syncIcons();
  }

  function renderSummary() {
    const payload = state.payload;
    const record = payload.record;
    const events = payload.reviewed_events;
    const stats = eventStats(events, payload);
    const hours = Math.max(0.01, record.duration_sec / 3600);
    dom.recordName.textContent = record.filename || "-";
    dom.recordMeta.textContent = `${hours.toFixed(1)} h · ${record.sfreq || "-"} Hz · ${record.channels.join(" / ")}`;
    dom.confirmedMetric.textContent = String(stats.confirmed);
    dom.eventRateMetric.textContent = `${(stats.confirmed / hours).toFixed(3)} 纳入草稿候选/小时（预览值，非发作频率）`;
    dom.pendingMetric.textContent = `${stats.needsReview + stats.unreviewed}`;
    dom.coverageMetric.textContent = `${Math.round((stats.reviewed / Math.max(1, stats.total)) * 100)}%`;
    dom.coverageHint.textContent = stats.implicitUnreviewed > 0
      ? `${stats.reviewed}/${stats.total} 候选已有人工状态，另有 ${stats.implicitUnreviewed} 个候选未载入`
      : `${stats.reviewed}/${stats.total} 候选已有人工状态`;
    const status = reportStatus();
    const candidateSetKnown = Boolean(payload.metadata?.has_full_candidate_set || payload.metadata?.has_explicit_candidate_denominator);
    dom.overallStatement.textContent = status === "complete_review_preview"
      ? "候选复核已覆盖当前预览候选包；当前图表仍为预览示意。"
      : status === "not_ready"
        ? (events.length
          ? "已显示候选复核表，但缺少当前候选包分母，不能下载复核草稿数据。"
          : (payload.metadata?.empty_reason || "复核记录为空，不能输出草稿数据。"))
        : candidateSetKnown
          ? "部分复核草稿，仍含待确认或未复核候选。"
          : "部分复核草稿，且当前候选包分母仍需确认。";
    dom.contractLabel.textContent = "复核草稿";
  }

  function renderExportState() {
    const canExport = canExportReportDraft();
    dom.exportReportBtn.disabled = !canExport;
    dom.exportCsvBtn.disabled = !state.payload.reviewed_events.length;
    dom.exportReportBtn.querySelector("span").textContent = canExport ? "下载复核草稿数据" : "复核草稿数据不可下载";
    dom.exportReportBtn.title = canExport
      ? "从后端导出当前复核草稿数据。"
      : "需要后端复核会话和真实 EDF 波形窗口证据后，才能下载复核草稿数据。";
    dom.exportCsvBtn.querySelector("span").textContent = canExport ? "导出候选复核表" : "导出当前候选复核表";
    dom.exportCsvBtn.title = dom.exportCsvBtn.disabled ? "复核记录为空，不能导出候选复核表。" : "导出当前候选复核表；文件头会标注草稿边界和候选包分母。";
    dom.reportBanner?.classList.toggle("is-blocked", !canExport);
  }

  function renderTexts() {
    dom.interpretationText.textContent = summaryText();
    dom.dataMethodText.textContent = dataMethodText();
    dom.reviewMethodText.textContent = reviewMethodText();
  }

  function renderEventTable() {
    const rows = [...state.payload.reviewed_events].sort((a, b) => {
      const status = (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9);
      if (status !== 0) return status;
      return a.start_sec - b.start_sec;
    });
    if (!rows.length) {
      dom.eventTableBody.innerHTML = `<tr><td colspan="8">尚未载入复核记录。请从复核工作台进入，或手动载入复核记录。</td></tr>`;
      return;
    }
    dom.eventTableBody.innerHTML = rows.map((event) => `
      <tr>
        <td><strong>${h(event.event_id)}</strong></td>
        <td>${h(timeRangeText(event.start_sec, event.end_sec))}<small>${h(event.duration_sec.toFixed(1))} s</small></td>
        <td>${h(timeRangeText(event.original_start_sec, event.original_end_sec))}</td>
        <td>${h(TYPE_LABEL[event.event_type] || event.event_type)}</td>
        <td>${h(event.channels.join(" / ") || "-")}</td>
        <td>${h(evidenceSummary(event))}</td>
        <td><span class="ep-status ${h(event.status)}">${h(STATUS_LABEL[event.status] || event.status)}</span></td>
        <td>${h(reviewTraceText(event))}</td>
      </tr>
    `).join("");
  }

  function timeRangeText(start, end) {
    if (!Number.isFinite(Number(start)) || !Number.isFinite(Number(end))) return "-";
    return `${formatClock(start)} - ${formatClock(end)}`;
  }

  function evidenceSummary(event) {
    const parts = [`证据 ${event.evidence_grade || "-"}`];
    if (event.artifact_reason) parts.push(artifactLabel(event.artifact_reason));
    if (event.note) parts.push(event.note);
    if (event.source_artifact_id) parts.push(`证据来源编号 ${event.source_artifact_id}`);
    if (event.window_id) parts.push(`窗口 ${event.window_id}`);
    return parts.join(" · ");
  }

  function reviewTraceText(event) {
    const reviewer = event.reviewer || "复核人待记录";
    const reviewedAt = event.reviewed_at ? formatAuditTime(event.reviewed_at) : "未记录时间";
    return `${reviewer} · ${reviewedAt}`;
  }

  function renderAudit() {
    const actions = state.payload.actions.slice(-6).reverse();
    if (!actions.length) {
      dom.auditList.innerHTML = `<article><strong>暂无操作记录</strong><span>载入正式复核记录后会显示追溯信息。</span></article>`;
      return;
    }
    dom.auditList.innerHTML = actions.map((item) => `
      <article>
        <strong>${h(item.label || actionLabel(item.type))}</strong>
        <span>${h(item.detail || item.note || item.type || "-")}</span>
        <span>${h(formatAuditTime(item.created_at))}</span>
      </article>
    `).join("");
  }

  function resizeFigures() {
    ["timelineFigure", "waveformFigure", "funnelFigure", "densityFigure", "qcFigure"].forEach((id) => {
      const canvas = dom[id];
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.round(rect.width * dpr));
      canvas.height = Math.max(1, Math.round(rect.height * dpr));
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    });
    drawFigures();
  }

  function drawFigures() {
    drawTimeline(dom.timelineFigure);
    drawWaveform(dom.waveformFigure);
    drawFunnel(dom.funnelFigure);
    drawDensity(dom.densityFigure);
    drawQc(dom.qcFigure);
  }

  function drawTimeline(canvas) {
    const ctx = context(canvas);
    const { w, h: height } = canvasSize(canvas);
    const payload = state.payload;
    const duration = Math.max(1, payload.record.duration_sec);
    clearFigure(ctx, w, height);
    const left = 62;
    const right = 28;
    const top = 48;
    const rowGap = 38;
    const plotW = w - left - right;
    const rows = [
      ["confirmed", "纳入草稿"],
      ["rejected", "不纳入"],
      ["needs_review", "存疑/需二次复核"],
      ["unreviewed", "未复核"],
    ];
    ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
    ctx.fillStyle = "#17201b";
    ctx.fillText("当前候选包时间轴", left, 24);
    rows.forEach(([status, label], row) => {
      const y = top + row * rowGap;
      ctx.fillStyle = "#66746d";
      ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(label, 10, y + 4);
      ctx.strokeStyle = "#dce4df";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(left + plotW, y);
      ctx.stroke();
      payload.reviewed_events.filter((event) => event.status === status || (status === "confirmed" && event.status === "kept") || (status === "rejected" && event.status === "excluded") || (status === "needs_review" && event.status === "uncertain")).forEach((event) => {
        const x = left + (event.start_sec / duration) * plotW;
        ctx.fillStyle = statusColor(event.status);
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fill();
      });
    });
    ctx.fillStyle = "#66746d";
    ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
    for (let i = 0; i <= 7; i += 1) {
      const x = left + (i / 7) * plotW;
      ctx.fillText(`${((duration / 3600) * (i / 7)).toFixed(0)}h`, x - 9, height - 18);
      ctx.strokeStyle = "#eef2ef";
      ctx.beginPath();
      ctx.moveTo(x, top - 16);
      ctx.lineTo(x, top + rowGap * (rows.length - 1) + 16);
      ctx.stroke();
    }
  }

  function drawWaveform(canvas) {
    const ctx = context(canvas);
    const { w, h: height } = canvasSize(canvas);
    clearFigure(ctx, w, height);
    const event = representativeEvent();
    if (!event) {
      centerText(ctx, w, height, "暂无纳入草稿候选");
      return;
    }
    const channels = state.payload.record.channels.slice(0, 4);
    const left = 66;
    const right = 22;
    const top = 42;
    const bottom = 36;
    const plotW = w - left - right;
    const plotH = height - top - bottom;
    const rowH = plotH / channels.length;
    const windowStart = event.start_sec - 8;
    const windowDur = Math.max(20, event.duration_sec + 18);
    const eventX1 = left + ((event.start_sec - windowStart) / windowDur) * plotW;
    const eventX2 = left + ((event.end_sec - windowStart) / windowDur) * plotW;
    ctx.fillStyle = "rgba(178, 65, 61, 0.1)";
    ctx.fillRect(eventX1, top, Math.max(3, eventX2 - eventX1), plotH);
    ctx.strokeStyle = "rgba(178, 65, 61, 0.68)";
    ctx.beginPath();
    ctx.moveTo(eventX1, top);
    ctx.lineTo(eventX1, top + plotH);
    ctx.moveTo(eventX2, top);
    ctx.lineTo(eventX2, top + plotH);
    ctx.stroke();
    ctx.fillStyle = "#17201b";
    ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(`代表候选 ${event.event_id}`, left, 23);
    channels.forEach((channel, index) => {
      const y = top + rowH * (index + 0.5);
      ctx.strokeStyle = "#eef2ef";
      ctx.beginPath();
      ctx.moveTo(left, y);
      ctx.lineTo(left + plotW, y);
      ctx.stroke();
      ctx.fillStyle = "#253029";
      ctx.font = "700 12px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(channel, 14, y + 4);
      ctx.strokeStyle = channelColor(channel);
      ctx.lineWidth = event.channels.includes(channel) ? 1.8 : 1.15;
      ctx.beginPath();
      const points = Math.max(220, Math.round(w));
      for (let i = 0; i <= points; i += 1) {
        const x = left + (i / points) * plotW;
        const t = windowStart + (i / points) * windowDur;
        const value = waveformValue(channel, t, event);
        const yPoint = y - value * rowH * (channel === "ACC" ? 0.18 : channel === "EMG" ? 0.2 : 0.27);
        if (i === 0) ctx.moveTo(x, yPoint);
        else ctx.lineTo(x, yPoint);
      }
      ctx.stroke();
    });
  }

  function drawFunnel(canvas) {
    const ctx = context(canvas);
    const { w, h: height } = canvasSize(canvas);
    const stats = eventStats(state.payload.reviewed_events, state.payload);
    clearFigure(ctx, w, height);
    const rows = [
      ["候选片段", stats.total, "#2f659f"],
      ["已有人工状态", stats.reviewed, "#6f5aa8"],
      ["纳入草稿", stats.confirmed, "#2f7d55"],
      ["不纳入", stats.rejected, "#b2413d"],
      ["存疑/需二次复核", stats.needsReview, "#a86513"],
    ];
    const max = Math.max(1, ...rows.map((item) => item[1]));
    const left = 92;
    const right = 30;
    const top = 42;
    const barH = 28;
    const gap = 18;
    ctx.fillStyle = "#17201b";
    ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
    ctx.fillText("复核漏斗", left, 23);
    rows.forEach(([label, value, color], index) => {
      const y = top + index * (barH + gap);
      const width = ((w - left - right) * value) / max;
      ctx.fillStyle = "#66746d";
      ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(label, 18, y + 19);
      ctx.fillStyle = "#eef2ef";
      roundRect(ctx, left, y, w - left - right, barH, 6);
      ctx.fill();
      ctx.fillStyle = color;
      roundRect(ctx, left, y, Math.max(4, width), barH, 6);
      ctx.fill();
      ctx.fillStyle = "#17201b";
      ctx.font = "700 12px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(String(value), left + Math.max(8, width) + 8, y + 19);
    });
  }

  function drawDensity(canvas) {
    const ctx = context(canvas);
    const { w, h: height } = canvasSize(canvas);
    clearFigure(ctx, w, height);
    const record = state.payload.record;
    const durationH = Math.max(1, Math.ceil(record.duration_sec / 3600));
    const bucketCount = Math.min(14, Math.max(7, Math.ceil(durationH / 6)));
    const buckets = Array.from({ length: bucketCount }, () => 0);
    confirmedEvents().forEach((event) => {
      const index = Math.min(bucketCount - 1, Math.floor((event.start_sec / Math.max(1, record.duration_sec)) * bucketCount));
      buckets[index] += 1;
    });
    const max = Math.max(1, ...buckets);
    const left = 42;
    const right = 18;
    const top = 42;
    const bottom = 38;
    const plotW = w - left - right;
    const plotH = height - top - bottom;
    ctx.fillStyle = "#17201b";
    ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
    ctx.fillText("纳入草稿的候选数（预览）", left, 23);
    ctx.strokeStyle = "#dce4df";
    ctx.beginPath();
    ctx.moveTo(left, top);
    ctx.lineTo(left, top + plotH);
    ctx.lineTo(left + plotW, top + plotH);
    ctx.stroke();
    buckets.forEach((value, index) => {
      const bw = plotW / bucketCount;
      const x = left + index * bw + 5;
      const barH = (plotH * value) / max;
      ctx.fillStyle = "#2f7d55";
      roundRect(ctx, x, top + plotH - barH, Math.max(5, bw - 10), barH, 5);
      ctx.fill();
      ctx.fillStyle = "#66746d";
      ctx.font = "11px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(String(value), x + Math.max(5, bw - 10) / 2 - 3, top + plotH - barH - 6);
    });
  }

  function drawQc(canvas) {
    const ctx = context(canvas);
    const { w, h: height } = canvasSize(canvas);
    clearFigure(ctx, w, height);
    const channels = state.payload.record.channels;
    const confirmed = confirmedEvents();
    const counts = channels.map((channel) => confirmed.filter((event) => event.channels.includes(channel)).length);
    const max = Math.max(1, ...counts);
    const left = 72;
    const right = 30;
    const top = 46;
    const barH = 30;
    const gap = 22;
    ctx.fillStyle = "#17201b";
    ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
    ctx.fillText("通道参与概览", left, 23);
    channels.forEach((channel, index) => {
      const y = top + index * (barH + gap);
      const width = ((w - left - right) * counts[index]) / max;
      ctx.fillStyle = "#66746d";
      ctx.font = "700 12px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(channel, 20, y + 20);
      ctx.fillStyle = "#eef2ef";
      roundRect(ctx, left, y, w - left - right, barH, 6);
      ctx.fill();
      ctx.fillStyle = channelColor(channel);
      roundRect(ctx, left, y, Math.max(4, width), barH, 6);
      ctx.fill();
      ctx.fillStyle = "#17201b";
      ctx.font = "12px Inter, Microsoft YaHei, sans-serif";
      ctx.fillText(`${counts[index]} 个`, left + Math.max(8, width) + 8, y + 20);
    });
  }

  function reportPayload() {
    const payload = state.payload;
    const stats = eventStats(payload.reviewed_events, payload);
    return {
      schema_version: REPORT_SCHEMA,
      generated_at: new Date().toISOString(),
      source_review_schema_version: payload.schema_version,
      non_medical_scope: payload.non_medical_scope,
      record: payload.record,
      summary: {
        auto_candidates: stats.total,
        reviewed: stats.reviewed,
        confirmed: stats.confirmed,
        rejected: stats.rejected,
        needs_review: stats.needsReview,
        unreviewed: stats.unreviewed,
        candidate_denominator: stats.total,
        confirmed_candidates_per_record_hour_preview: Number((stats.confirmed / Math.max(0.01, payload.record.duration_sec / 3600)).toFixed(4)),
        report_status: reportStatus(),
      },
      interpretation: summaryText(),
      methods: methodsText(),
      methods_structured: methodsStructured(),
      figure_manifest: figureManifest(),
      report_readiness: reportReadiness(),
      provenance: provenanceManifest(),
      confirmed_events: confirmedEvents(),
      all_reviewed_events: payload.reviewed_events,
      actions: payload.actions,
      research_draft: researchDraft(),
    };
  }

  function customerReportPackage() {
    const payload = reportPayload();
    const record = payload.record || {};
    const summary = payload.summary || {};
    return {
      草稿类型: "癫痫样候选窗口复核草稿",
      生成时间: payload.generated_at,
      使用边界: "仅用于科研筛查和人工复核支持；不作为诊疗或用药依据。",
      记录: {
        文件名: record.filename || "",
        记录时长秒: record.duration_sec || 0,
        采样率Hz: record.sfreq || "",
        通道: record.channels || [],
      },
      摘要: {
        候选总数: summary.auto_candidates || 0,
        已有人工状态: summary.reviewed || 0,
        纳入草稿候选: summary.confirmed || 0,
        不纳入草稿候选: summary.rejected || 0,
        "存疑/需二次复核": summary.needs_review || 0,
        未复核: summary.unreviewed || 0,
        草稿状态: reportStatusLabel(summary.report_status),
        纳入草稿候选数每记录小时: summary.confirmed_candidates_per_record_hour_preview || 0,
      },
      复核摘要: payload.interpretation,
      方法与限制: payload.methods,
      候选复核表: payload.all_reviewed_events.map(customerReportEventRow),
      图表说明: figureManifest().map((figure) => ({
        图表: figure.title,
        来源: figure.source === "合成预览波形" ? "版式示意" : "复核草稿",
        限制: figure.limitation || figure.provenance || "",
      })),
      追溯: {
        复核草稿状态: reportStatusLabel(summary.report_status),
        当前候选包说明: state.payload.metadata?.denominator_note || "",
        正式报告就绪: "否，仍需真实 EDF 波形窗口、图表复核和正式报告审核。",
      },
    };
  }

  function customerReportEventRow(event) {
    return {
      候选编号: event.event_id,
      复核状态: STATUS_LABEL[event.status] || event.status,
      复核起始秒: event.start_sec,
      复核结束秒: event.end_sec,
      原始候选起始秒: event.original_start_sec,
      原始候选结束秒: event.original_end_sec,
      候选类型: TYPE_LABEL[event.event_type] || event.event_type,
      通道: event.channels,
      证据强度评级: event.evidence_grade,
      伪迹原因: artifactLabel(event.artifact_reason),
      复核优先级: priorityLabel(event.priority),
      复核备注: event.note || "",
      复核人: event.reviewer || "复核人待记录",
      复核时间: event.reviewed_at || "",
    };
  }

  function reportStatusLabel(status) {
    return {
      complete_review_preview: "当前候选包人工状态已覆盖，仍为研究草稿",
      partial_review_draft: "部分复核草稿",
      review_draft_ready: "复核草稿",
      not_ready: "尚不能生成草稿",
    }[status] || status || "未记录";
  }

  async function exportReportJson() {
    if (!canExportReportDraft()) {
      showToast("缺少后端复核会话或真实 EDF 波形窗口证据，不能下载复核草稿数据。");
      renderExportState();
      return;
    }
    try {
      const sessionId = encodeURIComponent(state.payload.backend_review_session.session_id);
      const [exportPackage, reportPackage] = await Promise.all([
        apiFetch(`/lab/epilepsy-full-flow/review-sessions/${sessionId}/exports`, { method: "POST" }),
        apiFetch(`/lab/epilepsy-full-flow/review-sessions/${sessionId}/report`),
      ]);
      if (exportPackage?.evidence_ready !== true || reportPackage?.report_readiness?.figure_evidence_ready !== true) {
        throw new Error("backend_waveform_evidence_not_ready");
      }
      const payload = {
        ...customerReportPackage(),
        schema_version: exportPackage.schema_version,
        export_source: "backend_review_session_export",
        session_id: exportPackage.session_id,
        exported_at: exportPackage.exported_at,
        generated_at: exportPackage.generated_at,
        non_medical_scope: exportPackage.non_medical_scope,
        evidence_ready: exportPackage.evidence_ready === true,
        manifest: exportPackage.manifest || exportPackage.export_manifest_json || reportPackage.export_manifest_json,
        summary_json: exportPackage.summary_json,
        scope_contract_json: exportPackage.scope_contract_json,
        model_manifest_json: exportPackage.model_manifest_json,
        review_revision_json: exportPackage.review_revision_json,
        input_data_manifest: exportPackage.input_data_manifest,
        scan_parameters: exportPackage.scan_parameters,
        qc_manifest: exportPackage.qc_manifest,
        event_evidence_manifest: exportPackage.event_evidence_manifest,
        figure_manifest: exportPackage.figure_manifest || reportPackage.figure_manifest,
      };
      saveBlob(JSON.stringify(payload, null, 2), exportFilename("epilepsy_review_draft", "json", exportPackage.session_id), "application/json;charset=utf-8");
      showToast("复核草稿数据已下载");
    } catch (error) {
      showToast("后端草稿材料生成失败，不能回退下载本地草稿。");
    }
  }

  async function exportEventsCsv() {
    const rows = state.payload.reviewed_events;
    if (!rows.length) {
      showToast("复核记录为空，不能导出候选复核表。");
      renderExportState();
      return;
    }
    if (!state.payload.backend_review_session?.session_id) {
      showToast("缺少后端复核会话，不能导出可追溯候选复核表。");
      renderExportState();
      return;
    }
    try {
      const sessionId = encodeURIComponent(state.payload.backend_review_session.session_id);
      const exportPackage = await apiFetch(`/lab/epilepsy-full-flow/review-sessions/${sessionId}/exports`, { method: "POST" });
      if (exportPackage?.evidence_ready !== true) throw new Error("backend_waveform_evidence_not_ready");
      const csv = exportPackage?.candidate_review_state_csv || exportPackage?.draft_included_candidates_csv || exportPackage?.final_review_events_csv;
      if (!csv) throw new Error("backend_csv_missing");
      saveBlob(csv, exportFilename("epilepsy_review_candidates", "csv", exportPackage.session_id), "text/csv;charset=utf-8");
      showToast("候选复核表已导出");
      return;
    } catch (error) {
      showToast("后端候选复核表生成失败，不能回退下载本地候选复核表。");
      return;
    }
    const columns = [
      ["候选编号", "event_id"],
      ["复核起始秒", "start_sec"],
      ["复核结束秒", "end_sec"],
      ["原始起始秒", "original_start_sec"],
      ["原始结束秒", "original_end_sec"],
      ["时长秒", "duration_sec"],
      ["候选类型", (row) => TYPE_LABEL[row.event_type] || row.event_type || ""],
      ["通道", "channels"],
      ["证据强度评级", "evidence_grade"],
      ["伪迹原因", (row) => artifactLabel(row.artifact_reason)],
      ["人工状态", (row) => STATUS_LABEL[row.status] || row.status || ""],
      ["复核优先级", (row) => priorityLabel(row.priority)],
      ["复核备注", "note"],
      ["复核人", "reviewer"],
      ["复核时间", "reviewed_at"],
      ["证据来源编号", "source_artifact_id"],
      ["窗口编号", "window_id"],
    ];
    const prelude = [
      ["文件说明", "当前候选复核表来自候选窗口复核草稿，不是正式报告，也不作为诊疗依据。"],
      ["草稿状态", reportStatusLabel(reportStatus())],
      ["候选包说明", state.payload.metadata?.denominator_note || "当前候选包分母未记录。"],
      ["候选总数", String(eventStats(rows, state.payload).total)],
      [],
    ];
    const csv = [
      ...prelude.map((row) => row.map(csvEscape).join(",")),
      columns.map(([header]) => header).join(","),
      ...rows.map((row) => columns.map(([, key]) => {
        const value = typeof key === "function" ? key(row) : row[key];
        return csvEscape(Array.isArray(value) ? value.join(";") : value);
      }).join(",")),
    ].join("\r\n");
    saveBlob(`\ufeff${csv}`, `${state.payload.record.id || "epilepsy"}_候选复核表.csv`, "text/csv;charset=utf-8");
    showToast("候选复核表已导出");
  }

  function summaryText() {
    const payload = state.payload;
    const stats = eventStats(payload.reviewed_events, payload);
    const hours = Math.max(0.01, payload.record.duration_sec / 3600);
    const rate = (stats.confirmed / hours).toFixed(3);
    const pending = stats.needsReview + stats.unreviewed;
    if (!stats.total) return "当前复核记录为空，不能生成复核草稿摘要。";
    const completenessText = state.payload.metadata.has_full_candidate_set
      ? "当前预览候选包已随复核记录载入"
      : state.payload.metadata.has_explicit_candidate_denominator
        ? "候选总数来自记录中的显式分母，但候选明细可能不完整"
        : "候选总数未知，不能视为完整复核";
    if (stats.confirmed === 0) {
      return `在 ${payload.record.filename} 的 ${hours.toFixed(1)} 小时记录中，当前未形成可纳入草稿统计的候选。${completenessText}；共有 ${pending} 个候选仍需确认或复核，不能作为确认或排除发作的依据。`;
    }
    return `在 ${payload.record.filename} 的 ${hours.toFixed(1)} 小时记录中，当前预览候选包包含 ${stats.total} 个候选片段；经人工复核后，${stats.confirmed} 个候选被纳入草稿。纳入草稿候选数按记录小时归一化约 ${rate}/小时，仅为预览值，不表示发作频率、疾病活动度，也不代表全记录负荷估计。${stats.rejected} 个候选不纳入草稿，${pending} 个候选仍需确认或未复核。${completenessText}。`;
  }

  function dataMethodText() {
    const record = state.payload.record;
    const duration = Math.max(0, record.duration_sec / 3600).toFixed(1);
    return `输入记录为 ${record.filename}，总时长约 ${duration} 小时，采样率 ${record.sfreq || "-"} Hz，复核涉及通道为 ${record.channels.join("、")}。当前预览中的候选波形可能为版式示意；正式复核草稿必须使用真实 EDF 波形窗口，并在图注中标注窗口、单位、滤波和通道。`;
  }

  function reviewMethodText() {
    const model = state.payload.model || {};
    const methodText = model.detector_version || Number.isFinite(Number(model.threshold))
      ? "候选生成设置已随草稿保存，可用于追溯。"
      : "候选生成设置待正式记录。";
    return `候选片段先形成当前预览候选包，再由人工复核。${methodText} 人工复核记录候选状态、时间边界、证据强度评级、伪迹原因和操作记录。草稿只汇总人工复核后的结果，不把系统原始候选直接写成结论。证据等级 A/B/C/X 分别表示证据明确、较充分、较弱、不可判读；不纳入草稿的常见原因包括 EMG 增高、ACC 同步体动、电极问题、饱和和不可判读。`;
  }

  function methodsText() {
    return `${dataMethodText()}\n${reviewMethodText()}\n统计口径：仅“已复核纳入草稿”的候选进入草稿摘要、代表图及预览归一化统计；“不纳入草稿”的候选不参与统计；存疑或尚未复核的候选列为“待确认”。纳入草稿候选数按记录小时归一化只作为预览值，不代表发作频率、疾病活动度或全记录负荷估计。算法候选分数仅用于排序或复核优先级。局限性：当前数据缺少同步视频和外部人工标注；EMG/ACC 仅能辅助判断运动或肌电伪迹，不能单独确认候选性质；自动检测的敏感性和特异性需通过外部标注集进行验证。`;
  }

  function figureManifest() {
    const waveformReady = figureEvidenceReady();
    return [
      { id: "timelineFigure", title: "当前候选包时间轴", source: "reviewed_events", provenance: "derived_from_review_layer" },
      {
        id: "waveformFigure",
        title: waveformReady ? "代表候选真实 EDF 波形窗口" : "候选波形版式示意",
        source: waveformReady ? "真实 EDF 波形窗口" : "合成预览波形",
        provenance: waveformReady ? "review_payload.evidence_window" : "正式草稿需替换为真实 EDF 波形窗口",
        evidence_ready: waveformReady,
      },
      { id: "funnelFigure", title: "复核漏斗", source: "reviewed_events", provenance: "derived_from_review_layer" },
      { id: "densityFigure", title: "已复核纳入草稿的候选数（按记录小时归一化，预览值）", source: "confirmed_reviewed_candidates", provenance: "derived_from_review_layer", limitation: "该数值不表示发作频率、疾病活动度，也不代表全记录负荷估计。" },
      { id: "qcFigure", title: "通道参与概览", source: "confirmed_reviewed_events", provenance: "derived_from_review_layer" },
    ];
  }

  function provenanceManifest() {
    const context = state.payload.context || {};
    return {
      review_schema_version: state.payload.schema_version,
      workflow_id: context.workflow_id || state.payload.model?.workflow_id || "",
      task_id: context.task_id || "",
      input_file_id: context.input_file_id || state.payload.record.file_id || "",
      review_session_id: context.review_session_id || "",
      source_algorithm_artifact_id: context.source_algorithm_artifact_id || "",
      report_status: reportStatus(),
      source_completeness: {
        event_source: state.payload.metadata.review_event_source,
        has_full_candidate_set: state.payload.metadata.has_full_candidate_set,
        has_explicit_candidate_denominator: state.payload.metadata.has_explicit_candidate_denominator,
        candidate_denominator: state.payload.metadata.candidate_denominator,
        candidate_set_scope: state.payload.metadata.candidate_set_scope || "",
        note: state.payload.metadata.denominator_note,
      },
      report_readiness: reportReadiness(),
      waveform_provenance: "当前为合成预览；正式草稿需接入真实 EDF 波形窗口",
    };
  }

  function reportReadiness() {
    const metadata = state.payload.metadata || {};
    return {
      candidate_set_ready: Boolean(state.payload.reviewed_events.length && (metadata.has_full_candidate_set || metadata.has_explicit_candidate_denominator)),
      event_review_complete: reportStatus() === "complete_review_preview",
      figure_evidence_ready: figureEvidenceReady(),
      正式报告就绪: false,
      note: figureEvidenceReady()
        ? "当前复核草稿已包含真实 EDF 波形窗口证据清单；仍不是正式科研交付报告。"
        : "当前代表波形仍为版式示意或缺少真实 EDF 波形窗口，不能下载复核草稿数据。",
    };
  }

  function figureEvidenceReady() {
    const events = Array.isArray(state.payload.reviewed_events) ? state.payload.reviewed_events : [];
    if (!events.length) return false;
    return events.every((event) => eventHasRealWaveformEvidence(event));
  }

  function eventHasRealWaveformEvidence(event) {
    const windowInfo = event?.evidence_window || {};
    const windowChannels = Array.isArray(windowInfo.channels) && windowInfo.channels.length
      ? windowInfo.channels
      : event?.channels;
    const hasWindowCoordinates = Number.isFinite(Number(windowInfo.start_sec)) && Number(windowInfo.duration_sec) > 0;
    const hasWindowChannels = Array.isArray(windowChannels) && windowChannels.length > 0;
    const explicitRealWindow = windowInfo.source === "real_edf_window" || event?.source_artifact_id || event?.window_id;
    const backendVerifiedWindow = Boolean(
      state.payload.backend_review_session?.session_id
      && state.payload.record?.file_id
      && hasWindowCoordinates
      && hasWindowChannels
    );
    return Boolean(hasWindowCoordinates && hasWindowChannels && (explicitRealWindow || backendVerifiedWindow));
  }

  function methodsStructured() {
    const record = state.payload.record;
    const model = state.payload.model || {};
    return {
      input_record: {
        filename: record.filename,
        duration_sec: record.duration_sec,
        sfreq: record.sfreq,
        channels: record.channels,
      },
      preprocessing: {
        filter_profile: "预览草稿未记录；正式草稿需补充滤波设置。",
        reference: "预览草稿未记录；正式草稿需补充参考方式。",
        waveform_window_source: "当前为合成预览；正式草稿需接入真实 EDF 波形窗口",
      },
      candidate_generation: {
        workflow_id: state.payload.context?.workflow_id || model.workflow_id || "预览草稿未记录",
        detector_version: model.detector_version || "预览草稿未记录",
        threshold: Number.isFinite(Number(model.threshold)) ? Number(model.threshold) : "预览草稿未记录",
      },
      manual_review_mapping: {
        confirmed: "纳入草稿候选，进入草稿摘要和候选复核表。",
        rejected: "不纳入草稿候选，仅保留追溯。",
        needs_review: "存疑/需二次复核候选，不形成结论。",
        unreviewed: "未复核候选，不形成结论。",
      },
      evidence_grade_definition: {
        A: "明确",
        B: "较可信",
        C: "展示证据较弱",
        X: "不可判读",
      },
      statistics_policy: "仅纳入草稿候选进入预览归一化统计；该统计不是发作频率、疾病活动度或全记录负荷估计。",
      limitations: "无同步视频、无外部人工标注、无外部验证集指标；不能估计敏感性或特异性，也不能代表确认或排除发作。",
    };
  }

  function researchDraft() {
    return {
      title: `${state.payload.record.filename || "EEG"} 癫痫样候选窗口复核草稿`,
      abstract_like_summary: summaryText(),
      methods: methodsStructured(),
      figure_captions: figureManifest().map((figure) => ({
        id: figure.id,
        title: figure.title,
        provenance: figure.provenance,
        limitation: figure.limitation || (figure.evidence_ready === false ? "合成示意，不能作为正式 EEG 证据。" : ""),
      })),
      event_table: state.payload.reviewed_events,
      limitations: methodsStructured().limitations,
    };
  }

  function eventStats(events, payload = state.payload) {
    const candidateDenominator = Number(payload?.metadata?.candidate_denominator);
    const total = Math.max(events.length, Number.isFinite(candidateDenominator) ? candidateDenominator : events.length);
    const stats = { total, confirmed: 0, rejected: 0, needsReview: 0, unreviewed: 0, reviewed: 0, implicitUnreviewed: 0 };
    events.forEach((event) => {
      if (event.status === "confirmed" || event.status === "kept") stats.confirmed += 1;
      else if (event.status === "rejected" || event.status === "excluded") stats.rejected += 1;
      else if (event.status === "needs_review" || event.status === "uncertain") stats.needsReview += 1;
      else stats.unreviewed += 1;
    });
    stats.implicitUnreviewed = Math.max(0, stats.total - events.length);
    stats.unreviewed += stats.implicitUnreviewed;
    stats.reviewed = stats.confirmed + stats.rejected + stats.needsReview;
    return stats;
  }

  function reportStatus() {
    const stats = eventStats(state.payload.reviewed_events, state.payload);
    if (!state.payload.reviewed_events.length || !canExportReportDraft()) return "not_ready";
    if (stats.unreviewed > 0 || stats.needsReview > 0) return "partial_review_draft";
    return "complete_review_preview";
  }

  function canExportReportDraft() {
    const metadata = state.payload.metadata || {};
    const stats = eventStats(state.payload.reviewed_events, state.payload);
    return Boolean(
      state.payload.reviewed_events.length
      && stats.reviewed > 0
      && (metadata.has_full_candidate_set || metadata.has_explicit_candidate_denominator)
      && state.payload.backend_review_session?.session_id
      && figureEvidenceReady()
    );
  }

  function confirmedEvents() {
    return state.payload.reviewed_events.filter((event) => event.status === "confirmed" || event.status === "kept");
  }

  function representativeEvent() {
    return confirmedEvents().sort((a, b) => (b.preview_rms_ptp_rank_score || 0) - (a.preview_rms_ptp_rank_score || 0))[0] || state.payload.reviewed_events[0];
  }

  function normalizeStatus(status) {
    const value = String(status || "unreviewed");
    if (value === "kept") return "confirmed";
    if (value === "excluded") return "rejected";
    if (value === "uncertain") return "needs_review";
    if (["confirmed", "rejected", "needs_review", "unreviewed"].includes(value)) return value;
    return "unreviewed";
  }

  function sampleReviewPayload() {
    const duration = 69.78 * 3600;
    const events = [
      sampleEvent("HE105-E001", 858.4, 860.1, "confirmed", "ied", ["EEG1", "EEG2"], "A", "", 0.91, "双导同步尖慢波，EMG/ACC 未同步增高。"),
      sampleEvent("HE105-E002", 2526.2, 2529.7, "needs_review", "seizure_like", ["EEG1"], "B", "", 0.88, "短程节律增强，需要第二复核。"),
      sampleEvent("HE105-E003", 9071.5, 9073.0, "rejected", "artifact_suspect", ["EEG2"], "X", "motion_acc", 0.67, "EMG/ACC 同步，倾向体动伪迹。"),
      sampleEvent("HE105-E004", 18525.0, 18526.8, "confirmed", "ied", ["EEG1"], "B", "", 0.73, "单导尖波候选，形态较清晰。"),
      sampleEvent("HE105-E005", 39748.4, 39752.2, "needs_review", "rhythmic", ["EEG1", "EEG2"], "C", "", 0.61, "展示证据较弱的节律片段。"),
      sampleEvent("HE105-E006", 73029.1, 73031.8, "confirmed", "ied", ["EEG2"], "B", "", 0.84, "高幅尖慢波。"),
      sampleEvent("HE105-E007", 129784.6, 129787.4, "rejected", "artifact_suspect", ["EEG1", "EEG2"], "X", "motion_acc", 0.69, "体动同步疑似。"),
      sampleEvent("HE105-E008", 221559.3, 221560.4, "unreviewed", "ied", ["EEG1"], "C", "", 0.58, ""),
    ];
    return {
      schema_version: REVIEW_SCHEMA,
      generated_at: new Date().toISOString(),
      non_medical_scope: "research_screening_support_only",
      record: {
        id: "he-105",
        file_id: "local_he_105_edf",
        filename: "HE-105.edf",
        duration_sec: duration,
        sfreq: 1000,
        channels: ["EEG1", "EEG2", "EMG", "ACC"],
      },
      context: {
        workflow_id: "epilepsy_ml_xgboost",
        task_id: "preview_local_task",
        source: "standalone_report_page",
      },
      model: {
        workflow_id: "epilepsy_ml_xgboost",
        detector_version: "preview-local-he-v1",
        threshold: 0.72,
      },
      metadata: {
        review_event_source: "reviewed_events",
        has_full_candidate_set: true,
        has_explicit_candidate_denominator: true,
        candidate_denominator: events.length,
        candidate_set_scope: "current_preview_candidate_package",
        denominator_note: "示例记录包含当前已载入的预览候选包；这不是完整检测器的全记录负荷估计。",
      },
      reviewed_events: events,
      actions: [
        { type: "event_review", label: "纳入草稿", detail: "HE105-E001", created_at: new Date(Date.now() - 720000).toISOString() },
        { type: "event_review", label: "存疑/需二次复核", detail: "HE105-E002 · needs_review", created_at: new Date(Date.now() - 620000).toISOString() },
        { type: "adjust_event_interval", label: "调整边界", detail: "HE105-E004 · 18525.0-18526.8s", created_at: new Date(Date.now() - 420000).toISOString() },
        { type: "event_review", label: "不纳入草稿", detail: "HE105-E007 · 体动 / ACC 同步", created_at: new Date(Date.now() - 180000).toISOString() },
      ],
    };
  }

  function emptyReviewPayload(reason = "尚未载入复核记录。请从复核工作台进入，或手动载入复核记录。") {
    return {
      schema_version: REVIEW_SCHEMA,
      generated_at: new Date().toISOString(),
      non_medical_scope: "research_screening_support_only",
      metadata: {
        review_event_source: "none",
        has_full_candidate_set: false,
        has_explicit_candidate_denominator: false,
        candidate_denominator: 0,
        denominator_note: "尚未载入复核记录",
        empty_reason: reason,
      },
      record: {
        id: "empty-review",
        file_id: "",
        filename: "未载入复核记录",
        duration_sec: 0,
        sfreq: 0,
        channels: [],
      },
      context: {},
      model: {},
      reviewed_events: [],
      actions: [],
    };
  }

  function sampleEvent(id, start, end, status, eventType, channels, grade, artifactReason, score, note) {
    return {
      event_id: id,
      start_sec: start,
      end_sec: end,
      duration_sec: round1(end - start),
      event_type: eventType,
      channels,
      evidence_grade: grade,
      artifact_reason: artifactReason,
      status,
      score,
      note,
    };
  }

  function waveformValue(channel, t, event) {
    const seed = hash(`${event.event_id}:${channel}`);
    const base = Math.sin(t * 2.2 + seed) * 0.22 + Math.sin(t * 7.7 + seed * 0.21) * 0.08;
    const noise = Math.sin(t * 31.1 + seed * 1.7) * 0.035 + Math.sin(t * 53.3 + seed * 0.41) * 0.018;
    const center = (event.start_sec + event.end_sec) / 2;
    const envelope = Math.exp(-Math.pow((t - center) / Math.max(0.18, event.duration_sec / 2.4), 2));
    if (channel === "EMG") {
      const artifact = event.artifact_reason ? 1.0 * envelope * (1 + Math.sin(t * 70) * 0.2) : 0.15 * envelope;
      return base * 0.45 + noise * 3 + artifact;
    }
    if (channel === "ACC") {
      const motion = event.artifact_reason ? 1.05 * envelope : 0.08 * envelope;
      return Math.sin(t * 0.34 + seed) * 0.28 + motion;
    }
    if (!event.channels.includes(channel)) return base + noise;
    if (event.event_type === "seizure_like" || event.event_type === "rhythmic") {
      return base + noise + Math.sin((t - event.start_sec) * Math.PI * 7.2) * envelope * 0.8 + envelope * 0.2;
    }
    const spike = Math.exp(-Math.pow((t - center) / 0.045, 2)) * 1.35;
    const slowWave = -Math.exp(-Math.pow((t - (center + 0.22)) / 0.22, 2)) * 0.65;
    return base + noise + spike + slowWave;
  }

  function context(canvas) {
    return canvas.getContext("2d");
  }

  function canvasSize(canvas) {
    const rect = canvas.getBoundingClientRect();
    return { w: rect.width, h: rect.height };
  }

  function clearFigure(ctx, w, height) {
    ctx.clearRect(0, 0, w, height);
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, w, height);
  }

  function centerText(ctx, w, height, text) {
    ctx.fillStyle = "#66746d";
    ctx.font = "700 14px Inter, Microsoft YaHei, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(text, w / 2, height / 2);
    ctx.textAlign = "left";
  }

  function roundRect(ctx, x, y, w, height, radius) {
    const r = Math.min(radius, Math.abs(w) / 2, Math.abs(height) / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + height, r);
    ctx.arcTo(x + w, y + height, x, y + height, r);
    ctx.arcTo(x, y + height, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  function statusColor(status) {
    if (status === "confirmed" || status === "kept") return "#2f7d55";
    if (status === "rejected" || status === "excluded") return "#b2413d";
    if (status === "needs_review" || status === "uncertain") return "#a86513";
    return "#66746d";
  }

  function channelColor(channel) {
    if (channel === "EMG") return "#a86513";
    if (channel === "ACC") return "#2f7d55";
    return channel === "EEG1" ? "#2f659f" : "#6f5aa8";
  }

  function artifactLabel(value) {
    const labels = {
      emg: "EMG 伪迹",
      motion_acc: "体动 / ACC",
      electrode: "电极问题",
      saturation: "饱和",
      unreadable: "不可判读",
    };
    return labels[value] || value;
  }

  function linkedPreviewUrl(path, source) {
    const params = new URLSearchParams({ source });
    const currentParams = new URLSearchParams(window.location.search);
    const apiBase = currentParams.get("api") || state.payload?.context?.api_base || "";
    if (apiBase && isLocalPage() && isLocalApiBase(apiBase)) params.set("api", apiBase);
    return `${path}?${params.toString()}`;
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
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...(options.headers || {}),
      },
    });
    if (!response.ok) {
      const text = await response.text().catch(() => "");
      throw new Error(text || `HTTP ${response.status}`);
    }
    return response.json();
  }

  function exportFilename(kind, extension, sessionId = "") {
    const recordId = (state.payload.record?.id || state.payload.record?.file_id || "epilepsy").replace(/[^a-z0-9_-]+/gi, "_");
    const sessionPart = String(sessionId || "local").replace(/[^a-z0-9_-]+/gi, "_");
    const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\..+$/, "").replace("T", "-");
    return `${recordId}_${kind}_${sessionPart}_${stamp}.${extension}`;
  }

  function priorityLabel(priority) {
    const labels = {
      high: "高",
      medium: "中",
      low: "低",
    };
    return labels[String(priority || "").toLowerCase()] || priority || "未记录";
  }

  function actionLabel(value) {
    const labels = {
      event_review: "候选复核",
      review_fields: "字段更新",
      adjust_event_interval: "边界调整",
      note_template: "备注",
      undo: "撤销",
    };
    return labels[value] || value || "操作";
  }

  function splitChannels(value) {
    if (!value) return [];
    return String(value).split(/[;,/|]/).map((item) => item.trim()).filter(Boolean);
  }

  function numberOr(...values) {
    for (const value of values) {
      if (value === null || value === undefined || value === "") continue;
      const number = Number(value);
      if (Number.isFinite(number)) return number;
    }
    return 0;
  }

  function round1(value) {
    return Math.round(Number(value) * 10) / 10;
  }

  function hash(text) {
    let value = 0;
    for (let i = 0; i < text.length; i += 1) value = (value * 31 + text.charCodeAt(i)) >>> 0;
    return value / 1000;
  }

  function formatClock(seconds) {
    const total = Math.max(0, Math.floor(seconds));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  }

  function formatAuditTime(iso) {
    if (!iso) return "-";
    return new Date(iso).toLocaleString("zh-CN", { hour12: false });
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

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast("已复制");
    } catch {
      saveBlob(text, "epilepsy_report_text.txt", "text/plain;charset=utf-8");
      showToast("浏览器未允许复制，已下载文本");
    }
  }

  function csvEscape(value) {
    let raw = String(value ?? "");
    if (/^[=+\-@]/.test(raw)) raw = `'${raw}`;
    if (/[",\n\r]/.test(raw)) return `"${raw.replace(/"/g, '""')}"`;
    return raw;
  }

  function showToast(message) {
    document.querySelector(".ep-toast")?.remove();
    const toast = document.createElement("div");
    toast.className = "ep-toast";
    toast.textContent = message;
    document.body.appendChild(toast);
    window.setTimeout(() => toast.remove(), 2200);
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
