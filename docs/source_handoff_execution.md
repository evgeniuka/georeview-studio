# Source Handoff Execution

`Source Handoff Execution` is the v053 controlled execution layer for approved source handoffs.

It does four things:

- lists handoffs that are `ready_for_controlled_execution`;
- requires an explicit `execute approved handoff` acknowledgement;
- runs the selected profile through the controlled execution queue with `execute_now=true`;
- compares generated workspace tables against the mapper outputs recorded in the handoff.

## API

- `GET /api/source-handoff-execution`
- `GET /api/source-handoff-execution/candidates`
- `POST /api/source-handoff-execution/execute`
- `GET /api/source-handoff-execution/executions`
- `GET /api/source-handoff-execution/executions/{execution_id}`
- `GET /api/source-handoff-execution/executions/{execution_id}/download`

## Required Acknowledgements

The execution endpoint requires:

- `execution_ack = execute approved handoff`
- `source_files_read_only_ack = true`
- `generated_outputs_only_ack = true`
- `claim_boundary_ack = true`
- `compare_outputs_ack = true`

## Evidence Boundary

The workflow writes generated workspace outputs and comparison evidence under `analysis_output`. It does not edit, move, rename or overwrite source GIS files. Generated metrics remain infrastructure review indicators and data-quality evidence.

Approved wording:

`This location has infrastructure risk indicators and should be reviewed on-site.`
