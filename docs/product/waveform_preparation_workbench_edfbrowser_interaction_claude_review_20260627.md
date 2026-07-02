# QLanalyser EDFbrowser 风格波形交互 Claude 评审

版本：2026-06-27

Claude says:

```text
# 1. SCOPE_CONFIRMATION

Reviewed ONLY the three embedded EDFbrowser-interaction documents dated 2026-06-27:
- `..._requirements_20260627.md`
- `..._detailed_design_20260627.md`
- `..._e2e_test_plan_20260627.md`

I did NOT inspect the git diff, `epilepsy-workbench.css/js`, `e2e_epilepsy_timechart_lab.mjs`, minimap code, or any working-tree change. I did not open the actual workbench source (the scope rule forbids it, and reading it would pull in out-of-scope material). All findings below are derived from the document text itself: internal consistency, completeness, feasibility, and requirement-to-test traceability. Target product treated as QLanalyser 07 main Canvas data-preparation waveform workbench. No TimeChart suggestion. No dependency-install suggestion.

# 2. VERDICT

Conditional GO. The direction is correct and the three documents are mostly coherent and mutually reinforcing. They are not yet an executable acceptance packet because four concrete gaps would force implementation guesswork or make named e2e cases unwritable. Close the P0 blockers (mode-switch affordance, `selected_segment` write-timing contradiction, missing numeric contract, missing automated gate/status-bar cases) and this becomes a clean GO. None of the blockers challenge the core design; they are specification holes, not design errors.

# 3. STRONGEST_POINTS

1. Browse-default / explicit-write modal split (req 4.3, design sec 2-3.3) is the right mental model and the central correct decision; it directly neutralizes the three named misoperations in req sec 2.
2. The deprecation list (req sec 6) is mirrored by hard e2e failure criteria (test sec 4) — requirement, rejection, and test close the loop instead of drifting apart.
3. Reuse of the proven Canvas contract (design sec 5: `times_sec` x-mapping, payload normalization, min/max bucket downsample, `requestSeq`/stale-ignore, `data_preparation_contract_version` gate, teaching-data protection) rather than a rewrite. This is the lowest-risk path and keeps the no-TimeChart constraint intact.
4. Time-zoom vs amplitude-sensitivity separation (req 4.2) with a dedicated test (T-EDF-09) — the single most common EEG-tool ergonomics complaint, handled explicitly.
5. Honest degradation paths: middle-drag automation flakiness gets a manual-screenshot fallback (T-EDF-05); browse-mode left-drag may degrade to crosshair/time-readout (design 3.3) rather than blocking the milestone (design sec 6 P0 ordering).
6. Non-medical wording discipline is consistent across all three docs and is itself a test assertion (T-EDF-10).

# 4. P0_BLOCKERS

1. Mode-switch affordance is undefined. Req 4.3 and design sec 2 define `browse/selectSegment/markBadSegment/markBadChannel`, but neither doc says HOW the user enters a mode (toolbar button? keyboard? `data-mode` attribute?). T-EDF-07 and T-EDF-08 both begin "switch to segment/bad-segment mode" with no trigger or selector. These two cases cannot be automated until the affordance and its selector exist. Define button/keyboard entry + a status-bar mode indicator.

2. `selected_segment` write-timing is self-contradictory across docs. Req 4.3 says select mode "updates `#segmentStart`/`#segmentEnd`, writes draft ONLY after save/confirm." Design 3.3 says select mode "writes `selected_segment` UI draft on release." The state model (design sec 2) has `draft.selected_segment` but no notion of an intermediate in-memory vs persisted tier. Implementers will diverge. Resolve into an explicit three-tier model: (a) transient in-progress selection, (b) in-memory UI draft, (c) persisted prep-plan revision — and state which tier each gesture/button writes.

