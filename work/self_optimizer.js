const fs = require("fs");
const path = require("path");
const https = require("https");
const { spawn } = require("child_process");
const crypto = require("crypto");

const root = path.resolve(__dirname, "..");
const devRoot = path.join(root, "outputs", "eeglab-mne-dev");
const optimizerDir = path.join(root, "outputs", "eeglab-mne-dev", "assets", "realtime_optimizer");
const stateFile = path.join(optimizerDir, "self_optimizer_state.json");
const logFile = path.join(optimizerDir, "self_optimizer_log.jsonl");
const queueFile = path.join(optimizerDir, "self_optimizer_queue.jsonl");
const eventsFile = path.join(optimizerDir, "self_optimizer_events.jsonl");
const issuesFile = path.join(optimizerDir, "self_optimizer_issues.jsonl");
const memoryFile = path.join(optimizerDir, "self_optimizer_memory.json");
const patchPlanFile = path.join(optimizerDir, "self_optimizer_patch_plan.json");
const roleplayDetailFile = path.join(optimizerDir, "self_optimizer_roleplay_detail.jsonl");
const externalResearchFile = path.join(optimizerDir, "self_optimizer_external_code_research.json");
const emailTool = process.env.QL_SELF_OPTIMIZER_EMAIL_TOOL || "C:\\Users\\XGN\\.codex\\skills\\quanlan-email-delivery\\scripts\\email_tool.py";
const emailPython = process.env.QL_SELF_OPTIMIZER_EMAIL_PYTHON || "C:\\Users\\XGN\\miniconda3\\python.exe";
const emailProject = process.env.QL_SELF_OPTIMIZER_EMAIL_PROJECT || "D:\\Quanlan\\Codes\\Python\\xgn-assistant\\modes\\culture";
const emailTo = process.env.QL_SELF_OPTIMIZER_EMAIL_TO || "399467826@qq.com";
const emailOutDir = path.join(optimizerDir, "email_reports");
const intervalMs = Number(process.env.QL_SELF_OPTIMIZER_INTERVAL_MS || 300_000);
const idleUpdateMinMs = Number(process.env.QL_SELF_OPTIMIZER_IDLE_UPDATE_MIN_MS || 3_600_000);
const roleplayUpdateMinMs = Number(process.env.QL_SELF_OPTIMIZER_ROLEPLAY_UPDATE_MIN_MS || 3_600_000);
const devIdleStableMs = Number(process.env.QL_SELF_OPTIMIZER_DEV_IDLE_STABLE_MS || 600_000);
const bugPattern = /(error|failed|failure|exception|traceback|timeout|fatal|crash|bug|报错|错误|失败|卡住|卡主)/i;
const externalLearningPattern = /(你去学学别人的代码|学学别人的代码|学习.*别人.*代码|参考.*github|github.*参考|借鉴.*开源|开源.*借鉴|看看.*github|外部代码|别人.*工程|常见.*脑电.*方法|常见.*脑电.*工作流)/i;

