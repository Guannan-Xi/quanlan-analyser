# QLanalyser Visual Layout DESIGN_SPEC Contract

Status: required for all generated visual artifacts.

This contract applies before generating or rendering any image, chart, diagram,
video frame, poster, report figure, subtitle card, self-media visual, or other
customer/reviewer-visible visual asset.

## Required Workflow

1. Create a numeric `DESIGN_SPEC` before rendering.
2. Rendering code must consume the `DESIGN_SPEC` constants.
3. Run preflight before human QA.
4. Fail preflight on overflow, collision, forbidden overlap, Chinese mojibake,
   replacement characters, three consecutive question marks, or density above
   the threshold.
5. Render only after preflight passes.
6. Evidence-check the rendered artifact after generation.

Draw-first-inspect-later is not allowed.

## Minimum DESIGN_SPEC Fields

Every visual generator must define these numeric fields:

```json
{
  "canvas": {
    "width_px": 1920,
    "height_px": 1080,
    "fps": 30
  },
  "safe_margins": {
    "top_px": 96,
    "right_px": 96,
    "bottom_px": 96,
    "left_px": 96
  },
  "panel_grid": {
    "columns": 12,
    "rows": 6,
    "gutter_px": 24,
    "min_panel_width_px": 240,
    "min_panel_height_px": 160
  },
  "zones": {
    "title": {"x": 96, "y": 72, "w": 1728, "h": 120},
    "plot": {"x": 144, "y": 220, "w": 1320, "h": 680},
    "axis": {"x": 144, "y": 900, "w": 1320, "h": 84},
    "legend": {"x": 1500, "y": 220, "w": 324, "h": 360},
    "caption": {"x": 144, "y": 984, "w": 1680, "h": 72}
  },
  "typography": {
    "title_min_font_px": 32,
    "body_min_font_px": 20,
    "axis_min_font_px": 18,
    "caption_min_font_px": 18,
    "subtitle_min_font_px": 24
  },
  "label_limits": {
    "max_labels": 24,
    "max_chars_per_line": 28,
    "max_lines": 2,
    "min_label_gap_px": 12
  },
  "density": {
    "max_ink_ratio": 0.34,
    "max_panel_fill_ratio": 0.78,
    "max_text_blocks": 18
  },
  "reserved_zones": [
    {"name": "brand", "x": 96, "y": 36, "w": 220, "h": 48},
    {"name": "source_note", "x": 96, "y": 1010, "w": 1728, "h": 46}
  ],
  "forbidden_overlap_zones": [
    {"name": "title_plot_overlap", "a": "title", "b": "plot"},
    {"name": "legend_plot_overlap", "a": "legend", "b": "plot"},
    {"name": "caption_axis_overlap", "a": "caption", "b": "axis"}
  ],
  "motion_bounds": {
    "max_translation_px_per_frame": 48,
    "max_scale_per_frame": 1.08,
    "max_rotation_deg_per_frame": 12,
    "min_subtitle_visible_ms": 1200
  }
}
```

## Preflight Rules

Preflight must reject:

- Any element outside the canvas or safe margins.
- Any zone collision not explicitly allowed.
- Any title, axis, legend, label, subtitle, or caption text below minimum font
  size.
- More labels, characters per line, lines, or text blocks than the numeric
  limits allow.
- Density above `max_ink_ratio` or `max_panel_fill_ratio`.
- Motion exceeding `motion_bounds`.
- Chinese mojibake, replacement characters, or three consecutive question marks.
- Missing screenshot, frame, SVG, PNG, PDF, or manifest evidence when the visual
  artifact is claimed as passed.

## Evidence Contract

Each visual artifact acceptance result must write JSON with:

- `status`
- `design_spec_path` or embedded `design_spec`
- `artifact_path`
- `canvas`
- `safe_margins`
- `checked_zones`
- `overflow_count`
- `collision_count`
- `mojibake_count`
- `density`
- `font_minimums`
- `motion_bounds`
- `warnings`
- `errors`

The release gate must fail if `status` is not `passed`.

## QLanalyser Web Workspace Layout Standard

Status: required for all customer-facing QLanalyser web workspace pages.

This section applies to the browser application shell, login cover, project
management, data management, data preparation, analysis, result review, report
delivery, user center, admin workspace, and module/lab workbenches.

### Design Targets

The product is a desktop research workbench. It should feel spacious on common
external monitors while staying safe on laptops.

Primary design target:

- `1920 x 1080`
- browser zoom `100%`
- OS display scale `100%` or `125%`
- left navigation visible
- no horizontal browser scroll

Minimum safe desktop target:

- `1366 x 768`
- browser zoom `100%`
- no element overlap, clipping of primary controls, or horizontal page overflow
- dense panels may stack vertically

Required verification widths:

- `1366 x 768`
- `1536 x 864`
- `1920 x 1080`
- `2048 x 1086`
- `2560 x 1440`

The best experience may be optimized for `1920 x 1080`, but the layout must not
break at the minimum safe desktop target.