3. No numeric contract. `clamp(duration, minDuration, maxDuration)` (design 3.1) never defines the bounds; amplitude `+/-` step and gain min/max are never given; wheel pan is `0.08` in design 3.1 but "8%-10%" in req 5.4; zoom factor `1.2` is design-only. T-EDF-02 (anchor drift), T-EDF-04 (`duration*0.1`), and T-EDF-09 (amplitude vs time) cannot be made deterministic without a single source-of-truth constants table.

4. The core analysis gate has no automated case. Goal #5 (req sec 3) and design sec 5 require downstream PSD/ERP to carry prep-plan id + revision + `data_preparation_contract_version`, and test sec 4 lists "unconfirmed plan can still submit PSD/ERP" as a hard failure. Yet Section 2 (P0 automation) has NO positive case asserting the gate blocks analysis until confirmation, and none asserting the carried id/revision/contract-version. The single most consequential acceptance criterion is untested in automation.

# 5. P1_RISKS

1. Zoom anchor tolerance conflicts with boundary clamp. T-EDF-02 requires anchor drift < `max(0.05s, 2/display_sample_rate_hz)`, but `clamp(new_start>=0, <=fileEnd)` (design 3.1) necessarily breaks the anchor invariant when zooming near t=0 or file end. The test will fail at boundaries unless it carves out a clamp exception.
2. Focus-retention priority conflict. Req 5.5 labels it P1 (enhancement), but design 3.2 makes it a "must" and test sec 4 makes focus-loss a hard acceptance failure. Mislabeled as optional in the requirements doc; it could be descoped while being a release gate. Promote to P0 in the requirements doc.
3. `Ctrl/Cmd + Home/End` (req 4.1 P0 table) is absent from the design keyboard table (3.2) and from every e2e case. Required but neither designed nor tested.
4. DOM-selector assumptions are unverified within the docs. `#eegCanvas`, `#eegStartInput`, `#segmentStart`, `#segmentEnd`, status-bar node, mode controls are asserted by tests but never inventoried; any mismatch with the real workbench breaks every case. Needs a confirmed selector inventory.
5. `audit_actions` / `restored_*` (design sec 2) have no schema. T-EDF-08 asserts audit retains "ever-created / ever-undone" but the audit shape and whether it persists are undefined, so the assertion is unimplementable as written.
6. Stale-response protection is described for wheel only (design 3.1). Keyboard PageUp/PageDown/arrow spam also triggers reloads; without the same `requestSeq` guard, fast keyboard nav can white-screen or apply a stale window. Not asserted by any keyboard case.
7. `Shift + wheel` 50% accelerate (req 5.4) is missing from the design input map (3.1 covers only with/without Ctrl) and untested.

# 6. P2_POLISH

1. Wheel direction sign is unspecified: normal-wheel `sign(deltaY)` pan and Ctrl-wheel `deltaY>0 -> 1.2` (zoom out) are never stated as a product decision ("scroll-down = forward / zoom-out"); T-EDF-01 only asserts "start changes," pinning nothing.
2. `+` key handling: plain `+` (req 4.2 / design 3.2) requires Shift on most layouts; `=`, numpad `+`, and Shift+`=` need handling.
3. Dual gain units `gain_px_per_uv` vs `sensitivity_uv_per_row` (design sec 2) — pick one canonical unit so the status-bar `50 uV/row` format is unambiguous.
4. `xToTime` must account for the channel-label gutter / left margin offset; note reuse of `times_sec` mapping explicitly for the anchor math.
5. Test env uses `customer_demo=auto` auto-login (known slow ~16-18s per prior session memory); the e2e plan budgets no wait for it.

# 7. AGREEMENT_ON_OLD_MODEL_REJECTION

Strongly agree with req sec 6. Rejecting (a) default-wheel-zoom, (b) default left-drag-pan, (c) Ctrl+wheel-changes-amplitude, (d) button-only navigation, and (e) waveform-as-static-preview is correct for EEG review ergonomics and matches EDFbrowser muscle memory. Item (c) in particular is right: Ctrl+wheel must mean time-zoom (EDFbrowser timescale), not amplitude. The rejection is well-supported because it is paired with mirrored e2e failure criteria, so the rejection is enforceable rather than aspirational. No dissent.

