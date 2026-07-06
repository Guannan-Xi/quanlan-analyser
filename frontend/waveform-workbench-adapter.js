export function createWaveformApi(apiBase) {
  const base = String(apiBase || "http://127.0.0.1:8001/api").replace(/\/$/, "");
  const authKey = "qlanalyser_auth_session";
  function authToken() {
    try {
      const session = JSON.parse(localStorage.getItem(authKey) || sessionStorage.getItem(authKey) || "{}");
      return session.token || "";
    } catch {
      return "";
    }
  }
  function withAuthHeaders(headers = {}) {
    const token = authToken();
    return token && !headers.Authorization ? { ...headers, Authorization: `Bearer ${token}` } : headers;
  }
  async function apiJson(path, options = {}) {
    const response = await fetch(`${base}${path}`, {
      ...options,
      headers: withAuthHeaders(options.headers || {}),
    });
    const contentType = response.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = typeof data === "string" ? data : (data.detail || data.message || JSON.stringify(data));
      throw new Error(detail || `Request failed: ${response.status}`);
    }
    return data;
  }
  async function loadTeachingDataset() {
    return apiJson("/lab/demo/dataset");
  }
  async function createWaveformPreviewTask({ projectId, fileId, parameters = {} }) {
    return apiJson("/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projectId,
        input_file_id: fileId,
        module_name: "qc",
        workflow_id: "qc_waveform_preview",
        parameters_json: parameters,
        owner_user_id: "local-user",
        created_by: "local-user",
      }),
    });
  }
  async function fetchTaskArtifacts(taskId) {
    return apiJson(`/tasks/${encodeURIComponent(taskId)}/artifacts`);
  }
  async function fetchArtifactJson(artifact) {
    const id = artifact?.id;
    if (!id) throw new Error("Artifact id is missing");
    const response = await fetch(`${base}/artifacts/${encodeURIComponent(id)}/download`, {
      headers: withAuthHeaders(),
    });
    if (!response.ok) throw new Error(`Artifact download failed: ${response.status}`);
    return response.json();
  }
  async function fetchWaveformChunk({ fileId, startSec = 0, durationSec = 24, channelLimit = 8, displaySfreq = 200, mode = "minmax", widthPx = 1440, signal } = {}) {
    if (!fileId) throw new Error("File id is missing");
    const query = new URLSearchParams({
      start_sec: String(startSec),
      duration_sec: String(durationSec),
      channel_limit: String(channelLimit),
      display_sfreq: String(displaySfreq),
      mode,
      width_px: String(widthPx),
    });
    return apiJson(`/eeg/files/${encodeURIComponent(fileId)}/waveform/chunk?${query.toString()}`, { signal });
  }
  return { base, apiJson, loadTeachingDataset, createWaveformPreviewTask, fetchTaskArtifacts, fetchArtifactJson, fetchWaveformChunk };
}

export function waveformArtifactFromList(artifacts = []) {
  return artifacts.find((artifact) => {
    const key = `${artifact.label || ""} ${artifact.artifact_type || ""} ${artifact.object_key || ""} ${artifact.path || ""}`.toLowerCase();
    return key.includes("waveform_preview") && key.includes("json");
  }) || artifacts.find((artifact) => {
    const key = `${artifact.label || ""} ${artifact.artifact_type || ""} ${artifact.object_key || ""} ${artifact.path || ""}`.toLowerCase();
    return key.includes("waveform") && key.includes("json");
  }) || null;
}

export function normalizeWaveformPreview(payload = {}) {
  const channels = Array.isArray(payload.channels) ? payload.channels : (Array.isArray(payload.channel_names) ? payload.channel_names : []);
  const rawData = Array.isArray(payload.data_uv) ? payload.data_uv : (Array.isArray(payload.data) ? payload.data : []);
  const data_uv = rawData.map((row) => Array.isArray(row) ? row.map((value) => Number(value) || 0) : []);
  const start = Number(payload.start_sec ?? payload.window?.start_sec ?? 0) || 0;
  const duration = Number(payload.duration_sec ?? payload.window_sec ?? payload.window?.duration_sec ?? 10) || 10;
  const fileDuration = Number(payload.file_duration_sec ?? payload.duration_total_sec ?? payload.metadata?.duration_sec ?? Math.max(duration, start + duration)) || Math.max(duration, start + duration);
  let times = Array.isArray(payload.times_sec) ? payload.times_sec.map(Number) : [];
  if (!times.length && data_uv[0]?.length) {
    const n = data_uv[0].length;
    times = Array.from({ length: n }, (_, index) => start + (duration * index) / Math.max(1, n - 1));
  }
  return {
    ...payload,
    channels,
    data_uv,
    times_sec: times,
    start_sec: start,
    duration_sec: duration,
    file_duration_sec: fileDuration,
    display_sample_rate_hz: Number(payload.display_sample_rate_hz ?? payload.sfreq_display ?? payload.sample_rate_hz ?? 0) || 200,
    unit: "uV",
    events: Array.isArray(payload.events) ? payload.events : (Array.isArray(payload.annotations) ? payload.annotations : []),
    bad_segments: Array.isArray(payload.bad_segments) ? payload.bad_segments : [],
    bad_channels: Array.isArray(payload.bad_channels) ? payload.bad_channels : [],
  };
}