function nowIso() {
  return new Date().toISOString();
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function appendJsonl(file, record) {
  ensureDir(path.dirname(file));
  fs.appendFileSync(file, `${JSON.stringify({ at: nowIso(), ...record })}\n`, "utf8");
}

function stableId(parts) {
  return crypto.createHash("sha1").update(parts.filter(Boolean).join("\n")).digest("hex").slice(0, 16);
}

function classifyIssue(text, source = "") {
  const value = `${source}\n${text || ""}`;
  const area = /EDF|BIDS|MNE|ICA|PREP|P300|oddball|采样|通道|坏道|事件|脑电/i.test(value) ? "scientific-validity"
    : /release|发布|runtime-state|candidate|validate|正式版/i.test(value) ? "release"
      : /UI|界面|看不懂|上传|导出|workflow|流程/i.test(value) ? "ux"
        : /error|failed|exception|timeout|bug|报错|错误|失败/i.test(value) ? "runtime"
          : "research";
  const severity = /数据错|论文|复现|release|正式版|fatal|crash|报错|错误|failed|timeout/i.test(value) ? "high"
    : /看不懂|缺少|建议|优化|不准/i.test(value) ? "medium"
      : "low";
  return { area, severity };
}

function recordEvolutionEvent(state, event) {
  const classified = classifyIssue(event.text || event.summary || "", event.source || event.type || "");
  const enriched = {
    project: "QL脑电分析平台",
    stage: event.stage || "observe",
    area: event.area || classified.area,
    severity: event.severity || classified.severity,
    ...event,
  };
  appendJsonl(eventsFile, enriched);
  state.evolution_event_count = Number(state.evolution_event_count || 0) + 1;
  return enriched;
}

function recordIssue(state, input) {
  const text = input.text || input.summary || "";
  const classified = classifyIssue(text, input.source || input.type || "");
  const issue = {
    id: input.id || stableId(["ql-eeg", input.source, classified.area, text.slice(0, 500)]),
    project: "QL脑电分析平台",
    status: "pending",
    source: input.source || "self-optimizer",
    type: input.type || "feedback",
    area: input.area || classified.area,
    severity: input.severity || classified.severity,
    summary: String(input.summary || text).slice(0, 500),
    evidence: input.evidence || text,
    next_action: input.next_action || "convert-to-regression-or-safe-patch",
  };
  state.issue_ids = state.issue_ids || [];
  if (!state.issue_ids.includes(issue.id)) {
    appendJsonl(issuesFile, issue);
    state.issue_ids.push(issue.id);
    state.issue_ids = state.issue_ids.slice(-1000);
  }
  return issue;
}

function updateLearningMemory(state, input) {
  const memory = readJson(memoryFile, {
    project: "QL脑电分析平台",
    principles: [],
    recurring_issues: {},
    release_lessons: [],
  });
  for (const issue of input.issues || []) {
    memory.recurring_issues[issue.area] = Number(memory.recurring_issues[issue.area] || 0) + 1;
  }
  if (input.release) memory.release_lessons.push({ at: nowIso(), ...input.release });
  memory.principles = [
    "脑电分析优化必须优先保证科学有效性和可复现性。",
    "上传、预处理、事件、坏道、导出类问题应沉淀为回归检查。",
    "正式版更新只通过 release-candidate 校验和空闲发布脚本。",
  ];
  memory.release_lessons = memory.release_lessons.slice(-50);
  writeJson(memoryFile, memory);
  return memory;
}

function writePatchPlan(state, issues, roleReviews) {
  const plan = {
    project: "QL脑电分析平台",
    generated_at: nowIso(),
    automation_level: "L2-L3 guarded",
    stages: ["observe", "classify_dedupe", "roleplay_review", "external_research", "patch_plan", "test", "idle_release", "learn"],
    pending_issues: issues.slice(-30),
    roleplay_reviews: roleReviews,
    external_research_sources: [
      "MNE official tutorials",
      "EEG preprocessing papers",
      "OpenNeuro/EEGDash/MOABB datasets",
      "GitHub public EEG/MNE/EEGLAB workflow repositories",
    ],
    external_code_research_file: externalResearchFile,
    safe_actions: [
      "refresh realtime optimizer seed queue",
      "generate role-play review matrix",
      "validate release candidate",
      "promote release only through promote_release_if_idle.ps1",
    ],
    requires_human_confirmation: ["large algorithm changes", "clinical claims", "destructive release cleanup", "data privacy changes"],
  };
  writeJson(patchPlanFile, plan);
  appendJsonl(eventsFile, { project: "QL脑电分析平台", stage: "patch_plan", event: "patch-plan-written", issues: issues.length });
  return plan;
}

function writeRoleplayDetails(state, roleReviews, issues) {
  const details = roleReviews.map((review) => {
    const matched = issues.filter((issue) => {
      const text = `${issue.area || ""} ${issue.summary || ""}`;
      if (/novice|EDF/i.test(review.role)) return /ux|scientific-validity|EDF|上传|通道|采样|事件/i.test(text);
      if (/paper|reproduction/i.test(review.role)) return /scientific-validity|research|MNE|论文|复现/i.test(text);
      if (/clinical/i.test(review.role)) return /scientific-validity|runtime|临床|预处理|风险/i.test(text);
      if (/operator|release/i.test(review.role)) return /release|runtime|发布|runtime-state/i.test(text);
      return false;
    });
    return {
      project: "QL脑电分析平台",
      round_at: nowIso(),
      virtual_user: review.role,
      test_focus: review.prompt,
      simulated_questions: roleplayQuestions(review.role),
      evidence_sources: [logFile, issuesFile, patchPlanFile],
      observed_issues: matched.map((issue) => ({
        id: issue.id || "",
        area: issue.area || "unknown",
        severity: issue.severity || "unknown",
        summary: issue.summary || "",
      })),
      conclusion: matched.length ? `发现 ${matched.length} 个相关问题，需要转成脑电流程回归测试。` : "本轮没有发现该角色视角下的新高优先级问题。",
      recommendation: matched.length ? "优先补充上传、预处理、事件/坏道和发布校验的可复现测试。" : "继续积累真实 EDF/MNE 工作流反馈。",
      needs_human_confirmation: matched.some((issue) => issue.severity === "high" && issue.area === "scientific-validity"),
    };
  });
  for (const detail of details) appendJsonl(roleplayDetailFile, detail);
  state.last_roleplay_detail_file = roleplayDetailFile;
  state.last_roleplay_details = details;
  appendJsonl(eventsFile, { project: "QL脑电分析平台", stage: "roleplay_review", event: "roleplay-details-written", roles: details.length });
  return details;
}

function userProblemLine(issue) {
  const raw = String(issue.summary || issue.source || "").replace(/\s+/g, " ").trim();
  const text = raw.slice(0, 500);
  if (issue.area === "scientific-validity" || /EDF|MNE|ICA|PREP|采样|通道|坏道|事件|脑电/i.test(text)) {
    return "脑电分析解释更清楚：重点检查上传 EDF 后的采样率、通道、坏道、事件和预处理风险。";
  }
  if (issue.area === "ux" || /看不懂|上传|导出|界面|workflow|流程/i.test(text)) {
    return "操作体验更清楚：把用户看不懂的流程提示记录为后续界面优化任务。";
  }
  if (issue.area === "release" || /release|发布|candidate|正式版|runtime-state/i.test(text)) {
    return "正式版发布更稳：检查发布候选和运行状态，避免带着未完成任务更新正式版。";
  }
  if (issue.area === "runtime" || /error|failed|timeout|报错|错误|失败/i.test(text)) {
    return "运行稳定性已被检查，失败任务会转成后续修复和回归测试。";
  }
  return text && !text.startsWith("{") ? text.slice(0, 140) : "发现一条内部运行信号，已记录到问题单等待后续处理。";
}

function summarizeUserOutcomes(issues, idle) {
  const outcomes = [];
  if (idle.seed?.ok) outcomes.push("脑电知识和训练问题已刷新，后续小猪理能更好回答 EEG/MNE 相关问题。");
  if (idle.promote?.ok) outcomes.push("正式版已通过校验并完成空闲更新。");
  if (issues.some((issue) => issue.area === "scientific-validity")) outcomes.push("科学有效性被重点检查，减少脑电流程解释不准的风险。");
  if (!outcomes.length) outcomes.push("本轮没有发现新的用户可感知问题，主要是例行巡检和发布安全检查。");
  return outcomes;
}

function uniqueUserProblemLines(issues) {
  return [...new Set(issues.map(userProblemLine))].filter(Boolean);
}

function buildUserFacingReport(issues, idle) {
  const text = issues.map((issue) => `${issue.area || ""} ${issue.summary || ""}`).join("\n");
  const handled = [];
  const pending = [];
  if (idle.seed?.ok) handled.push("知识刷新：已刷新 EEG/MNE 训练问题，后续回答脑电流程时更不容易漏掉关键检查点。");
  if (idle.promote?.ok) handled.push("正式版更新：已通过校验并完成空闲更新。");
  if (/scientific-validity|EDF|MNE|ICA|PREP|采样|通道|坏道|事件|脑电/i.test(text)) {
    handled.push("脑电结果可信度：已重点检查 EDF 上传、采样率、通道、坏道、事件和预处理解释风险。");
  }
  if (/ux|看不懂|上传|导出|界面|workflow|流程/i.test(text)) {
    handled.push("操作体验：已把用户看不懂的上传、导出、流程提示记录为界面优化任务。");
  }
  if (/release|发布|candidate|正式版|runtime-state/i.test(text) && !idle.promote?.ok) {
    pending.push("正式版发布：仍需继续观察发布候选和运行状态，避免把未完成任务带进正式版。");
  }
  if (/runtime|error|failed|timeout|报错|错误|失败/i.test(text)) {
    pending.push("运行稳定性：失败任务已进入后续修复和回归测试列表。");
  }
  if (!issues.length && !handled.length) handled.push("本轮没有发现新的用户可感知问题，后台继续巡检、学习资料和校验正式版。");
  if (!handled.length) handled.push(...uniqueUserProblemLines(issues));
  return { handled: [...new Set(handled)], pending: [...new Set(pending)] };
}

function roleplayQuestions(role) {
  const entries = [
    [/novice|EDF/i, [
      "我第一次上传 EDF，系统有没有告诉我采样率、通道数、事件标记是否正常？",
      "如果坏道或事件缺失，界面会不会明确告诉我该怎么修？",
    ]],
    [/paper|reproduction/i, [
      "我要复现论文里的 MNE 流程，预处理步骤、参数和导出结果有没有可核对依据？",
      "ICA/PREP/坏道处理会不会让结果解释失真？",
    ]],
    [/clinical/i, [
      "这个预处理结果能不能用于临床解释？哪些地方必须提示风险和限制？",
      "如果数据质量差，系统会不会阻止我给出过度结论？",
    ]],
    [/operator|release/i, [
      "正式版更新前有没有确认任务都跑完、候选版本能通过校验？",
      "发布失败时，用户数据和已有结果会不会被覆盖或丢失？",
    ]],
  ];
  const found = entries.find(([pattern]) => pattern.test(role || ""));
  return found ? found[1] : ["这个脑电流程最容易让用户误解什么？", "当前版本有没有清楚提示风险、来源和下一步？"];
}

function roleplayFindingLine(item) {
  const issues = Array.isArray(item.observed_issues) ? item.observed_issues : [];
  const findings = [...new Set(issues.map(userProblemLine))].filter(Boolean);
  if (!findings.length) return "暂无新的高优先级问题。";
  return findings.join(" / ");
}

function roleplayEmailLine(item, index) {
  const rawUser = item.virtual_user || "虚拟用户";
  const rawFocus = item.test_focus || "真实脑电工作流";
  const roleNames = [
    [/novice|EDF/i, "第一次上传 EDF 的新手用户"],
    [/paper|reproduction/i, "复现论文流程的研究者"],
    [/clinical/i, "关注临床预处理风险的使用者"],
    [/operator|release/i, "发布版维护者"],
  ];
  const user = (roleNames.find(([pattern]) => pattern.test(rawUser)) || [null, rawUser])[1];
  const focus = rawFocus
    .replace(/Role-play as .*?; inspect QL EEG workflow risks, missing guidance, validation gaps, and release blockers\./i, "检查脑电上传、分析解释、流程提示、校验缺口和正式版发布风险")
    .replace(/QL EEG workflow risks, missing guidance, validation gaps, and release blockers/ig, "脑电流程风险、缺失提示、校验缺口和发布阻塞");
  const questions = Array.isArray(item.simulated_questions) && item.simulated_questions.length
    ? item.simulated_questions
    : roleplayQuestions(rawUser);
  const count = Array.isArray(item.observed_issues) ? item.observed_issues.length : 0;
  const needsConfirm = item.needs_human_confirmation ? "涉及科学有效性，需要人工确认。" : "暂不需要人工确认。";
  const result = count
    ? `发现 ${count} 类需要继续优化的脑电流程风险，已进入问题单和补丁计划。`
    : "本轮没有发现新的高优先级风险。";
  return [
    `- ${index + 1}. ${user}`,
    `  - 模拟提问：${questions.join(" / ")}`,
    `  - 检查重点：${focus}`,
    `  - 本轮结果：${result}`,
    `  - 具体发现：${roleplayFindingLine(item)}`,
    `  - 下一步：${needsConfirm}`,
  ].join("\n");
}

function writeEmailReport(kind, payload = {}) {
  ensureDir(emailOutDir);
  const stamp = nowIso().replace(/[:.]/g, "-");
  const file = path.join(emailOutDir, `${kind}-${stamp}.txt`);
  const issues = payload.issues || [];
  const roleplayDetails = payload.roleplay_details || [];
  const idle = payload.idle_optimization || {};
  const outcomes = summarizeUserOutcomes(issues, idle);
  const userFacing = buildUserFacingReport(issues, idle);
  const issueCategories = uniqueUserProblemLines(issues).length;
  const lines = [
    "QL脑电分析平台自优化日志",
    "",
    `时间：${nowIso()}`,
    `本轮类型：${kind}`,
    `邮件收件人：${emailTo}`,
    "",
    "一、本轮升级了什么",
    ...outcomes.map((item) => `- ${item}`),
    "",
    "二、已经解决或加固了什么",
    ...userFacing.handled.map((item) => `- ${item}`),
    "",
    "三、还没完全解决但已经保护了什么",
    ...(userFacing.pending.length ? userFacing.pending.map((item) => `- ${item}`) : ["- 暂无需要你立刻处理的遗留风险。"]),
    "",
    "四、本轮结果",
    `- 种子刷新：${idle.seed?.ok ? "成功" : idle.seed ? "失败" : "未运行"}`,
    `- 正式版校验/更新：${idle.promote?.ok ? "成功" : idle.promote ? "失败" : "未运行"}`,
    `- 本轮主要处理的用户风险类型：${issueCategories || 0} 类`,
    "",
    "五、具体处理清单",
    ...(issues.length ? uniqueUserProblemLines(issues).map((item, index) => `- ${index + 1}. ${item}`) : ["- 没有发现需要立刻处理的新问题。"]),
    "",
    "六、虚拟用户测试详细记录",
    ...(roleplayDetails.length ? roleplayDetails.map(roleplayEmailLine) : ["- 本轮未生成虚拟用户明细。"]),
    `- 明细文件：${roleplayDetailFile}`,
    "",
    "七、下一步",
    issues.length ? "- 下一轮会继续把这些问题转成脑电工作流测试、发布校验和界面提示优化。" : "- 继续保持后台巡检、资料学习和正式版安全校验。",
    "",
    "八、追溯文件",
    `- 运行日志：${logFile}`,
    `- 事件流：${eventsFile}`,
    `- 问题单：${issuesFile}`,
    `- 补丁计划：${patchPlanFile}`,
    `- 学习记忆：${memoryFile}`,
    `- 虚拟用户明细：${roleplayDetailFile}`,
  ];
  fs.writeFileSync(file, `${lines.join("\n")}\n`, "utf8");
  return file;
}

async function emailOptimizationLog(kind, payload = {}) {
  const reportFile = writeEmailReport(kind, payload);
  let result = { ok: false, error: "not-started", reportFile };
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    result = await run(emailPython, [
      emailTool,
      "send",
      "--project", emailProject,
      "--path", reportFile,
      "--to", emailTo,
      "--subject", `QL脑电分析平台自优化日志：${kind}`,
      "--body", fs.readFileSync(reportFile, "utf8"),
    ], { timeoutMs: 90_000 }).then((res) => ({ ok: true, attempt, stdout: res.stdout.slice(0, 1000), stderr: res.stderr.slice(0, 1000), reportFile }))
      .catch((err) => ({ ok: false, attempt, error: err.message, reportFile }));
    if (result.ok) break;
  }
  appendJsonl(logFile, { event: result.ok ? "optimization-log-email-sent" : "optimization-log-email-failed", kind, to: emailTo, result });
  appendJsonl(eventsFile, { project: "QL脑电分析平台", stage: "notify", event: result.ok ? "email-sent" : "email-failed", kind, to: emailTo, result });
  return result;
}

