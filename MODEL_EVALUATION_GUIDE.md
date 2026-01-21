# Video LLM Model Evaluation Guide

This guide explains how to evaluate videos for misinformation using various Video LLM models including Gemini, GPT-4o, and Qwen.

## Supported Models

### 1. Google Gemini Models
Native video understanding with audio-visual analysis.

**Available Variants:**
- `gemini-1.5-pro` (default) - Most capable general-purpose model
- `gemini-2.0-flash-exp` - Best price-performance (Gemini 2.5 Flash)
- `gemini-exp-1206` - Advanced thinking model (Gemini 2.5 Pro)

**Setup:**
```bash
export GEMINI_API_KEY="your_google_ai_studio_api_key"
```

Get your API key from: https://makersuite.google.com/app/apikey

### 2. OpenAI GPT-4o
Frame-based video analysis (extracts frames + ASR pipeline).

**Available Variants:**
- `gpt-4o` - State-of-the-art reasoning and vision

**Setup:**
```bash
export OPENAI_API_KEY="your_openai_api_key"
```

### 3. Qwen VL Models
Open-source models with native video understanding.

**Available Variants:**
- `qwen2.5-vl-7b-instruct` (default) - Lightweight 7B model
- `qwen2.5-vl-32b-instruct` - Best for long-video analysis
- `qwen3-vl-8b-thinking` - 8B reasoning-enhanced model
- `qwen3-vl-32b` - Mid-tier 32B model
- `qwen3-vl-235b-a22b` - Flagship 235B model (most powerful)

**Setup Options:**

#### Option A: API Mode (Alibaba Cloud DashScope)
```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key"
pip install dashscope
```

Get API key from: https://dashscope.aliyun.com/

#### Option B: Local Inference
```bash
pip install torch transformers qwen-vl-utils
```

**Note:** Local inference requires significant GPU resources:
- 7B models: ~16GB VRAM
- 32B models: ~64GB VRAM
- 235B models: Multiple GPUs with 200GB+ VRAM

## Installation

### Basic Setup
```bash
# Install core dependencies
pip install -r requirements.txt

# For Qwen API access (optional)
pip install dashscope

# For Qwen local inference (optional)
pip install torch transformers qwen-vl-utils
```

## Output Structure

Evaluations are organized into **run directories** with the following structure:

```
data/evaluation/
├── runs/
│   ├── run_20250121_143052/
│   │   ├── config.json                    # Run configuration & model versions
│   │   ├── unified_results.json           # All models together (comparison)
│   │   ├── summary_report.txt             # Human-readable comparison
│   │   ├── models/
│   │   │   ├── gemini-2.0-flash-exp.json  # Individual model results
│   │   │   ├── qwen2.5-vl-7b-instruct.json
│   │   │   └── gpt-4o.json
│   │   └── metrics/
│   │       ├── comparison_table.csv       # Quick comparison table
│   │       └── aggregate_stats.json       # Aggregate metrics only
│   ├── run_20250121_150324/
│   │   └── ...
│   └── latest -> run_20250121_150324/     # Symlink to latest run
├── dataset.json
└── .eval_cache.json
```

### Output Files Explained

