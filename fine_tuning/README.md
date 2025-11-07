# EcoSupplyAI - LLM Fine-Tuning for Supply Chain Sustainability

## Overview

This directory contains a fine-tuning pipeline for adapting a small language model to the supply chain sustainability domain. The approach uses **LoRA (Low-Rank Adaptation)** to efficiently train only ~1-2% of model parameters, enabling domain-specific fine-tuning on consumer-grade hardware.

The fine-tuned model improves answer quality for:
- ESG (Environmental, Social, Governance) scoring and analysis
- Supply chain regulation compliance (CSRD, CBAM, EUDR, LkSG)
- Greenhouse gas emissions analysis (Scope 1, 2, and 3)
- Multi-criteria supplier comparison and ranking
- Supply chain sustainability risk assessment

## Files

| File | Description |
|------|-------------|
| `fine_tune_supply_chain.ipynb` | Main notebook with the complete fine-tuning pipeline |
| `fine_tune_data.json` | Generated training dataset (created when running the notebook) |
| `README.md` | This file |

## Prerequisites

### Hardware

- **Recommended**: NVIDIA GPU with at least 8GB VRAM (T4, A10G, RTX 3070+)
- **Minimum**: CPU execution is possible but extremely slow (not recommended for training)
- **Cloud alternative**: Azure ML Compute, AWS SageMaker, or Google Colab Pro

### Software

Python 3.10+ with the following packages:

```bash
pip install torch transformers datasets peft accelerate
pip install pandas matplotlib numpy
```

For Azure ML deployment (optional):

```bash
pip install azure-ai-ml azure-identity
```

### Recommended Environment Setup

```bash
# Create a virtual environment
python -m venv ecosupplyai-ft
source ecosupplyai-ft/bin/activate  # Linux/Mac
# ecosupplyai-ft\Scripts\activate   # Windows

# Install dependencies
pip install torch transformers datasets peft accelerate
pip install pandas matplotlib numpy jupyter
```

## How to Run

1. **Start Jupyter**:
   ```bash
   cd EcoSupplyAI/fine_tuning
   jupyter notebook fine_tune_supply_chain.ipynb
   ```

2. **Run cells sequentially** (Cells 1-8 set up the pipeline):
   - Cell 1-2: Imports and device detection
   - Cell 3-4: Dataset creation (generates `fine_tune_data.json`)
   - Cell 5-6: Tokenizer and data preprocessing
   - Cell 7-8: LoRA configuration and model setup

3. **Start training** (Cell 10):
   - Uncomment the `trainer.train()` line
   - Requires GPU; estimated 5-15 minutes on T4/A10G

4. **Evaluate** (Cell 12):
   - Uncomment the comparison code after training completes
   - Generates training loss curves and perplexity comparisons

5. **Export** (Cell 14):
   - Uncomment export functions to save the LoRA adapter and merged model

6. **Deploy** (Cell 16, optional):
   - Requires Azure ML workspace and credentials
   - Follow the commented code to register and deploy the model

## Fine-Tuning Approach

### Base Model

- **TinyLlama/TinyLlama-1.1B-Chat-v1.0** (1.1B parameters)
- Selected for efficient fine-tuning and fast inference
- Can be swapped for larger models (Phi-2, Llama-2-7B) for production

### LoRA Configuration

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Rank (r) | 16 | Good balance of capacity and efficiency |
| Alpha | 32 | Standard 2x rank scaling |
| Dropout | 0.1 | Prevents overfitting on small dataset |
| Target modules | q, k, v, o projections | All attention layers for comprehensive adaptation |

### Training Configuration

| Parameter | Value |
|-----------|-------|
| Epochs | 3 |
| Batch size | 4 (effective 16 with gradient accumulation) |
| Learning rate | 2e-4 |
| Scheduler | Cosine with warmup |
| Warmup steps | 10 |
| Precision | FP16 (CUDA) / FP32 (CPU) |

## Dataset

The training dataset contains 22 instruction-tuning examples in Alpaca format covering:

- **ESG Scoring** (4 examples): Score calculation, framework components, trend analysis
- **Regulations** (4 examples): CSRD, CBAM, EUDR, LkSG compliance guidance
- **Emissions** (4 examples): Scope 3 analysis, calculation methods, emission factors
- **Supplier Comparison** (4 examples): Multi-criteria ranking, improvement plan evaluation
- **Risk Assessment** (6 examples): Geographic risk, financial risk, climate risk, SBTs, onboarding, dashboards, double materiality, questionnaires

For production use, expand the dataset to 500-2000+ examples with domain expert validation.

## Output Artifacts

After training, the pipeline produces:

```
ecosupplyai-lora-adapter/     # LoRA weights only (~10-50 MB)
ecosupplyai-merged-model/     # Full merged model (~2-4 GB)
ecosupplyai-deployment/       # Azure ML deployment package
training_evaluation.png       # Loss curves and perplexity charts
```

## License

Internal use - EcoSupplyAI project.