function extractReleaseEventFromIdle(idleResult) {
  const promote = idleResult?.promote || {};
  const stdout = String(promote.stdout || "");
  if (promote.ok && /Release candidate promoted from development/i.test(stdout)) {
    return { sent_worthy: true, reason: "release-promoted", details: promote };
  }
  if (promote.ok === false) {
    return { sent_worthy: true, reason: "release-promotion-failed", details: promote };
  }
  return { sent_worthy: false, reason: promote.ok ? "validated-only-no-release-change" : "no-release-promotion-run", details: promote };
}

async function syncReleaseToGithub(releaseEvent = {}) {
  if (!releaseEvent.sent_worthy) return { ok: true, skipped: true, reason: "no-release-event" };
  const message = `chore: sync release optimization ${releaseEvent.reason || "release"}`;
  const status = await run("git", ["status", "--porcelain"], { timeoutMs: 30_000 }).catch((err) => ({ stdout: "", error: err.message }));
  if (status.error) return { ok: false, stage: "status", error: status.error };
  if (!status.stdout.trim()) return { ok: true, skipped: true, reason: "no-git-changes" };
  const addTracked = await run("git", ["add", "-u"], { timeoutMs: 60_000 }).catch((err) => ({ error: err.message }));
  if (addTracked.error) return { ok: false, stage: "add-tracked", error: addTracked.error };
  await run("git", ["add", "work/self_optimizer.js", "start-self-optimizer.ps1", "work/promote_release_if_idle.ps1", "work/validate_release.js", "work/generate_realtime_optimizer_seed.js"], { timeoutMs: 60_000 }).catch(() => ({ skipped: true }));
  const staged = await run("git", ["diff", "--cached", "--name-only"], { timeoutMs: 30_000 }).catch((err) => ({ stdout: "", error: err.message }));
  if (staged.error) return { ok: false, stage: "staged", error: staged.error };
  const safeFiles = staged.stdout.split(/\r?\n/).filter(Boolean).filter((file) => !/(^|\/)(node_modules|outputs\/.*email_reports|outputs\/generated_data|\.workbench_runtime)\//.test(file) && !/\.(log|jsonl|lock)$/i.test(file) && !/smtp_password|password|secret|token/i.test(file));
  if (!safeFiles.length) return { ok: true, skipped: true, reason: "no-safe-staged-files" };
  await run("git", ["reset"], { timeoutMs: 30_000 }).catch(() => ({ skipped: true }));
  await run("git", ["add", ...safeFiles], { timeoutMs: 60_000 });
  const commit = await run("git", ["commit", "-m", message], { timeoutMs: 120_000 }).catch((err) => ({ error: err.message }));
  if (commit.error && !/nothing to commit/i.test(commit.error)) return { ok: false, stage: "commit", error: commit.error };
  const branch = (await run("git", ["branch", "--show-current"], { timeoutMs: 30_000 })).stdout.trim() || "main";
  const push = await run("git", ["push", "origin", branch], { timeoutMs: 180_000 }).catch((err) => ({ error: err.message }));
  if (push.error) return { ok: false, stage: "push", error: push.error };
  return { ok: true, branch, files: safeFiles };
}

async function maybeEmailOptimizationLog(kind, payload = {}) {
  const release = payload.release_event || {};
  if (!release.sent_worthy) {
    const reason = release.reason || "no-release-or-package-change";
    appendJsonl(logFile, { event: "optimization-log-email-skipped", kind, reason });
    appendJsonl(eventsFile, { project: "QL脑电分析平台", stage: "notify", event: "email-skipped", kind, reason });
    return { ok: true, skipped: true, reason };
  }
  const github = await syncReleaseToGithub(release);
  appendJsonl(logFile, { event: github.ok ? "github-sync-complete" : "github-sync-failed", kind, release_reason: release.reason, github });
  appendJsonl(eventsFile, { project: "QL脑电分析平台", stage: "github", event: github.ok ? "github-sync-complete" : "github-sync-failed", kind, release_reason: release.reason, github });
  return emailOptimizationLog(kind, payload);
}

function readJson(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8").replace(/^\uFEFF/, ""));
  } catch (err) {
    if (err.code === "ENOENT") return fallback;
    throw err;
  }
}

