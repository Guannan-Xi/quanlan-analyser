const fs = require("fs");
const path = require("path");

const outDir = path.resolve(__dirname, "../outputs/eeglab-mne-mvp/assets");
fs.mkdirSync(outDir, { recursive: true });

const fsHz = 256;
const seconds = 120;
const samples = fsHz * seconds;
const channels = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4"];
const events = [
  { onset: 10, duration: 0.2, type: "stim/target" },
  { onset: 24, duration: 0.2, type: "stim/standard" },
  { onset: 39, duration: 0.2, type: "stim/target" },
  { onset: 55, duration: 0.2, type: "button/left" },
  { onset: 74, duration: 0.2, type: "stim/standard" },
  { onset: 93, duration: 0.2, type: "stim/target" },
  { onset: 108, duration: 0.2, type: "artifact/blink" },
];

function noise(i, c) {
  const x = Math.sin((i * 12.9898 + c * 78.233) * 43758.5453);
  return (x - Math.floor(x) - 0.5) * 2;
}

function eegValue(i, c) {
  const t = i / fsHz;
  const alpha = 38 * Math.sin(2 * Math.PI * (9.5 + c * 0.2) * t + c * 0.4);
  const theta = 12 * Math.sin(2 * Math.PI * 5.2 * t + c);
  const beta = 8 * Math.sin(2 * Math.PI * 18 * t);
  const drift = 18 * Math.sin(2 * Math.PI * 0.2 * t + c * 0.1);
  let v = alpha + theta + beta + drift + noise(i, c) * 9;
  for (const ev of events) {
    if (ev.type.includes("target")) {
      const d = t - ev.onset - 0.32;
      v += (c >= 4 ? 18 : 10) * Math.exp(-(d * d) / 0.012);
    }
    if (ev.type.includes("blink") && c < 2) {
      const d = t - ev.onset;
      v += 180 * Math.exp(-(d * d) / 0.08);
    }
  }
  return Math.max(-200, Math.min(200, v));
}

function pad(value, length) {
  const text = String(value);
  return (text + " ".repeat(length)).slice(0, length);
}

function writeEdf() {
  const headerBytes = 256 + channels.length * 256;
  const records = seconds;
  const headerParts = [
    pad("0", 8),
    pad("X X X X", 80),
    pad("Startdate X X synthetic_eeg", 80),
    pad("06.06.26", 8),
    pad("10.00.00", 8),
    pad(headerBytes, 8),
    pad("", 44),
    pad(records, 8),
    pad("1", 8),
    pad(channels.length, 4),
  ];
  const field = (values, len) => values.map((v) => pad(v, len)).join("");
  headerParts.push(field(channels, 16));
  headerParts.push(field(channels.map(() => "AgAgCl cup"), 80));
  headerParts.push(field(channels.map(() => "uV"), 8));
  headerParts.push(field(channels.map(() => "-200"), 8));
  headerParts.push(field(channels.map(() => "200"), 8));
  headerParts.push(field(channels.map(() => "-32768"), 8));
  headerParts.push(field(channels.map(() => "32767"), 8));
  headerParts.push(field(channels.map(() => "HP:0.1Hz LP:45Hz N:50Hz"), 80));
  headerParts.push(field(channels.map(() => fsHz), 8));
  headerParts.push(field(channels.map(() => ""), 32));

  const buffers = [Buffer.from(headerParts.join(""), "ascii")];
  for (let rec = 0; rec < records; rec += 1) {
    for (let c = 0; c < channels.length; c += 1) {
      const b = Buffer.alloc(fsHz * 2);
      for (let j = 0; j < fsHz; j += 1) {
        const i = rec * fsHz + j;
        const uv = eegValue(i, c);
        const digital = Math.round((uv / 200) * 32767);
        b.writeInt16LE(Math.max(-32768, Math.min(32767, digital)), j * 2);
      }
      buffers.push(b);
    }
  }
  fs.writeFileSync(path.join(outDir, "synthetic_8ch_120s.edf"), Buffer.concat(buffers));
  fs.writeFileSync(
    path.join(outDir, "synthetic_8ch_120s_events.tsv"),
    ["onset\tduration\ttrial_type", ...events.map((e) => `${e.onset}\t${e.duration}\t${e.type}`)].join("\n"),
    "utf8"
  );
}

function svgFrame(title, subtitle, body, width = 920, height = 520) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="${width}" height="${height}" fill="#f7faf9"/>
  <rect x="18" y="18" width="${width - 36}" height="${height - 36}" rx="8" fill="#ffffff" stroke="#d9e0e7"/>
  <text x="42" y="58" font-family="Arial, Microsoft YaHei, sans-serif" font-size="25" font-weight="700" fill="#17202a">${title}</text>
  <text x="42" y="86" font-family="Arial, Microsoft YaHei, sans-serif" font-size="14" fill="#6b7785">${subtitle}</text>
  ${body}
