const http = require("http");
const fs = require("fs");
const path = require("path");
const { handleApi } = require("./platform-adapters");

const root = __dirname;
const port = Number(process.argv[2] || process.env.PORT || 4173);
const legacyLocalBdfPath = process.env.QLANALYSER_LOCAL_BDF ||
  "D:\\Quanlan\\Data\\C64ERP\\【诺赫】北京301眼科–RSC–64RS（0610）\\C64RS_390026040074_260531103644.bdf";

const localBdfFileName = "C64RS_390026040074_260531103644.bdf";

function findFileByName(dir, fileName, maxDepth = 4) {
  if (maxDepth < 0) return "";
  let entries = [];
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return "";
  }
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isFile() && entry.name === fileName) return fullPath;
  }
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const found = findFileByName(path.join(dir, entry.name), fileName, maxDepth - 1);
    if (found) return found;
  }
  return "";
}

const localBdfPath = legacyLocalBdfPath && fs.existsSync(legacyLocalBdfPath)
  ? legacyLocalBdfPath
  : findFileByName("D:\\Quanlan\\Data\\C64ERP", localBdfFileName);
const localBdfManifestPath = path.join(root, "assets", "nohe_301_c64rs_0610", "nohe_analysis_manifest.json");

const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".tsv": "text/tab-separated-values; charset=utf-8",
  ".csv": "text/csv; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".edf": "application/octet-stream",
  ".bdf": "application/octet-stream",
  ".zip": "application/zip",
};

function resolveFile(url) {
  const parsed = new URL(url, `http://127.0.0.1:${port}`);
  const routePath = parsed.pathname === "/v0.html" ? "/index.html" : parsed.pathname;
  const pathname = decodeURIComponent(routePath === "/" ? "/index.html" : routePath);
  const filePath = path.resolve(root, `.${pathname}`);
  if (!filePath.startsWith(root)) return null;
  return filePath;
}

function json(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function readLocalBdfEventSummary() {
  try {
    const manifest = JSON.parse(fs.readFileSync(localBdfManifestPath, "utf8"));
    return {
      source: manifest.analysis || "BDF annotations",
      annotationSignal: manifest.raw?.annotation_signal || "",
      annotationCounts: manifest.raw?.annotation_counts || {},
      selectedCounts: manifest.epochs || {},
      limitations: manifest.limitations || [],
    };
  } catch {
    return null;
  }
}

function handleLocalSample(req, res, origin) {
  const parsed = new URL(req.url || "/", origin);
  if (!parsed.pathname.startsWith("/api/local-sample/")) return false;
  if (parsed.pathname === "/api/local-sample/nohe-bdf/meta") {
    fs.stat(localBdfPath, (error, stat) => {
      if (error || !stat.isFile()) {
        json(res, 404, { ok: false, message: "本地 BDF 测试数据不存在", path: localBdfPath });
        return;
      }
      json(res, 200, {
        ok: true,
        id: "local_nohe_301_c64rs_bdf",
        name: "本地测试 BDF：RSC-64RS ERP",
        fileName: path.basename(localBdfPath),
        format: "BDF",
        channelCount: 64,
        sizeBytes: stat.size,
        sizeLabel: `${(stat.size / 1024 / 1024).toFixed(1)} MB`,
        fileUrl: "/api/local-sample/nohe-bdf/file",
        eventsUrl: "./assets/nohe_301_c64rs_0610/events_used_for_erp.csv",
        eventSummary: readLocalBdfEventSummary(),
        sourceLabel: "本机测试数据",
      });
    });
    return true;
  }
  if (parsed.pathname === "/api/local-sample/nohe-bdf/file") {
    fs.stat(localBdfPath, (error, stat) => {
      if (error || !stat.isFile()) {
        res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "no-store" });
        res.end("Local BDF sample not found");
        return;
      }
      res.writeHead(200, {
        "Content-Type": "application/octet-stream",
        "Content-Length": stat.size,
        "Cache-Control": "no-store",
      });
      fs.createReadStream(localBdfPath).pipe(res);
    });
    return true;
  }
  json(res, 404, { ok: false, message: "未知本地样本接口" });
  return true;
}

const server = http.createServer(async (req, res) => {
  const origin = `http://127.0.0.1:${port}`;
  if (handleLocalSample(req, res, origin)) return;
  if ((req.url || "").startsWith("/api/")) {
    const handled = await handleApi(req, res, origin);
    if (handled) return;
  }
  const filePath = resolveFile(req.url || "/");
  if (!filePath) {
    res.writeHead(403);
    res.end("Forbidden");
    return;
  }
  fs.stat(filePath, (statError, stat) => {
    if (statError || !stat.isFile()) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Not found");
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      "Content-Type": mime[ext] || "application/octet-stream",
      "Content-Length": stat.size,
      "Cache-Control": "no-store",
    });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(port, "127.0.0.1", () => {
  console.log(`QLanalyser local static server listening at http://127.0.0.1:${port}/`);
});