# 8. AGREEMENT_ON_BROWSE_WRITE_MODE_SPLIT

Agree — this is the strongest decision in the packet. EDFbrowser is read-dominant with explicit annotation; QLanalyser adds prep-plan drafts, so separating viewport navigation from draft writes is exactly correct and prevents the destructive accidental-write class. Three caveats before it is fully sound: (1) define the mode-switch affordance (P0 #1); (2) resolve the `selected_segment` draft-timing contradiction (P0 #2) so "write" has one meaning across the three tiers; (3) keep the documented browse-mode left-drag degradation (crosshair/time-readout when zoom-select is not yet built, design 3.3) — I endorse that fallback because it preserves the "left-drag is never default pan" guarantee even under partial implementation.

# 9. E2E_GAPS

1. No automated analysis-gate case (block PSD/ERP until confirmed; assert carried id/revision/`contract_version`) — see P0 #4.
2. No mode-switch / mode-indicator case (status bar must reflect current mode per req 4.4) — unwritable until P0 #1 closes.
3. No status-bar completeness case: req 4.2/4.4 demand window start-end, duration, time scale, sample rate, gain/sensitivity, channel count, filter/reference preview, plan state — only T-EDF-10 checks wording, nothing asserts these fields render.
4. No `Ctrl/Cmd + Home/End` case (P1 #3).
5. No standalone focus-retention case; it is only embedded in T-EDF-03 despite being a hard failure gate (P1 #2).
6. No keyboard-path stale-response / no-white-screen case (P1 #6).
7. No boundary case for zoom clamp at t=0 / file end; T-EDF-02 tolerance conflicts with clamp (P1 #1).
8. No amplitude clamp-bounds case, and T-EDF-09 cannot be deterministic without the numeric contract (P0 #3).
9. `audit_actions` assertion in T-EDF-08 has no defined schema to assert against (P1 #5).

# 10. NEXT_1_TO_2_HOUR_07_PACKET

Smallest set that unblocks the most, in order:

1. Mode-switch + indicator spec (30 min): toolbar controls with `data-mode` (or keyboard) for browse/select/badSegment/badChannel, plus status-bar mode text. Unblocks T-EDF-07, T-EDF-08, and the mode-indicator e2e gap.
2. Numeric-contract table (20 min): single source of truth for `minDuration`/`maxDuration`, wheel-pan fraction (reconcile 0.08 vs "8-10%"), zoom factor 1.2, amplitude min/max + step, and explicit wheel-direction sign. Unblocks T-EDF-02, T-EDF-04, T-EDF-09.
3. Resolve `selected_segment` write tiers (20 min): one paragraph defining transient -> in-memory draft -> persisted revision, and edit req 4.3 + design 3.3 to agree. Removes the only normative contradiction.
4. Add two automated e2e cases (30 min): (a) analysis-gate (unconfirmed plan blocks PSD/ERP; confirmed plan carries id/revision/`contract_version`), (b) status-bar completeness. These cover the highest-value untested requirement.
5. Selector inventory + boundary carve-out (15 min): list the asserted DOM selectors for the implementer to confirm against the real workbench, and add the t=0/file-end exception to T-EDF-02's tolerance.

Defer to a later packet: minimap, event-jump, `Shift+wheel` accelerate, `+`-key layout handling, audit schema detail.

# 11. final_receipt

completed_edfbrowser_interaction_claude_review
```

Codex note:

这份 Claude 评审为第三次有效调用结果。前两次结果分别出现中文编码损坏和评审范围跑偏；本文件采用第三次嵌入三份文档正文后的结果。Claude 明确确认只评审三份 EDFbrowser 交互文档，没有评审 git diff、癫痫工作台、TimeChart 或 minimap 代码。
