# QLanalyser 脑电分析平台部署说明

品牌：QuanLan BrainScience<sup>®</sup> / 全澜脑科学<sup>®</sup>

## 本地预览

```bash
npm install
npm run serve
```

打开：

```text
http://127.0.0.1:4173/?bust=local-cover-dom4
```

## 静态部署

当前版本是 QLanalyser 脑电分析平台的唯一静态前端成品目录，可直接由 Nginx、OSS 静态站点或任意静态文件服务托管。

必须包含：

- `index.html`
- `styles.css`
- `app.js`
- `assets/`
- `vendor/`

## Docker / Nginx

```bash
docker build -t qlanalyser-eeg-platform .
docker run -p 8080:80 qlanalyser-eeg-platform
```

访问：

```text
http://服务器IP:8080
```

## 说明

此目录为当前唯一保留的本地 4173 版本。上线前如需接入真实支付、短信/邮箱验证码、对象存储上传、任务队列和多用户权限，请以正式后端服务配置为准。

