const fs = require("fs");
const path = require("path");

const assetDir = path.join(__dirname, "assets", "system_teaching_oddball");
const edfPath = path.join(assetDir, "system_visual_oddball_p300.edf");
const manifestPath = path.join(assetDir, "system_teaching_manifest.json");

function ascii(buffer, start, length) {
  return buffer.subarray(start, start + length).toString("ascii").trim();
}

function fail(message) {
  console.error(message);
  process.exit(1);
}

if (!fs.existsSync(edfPath)) fail(`Missing EDF: ${edfPath}`);
if (!fs.existsSync(manifestPath)) fail(`Missing manifest: ${manifestPath}`);

const header = fs.readFileSync(edfPath);
const headerBytes = Number(ascii(header, 184, 8));
const signalCount = Number(ascii(header, 252, 4));
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

if (signalCount !== 64) fail(`System teaching EDF must be 64 channels, got ${signalCount}`);
if (!Number.isFinite(headerBytes) || headerBytes < 256 + signalCount * 256) fail("EDF header is incomplete");
if (!Array.isArray(manifest.channels) || manifest.channels.length !== 64) fail("System teaching manifest must list 64 channels");
if (manifest.locked !== true || manifest.customerDeleteAllowed !== false) fail("System teaching dataset must be locked and not customer deletable");

console.log(`System teaching EDF verified: ${signalCount} channels`);
