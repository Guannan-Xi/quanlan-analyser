# QLanalyser Product Documentation Governance

Date: 2026-06-22

## 1. Purpose

This document governs the living product documentation set for QLanalyser.

The documentation set is a working system, not a dump of notes.

## 2. Single source of truth

The product documentation set in `docs/product/` is the canonical source for:

- product scope;
- page behavior;
- user-facing labels;
- API contract inventory;
- data dictionary;
- acceptance criteria;
- release notes and maintenance logs.

If code and documentation differ, the divergence must be treated as a defect or an intentional scope change that is written into the docs first.

## 3. Mandatory maintenance rule

Whenever a page, API, status label, or user path changes:

1. Update the page change log.
2. Update the page interaction inventory.
3. Update the acceptance matrix.
4. Update the API contract inventory if the request or response changed.
5. Update the data dictionary if any user-visible field or label changed.
6. Update the user guide if the user path changed.
7. Update the module lifecycle matrix if a method state changed.
8. Update the error code catalog if a new user-visible error appeared.

## 4. Review-before-work rule

Before new product work starts, the reviewer must read:

- `docs/product/README.md`
- the page change log
- the page or module document relevant to the current work
- the acceptance matrix relevant to the current work
- the latest knowledge-base updates relevant to the task

## 5. Review-after-work rule

After product work finishes, the reviewer must record:

- what changed;
- what docs were updated;
- what evidence was used;
- whether the change affects pass / conditional pass / fail;
- whether any follow-up documentation work is still needed.

## 6. Page-by-page rule

This product is being maintained page by page.

That means:

- no page may change without a change-log entry;
- no new visible label may appear without being added to the data dictionary or inventory;
- no new workflow step may appear without an acceptance rule;
- no new backend field may appear without an API inventory update.

## 7. Ownership rule

Each living document should have a practical owner:

- product owner for product scope;
- frontend owner for page interaction inventory;
- backend owner for API contract inventory;
- quality owner for acceptance matrix and evidence;
- release owner for runbook and evidence packaging.

## 8. Merge rule

Do not merge unrelated departments into one document pile.

Shared review core is allowed.
Shared maintenance rules are allowed.
Department-specific scope documents must remain separate.
