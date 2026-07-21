# QLanalyser Product Requirements Freeze

Date: 2026-06-22

## 1. Product intent

QLanalyser is a research EEG analysis platform. It must support real project work, real EDF ingestion, real data preparation, real analysis, real result review, and real report delivery.

It is not a static demo and not a clinical diagnosis product.

## 2. Frozen V1 scope

The V1 product scope must include:

- project creation and selection;
- project-level CRUD;
- project-scoped data management;
- EDF upload and metadata reading;
- data preview and preparation;
- PSD;
- ERP when events exist;
- result review;
- report download;
- customer account and billing surfaces that are not in the main workflow;
- acceptance evidence and rollback evidence.

## 3. Explicit non-scope for the project workbench page

The project workbench page must not default to:

- method workbench content;
- result interpretation essays;
- technical/internal field names;
- account billing noise;
- data lists before a project is selected;
- preparation details before a file is selected.

## 4. Freeze rules

When the current page is the project workbench:

1. The page should only show what is needed for project and data management.
2. The page should not expose unrelated methods or unneeded internal labels.
3. Each displayed status must have user meaning.
4. Each button must have a real action.
5. Each panel must have a current-stage purpose.

## 5. What counts as product-ready

A feature is product-ready only when all of the following are true:

- the UI is reachable by normal user clicks;
- the backend performs the real action;
- the action generates readable evidence;
- failures produce clear messages;
- the flow is covered by acceptance tests;
- the flow is reflected in the current docs.

## 6. Change rule

When a page or workflow changes:

- update the freeze section if scope changes;
- update the page inventory;
- update the acceptance matrix;
- update the change log;
- update the user guide if the user path changed.