function writeJson(file, value) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function httpJson(url, timeoutMs = 30_000) {
  return new Promise((resolve, reject) => {
    const req = https.get(url, {
      headers: {
        "User-Agent": "QL-EEG-self-optimizer",
        "Accept": "application/vnd.github+json",
      },
    }, (res) => {
      let body = "";
      res.setEncoding("utf8");
      res.on("data", (chunk) => { body += chunk; });
      res.on("end", () => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          reject(new Error(`GET ${url} failed ${res.statusCode}: ${body.slice(0, 300)}`));
          return;
        }
        try {
          resolve(JSON.parse(body));
        } catch (err) {
          reject(err);
        }
      });
    });
    req.setTimeout(timeoutMs, () => {
      req.destroy(new Error(`timeout: ${url}`));
    });
    req.on("error", reject);
  });
}

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd: root,
      env: { ...process.env, ...(options.env || {}) },
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`timeout: ${command} ${args.join(" ")}`));
    }, options.timeoutMs || 120_000);
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => { stdout += chunk; });
    child.stderr.on("data", (chunk) => { stderr += chunk; });
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) resolve({ stdout, stderr });
      else reject(new Error(`${command} ${args.join(" ")} failed ${code}: ${stderr || stdout}`));
    });
  });
}

function newestDevWriteMs(dir = devRoot, depth = 0) {
  if (!fs.existsSync(dir) || depth > 5) return 0;
  let newest = 0;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (["node_modules", ".git", "assets", "data"].includes(entry.name)) continue;
    const full = path.join(dir, entry.name);
    let stat;
    try {
      stat = fs.statSync(full);
    } catch {
      continue;
    }
    if (entry.isDirectory()) {
      newest = Math.max(newest, newestDevWriteMs(full, depth + 1));
    } else if (/\.(js|css|html|json|md|py|mjs|ts|tsx|jsx)$/i.test(entry.name)) {
      newest = Math.max(newest, stat.mtimeMs);
    }
  }
  return newest;
}

