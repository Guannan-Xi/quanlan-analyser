(function () {
  "use strict";

  const REPORT_SCHEMA = "qlanalyser.epilepsy.report_preview.v1";
  const REVIEW_SCHEMA = "qlanalyser.epilepsy.manual_correction_preview.v1";
  const STATUS_LABEL = {
    confirmed: "人工保留",
    kept: "人工保留",
    rejected: "排除",
    excluded: "排除",
    needs_review: "存疑",
    uncertain: "存疑",
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
    ied: "IED / 尖慢波",
    seizure_like: "发作样节律",
    rhythmic: "节律性放电",
    artifact_suspect: "伪迹疑似",
  };

  const state = {
    payload: sampleReviewPayload(),
  };

  const dom = {};

  function init() {
    cacheDom();
    hydrateFromReviewPreview();
    bindEvents();
    renderReport();
    resizeFigures();
    window.addEventListener("resize", resizeFigures);
    syncIcons();
  }

  function hydrateFromReviewPreview() {
    try {
      const storageKey = "qlanalyser.epilepsy.review_preview.latest";
      const raw = window.sessionStorage.getItem(storageKey) || window.localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (parsed && (parsed.schema_version === REVIEW_SCHEMA || parsed.reviewed_events || parsed.all_reviewed_events || parsed.confirmed_events || parsed.event_reviews)) {
        state.payload = parsed;
      }
    } catch {
      // Keep the built-in sample report when browser storage is blocked or the saved draft is malformed.
    }
  }

  function cacheDom() {
    [
      "reviewJsonInput",
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

  async function loadReviewJson(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const raw = JSON.parse(text);
      state.payload = normalizePayload(raw);
      renderReport();
      resizeFigures();
      showToast(`已载入 ${file.name}`);
    } catch (error) {
      showToast(`JSON 无法读取：${error.message || error}`);
    } finally {
      event.target.value = "";
    }
  }

  function normalizePayload(raw) {
    const record = raw.record || {};
    const reviewedEvents = Array.isArray(raw.reviewed_events)
      ? raw.reviewed_events
      : Array.isArray(raw.all_reviewed_events)
        ? raw.all_reviewed_events
        : Array.isArray(raw.confirmed_events)
          ? raw.confirmed_events
          : [];
    const eventReviews = raw.event_reviews || {};
    const events = reviewedEvents.map((item, index) => {
      const id = String(item.event_id || item.id || `event_${index + 1}`);
      const review = eventReviews[id] || {};
      const uiReview = review.ui_review || {};
      const status = normalizeStatus(item.backend_status || item.review_status || item.status || review.status || uiReview.status || "unreviewed");
      const start = numberOr(item.reviewed_start_sec, item.start_sec, item.original_start_sec, 0);
      const end = numberOr(item.reviewed_end_sec, item.end_sec, item.original_end_sec, start + numberOr(item.duration_sec, 1));
      return {
        event_id: id,
        start_sec: round1(start),
        end_sec: round1(Math.max(end, start + 0.1)),
        duration_sec: round1(Math.max(0.1, end - start)),
        event_type: item.reviewed_type || item.event_type || uiReview.event_type || item.ai_type || "ied",
        channels: Array.isArray(item.channels) ? item.channels : splitChannels(item.channels),
        evidence_grade: item.evidence_grade || uiReview.grade || "C",
        artifact_reason: item.artifact_reason || uiReview.artifact_reason || "",
        status,
        preview_rms_ptp_rank_score: Number(item.preview_rms_ptp_rank_score || item.score || item.probability || 0),
        score_kind: item.score_kind || "preview_rank_not_probability",
        score_note: item.score_note || "预览排序值不是临床概率、检测置信度或诊断结论。",
        note: item.note || review.note || uiReview.note || "",
      };
    });
    return {
      schema_version: raw.schema_version || REVIEW_SCHEMA,
      generated_at: raw.generated_at || new Date().toISOString(),
      non_medical_scope: raw.non_medical_scope || "research_screening_support_only",
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
      reviewed_events: events,
      actions: Array.isArray(raw.actions) ? raw.actions : [],
    };
  }

  function renderReport() {
    state.payload = normalizePayload(state.payload);
    renderSummary();
    renderTexts();
    renderEventTable();
    renderAudit();
    syncIcons();
  }

  function renderSummary() {
    const payload = state.payload;
    const record = payload.record;
    const events = payload.reviewed_events;
    const stats = eventStats(events);
    const hours = Math.max(0.01, record.duration_sec / 3600);
    dom.recordName.textContent = record.filename || "-";
    dom.recordMeta.textContent = `${hours.toFixed(1)} h · ${record.sfreq || "-"} Hz · ${record.channels.join(" / ")}`;
    dom.confirmedMetric.textContent = String(stats.confirmed);
    dom.eventRateMetric.textContent = `${(stats.confirmed / hours).toFixed(3)} / h`;
    dom.pendingMetric.textContent = `${stats.needsReview + stats.unreviewed}`;
    dom.coverageMetric.textContent = `${Math.round((stats.reviewed / Math.max(1, events.length)) * 100)}%`;
    dom.coverageHint.textContent = `${stats.reviewed}/${events.length} 候选已复核`;
    dom.overallStatement.textContent = reportStatus() === "complete_review_preview"
      ? "人工复核已覆盖全部候选。"
      : "部分复核草稿，仍含待确认候选。";
    dom.contractLabel.textContent = REPORT_SCHEMA;
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
    dom.eventTableBody.innerHTML = rows.map((event) => `
      <tr>
        <td><strong>${h(event.event_id)}</strong></td>
        <td>${h(formatClock(event.start_sec))}</td>
        <td>${h(event.duration_sec.toFixed(1))} s</td>
        <td>${h(TYPE_LABEL[event.event_type] || event.event_type)}</td>
        <td>${h(event.channels.join(" / ") || "-")}</td>
        <td>${h(event.evidence_grade || "-")}${event.artifact_reason ? ` · ${h(artifactLabel(event.artifact_reason))}` : ""}</td>
        <td><span class="ep-status ${h(event.status)}">${h(STATUS_LABEL[event.status] || event.status)}</span></td>
      </tr>
    `).join("");
  }

  function renderAudit() {
    const actions = state.payload.actions.slice(-6).reverse();
    if (!actions.length) {
      dom.auditList.innerHTML = `<article><strong>暂无操作记录</strong><span>载入正式复核 JSON 后会显示审计链。</span></article>`;
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
      ["confirmed", "人工保留"],
      ["rejected", "排除"],
      ["needs_review", "存疑"],
      ["unreviewed", "未复核"],
    ];
    ctx.font = "700 13px Inter, Microsoft YaHei, sans-serif";
    ctx.fillStyle = "#17201b";
    ctx.fillText("全记录候选时间轴", left, 24);
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
      centerText(ctx, w, height, "暂无人工保留事件");
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
    ctx.fillText(`代表事件 ${event.event_id}`, left, 23);
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
    const stats = eventStats(state.payload.reviewed_events);
    clearFigure(ctx, w, height);
    const rows = [
      ["AI 候选", stats.total, "#2f659f"],
      ["已复核", stats.reviewed, "#6f5aa8"],
      ["人工保留", stats.confirmed, "#2f7d55"],
      ["排除", stats.rejected, "#b2413d"],
      ["存疑", stats.needsReview, "#a86513"],
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
    ctx.fillText("人工保留事件密度", left, 23);
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
    ctx.fillText("通道证据参与", left, 23);
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
    const stats = eventStats(payload.reviewed_events);
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
        confirmed_rate_per_hour: Number((stats.confirmed / Math.max(0.01, payload.record.duration_sec / 3600)).toFixed(4)),
      },
      interpretation: summaryText(),
      methods: methodsText(),
      figure_manifest: figureManifest(),
      provenance: provenanceManifest(),
      confirmed_events: confirmedEvents(),
      all_reviewed_events: payload.reviewed_events,
      actions: payload.actions,
    };
  }

  function exportReportJson() {
    saveBlob(JSON.stringify(reportPayload(), null, 2), `${state.payload.record.id || "epilepsy"}_report_preview.json`, "application/json;charset=utf-8");
    showToast("报告预览 JSON 已导出");
  }

  function exportEventsCsv() {
    const rows = state.payload.reviewed_events;
    const columns = [
      ["event_id", "event_id"],
      ["reviewed_start_sec", "start_sec"],
      ["reviewed_end_sec", "end_sec"],
      ["duration_sec", "duration_sec"],
      ["event_type", "event_type"],
      ["channels", "channels"],
      ["evidence_grade", "evidence_grade"],
      ["artifact_reason", "artifact_reason"],
      ["review_status", "status"],
      ["preview_rms_ptp_rank_score", "preview_rms_ptp_rank_score"],
      ["score_kind", "score_kind"],
      ["score_note", "score_note"],
      ["review_note", "note"],
    ];
    const csv = [
      columns.map(([header]) => header).join(","),
      ...rows.map((row) => columns.map(([, key]) => {
        const value = typeof key === "function" ? key(row) : row[key];
        return csvEscape(Array.isArray(value) ? value.join(";") : value);
      }).join(",")),
    ].join("\r\n");
    saveBlob(`\ufeff${csv}`, `${state.payload.record.id || "epilepsy"}_reviewed_events.csv`, "text/csv;charset=utf-8");
    showToast("事件 CSV 已导出");
  }

  function summaryText() {
    const payload = state.payload;
    const stats = eventStats(payload.reviewed_events);
    const hours = Math.max(0.01, payload.record.duration_sec / 3600);
    const rate = (stats.confirmed / hours).toFixed(3);
    const pending = stats.needsReview + stats.unreviewed;
    if (stats.confirmed === 0) {
      return `在 ${payload.record.filename} 的 ${hours.toFixed(1)} 小时记录中，当前未形成可纳入统计的人工保留癫痫样事件候选。共有 ${pending} 个候选仍需确认或复核，不能代表确认或排除发作的临床结论。`;
    }
    return `在 ${payload.record.filename} 的 ${hours.toFixed(1)} 小时记录中，AI 产生 ${stats.total} 个候选，经人工复核后保留 ${stats.confirmed} 个癫痫样事件候选；已复核人工保留候选负荷约 ${rate} 次/小时。${stats.rejected} 个候选被排除，${pending} 个候选仍需确认或未复核。`;
  }

  function dataMethodText() {
    const record = state.payload.record;
    const duration = Math.max(0, record.duration_sec / 3600).toFixed(1);
    return `输入记录为 ${record.filename}，总时长约 ${duration} 小时，采样率 ${record.sfreq || "-"} Hz，报告通道为 ${record.channels.join("、")}。当前报告预览中的代表波形为合成示意；正式报告必须使用真实 EDF waveform-window 或 evidence package，并在图注中标注窗口、单位、滤波和通道。`;
  }

  function reviewMethodText() {
    const context = state.payload.context || {};
    const workflow = context.workflow_id || state.payload.model?.workflow_id || "epilepsy_ml_xgboost";
    const model = state.payload.model || {};
    const modelText = model.detector_version ? `检测器版本 ${model.detector_version}` : "检测器版本待记录";
    const thresholdText = Number.isFinite(Number(model.threshold)) ? `候选阈值 ${model.threshold}` : "候选阈值待记录";
    return `自动候选来自 ${workflow} 工作流，${modelText}，${thresholdText}。人工复核记录事件状态、边界修正、证据等级、伪迹原因和审计操作；报告只读取复核层，不覆盖算法原始产物。证据等级 A/B/C/X 分别表示明确、较可信、低可信、不可判读；排除规则包括 EMG 增高、ACC 同步体动、电极问题、饱和和不可判读。`;
  }

  function methodsText() {
    return `${dataMethodText()}\n${reviewMethodText()}\n统计口径：仅人工保留候选进入报告摘要、负荷统计和代表图；排除、存疑、未复核候选保留为追溯记录。算法候选分数仅用于排序或复核优先级，不代表临床置信度。局限性：当前预览无同步视频、无临床标注、无外部验证集指标，不能估计敏感性或特异性，也不能代表确认或排除发作。`;
  }

  function figureManifest() {
    return [
      { id: "timelineFigure", title: "全记录候选时间轴", source: "reviewed_events", provenance: "derived_from_review_layer" },
      { id: "waveformFigure", title: "代表事件波形示意", source: "synthetic_preview_waveform", provenance: "demo_only_replace_with_waveform_window" },
      { id: "funnelFigure", title: "复核漏斗", source: "reviewed_events", provenance: "derived_from_review_layer" },
      { id: "densityFigure", title: "已复核人工保留候选负荷", source: "confirmed_reviewed_events", provenance: "derived_from_review_layer" },
      { id: "qcFigure", title: "通道证据参与", source: "confirmed_reviewed_events", provenance: "derived_from_review_layer" },
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
      waveform_provenance: "synthetic_preview_until_real_waveform_window_is_connected",
    };
  }

  function eventStats(events) {
    const stats = { total: events.length, confirmed: 0, rejected: 0, needsReview: 0, unreviewed: 0, reviewed: 0 };
    events.forEach((event) => {
      if (event.status === "confirmed" || event.status === "kept") stats.confirmed += 1;
      else if (event.status === "rejected" || event.status === "excluded") stats.rejected += 1;
      else if (event.status === "needs_review" || event.status === "uncertain") stats.needsReview += 1;
      else stats.unreviewed += 1;
    });
    stats.reviewed = stats.confirmed + stats.rejected + stats.needsReview;
    return stats;
  }

  function reportStatus() {
    const stats = eventStats(state.payload.reviewed_events);
    if (stats.unreviewed > 0 || stats.needsReview > 0) return "partial_review_draft";
    return "complete_review_preview";
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
      sampleEvent("HE105-E005", 39748.4, 39752.2, "needs_review", "rhythmic", ["EEG1", "EEG2"], "C", "", 0.61, "低置信节律片段。"),
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
      reviewed_events: events,
      actions: [
        { type: "event_review", label: "保留", detail: "HE105-E001 · confirmed", created_at: new Date(Date.now() - 720000).toISOString() },
        { type: "event_review", label: "存疑", detail: "HE105-E002 · needs_review", created_at: new Date(Date.now() - 620000).toISOString() },
        { type: "adjust_event_interval", label: "调整边界", detail: "HE105-E004 · 18525.0-18526.8s", created_at: new Date(Date.now() - 420000).toISOString() },
        { type: "event_review", label: "排除", detail: "HE105-E007 · motion_acc", created_at: new Date(Date.now() - 180000).toISOString() },
      ],
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

  function actionLabel(value) {
    const labels = {
      event_review: "事件复核",
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
