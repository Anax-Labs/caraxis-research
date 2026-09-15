# Notebooks

## caraxis_finetune_3b_colab.ipynb

Google Colab notebook for QLoRA fine-tuning of `unsloth/Llama-3.2-3B-Instruct-bnb-4bit`.

### How to open

1. Go to [Google Colab](https://colab.research.google.com)
2. **File → Upload notebook**
3. Select `caraxis_finetune_3b_colab.ipynb`
4. **Runtime → Change runtime type → T4 GPU**
5. Run cells **0 → 10** in order

### Before running

Upload to Google Drive:

```
MyDrive/caraxis/train.jsonl
MyDrive/caraxis/val.jsonl
```

From your repo: `data/caraxis_analyst_v1/processed/train.jsonl` and `val.jsonl`

### Cell overview

| Cell | Purpose |
|------|---------|
| 0 | Configuration (paths, hyperparameters) |
| 1 | Install Unsloth |
| 2 | Verify install |
| 3 | Hugging Face login |
| 4 | Mount Drive + load dataset |
| 5 | Load model + LoRA |
| 6 | Format dataset |
| 7 | Train |
| 8 | Save adapter |
| 9 | Test inference |
| 10 | Save to Drive + download zip |
