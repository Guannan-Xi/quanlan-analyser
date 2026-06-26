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
