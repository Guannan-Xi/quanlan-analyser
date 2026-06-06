const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const releaseDir = process.argv[2] ? path.resolve(process.argv[2]) : path.join(root, "outputs", "eeglab-mne-release");
const required = ["index.html", "styles.css", "app.js", "vendor/lucide.min.js", "assets/runtime-state.json"];
const forbidden = [
  /V1/i, /验收/, /测试工程师/, /心理学家\s*\d/, /认知神经科学家\s*\d/, /SMTP/i, /\.eml/i,
  /MVP/i, /内部/, /开发版/, /发布版/, /升级/, /提升版本/, /开发版评审/, /demo/i, /demo123456/i, /admin123456/i, /progress:\s*12/i,
  /customer_oddball_case/i, /publication_package/i, /已生成/, /充值金额/, /Oddball 小白用户/,
  /399467826@qq\.com/i, /示例\s*\d*\s*通道/i
];

const errors = [];
for (const rel of required) {
  if (!fs.existsSync(path.join(releaseDir, rel))) errors.push(`Missing required file: ${rel}`);
}

for (const rel of ["index.html", "styles.css", "app.js"]) {
  const file = path.join(releaseDir, rel);
  if (!fs.existsSync(file)) continue;
  const text = fs.readFileSync(file, "utf8");
  forbidden.forEach((pattern) => {
    if (pattern.test(text)) errors.push(`Forbidden release text ${pattern} in ${rel}`);
  });
}

const html = fs.readFileSync(path.join(releaseDir, "index.html"), "utf8");
for (const match of html.matchAll(/(?:src|href)="\.\/([^"]+)"/g)) {
  const rel = match[1].split("#")[0].split("?")[0];
  if (/^assets\/runtime-state\.json$/.test(rel)) continue;
  if (!fs.existsSync(path.join(releaseDir, rel))) errors.push(`Broken resource reference: ${rel}`);
}

const runtimeText = fs.readFileSync(path.join(releaseDir, "assets", "runtime-state.json"), "utf8").replace(/^\uFEFF/, "");
const runtime = JSON.parse(runtimeText);
const active = [...(runtime.runningTasks || []), ...(runtime.queuedTasks || [])];
if (active.some((task) => task.progress === 12)) errors.push("Runtime state contains stale 12% progress.");
if ((runtime.completedResults || []).some((item) => item.ready !== true)) errors.push("Completed result entry is not explicitly ready.");

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}

console.log("Release validation passed.");
