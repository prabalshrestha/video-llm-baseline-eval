# Quick Start: Run Directory Structure

## What Changed?

Evaluations now create **organized run directories** instead of single files. Each run gets its own timestamped folder with multiple output formats.

## Before vs After

### Before (Old)
```bash
python scripts/evaluation/evaluate_models.py --models gemini

# Output:
data/evaluation/llm_results_20250121_143052.json
data/evaluation/evaluation_summary_20250121_143052.txt
```

### After (New - Default)
```bash
python scripts/evaluation/evaluate_models.py --models gemini

# Output:
data/evaluation/runs/run_20250121_143052/
├── config.json                    # What you ran
├── unified_results.json           # All models
├── summary_report.txt             # Human-readable
├── models/
│   └── gemini-1.5-pro.json       # Individual model
└── metrics/
    ├── comparison_table.csv       # Excel-friendly
    └── aggregate_stats.json       # For scripts
```

## Quick Examples

### Run with Default Settings
```bash
python scripts/evaluation/evaluate_models.py --models gemini,qwen
```
✓ Creates timestamped run directory  
✓ Saves all formats  
✓ Updates `latest` symlink  

### Run with Custom Name
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --run-name experiment_1
```
✓ Creates `data/evaluation/runs/experiment_1/`

### Run Faster (Skip Individual Files)
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --no-per-model-files
```
✓ Only creates unified results (faster)

### Use Old Behavior (Single File)
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --output my_results.json
```
✓ Creates single file (backward compatible)

## Accessing Results

### View Latest Results
```bash
cd data/evaluation/runs/latest/
cat summary_report.txt
open metrics/comparison_table.csv
```

### Load in Python
```python
import json
import pandas as pd

# Unified results
with open("data/evaluation/runs/latest/unified_results.json") as f:
    data = json.load(f)

# Comparison table
df = pd.read_csv("data/evaluation/runs/latest/metrics/comparison_table.csv")
print(df)
```

### Compare Multiple Runs
```bash
# List all runs
ls data/evaluation/runs/

# Compare two runs
diff runs/run_20250121_143052/metrics/comparison_table.csv \
     runs/run_20250121_150324/metrics/comparison_table.csv
```

## File Descriptions

| File | Purpose | Format |
|------|---------|--------|
| `config.json` | Records what was run (models, dataset, settings) | JSON |
| `unified_results.json` | Complete results with all models | JSON |
| `summary_report.txt` | Human-readable summary | Text |
| `models/*.json` | Individual model results | JSON |
| `metrics/comparison_table.csv` | Quick comparison table | CSV |
| `metrics/aggregate_stats.json` | Aggregate metrics only | JSON |

## Benefits

### 🎯 **Organized**
- Each evaluation is self-contained
- Timestamped for easy tracking
- No more scattered files

### 📊 **Flexible**
- Unified file for comparison
- Individual files for focused analysis
- CSV for Excel/pandas

### 🔍 **Traceable**
- Config records exact setup
- Reproducible evaluations
- Easy to share specific results

### ⚡ **Efficient**
- Can skip per-model files if not needed
- `latest` symlink for quick access
- Backward compatible with old code

## New CLI Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--run-name` | Custom run name | `--run-name my_experiment` |
| `--no-per-model-files` | Skip individual model files | `--no-per-model-files` |

## Workflows

### Workflow 1: Quick Test → Full Run
```bash
# Test with 5 samples
python scripts/evaluation/evaluate_models.py \
  --models gemini --limit 5 --run-name test

# If good, run full evaluation
python scripts/evaluation/evaluate_models.py \
  --models gemini --run-name full_eval
```

### Workflow 2: Compare Models
```bash
# Run multiple models
python scripts/evaluation/evaluate_models.py \
  --models gemini,qwen,gpt4o

# Open comparison table
open data/evaluation/runs/latest/metrics/comparison_table.csv
```

### Workflow 3: Track Improvements
```bash
# Baseline
python scripts/evaluation/evaluate_models.py \
  --models gemini --run-name baseline

# Improved version
python scripts/evaluation/evaluate_models.py \
  --models gemini --gemini-model gemini-2.0-flash-exp \
  --run-name improved

# Compare
diff runs/baseline/metrics/comparison_table.csv \
     runs/improved/metrics/comparison_table.csv
```

## Tips

💡 **Use `--run-name` for experiments** - easier to find later  
💡 **Use `--no-per-model-files` for quick tests** - faster execution  
💡 **Use `latest` symlink** - always points to most recent  
💡 **Share run directories** - complete and self-contained  
💡 **Load CSV in Excel** - quick visual comparison  

## Troubleshooting

**Q: Where are my results?**  
A: Check `data/evaluation/runs/latest/`

**Q: Can I use the old single-file output?**  
A: Yes! Use `--output myfile.json`

**Q: How do I skip the per-model files?**  
A: Use `--no-per-model-files` flag

**Q: What if symlink doesn't work?**  
A: It's optional - just navigate to the timestamped directory

**Q: Can I delete old runs?**  
A: Yes, just delete the run directory: `rm -rf data/evaluation/runs/old_run/`

## More Information

- **Full Documentation**: MODEL_EVALUATION_GUIDE.md
- **Implementation Details**: HYBRID_OUTPUT_IMPLEMENTATION.md
- **Complete Status**: IMPLEMENTATION_COMPLETE.md
