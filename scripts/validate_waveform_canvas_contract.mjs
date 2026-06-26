import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const evidenceDir = path.join(root, "work", "release_evidence", "20260627-waveform-canvas-workbench-dev");
fs.mkdirSync(evidenceDir, { recursive: true });

const read = (relativePath) => fs.readFileSync(path.join(root, relativePath), "utf8");
const app = read("frontend/app.js");
const html = read("frontend/index.html");
const css = read("frontend/styles.css");

const checks = [];
function check(name, pass, detail = {}) {
  checks.push({ name, pass: Boolean(pass), detail });
}

check("canvas uses shared time mapping", app.includes("function timeToCanvasX(") && app.includes("function canvasXToTime("));
check("waveform drawing uses times_sec mapping", /const sampleTime = Number\(times\[index\]/.test(app) && /timeToCanvasX\(sampleTime/.test(app));
check("event markers are drawn on canvas", app.includes("payload.events") && app.includes("ctx.lineTo(x, top + plotHeight)") && app.includes("事件"));
check("bad and selected segment labels are readable", app.includes('"坏段"') && app.includes('"选段"') && !app.includes(' ? "??"'));
check("normalize waveform exposes contract fields", [
  "schema_version",
  "display_sample_rate_hz",
  "downsampled",
  "downsample_method",
  "scale_uv",
  "bad_segments",
].every((token) => app.includes(token)));
check("frontend min max bucket fallback exists", app.includes("function minMaxBucketWaveform(") && app.includes('"min_max_bucket"'));
check("preview stale response guard exists", app.includes("previewRequestSeq") && app.includes("requestSeq !== eegState.previewRequestSeq"));
check("ctrl wheel zoom uses mouse anchor", app.includes("anchorRatio") && app.includes("canvasXToTime(event.clientX - rect.left"));
check("resize redraw exists", app.includes("ResizeObserver") && app.includes("redrawCurrentWaveform()"));
check("analysis task carries preparation contract version", app.includes("data_preparation_contract_version") && app.includes("qlanalyser-data-preparation-v0.2"));
check("analysis gate selector exists", html.includes('data-testid="analysis-preparation-gate"') && app.includes('[data-testid="analysis-preparation-gate"]'));
check("teaching protection selector exists", html.includes('data-testid="teaching-data-protected"') && app.includes('[data-testid="teaching-data-protected"]'));
check("responsive waveform layout folds before narrow tablet", /@media \(max-width: 1100px\)[\s\S]*\.waveform-prep-layout[\s\S]*grid-template-columns: 1fr/.test(css));
check("timechart not integrated in canvas workbench", !/from\s+["'].*timechart|TimeChart\(/i.test(app + html));

const pass = checks.every((item) => item.pass);
const report = {
  status: pass ? "passed" : "failed",
  generated_at: new Date().toISOString(),
  checked_files: ["frontend/app.js", "frontend/index.html", "frontend/styles.css"],
  checks,
};

const outputPath = path.join(evidenceDir, "waveform_canvas_contract_static_validation.json");
fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify(report, null, 2));
if (!pass) process.exit(1);
