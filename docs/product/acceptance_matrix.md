# QLanalyser Acceptance Matrix

Date: 2026-06-22

## 1. Purpose

This matrix tells us what must pass before a product slice can be called product-ready.

## 2. Acceptance layers

| Layer | Question | Evidence |
| --- | --- | --- |
| Unit | Does the smallest rule behave correctly? | Unit test, function-level check, status mapping check |
| API | Does the backend contract return the right data and errors? | API test, JSON response, status code, contract file |
| UI | Can a user click through the flow? | Browser trace, screenshot, UI test result |
| End-to-end | Can a real EDF flow complete? | Upload to result trace, report package, artifacts |
| Review system | Can multiple reviewers agree from different angles? | Multi-role review report, repeated round evidence |

## 3. Product-level required passes

### 3.1 Project management

Must pass:

- create project;
- select project explicitly from the project list or selector;
- edit project;
- archive project;
- delete project with confirmation;
- show meaningful project state.

### 3.2 Data management

Must pass:

- upload EDF;
- list files only inside the selected project;
- open preview;
- rename file;
- update / re-upload file with natural wording;
- delete file with confirmation;
- keep file lists collapsed until a project is selected;
- show meaningful file state.

### 3.3 Data preparation

Must pass:

- preview waveform;
- choose time window;
- mark bad channels;
- mark bad segments;
- handle annotations;
- save plan;
- detect plan revision conflict;
- show plain-language status.

### 3.4 Analysis and results

Must pass:

- submit valid task;
- reject invalid prerequisite state;
- show task progress;
- expose artifacts;
- open result page;
- download report package;
- preserve provenance.

### 3.5 Personal center

Must pass:

- show account info;
- show wallet summary;
- recharge flow;
- invoice flow;
- notification / inbox entry;
- help / feedback entry;
- keep non-workflow content out of the main page.

## 4. Pass / conditional pass / fail

### Pass

The path is fully usable, evidence-backed, and no user-blocking issue remains.

### Conditional pass

The main path is usable, but a non-blocking issue remains and the issue is logged with a clear next fix.

### Fail

The main path is broken, misleading, unusable, or not evidence-backed.

## 5. Evidence requirements

Each accepted slice must include:

- page or feature name;
- date;
- test scope;
- command or click path;
- screenshots or browser evidence;
- JSON or log evidence;
- blockers;
- next-step fix if needed.

## 6. Update rule

Whenever a page changes:

- update this matrix;
- update the page inventory;
- update the change log;
- update acceptance scripts if needed.
