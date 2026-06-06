# NeuroCloud EEG MVP 部署说明

## 本地预览

```bash
npm install
npm run serve
```

打开：

```text
http://127.0.0.1:4173
```

## Docker / Nginx 部署

```bash
docker build -t neurocloud-eeg-mvp .
docker run -p 8080:80 neurocloud-eeg-mvp
```

线上访问：

```text
http://服务器IP:8080
```

## 静态站点部署

也可以直接把当前目录上传到静态网站服务，例如 Nginx、OSS 静态网站、Netlify、Vercel 或企业内网对象存储。

必须包含：

- `index.html`
- `styles.css`
- `app.js`
- `assets/`

## 上线前注意

- 当前支付宝和微信支付是模拟交互；正式上线需要商户号、回调地址、签名验签和订单状态服务。
- 当前上传是前端演示；正式产品应接入后端分片签名、对象存储直传、病毒/隐私扫描、任务队列和用户权限。
- EDF/MNE 分析资产已作为 MVP 示例随 `assets/` 发布。