function getDevIdleState(state) {
  const newestWriteMs = newestDevWriteMs();
  const stableForMs = newestWriteMs ? Date.now() - newestWriteMs : 0;
  const signature = `${newestWriteMs}`;
  const alreadyLearned = state.last_external_code_learning_dev_signature === signature;
  return {
    idle: Boolean(newestWriteMs) && stableForMs >= devIdleStableMs,
    stableForMs,
    newestWriteMs,
    signature,
    alreadyLearned,
  };
}

function walkLogs(dir, depth = 0, out = []) {
  if (depth > 3 || !fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === ".git") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walkLogs(full, depth + 1, out);
    else if (/\.(?:err\.)?log$/i.test(entry.name)) out.push(full);
  }
  return out;
}

function scanRuntimeStateIssues() {
  const issues = [];
  for (const rel of [
    "outputs/eeglab-mne-dev/assets/runtime-state.json",
    "outputs/eeglab-mne-release/assets/runtime-state.json",
  ]) {
    const file = path.join(root, rel);
    const runtime = readJson(file, null);
    if (!runtime) continue;
    const active = [...(runtime.runningTasks || []), ...(runtime.queuedTasks || [])];
    const failed = [...(runtime.completedResults || [])].filter((item) => item.ready === false || item.error);
    if (active.some((task) => bugPattern.test(JSON.stringify(task)))) issues.push({ source: rel, kind: "active-task-error" });
    for (const item of failed.slice(-10)) issues.push({ source: rel, kind: "failed-result", item });
  }
  return issues;
}

