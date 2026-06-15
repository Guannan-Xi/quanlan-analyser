import { sampleDataset } from "../../data/sampleDataset.js";

export const Data = {
  title: "数据管理",
  render(state) {
    const rows = state.files
      .map(
        (file) => `
          <tr>
            <td>${file.filename}</td>
            <td>${file.format}</td>
            <td>${file.subject}</td>
            <td><span class="badge ${file.status.includes("识别") ? "ok" : file.status.includes("等待") || file.status.includes("草稿") ? "warn" : ""}">${file.status}</span></td>
            <td>${file.risk}</td>
            <td>
              ${
                file.id === "demo-bdf"
                  ? '<button class="button secondary" type="button" data-action="editData">编辑</button>'
                  : file.id === "sub-02"
                    ? '<button class="button secondary" type="button" data-action="archiveData">归档</button>'
                    : file.id === "resting-demo"
                      ? '<button class="button secondary" type="button" data-action="deleteData">删除</button>'
                      : '<span class="badge">新建</span>'
              }
            </td>
          </tr>
        `
      )
      .join("");

    return `
      <section class="grid">
        <article class="panel">
          <h2>数据上传</h2>
          <p class="muted">原始 EEG 文件保存到 data/uploads，并关联到对应的被试和 session 记录。</p>
          <div class="toolbar">
            <button class="button" type="button" data-action="chooseEeg">选择 EEG 文件</button>
            <button class="button secondary" type="button" data-action="uploadEvents">上传事件 TSV</button>
            <button class="button secondary" type="button" data-action="createData">新增数据记录</button>
          </div>
        </article>
        <article class="panel">
          <h2>元数据</h2>
          <ul class="list">
            <li><span>文件格式</span><strong>EDF / SET / BDF</strong></li>
            <li><span>采样率</span><strong>自动识别</strong></li>
            <li><span>通道数</span><strong>自动识别</strong></li>
          </ul>
        </article>
        <article class="panel wide">
          <h2>真实 BDF 示例数据</h2>
          <p class="muted">${sampleDataset.label}：${sampleDataset.filename}</p>
          <div class="score-grid">
            <div class="score"><span>设备/格式</span><strong>${sampleDataset.device} / ${sampleDataset.format}</strong></div>
            <div class="score"><span>大小</span><strong>${sampleDataset.size}</strong></div>
            <div class="score"><span>EEG 通道</span><strong>${sampleDataset.eegChannelCount}</strong></div>
            <div class="score"><span>Header 信号</span><strong>${sampleDataset.headerSignalCount}</strong></div>
            <div class="score"><span>采样率</span><strong>${sampleDataset.samplingRate}</strong></div>
            <div class="score"><span>时长</span><strong>${sampleDataset.duration}</strong></div>
            <div class="score"><span>事件标记</span><strong>${sampleDataset.annotationsCount} 条</strong></div>
            <div class="score"><span>读取方式</span><strong>${sampleDataset.mneReader}</strong></div>
          </div>
          <p class="muted">${sampleDataset.handling}</p>
        </article>
        <article class="panel wide dense">
          <h2>文件队列</h2>
          <table class="table">
            <thead><tr><th>文件</th><th>格式</th><th>被试</th><th>状态</th><th>风险</th><th>操作</th></tr></thead>
            <tbody>${rows}</tbody>
          </table>
        </article>
      </section>
    `;
  }
};
