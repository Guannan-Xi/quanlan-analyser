# QLanalyser Page Interaction Inventory

Date: 2026-06-22

## 1. Inventory purpose

This document maps each visible page or major panel to:

- default state;
- primary action;
- hidden-by-default content;
- status text policy;
- maintenance owner.

## 2. Pages and panels

| Page / panel | Default visible content | Primary action | Hidden by default | Notes |
| --- | --- | --- | --- | --- |
| Project workbench | Project list, explicit project selector, project CRUD | Select / create / edit project | Data list, preparation, methods, report body until a project is chosen | 07 product owner |
| Project data area | Current project file list, file actions, explicit file selector | Upload / select file inside the chosen project | Preparation details before file selection | 07 frontend / backend owner |
| Data preparation area | Preview controls, bad channel / bad segment / annotation actions | Save preparation plan | Analysis method pages | 07 product owner + backend owner |
| Analysis task area | Task creation, task status, selected method | Run PSD / ERP / other allowed module | Internal runner debug | Module owner |
| Result review area | Result summary, figures, tables, key warnings | Open result / review evidence | Raw internal storage fields | Module owner + quality owner |
| Report download area | Download button, package contents summary | Download report package | Hidden technical manifest details unless in expert mode | Release owner |
| Personal center | Account, balance, recharge, invoice, notifications, help, security | Account or billing action | Project and analysis workflow content | Ops / billing owner |
| Method workbench | Method preview or expert method entry | Open method lab | Main workflow content | Module owner |

## 3. Default expansion rules

- No project selected: do not expand project data or file lists.
- No file selected: do not expand preparation details.
- No preparation confirmation: do not expose downstream analysis as if it were ready.
- No completed task: do not show report as if already available.

## 4. Status label rules

Status labels must be understandable without internal field knowledge.

Preferred style:

- `可进入`
- `需上传数据`
- `已上传`
- `需处理`
- `已准备`
- `可提交`
- `已完成`
- `已归档`

Avoid showing raw storage enums like `active`, `pending`, `not_prepared` unless they are translated for expert debug mode only.

## 5. Visual noise rules

- Do not keep unrelated buttons on the first screen.
- Do not surface account/billing controls inside the main workflow; keep them in the personal center.
- Do not show a method page as the top-level project workbench action.
- Do not show user-unfriendly labels such as internal audit tokens or technical status fragments.
