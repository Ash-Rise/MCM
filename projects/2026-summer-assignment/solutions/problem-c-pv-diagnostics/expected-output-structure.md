# Problem C Expected Output Structure

> 状态注记：实现已完成，本文保留为设计记录；当前状态以 `state.md`、`src/` 和 `results/` 为准。

> This is a planned interface for later implementation. Directories and result files listed below are not created in the model-design stage.

```text
problem-c-pv-diagnostics/
├── decisions.md
├── state.md
├── model-design-report.md
├── validation-plan.md
├── expected-output-structure.md
├── data/
│   └── derived/
│       ├── component_parameters.csv
│       ├── component_daily_generation.csv
│       └── station_daily_weather.csv
├── src/
│   ├── prepare_data.py
│   ├── diagnose_faults.py
│   ├── forecast_station.py
│   ├── rank_repairs.py
│   └── reproduce_all.py
├── results/
│   ├── task-1/
│   │   ├── component_diagnosis.csv
│   │   ├── fault_summary.json
│   │   ├── distribution_by_string.csv
│   │   └── shading_screen.csv
│   ├── task-2/
│   │   ├── candidate_metrics.csv
│   │   ├── loo_predictions.csv
│   │   ├── selected_model.json
│   │   └── day16_forecast.json
│   └── task-3/
│       ├── repair_ranking.csv
│       ├── priority_repairs.csv
│       └── improvement_summary.json
├── figures/
│   ├── task1_fault_distribution.*
│   ├── task2_candidate_validation.*
│   └── task3_repair_losses.*
└── tests/
    ├── test_data_contract.py
    ├── test_fault_rules.py
    ├── test_forecast_validation.py
    └── test_repair_ranking.py
```

## File roles

### Authority and design

- `decisions.md`: accepted human-owned semantic decisions only.
- `state.md`: current execution frontier.
- `model-design-report.md`: current candidate model contract; not numerical evidence.
- `validation-plan.md`: failure-driven checks and model-selection rules.
- `expected-output-structure.md`: planned implementation and result interfaces.

### Derived data

- `component_parameters.csv`: one row per module with identifiers and static metadata.
- `component_daily_generation.csv`: long-format component–day energy observations.
- `station_daily_weather.csv`: one row per day with weather and aggregated station generation where observed.

Derived data never replace the original DOCX as problem-fact authority.

### Task 1 results

- `component_diagnosis.csv`: module, supplied deviation, official class, shading-suspect flag, and metadata.
- `fault_summary.json`: reconciled state counts and threshold metadata.
- `distribution_by_string.csv`: group denominators, counts, and rates; additional grouping can use the same schema.
- `shading_screen.csv`: normalized-profile diagnostics separated from the official class.

### Task 2 results

- `candidate_metrics.csv`: one row per candidate with leave-one-day-out metrics and model complexity.
- `loo_predictions.csv`: 15 paired held-out predictions per candidate.
- `selected_model.json`: selected family, coefficients, selection evidence, residual scale, and limitations.
- `day16_forecast.json`: point forecast, expected-value confidence interval, realized-day prediction interval, units, and input forecast.

### Task 3 results

- `repair_ranking.csv`: all faulty modules with historical mean counterfactual, kWh/day loss, rank, and sensitivity fields.
- `priority_repairs.csv`: the selected 10 modules in primary order.
- `improvement_summary.json`: historical average station gain and supplementary day-16 gain with separate uncertainties.

### Source and tests

Source files are separated by model responsibility and share one data contract. `reproduce_all.py` will orchestrate the accepted deterministic workflow after code is authorized. Tests protect stable contracts: source dimensions, threshold boundaries, day-level validation separation, deviation inversion, and the top-10 ordering invariant.

## Explicit exclusions at this stage

- No `paper/` directory or paper artifact.
- No machine-learning pipeline, hyperparameter-search output, optimization solver, or large experiment store.
- No generated results or figures before implementation and validation are explicitly authorized.
