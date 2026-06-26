# QLanalyser Product Delivery Working Set

This folder is the living documentation set for product-level delivery.

## Canonical use

Read these documents together when planning, implementing, reviewing, or accepting product work:

- [Long-term goal and roadmap](./LONG_TERM_GOAL_AND_ONE_YEAR_ROADMAP.md)
- [Lab-to-main workflow gate](./lab_to_main_workflow_gate.md)
- [Unified review system governance](./review_system_governance.md)
- [Stage-gated development review system](./stage_gated_development_review_system.md)
- [Product documentation governance](./product_doc_governance.md)
- [Project workbench frontend detailed design](./project_workbench_frontend_detailed_design.md)
- [Project workbench backend detailed design](../architecture/project_workbench_backend_detailed_design.md)
- [Test and acceptance detailed design](../quality/test_acceptance_design.md)
- [Current V1 production readiness](../v01_production_readiness.md)

## Maintained companion docs

- [Product requirements freeze](./product_requirements_freeze.md)
- [Page interaction inventory](./page_interaction_inventory.md)
- [API contract inventory](./api_contract_inventory.md)
- [Data dictionary](./data_dictionary.md)
- [Acceptance matrix](./acceptance_matrix.md)
- [Release operations runbook](./release_ops_runbook.md)
- [User guide](./user_guide.md)
- [Module lifecycle matrix](./module_lifecycle_matrix.md)
- [Error code catalog](./error_code_catalog.md)
- [Page change log](./page_change_log.md)
- [Review log](./review_log.md)
- [Review system governance](./review_system_governance.md)
- [Product documentation governance](./product_doc_governance.md)

## Update rule

When a page changes, update the documents in this order:

1. `page_change_log.md`
2. `page_interaction_inventory.md`
3. `acceptance_matrix.md`
4. `api_contract_inventory.md` if the request/response shape changed
5. `data_dictionary.md` if fields or labels changed
6. `user_guide.md` if the user path changed
7. `module_lifecycle_matrix.md` if a method state changed
8. `error_code_catalog.md` if a new failure state or message appeared

When backend behavior changes, update:

1. `api_contract_inventory.md`
2. `data_dictionary.md`
3. `acceptance_matrix.md`
4. `release_ops_runbook.md` if operations or rollback changed

When a release gate changes, update:

1. `acceptance_matrix.md`
2. `release_ops_runbook.md`
3. `v01_production_readiness.md` if the public claim changes
4. `review_log.md` with the evidence, verdict, and next action

## Working rule

- Keep the docs plain, user-facing, and versioned.
- Do not write internal debug words into user-facing spec sections.
- Do not treat a visible button as valid unless the acceptance doc says how it is proven.
- Do not move a non-trivial task to the next development stage until the prior stage gate has evidence and GPT-5.5/Codex acceptance.
- Append to `page_change_log.md` rather than rewriting history.