- **config.json**: Records evaluation setup (models, versions, dataset, settings)
- **unified_results.json**: Complete results with all models for easy comparison
- **summary_report.txt**: Human-readable summary with aggregate statistics
- **models/**: Individual JSON files per model for focused analysis
- **metrics/comparison_table.csv**: Quick spreadsheet-friendly comparison
- **metrics/aggregate_stats.json**: Aggregate metrics in JSON format
- **latest**: Symlink to the most recent run directory

## Usage

### Basic Evaluation

```bash
# Evaluate with default models (Gemini 1.5 Pro + GPT-4o)
python scripts/evaluation/evaluate_models.py \
  --dataset data/evaluation/dataset.json

# Evaluate with specific models
python scripts/evaluation/evaluate_models.py \
  --models gemini,qwen \
  --dataset data/evaluation/dataset.json
```

**Output:**
Creates a run directory at `data/evaluation/runs/run_YYYYMMDD_HHMMSS/` with all output files.

### Advanced Usage

#### Use Different Gemini Variant
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --gemini-model gemini-2.0-flash-exp
```

#### Use Different Qwen Variant (API)
```bash
python scripts/evaluation/evaluate_models.py \
  --models qwen \
  --qwen-model qwen3-vl-32b
```

#### Use Qwen with Local Inference
```bash
python scripts/evaluation/evaluate_models.py \
  --models qwen \
  --qwen-model qwen2.5-vl-7b-instruct \
  --qwen-local
```

#### Evaluate Multiple Models
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini,gpt4o,qwen \
  --gemini-model gemini-2.0-flash-exp \
  --qwen-model qwen2.5-vl-7b-instruct
```

#### Custom Run Name
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini,qwen \
  --run-name experiment_flash_vs_qwen7b
```

**Output:** Creates `data/evaluation/runs/experiment_flash_vs_qwen7b/`

#### Skip Per-Model Files (Faster)
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --no-per-model-files
```

**Use Case:** When you only need the unified results for quick comparison.

#### Limit Evaluation Samples
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini,qwen \
  --limit 10
```

#### Custom Output Path (Legacy Mode)
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --output results/my_evaluation.json
```

**Note:** Using `--output` disables run directory structure and uses old single-file output.

#### Disable Cache
```bash
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --no-cache
```

## Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--dataset` | Path to evaluation dataset JSON | `data/evaluation/dataset.json` |
| `--models` | Comma-separated list of models | `gemini,gpt4o` |
| `--gemini-model` | Gemini variant to use | `gemini-1.5-pro` |
| `--qwen-model` | Qwen variant to use | `qwen2.5-vl-7b-instruct` |
| `--qwen-local` | Use local Qwen inference | `False` |
| `--limit` | Limit number of samples | `None` (all) |
| `--output` | Custom output path (disables run dirs) | `None` |
| `--cache` | Cache file path | `data/evaluation/.eval_cache.json` |
| `--no-cache` | Disable caching | `False` |
| `--run-name` | Custom run name | Auto-generated timestamp |
| `--no-per-model-files` | Skip individual model files | `False` |

## Testing Individual Models

### Test Gemini Service
```bash
python scripts/evaluation/llms/gemini.py
```

### Test GPT-4o Service
```bash
python scripts/evaluation/llms/gpt4o.py
```

### Test Qwen Service
```bash
python scripts/evaluation/llms/qwen.py
```

## Working with Results

### Access Latest Results
```bash
# View latest run directory
cd data/evaluation/runs/latest/

# View comparison table in Excel/Numbers
open metrics/comparison_table.csv

# View summary report
cat summary_report.txt
```

### Load Results in Python
```python
import json
from pathlib import Path

# Load unified results
with open("data/evaluation/runs/latest/unified_results.json") as f:
    data = json.load(f)

# Load specific model results
with open("data/evaluation/runs/latest/models/gemini-2.0-flash-exp.json") as f:
    gemini_results = json.load(f)

# Load comparison table with pandas
import pandas as pd
comparison = pd.read_csv("data/evaluation/runs/latest/metrics/comparison_table.csv")
print(comparison)
```

### Compare Multiple Runs
```bash
# List all runs
ls -la data/evaluation/runs/

# Compare two specific runs
diff data/evaluation/runs/run_20250121_143052/metrics/comparison_table.csv \
     data/evaluation/runs/run_20250121_150324/metrics/comparison_table.csv
```

## Model Comparison

| Model | Native Video | Audio Support | Deployment | Best For |
|-------|-------------|---------------|------------|----------|
| **Gemini 1.5 Pro** | ✅ | ✅ | API | General-purpose, audio-visual |
| **Gemini 2.0 Flash** | ✅ | ✅ | API | Fast, cost-effective |
| **Gemini 2.5 Pro** | ✅ | ✅ | API | Complex reasoning |
| **GPT-4o** | ❌ (frames) | ❌ (ASR needed) | API | Image analysis, OCR |
| **Qwen 7B** | ✅ | ✅ | API/Local | Lightweight, accessible |
| **Qwen 32B** | ✅ | ✅ | API/Local | Long videos, detailed |
| **Qwen 235B** | ✅ | ✅ | API/Local | State-of-the-art, most powerful |

## Environment Variables

Create a `.env` file in the project root:

```bash
# Gemini (Google AI Studio)
GEMINI_API_KEY=your_gemini_api_key

# OpenAI GPT-4o
OPENAI_API_KEY=your_openai_api_key

# Qwen (Alibaba Cloud DashScope) - Optional
DASHSCOPE_API_KEY=your_dashscope_api_key
# OR
QWEN_API_KEY=your_qwen_api_key

# Custom API base (optional)
QWEN_API_BASE=https://your-custom-endpoint.com
```

## Troubleshooting

### Gemini Issues
- **"API key not configured"**: Set `GEMINI_API_KEY` environment variable
- **"Video processing failed"**: Check video file format (MP4 recommended)
- **Rate limits**: Use `gemini-2.0-flash-exp` for faster, cheaper inference

### GPT-4o Issues
- **"opencv-python not installed"**: Run `pip install opencv-python`
- **"API key not configured"**: Set `OPENAI_API_KEY` environment variable

### Qwen Issues
- **API Mode**: Set `DASHSCOPE_API_KEY` or `QWEN_API_KEY`
- **Local Mode**: 
  - Install: `pip install torch transformers qwen-vl-utils`
  - Check GPU: `nvidia-smi` (requires CUDA)
  - Use smaller models (7B) for consumer GPUs
- **"Failed to parse JSON"**: Model may need prompt tuning or retry

## Performance Tips

1. **Use appropriate model sizes**:
   - Testing: Qwen 7B, Gemini Flash
   - Production: Gemini Pro, Qwen 32B
   - Research: Qwen 235B, Gemini 2.5 Pro

2. **Enable caching** for iterative development

3. **Batch processing** for large datasets:
   ```bash
   # Process in chunks
   python scripts/evaluation/evaluate_models.py --limit 100
   ```

4. **Use local inference** for Qwen to reduce API costs (if you have GPUs)

## Analysis Workflows

### Workflow 1: Model Comparison (A/B Testing)
1. Run evaluation with multiple models:
   ```bash
   python scripts/evaluation/evaluate_models.py \
     --models gemini,qwen,gpt4o \
     --limit 50
   ```
2. Open `runs/latest/metrics/comparison_table.csv` in Excel
3. Compare accuracy, ROUGE, and semantic similarity scores
4. Review `runs/latest/summary_report.txt` for detailed breakdown
5. Select best-performing model for production

### Workflow 2: Model Improvement Tracking
1. Run baseline evaluation:
   ```bash
   python scripts/evaluation/evaluate_models.py \
     --models gemini \
     --run-name baseline_gemini_pro
   ```
2. Try different model variant:
   ```bash
   python scripts/evaluation/evaluate_models.py \
     --models gemini \
     --gemini-model gemini-2.0-flash-exp \
     --run-name improved_gemini_flash
   ```
3. Compare results:
   ```bash
   diff runs/baseline_gemini_pro/metrics/comparison_table.csv \
        runs/improved_gemini_flash/metrics/comparison_table.csv
   ```

### Workflow 3: Individual Model Deep Dive
1. Run evaluation for specific model
2. Load per-model JSON file:
   ```python
   import json
   with open("runs/latest/models/gemini-2.0-flash-exp.json") as f:
       data = json.load(f)
   
   # Analyze errors
   errors = [r for r in data["results"] 
             if not r["metrics"]["classification_correct"]]
   print(f"Errors: {len(errors)}")
   ```
3. Review specific failure cases
4. Adjust prompts or model selection

### Workflow 4: Quick Experiments
Use `--limit` for rapid iteration:
```bash
# Test with 5 samples
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --limit 5 \
  --run-name quick_test

# If results look good, run full evaluation
python scripts/evaluation/evaluate_models.py \
  --models gemini \
  --run-name full_evaluation
```

## Benefits of Run Directory Structure

1. **Organized**: Each evaluation is self-contained with timestamp
2. **Traceable**: `config.json` records exact setup for reproducibility
3. **Flexible**: Both unified and per-model files for different analysis needs
4. **Shareable**: Easy to share specific model results or full runs
5. **Comparable**: CSV format enables quick Excel/pandas analysis
6. **Accessible**: `latest` symlink always points to most recent results

## Next Steps

1. Prepare your evaluation dataset (see `scripts/data_processing/create_dataset.py`)
2. Set up API keys for desired models
3. Run evaluation on a small sample first (`--limit 5`)
4. Review results in run directory structure
5. Use comparison table for quick model selection
6. Run full evaluation with selected models
7. Analyze results using the provided workflows

## Support

For issues or questions:
- Check model-specific documentation
- Review error messages in logs
- Test individual services with test scripts
- Verify API keys and environment setup