### Browser Zoom Policy

Do not try to fully disable browser zoom. Browser zoom and OS scaling are user
and accessibility controls.

Do prevent common accidental page zoom in the workspace:

- Prevent default browser action for `Ctrl/Cmd + mouse wheel`.
- Prevent default browser action for `Ctrl/Cmd + +`, `Ctrl/Cmd + -`,
  `Ctrl/Cmd + =`, and `Ctrl/Cmd + 0`.
- Do not stop event propagation when preventing the browser default; application
  handlers such as waveform time-window zoom may still consume the same input.
- Do not depend on this protection for layout correctness. The layout must still
  pass the required verification widths.

### Layout Rules

- Left navigation should stay compact around `176-188px` on `1920 x 1080`
  workspace screens. It may reduce to about `168px` at `1366 x 768`.
- The main workspace should use the available width and should not cap dense
  workbench pages too narrowly.
- High-value data areas such as EEG canvas, result figures, tables, and report
  previews get priority width.
- Secondary explanation panels, lifecycle cards, tips, and account/service cards
  may move below the main work area on medium widths.
- Nested grids must be more conservative than the outer grid. If an outer page
  already has a right-side card, inner details must stack earlier instead of
  overflowing into the neighboring panel.
- The customer data-preparation waveform layout must use a single column at
  `1536px` and below; the EEG canvas keeps priority over the preparation side
  panel on laptop-width screens.
- Any grid child that contains text, tables, canvases, images, or controls must
  have `min-width: 0` unless it is intentionally fixed.
- Fixed minimum widths above `320px` require a breakpoint or container rule that
  stacks before collision.
- Page sections and panels must not rely on browser zoom `80%` to look correct.
- Default workspace icons should be `12-14px`. Icon buttons should be
  `26-30px`; primary/ghost buttons should usually be `28-32px` high on desktop.
- Cards, method tiles, empty states, and toolbar rows must be sized by task
  value, not by icon size. A large icon is not a substitute for hierarchy.
- Empty/blocked states should use a constrained width, usually `760-960px`, and
  must not stretch into a full-width blank card on wide monitors.
- Login/cover styling must be isolated from workspace density rules. Use an
  explicit login/workspace shell class or equivalent scope.

### Customer Workflow Rules

The customer path is:

`项目 -> 数据 -> 准备 -> 分析 -> 结果 -> 报告`

- Each customer page state must expose one primary next action. Other actions
  are secondary or hidden until useful.
- Dashboard/project page must show a compact six-step path and make the current
  missing step obvious.
- Data page without a project shows only `创建或打开项目`. Data page with a
  project but no data shows only `选择 EEG 文件` / upload.
- Preparation page without data sends the user to data selection. After data is
  selected, the primary action is `确认准备并进入分析`.
- Workflow page must not show a wall of disabled analysis methods before the
  preparation plan is truly ready. Show one blocker CTA first; reveal methods
  only when the analysis-ready gate passes.
- First analysis recommendation is PSD. ERP, TFR, PAC, connectivity, CSD, and
  epilepsy candidate-event review need prerequisites, boundaries, or collapsed
  advanced grouping.
- Results page without results points to the current missing upstream action.
  Report page with a completed task uses `生成报告` directly, not a detour back
  to workflow.
- Customer-facing services use trial/line-confirmed wording such as `试用服务记录`
  and `线下确认后更新`; avoid presenting online payment or formal financial
  service capability when it is not the product surface.
- Customer personal center must not use balance-led, top-up, payment-method, or
  amount-preset UI. Show service status and offline-confirmed records instead.
- QLanalyser remains a research/support EEG analysis product. Do not imply
  clinical diagnosis, triage, treatment, source localization certainty, or
  causal neuroscience claims from exploratory analysis screens.

Recommended breakpoint behavior:

- `>= 1800px`: dense workspaces may use two-level side-by-side layouts.
- `1366px - 1799px`: inner detail panels stack vertically when the page already
  uses a right-side panel.
- `< 1200px`: use compact single-column or simplified two-column layouts.
- `< 760px`: mobile-safe layout; no fixed sidebar over content.

### Failure Conditions

Visual acceptance fails when any required verification width shows:

- horizontal page overflow;
- card, table, tooltip, canvas, modal, or detail panel overlap;
- primary controls clipped or unreachable;
- text inside buttons/cards visually colliding with adjacent content;
- hidden state, disabled state, or empty state covering another panel;
- important content only readable at browser zoom `80%`;
- browser page zoom changing the application into a broken state.

### Evidence Contract

For every major visual/layout change, save or report:

- screenshots for at least `1366`, `1536`, `1920`, and one wide viewport;
- DOM measurements for the risky panels, including `left`, `right`, `width`,
  and overlap booleans;
- horizontal overflow status from `document.documentElement.scrollWidth` versus
  `clientWidth`;
- the applied breakpoint decision, especially when an inner grid stacks earlier
  than the outer page grid.