</svg>`;
}

function polyline(points, x0, y0, w, h, color, strokeWidth = 2) {
  const min = Math.min(...points);
  const max = Math.max(...points);
  const den = max - min || 1;
  const d = points
    .map((v, i) => {
      const x = x0 + (i / (points.length - 1)) * w;
      const y = y0 + h - ((v - min) / den) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return `<polyline points="${d}" fill="none" stroke="${color}" stroke-width="${strokeWidth}" stroke-linejoin="round" stroke-linecap="round"/>`;
}

function axes(x, y, w, h, xlabel, ylabel) {
  let g = `<g stroke="#d9e0e7" stroke-width="1">`;
  for (let i = 0; i <= 4; i += 1) g += `<line x1="${x}" x2="${x + w}" y1="${y + (h * i) / 4}" y2="${y + (h * i) / 4}"/>`;
  g += `</g><line x1="${x}" x2="${x}" y1="${y}" y2="${y + h}" stroke="#526577"/><line x1="${x}" x2="${x + w}" y1="${y + h}" y2="${y + h}" stroke="#526577"/>
  <text x="${x + w / 2 - 35}" y="${y + h + 42}" font-family="Arial" font-size="13" fill="#6b7785">${xlabel}</text>
  <text x="${x - 34}" y="${y - 8}" font-family="Arial" font-size="13" fill="#6b7785">${ylabel}</text>`;
  return g;
}

function writeRawSegment() {
  const x = 72, y = 116, w = 780, h = 335;
  let body = axes(x, y, w, h, "Time: 12.0s - 18.0s", "uV");
  const colors = ["#157a77", "#d95f43", "#526577", "#d99a22"];
  for (let c = 0; c < 4; c += 1) {
    const pts = Array.from({ length: 600 }, (_, k) => eegValue((12 * fsHz) + Math.round(k * fsHz * 6 / 600), c) + c * 85);
    body += polyline(pts, x, y + c * 7, w, h - 28, colors[c], 1.7);
    body += `<text x="42" y="${y + 42 + c * 72}" font-family="Arial" font-size="13" fill="${colors[c]}">${channels[c]}</text>`;
  }
  body += `<rect x="418" y="${y}" width="2" height="${h}" fill="#d95f43"/><text x="430" y="${y + 20}" font-family="Arial" font-size="13" fill="#d95f43">stim/target</text>`;
  fs.writeFileSync(path.join(outDir, "analysis-raw-segment.svg"), svgFrame("数据段波形示例", "相对时间窗口与事件标记叠加显示", body));
}

function writeErp() {
  const x = 82, y = 112, w = 760, h = 342;
  const target = Array.from({ length: 350 }, (_, i) => {
    const t = -0.2 + i * 0.002;
    return -2 * Math.exp(-Math.pow(t - 0.1, 2) / 0.002) + 8 * Math.exp(-Math.pow(t - 0.32, 2) / 0.018) - 3 * Math.exp(-Math.pow(t - 0.48, 2) / 0.01);
  });
  const standard = target.map((v, i) => v * 0.48 + Math.sin(i / 16) * 0.4);
  let body = axes(x, y, w, h, "Time locked to stim onset (s)", "uV");
  body += `<line x1="${x + w * 0.286}" x2="${x + w * 0.286}" y1="${y}" y2="${y + h}" stroke="#17202a" stroke-dasharray="5 5"/>`;
  body += polyline(target, x, y, w, h, "#157a77", 3);
  body += polyline(standard, x, y, w, h, "#d95f43", 3);
  body += `<text x="650" y="130" font-family="Arial" font-size="15" fill="#157a77">Target P300</text><text x="650" y="154" font-family="Arial" font-size="15" fill="#d95f43">Standard</text>`;
  fs.writeFileSync(path.join(outDir, "analysis-erp.svg"), svgFrame("ERP 分析示例", "Oddball 条件平均、P300 峰值和潜伏期", body));
}

function writePsd() {
  const x = 80, y = 110, w = 760, h = 344;
  const pts = Array.from({ length: 180 }, (_, i) => {
    const f = 1 + i * 0.27;
    return 28 / Math.sqrt(f) + 42 * Math.exp(-Math.pow(f - 10, 2) / 9) + 8 * Math.exp(-Math.pow(f - 22, 2) / 22);
  });
  let body = axes(x, y, w, h, "Frequency (Hz)", "Power");
  body += `<rect x="${x + 124}" y="${y + 20}" width="110" height="${h - 20}" fill="#d9f0ee" opacity="0.85"/><text x="${x + 150}" y="${y + 42}" font-family="Arial" font-size="13" fill="#157a77">Alpha</text>`;
  body += polyline(pts, x, y, w, h, "#157a77", 3);
  fs.writeFileSync(path.join(outDir, "analysis-psd.svg"), svgFrame("静息态功率谱示例", "Welch PSD、频带积分和 Alpha 峰", body));
}

function writeTimeFreq() {
  const x = 84, y = 116, cell = 11, rows = 26, cols = 58;
  let body = axes(x, y, cols * cell, rows * cell, "Time (s)", "Hz");
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const t = c / cols;
      const f = r / rows;
      const v = Math.exp(-Math.pow(t - 0.42, 2) / 0.018) * Math.exp(-Math.pow(f - 0.38, 2) / 0.025) + 0.55 * Math.exp(-Math.pow(t - 0.72, 2) / 0.03) * Math.exp(-Math.pow(f - 0.68, 2) / 0.018);
      const hue = 195 - v * 170;
      const light = 88 - v * 38;
      body += `<rect x="${x + c * cell}" y="${y + (rows - r - 1) * cell}" width="${cell + 0.5}" height="${cell + 0.5}" fill="hsl(${hue}, 70%, ${light}%)"/>`;
    }
  }
  body += `<text x="704" y="168" font-family="Arial" font-size="14" fill="#6b7785">ERSP / ITC</text>`;
  fs.writeFileSync(path.join(outDir, "analysis-timefreq.svg"), svgFrame("时频分析示例", "Morlet 小波功率图，事件锁定频带变化", body));
}

function writeIca() {
  let body = "";
  const positions = [[160, 170], [360, 170], [560, 170], [260, 340], [460, 340], [660, 340]];
  positions.forEach(([cx, cy], i) => {
    body += `<circle cx="${cx}" cy="${cy}" r="58" fill="#f8faf9" stroke="#526577" stroke-width="2"/>`;
    for (let a = 0; a < 12; a += 1) {
      const rr = 48 - (a % 4) * 10;
      const px = cx + Math.cos(a * 1.7 + i) * rr;
      const py = cy + Math.sin(a * 1.7 + i) * rr;
      body += `<circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="${8 + (a % 3) * 3}" fill="${a % 2 ? "#d95f43" : "#157a77"}" opacity="0.72"/>`;
    }
    body += `<text x="${cx - 32}" y="${cy + 86}" font-family="Arial" font-size="14" fill="#17202a">IC ${i + 1}</text>`;
    body += `<text x="${cx - 40}" y="${cy + 106}" font-family="Arial" font-size="12" fill="${i === 1 ? "#d95f43" : "#6b7785"}">${i === 1 ? "Blink 0.91" : "Brain"}</text>`;
  });
  fs.writeFileSync(path.join(outDir, "analysis-ica.svg"), svgFrame("ICA 预处理示例", "ICLabel 分类、眼电成分识别和重建前检查", body));
}