function scanRuntimeBugs(state) {
  const offsets = state.log_offsets || {};
  const recorded = [];
  for (const file of walkLogs(path.join(root, "outputs"))) {
    const stat = fs.statSync(file);
    const oldOffset = Number(offsets[file] || 0);
    const start = stat.size < oldOffset ? 0 : oldOffset;
    if (stat.size > start) {
      const fd = fs.openSync(file, "r");
      try {
        const length = Math.min(stat.size - start, 512_000);
        const buffer = Buffer.alloc(length);
        fs.readSync(fd, buffer, 0, length, stat.size - length);
        const lines = buffer.toString("utf8").split(/\r?\n/).filter((line) => bugPattern.test(line)).slice(-20);
        for (const line of lines) {
          const source = path.relative(root, file);
          const issue = recordIssue(state, { type: "bug", source, summary: line.slice(0, 500), evidence: line, next_action: "reproduce-and-add-release-or-runtime-regression" });
          const item = { type: "runtime-bug", source, summary: line.slice(0, 500), status: "pending", issue_id: issue.id };
          appendJsonl(queueFile, item);
          recordEvolutionEvent(state, { stage: "observe", event: "runtime-bug-detected", source, text: line, issue_id: issue.id });
          recorded.push(item);
        }
        offsets[file] = stat.size;
      } finally {
        fs.closeSync(fd);
      }
    }
  }
  for (const issue of scanRuntimeStateIssues()) {
    const tracked = recordIssue(state, { type: "runtime-state-bug", source: issue.source, summary: issue.kind, evidence: JSON.stringify(issue), next_action: "inspect-runtime-state-and-release-readiness" });
    appendJsonl(queueFile, { type: "runtime-state-bug", status: "pending", issue_id: tracked.id, ...issue });
    recordEvolutionEvent(state, { stage: "observe", event: "runtime-state-issue-detected", source: issue.source, text: issue.kind, issue_id: tracked.id });
    recorded.push({ ...issue, issue_id: tracked.id });
  }
  state.log_offsets = offsets;
  appendJsonl(logFile, { event: "runtime-bug-scan", recorded: recorded.length });
  return recorded;
}

function addFeedback(text, source = "user-feedback") {
  const state = readJson(stateFile, {});
  const issue = recordIssue(state, { type: source === "add-bug" ? "bug" : "feedback", source, summary: text, evidence: text, next_action: "classify-and-convert-to-eeg-workflow-test" });
  const item = { type: source, status: "pending", text: String(text || "").trim(), issue_id: issue.id };
  appendJsonl(queueFile, item);
  if (externalLearningPattern.test(item.text)) {
    state.external_code_learning_requested_at = nowIso();
    state.external_code_learning_requested_by = source;
    recordEvolutionEvent(state, { stage: "external_research", event: "external-code-learning-requested", source, text, issue_id: issue.id, area: "research", severity: "medium" });
  }
  recordEvolutionEvent(state, { stage: "observe", event: "user-feedback-recorded", source, text, issue_id: issue.id });
  writeJson(stateFile, state);
  appendJsonl(logFile, { event: "feedback-recorded", source, length: item.text.length });
  return item;
}

