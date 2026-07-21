---
name: qlanalyser-ui-business-flow-review
description: Use this skill when QLanalyser UI looks cluttered, repetitive, developer-facing, or not aligned to the user's business workflow; also use it for screenshot review and customer-facing copy cleanup.
---

# QLanalyser UI Business Flow Review Skill

## Purpose

Make QLanalyser screens feel like a customer-usable EEG analysis product, not a pile of development notes, duplicate entries, internal platform settings, or repeated module descriptions.

UI must be organized around the business workflow the user is performing: upload, inspect, prepare data, analyze, review results, export reports, and handle billing/delivery when relevant.

## Triggers

Use this skill when:

- the user says the page is messy, repetitive, illogical, or not customer-facing
- reviewing UI screenshots
- building a module or workflow page
- adding navigation, cards, empty states, errors, or tutorial text
- deciding whether copy belongs in UI, docs, or developer notes

## Product Rule

After login, customers already know they are using QLanalyser for EEG analysis. Do not repeat what the product is on every screen.

Each screen should answer only five questions:

1. What step am I doing now?
2. What do I need to provide?
3. What will happen if I click this?
4. What is the current result?
5. What should I do next?

## Forbidden Customer UI Content

Unless explicitly inside admin or developer pages, do not show:

- internal development conversation text
- model, key, SMTP, control-console, or unrelated platform settings
- repeated product introductions or module-purpose paragraphs
- route names, manifest internals, debug IDs, or implementation notes
- long platform explanations
- multiple entries for the same action
- experimental features mixed into the formal customer workflow
- AI-chat style explanations that dominate operation pages

## Standard Screen Structure

Each customer-facing analysis page should include:

1. Page title: the current task, not a marketing slogan.
2. Current context: project, file, and task status in a compact area.
3. Primary action: one obvious next button.
4. Secondary actions: grouped and visually lower priority.
5. Work area: where the user edits, previews, selects, or inspects.
6. Result area: outputs, warnings, quality notes, and downloads.
7. Next step: what follows after this step is complete.

## Review Output

When reviewing a screenshot or page, output:

- Page goal.
- User primary path.
- Items that must be removed or merged.
- Items that must be kept or strengthened.
- Copy rewrite table.
- Development tasks for frontend, backend/API, and test/acceptance.

## Related Skills

- Use qlanalyser-team-orchestrator when dispatching UI work.
- Use qlanalyser-clean-code-quality-gate before accepting frontend code.
- Use qlanalyser-release-maintenance-gate before Pilot or customer demos.
