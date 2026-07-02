import fs from "node:fs";
import path from "node:path";

const repoRoot = process.cwd();
const outputDir = process.env.QLANALYSER_FRONTEND_DESIGN_DEBT_DIR
  || path.join(repoRoot, "work", "release_evidence", "20260628-frontend-design-debt-static");
const outputPath = path.join(outputDir, "frontend_design_debt_static.json");

const targets = [
  "frontend/app.js",
  "frontend/waveform-workbench.js",
  "frontend/epilepsy-workbench.js",
  "frontend/module-lab.js",
];

const expectedDuplicates = new Set([
  // The current app.js has known historical duplicates. Keep this list explicit
  // so new duplicates become visible without blocking the current cleanup packet.
  "frontend/app.js::renderProjectDataManagement",
  "frontend/app.js::selectedStateLabel",
  "frontend/app.js::projectStatusLabel",
  "frontend/app.js::fileStatusLabel",
  "frontend/app.js::updateDashboardSummaryCards",
  "frontend/app.js::fileDetailLabel",
  "frontend/app.js::preparationStatusLabel",
  "frontend/app.js::projectStatusLabelReadable",
  "frontend/app.js::fileStatusLabelReadable",
  "frontend/app.js::fileDetailLabelReadable",
  "frontend/app.js::preparationStatusLabelReadable",
  "frontend/app.js::selectedStateLabelReadable",
  "frontend/epilepsy-workbench.js::xOf",
  "frontend/module-lab.js::splitList",
  "frontend/module-lab.js::splitNumbers",
]);

fs.mkdirSync(outputDir, { recursive: true });

function lineNumberForIndex(source, index) {
  return source.slice(0, index).split(/\r?\n/).length;
}

function scanFunctions(filePath) {
  const abs = path.join(repoRoot, filePath);
  const source = fs.readFileSync(abs, "utf8");
  const matches = [];
  const patterns = [
    /\bfunction\s+([A-Za-z_$][\w$]*)\s*\(/g,
    /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>/g,
  ];
  for (const pattern of patterns) {
    let match;
    while ((match = pattern.exec(source))) {
      matches.push({ name: match[1], line: lineNumberForIndex(source, match.index) });
    }
  }
  const byName = new Map();
  for (const item of matches) {
    if (!byName.has(item.name)) byName.set(item.name, []);
    byName.get(item.name).push(item.line);
  }
  return [...byName.entries()]
    .filter(([, lines]) => lines.length > 1)
    .map(([name, lines]) => ({
      file: filePath,
      name,
      lines,
      expected: expectedDuplicates.has(`${filePath}::${name}`),
    }));
}

const duplicateFunctions = targets
  .filter((filePath) => fs.existsSync(path.join(repoRoot, filePath)))
  .flatMap(scanFunctions);

const unexpectedDuplicates = duplicateFunctions.filter((item) => !item.expected);

const report = {
  status: unexpectedDuplicates.length ? "failed" : "passed_with_known_debt",
  generatedAt: new Date().toISOString(),
  targets,
  duplicateFunctions,
  unexpectedDuplicates,
  knownDebtCount: duplicateFunctions.length - unexpectedDuplicates.length,
  unexpectedDuplicateCount: unexpectedDuplicates.length,
  guidance: [
    "Known duplicates must be removed through a scoped facade/state refactor.",
    "New duplicates should fail review unless explicitly allowlisted with a reason.",
  ],
};

fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
console.log(JSON.stringify({
  status: report.status,
  outputPath,
  knownDebtCount: report.knownDebtCount,
  unexpectedDuplicateCount: report.unexpectedDuplicateCount,
}, null, 2));

process.exit(unexpectedDuplicates.length ? 1 : 0);