async function learnFromExternalCode(state, { force = false } = {}) {
  const queries = [
    "mne eeg preprocessing",
    "eeglab preprocessing",
    "eeg bids mne",
    "p300 oddball eeg",
  ];
  const fallbackRepos = [
    { name: "mne-tools/mne-python", url: "https://github.com/mne-tools/mne-python", description: "MNE-Python: EEG/MEG analysis, preprocessing, epochs, ICA, events, time-frequency workflows.", stars: 0, language: "Python", topics: ["mne", "eeg", "meg", "epochs", "ica"] },
    { name: "sccn/eeglab", url: "https://github.com/sccn/eeglab", description: "EEGLAB: MATLAB EEG processing with clean_rawdata, ICA, epoching, event workflows.", stars: 0, language: "MATLAB", topics: ["eeglab", "eeg", "ica", "clean_rawdata"] },
    { name: "sappelhoff/pyprep", url: "https://github.com/sappelhoff/pyprep", description: "PyPREP: PREP pipeline for EEG referencing, line noise, bad channel detection.", stars: 0, language: "Python", topics: ["PREP", "bad-channels", "eeg"] },
    { name: "mne-tools/mne-bids", url: "https://github.com/mne-tools/mne-bids", description: "MNE-BIDS: BIDS import/export workflow for MNE EEG/MEG projects.", stars: 0, language: "Python", topics: ["BIDS", "mne", "eeg"] },
    { name: "NeuroTechX/moabb", url: "https://github.com/NeuroTechX/moabb", description: "MOABB: benchmark datasets and reproducible EEG/BCI analysis pipelines.", stars: 0, language: "Python", topics: ["eeg", "benchmark", "bci", "datasets"] },
  ];
  const methodKeywords = [
    "raw.filter", "notch_filter", "set_montage", "events_from_annotations", "Epochs",
    "ICA", "find_bads_eog", "interpolate_bads", "autoreject", "PREP",
    "clean_rawdata", "ASR", "BIDS", "mne-bids", "PSD", "time-frequency", "P300",
  ];
  const repos = [];
  for (const query of queries) {
    const url = `https://api.github.com/search/repositories?q=${encodeURIComponent(query)}&sort=stars&order=desc&per_page=5`;
    try {
      const data = await httpJson(url);
      for (const item of data.items || []) {
        repos.push({
          name: item.full_name,
          url: item.html_url,
          description: item.description || "",
          stars: item.stargazers_count || 0,
          language: item.language || "",
          topics: item.topics || [],
        });
      }
    } catch (err) {
      appendJsonl(logFile, { event: "external-code-search-failed", query, error: err.message });
    }
  }
  const unique = [...new Map(repos.map((repo) => [repo.name, repo])).values()]
    .sort((a, b) => b.stars - a.stars)
    .slice(0, 12);
  const sourceRepos = unique.length ? unique : fallbackRepos;
  const corpus = sourceRepos.map((repo) => `${repo.name} ${repo.description} ${(repo.topics || []).join(" ")}`).join("\n");
  const learnedMethods = methodKeywords.filter((keyword) => new RegExp(keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i").test(corpus));
  const recommendations = [
    "上传 EDF 后补齐采样率、通道、事件标记、坏道数量的显式校验。",
    "预处理工作流优先覆盖 notch/filter、坏道检测、ICA/PREP/ASR、插值、epoch 和导出报告。",
    "在界面上把每一步参数、风险提示和可复现来源写清楚，避免用户把探索结果当临床结论。",
    "为 P300/oddball、BIDS/MNE 导入、坏道/事件缺失分别沉淀回归样例。",
  ];
  const report = {
    generated_at: nowIso(),
    trigger: force ? "manual-or-feedback" : "dev-version-idle",
    source: "GitHub public repository search metadata",
    repositories: sourceRepos,
    fallback_used: !unique.length,
    learned_methods: learnedMethods,
    recommendations,
    safety_note: "Only metadata and workflow ideas are summarized; external code is not copied into this project.",
  };
  writeJson(externalResearchFile, report);
  state.last_external_code_learning_at = nowIso();
  state.external_code_learning_requested_at = "";
  state.external_code_learning_requested_by = "";
  const issue = recordIssue(state, {
    type: "external-code-learning",
    source: "github-public-repositories",
    area: "research",
    severity: "medium",
    summary: `学习 ${sourceRepos.length} 个公开 EEG/MNE/EEGLAB 相关仓库，提炼 ${learnedMethods.length} 个方法关键词和 ${recommendations.length} 条工作流升级建议。`,
    evidence: JSON.stringify({ repos: sourceRepos.map((repo) => repo.name), learnedMethods, recommendations }),
    next_action: "convert-external-workflow-lessons-to-regression-tests-and-guided-ui-improvements",
  });
  appendJsonl(queueFile, { type: "external-code-learning", status: "pending", issue_id: issue.id, report: externalResearchFile });
  recordEvolutionEvent(state, { stage: "external_research", event: "external-code-learning-complete", source: "github", text: issue.summary, issue_id: issue.id, area: "research", severity: "medium" });
  appendJsonl(logFile, { event: "external-code-learning-complete", repos: sourceRepos.length, learned_methods: learnedMethods.length, fallback_used: !unique.length, report: externalResearchFile });
  return report;
}

function refreshRolePlayQueue(state) {
  const product = fs.existsSync(path.join(root, "PRODUCT.md"))
    ? fs.readFileSync(path.join(root, "PRODUCT.md"), "utf8").slice(0, 4000)
    : "";
  const roles = [
    "EEG novice uploading EDF for the first time",
    "paper reproduction reviewer checking MNE workflow validity",
    "clinical research assistant checking preprocessing risk",
    "platform operator checking release readiness",
  ];
  const reviews = roles.map((role) => ({
    role,
    prompt: `Role-play as ${role}; inspect QL EEG workflow risks, missing guidance, validation gaps, and release blockers.`,
    source_hint: product ? "PRODUCT.md" : "default-role-template",
  }));
  state.role_play_reviews = reviews;
  appendJsonl(logFile, { event: "role-play-queue-refreshed", roles: reviews.length });
  return reviews;
}

async function runIdleOptimization(force = false) {
  const results = {};
  results.seed = await run("node", ["work/generate_realtime_optimizer_seed.js"], { timeoutMs: 60_000 })
    .then((res) => ({ ok: true, stdout: res.stdout.slice(0, 1000) }))
    .catch((err) => ({ ok: false, error: err.message }));
  results.promote = await run("powershell", ["-ExecutionPolicy", "Bypass", "-File", "work/promote_release_if_idle.ps1"], { timeoutMs: 180_000 })
    .then((res) => ({ ok: true, stdout: res.stdout.slice(0, 1000) }))
    .catch((err) => ({ ok: false, error: err.message }));
  appendJsonl(logFile, { event: "idle-optimization", force, results });
  return results;
}

async function optimizeOnce({ force = false } = {}) {
  ensureDir(optimizerDir);
  const state = readJson(stateFile, {});
  const bugs = scanRuntimeBugs(state);
  const externalRequested = Boolean(state.external_code_learning_requested_at);
  const devIdle = getDevIdleState(state);
  const externalDue = force || externalRequested || (devIdle.idle && !devIdle.alreadyLearned);
  const externalResearch = externalDue
    ? await learnFromExternalCode(state, { force: force || externalRequested }).catch((err) => {
      appendJsonl(logFile, { event: "external-code-learning-failed", error: err.message });
      recordEvolutionEvent(state, { stage: "external_research", event: "external-code-learning-failed", source: "github", text: err.message, area: "research", severity: "medium" });
      return { ok: false, error: err.message };
    })
    : { skipped: true, reason: devIdle.idle ? "dev-version-already-learned" : "dev-version-still-being-edited", dev_idle: devIdle };
  if (externalDue && externalResearch && !externalResearch.error) {
    state.last_external_code_learning_dev_signature = devIdle.signature;
  }
  const lastRoleplayAt = Date.parse(state.last_roleplay_at || 0);
  const roleplayDue = force || bugs.length > 0 || externalRequested || !lastRoleplayAt || Date.now() - lastRoleplayAt >= roleplayUpdateMinMs;
  const roles = roleplayDue ? refreshRolePlayQueue(state) : state.role_play_reviews || [];
  const issues = bugs.map((bug) => ({
    id: bug.issue_id,
    source: bug.source,
    area: classifyIssue(bug.summary || bug.kind, bug.source).area,
    severity: classifyIssue(bug.summary || bug.kind, bug.source).severity,
    summary: bug.summary || bug.kind,
  }));
  const patchPlan = (roleplayDue || issues.length) ? writePatchPlan(state, issues, roles) : { pending_issues: [] };
  const roleplayDetails = roleplayDue ? writeRoleplayDetails(state, roles, issues) : state.last_roleplay_details || [];
  if (roleplayDue) state.last_roleplay_at = nowIso();
  const idle = true;
  const lastIdleAt = Date.parse(state.last_idle_optimization_at || 0);
  const idleDue = force || externalDue || !lastIdleAt || Date.now() - lastIdleAt >= idleUpdateMinMs;
  const idleResult = idle && idleDue ? await runIdleOptimization(force) : { skipped: true, reason: idle ? "idle-update-throttled" : "not-idle" };
  if (idle && idleDue) state.last_idle_optimization_at = nowIso();
  if (idle && idleDue) {
    const releaseEvent = extractReleaseEventFromIdle(idleResult);
    await maybeEmailOptimizationLog("release-optimization", { idle_optimization: idleResult, release_event: releaseEvent, issues: issues.slice(-10), roleplay_details: roleplayDetails });
  }
  updateLearningMemory(state, { issues, release: idleResult });
  state.last_seen_at = nowIso();
  state.last_result = { bugs: bugs.length, roles: roles.length, patch_plan: patchPlan.pending_issues.length, idle_optimization: idleResult, external_research: externalResearch };
  writeJson(stateFile, state);
  appendJsonl(logFile, { event: "self-optimizer-tick", ...state.last_result });
  return state.last_result;
}

async function main() {
  const [cmd, ...args] = process.argv.slice(2);
  if (cmd === "add-feedback" || cmd === "add-bug") {
    console.log(JSON.stringify(addFeedback(args.join(" "), cmd), null, 2));
    return;
  }
  if (cmd === "--once" || cmd === "once" || cmd === "--force") {
    console.log(JSON.stringify(await optimizeOnce({ force: process.argv.includes("--force") }), null, 2));
    return;
  }
  appendJsonl(logFile, { event: "self-optimizer-started", mode: "daemon", interval_ms: intervalMs });
  for (;;) {
    await optimizeOnce().catch((err) => appendJsonl(logFile, { event: "self-optimizer-failed", error: err.message }));
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

main().catch((err) => {
  appendJsonl(logFile, { event: "self-optimizer-crashed", error: err.stack || err.message });
  console.error(err.stack || err.message);
  process.exit(1);
});