function writeSource() {
  let body = `<path d="M428 132 C560 98 708 166 720 284 C732 420 570 456 434 418 C286 376 230 260 300 174 C326 144 372 134 428 132Z" fill="#eef4f3" stroke="#526577" stroke-width="2"/>`;
  const spots = [[452, 226, 46, "#d95f43"], [536, 258, 68, "#d99a22"], [396, 314, 50, "#157a77"], [610, 335, 36, "#d95f43"]];
  spots.forEach(([cx, cy, r, color]) => {
    body += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="${color}" opacity="0.72"/>`;
  });
  body += `<text x="92" y="180" font-family="Arial" font-size="15" fill="#526577">dSPM inverse solution</text><text x="92" y="210" font-family="Arial" font-size="15" fill="#526577">BEM head model</text><text x="92" y="240" font-family="Arial" font-size="15" fill="#526577">Sensor-to-source projection</text>`;
  fs.writeFileSync(path.join(outDir, "analysis-source.svg"), svgFrame("源定位分析示例", "皮层激活分布、ROI 平均和条件对比", body));
}

function writeMl() {
  let body = `<g font-family="Arial" font-size="15" fill="#17202a">`;
  const x = 230, y = 130, s = 92;
  const vals = [[0.86, 0.08, 0.06], [0.11, 0.78, 0.11], [0.05, 0.14, 0.81]];
  for (let r = 0; r < 3; r += 1) {
    for (let c = 0; c < 3; c += 1) {
      const v = vals[r][c];
      body += `<rect x="${x + c * s}" y="${y + r * s}" width="${s}" height="${s}" fill="rgba(21,122,119,${0.18 + v * 0.75})" stroke="#ffffff"/><text x="${x + c * s + 31}" y="${y + r * s + 54}" fill="${v > 0.5 ? "#ffffff" : "#17202a"}">${Math.round(v * 100)}%</text>`;
    }
  }
  ["Left", "Right", "Rest"].forEach((t, i) => {
    body += `<text x="${x + i * s + 24}" y="${y - 18}" fill="#6b7785">${t}</text><text x="${x - 70}" y="${y + i * s + 55}" fill="#6b7785">${t}</text>`;
  });
  body += `<text x="590" y="178" font-size="18" font-weight="700">Accuracy 83.1%</text><text x="590" y="210" fill="#6b7785">CSP + Logistic Regression</text><text x="590" y="238" fill="#6b7785">5-fold cross validation</text></g>`;
  fs.writeFileSync(path.join(outDir, "analysis-ml.svg"), svgFrame("机器学习分析示例", "运动想象分类、混淆矩阵和交叉验证", body));
}

writeEdf();
writeRawSegment();
writeErp();
writePsd();
writeTimeFreq();
writeIca();
writeSource();
writeMl();

console.log(JSON.stringify({
  outDir,
  files: fs.readdirSync(outDir).sort(),
}, null, 2));
