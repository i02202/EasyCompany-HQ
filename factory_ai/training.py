"""
Campus Factory AI — Fine-Tuning Pipeline
==========================================
Converts crew interaction data into QLoRA training format and runs
fine-tuning using Unsloth on the local Ollama model.

Pipeline:
  1. Collect: DataCollector saves agent interactions as JSONL
  2. Format: Convert to ChatML training pairs (system/user/assistant)
  3. Train: QLoRA via Unsloth (4-bit, fits in 6GB VRAM)
  4. Export: Merge adapter → GGUF → ollama create
  5. Report: Emit training events to dashboard/Telegram

Requirements:
  pip install unsloth datasets trl peft
"""
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime

from factory_ai.config import OUTPUT_DIR, OLLAMA_MODEL, ZONES
from factory_ai.events import bus, EventType


TRAINING_DIR = OUTPUT_DIR / "training"
DATASET_PATH = OUTPUT_DIR / "training_data.jsonl"
CHATML_PATH = TRAINING_DIR / "chatml_dataset.jsonl"
ADAPTER_DIR = TRAINING_DIR / "lora_adapter"
GGUF_PATH = TRAINING_DIR / "campus-expert.gguf"
MODELFILE_PATH = TRAINING_DIR / "Modelfile"


def prepare_dataset() -> int:
    """
    Convert raw crew interaction JSONL into ChatML training pairs.
    Returns the number of training examples.
    """
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    if not DATASET_PATH.exists():
        print("[Training] No training data found")
        return 0

    raw_data = []
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                raw_data.append(json.loads(line))

    # Build ChatML pairs from task completions
    chatml_examples = []

    # System prompt for the fine-tuned model
    system_prompt = (
        "You are a campus design expert for isometric game environments. "
        "You understand a 40x40 tile grid with 128x64px isometric tiles. "
        "You design furniture layouts, assign textures, and validate designs "
        "for a modern tech company HQ with 13 zones."
    )

    # Group by agent for role-specific training
    for item in raw_data:
        if item.get("type") == "tool_use":
            continue  # Skip tool calls, focus on outputs

        agent = item.get("agent", "")
        task = item.get("task", "")
        output = item.get("output", "")

        if not task or not output:
            continue

        # Create a ChatML training example
        example = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"[{agent}] {task}"},
                {"role": "assistant", "content": output},
            ]
        }
        chatml_examples.append(example)

    # Add zone knowledge as training examples
    for zone_name, spec in ZONES.items():
        example = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Describe the {zone_name} zone specification"},
                {"role": "assistant", "content": (
                    f"Zone: {zone_name}\n"
                    f"Grid: rows {spec['rows']}, cols {spec['cols']}\n"
                    f"Floor tile: {spec['tile']}\n"
                    f"Wall type: {spec['wall']}\n"
                    f"Function: {spec['function']}"
                )},
            ]
        }
        chatml_examples.append(example)

    # Write ChatML dataset
    with open(CHATML_PATH, "w", encoding="utf-8") as f:
        for ex in chatml_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"[Training] Prepared {len(chatml_examples)} ChatML examples")
    return len(chatml_examples)


def run_training(epochs: int = 3, lr: float = 2e-4, batch_size: int = 2) -> bool:
    """
    Run QLoRA fine-tuning using Unsloth.
    Returns True if successful.
    """
    num_examples = prepare_dataset()
    if num_examples < 5:
        print(f"[Training] Only {num_examples} examples — need at least 5 to train")
        bus.emit(EventType.TRAINING_COMPLETE, {
            "status": "skipped",
            "reason": f"Only {num_examples} examples (need 5+)",
        })
        return False

    bus.emit(EventType.TRAINING_START, {
        "epochs": epochs,
        "examples": num_examples,
        "lr": lr,
        "model": OLLAMA_MODEL,
    })

    # Generate training script — tries Unsloth first, falls back to peft+trl
    train_script = TRAINING_DIR / "train.py"
    train_venv_python = str(Path(__file__).parent.parent / ".train-venv" / "Scripts" / "python.exe")
    train_script.write_text(f'''
"""Auto-generated QLoRA training script for campus design model."""
import json, sys, os
os.environ["PYTHONIOENCODING"] = "utf-8"

import torch
print(f"[Train] PyTorch {{torch.__version__}}, CUDA: {{torch.cuda.is_available()}}")

from datasets import Dataset
from trl import SFTTrainer, SFTConfig

# Try Unsloth first (2x faster), fall back to standard peft
USE_UNSLOTH = False
try:
    from unsloth import FastLanguageModel
    USE_UNSLOTH = True
    print("[Train] Using Unsloth (optimized)")
except Exception as e:
    print(f"[Train] Unsloth not available ({{e}}), using standard peft")
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

MODEL_NAME = "Qwen/Qwen2.5-7B"
MAX_SEQ = 2048

if USE_UNSLOTH:
    print("[Train] Loading model via Unsloth...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name="unsloth/Qwen2.5-7B-bnb-4bit",
        max_seq_length=MAX_SEQ, dtype=None, load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model, r=16,
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
        lora_alpha=16, lora_dropout=0, bias="none",
        use_gradient_checkpointing="unsloth",
    )
else:
    print("[Train] Loading model via HuggingFace 4-bit...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, quantization_config=bnb_config, device_map="auto", trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    lora_config = LoraConfig(
        r=16, lora_alpha=16, lora_dropout=0.05, bias="none",
        target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.gradient_checkpointing_enable()

# Load dataset
print("[Train] Loading dataset...")
examples = []
with open("{CHATML_PATH.as_posix()}", "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            examples.append(json.loads(line))

def format_chatml(example):
    text = ""
    for msg in example["messages"]:
        role = msg["role"]
        content = msg["content"]
        text += f"<|im_start|>{{role}}\\n{{content}}<|im_end|>\\n"
    return {{"text": text}}

dataset = Dataset.from_list(examples)
dataset = dataset.map(format_chatml)
print(f"[Train] Dataset: {{len(dataset)}} examples")

# Training
print("[Train] Starting training...")
trainer = SFTTrainer(
    model=model, tokenizer=tokenizer, train_dataset=dataset,
    args=SFTConfig(
        output_dir="{ADAPTER_DIR.as_posix()}",
        per_device_train_batch_size={batch_size},
        num_train_epochs={epochs},
        learning_rate={lr},
        logging_steps=1,
        save_strategy="epoch",
        fp16=not torch.cuda.is_bf16_supported(),
        bf16=torch.cuda.is_bf16_supported(),
        warmup_steps=5,
        max_seq_length=MAX_SEQ,
        dataset_text_field="text",
    ),
)

stats = trainer.train()
print(f"[Train] Done! Loss: {{stats.training_loss:.4f}}")

# Save adapter
model.save_pretrained("{ADAPTER_DIR.as_posix()}")
tokenizer.save_pretrained("{ADAPTER_DIR.as_posix()}")
print("[Train] Adapter saved to {ADAPTER_DIR.as_posix()}")

# Export to GGUF for Ollama
if USE_UNSLOTH:
    print("[Train] Exporting to GGUF via Unsloth...")
    try:
        model.save_pretrained_gguf(
            "{GGUF_PATH.parent.as_posix()}", tokenizer, quantization_method="q4_k_m",
        )
        print("[Train] GGUF exported successfully")
    except Exception as e:
        print(f"[Train] GGUF export failed: {{e}}")
else:
    print("[Train] GGUF export requires Unsloth. Adapter saved — merge manually with:")
    print(f"  python -m peft.merge_and_unload {ADAPTER_DIR.as_posix()}")
''', encoding="utf-8")

    # Generate Modelfile for Ollama
    MODELFILE_PATH.write_text(f"""FROM {GGUF_PATH.as_posix()}
SYSTEM "You are a campus design expert for isometric game environments. You understand a 40x40 tile grid with 128x64px isometric tiles. You design furniture layouts, assign textures, and validate designs for a modern tech company HQ with 13 zones."
PARAMETER temperature 0.7
PARAMETER num_ctx 2048
""", encoding="utf-8")

    # Run training
    print(f"[Training] Launching QLoRA training: {epochs} epochs, {num_examples} examples")

    try:
        # Use training venv with PyTorch installed
        python_exe = str(Path(__file__).parent.parent / ".train-venv" / "Scripts" / "python.exe")
        if not Path(python_exe).exists():
            python_exe = "python"  # fallback to system python
        print(f"[Training] Using Python: {python_exe}")
        proc = subprocess.Popen(
            [python_exe, str(train_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env={**dict(__import__("os").environ), "PYTHONIOENCODING": "utf-8"},
        )

        epoch_count = 0
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            print(f"  [Train] {line}")

            # Parse training progress from output
            if "'loss'" in line or "loss" in line.lower():
                try:
                    # Try to extract loss value
                    import re
                    loss_match = re.search(r"'loss':\s*([\d.]+)", line)
                    if loss_match:
                        loss = float(loss_match.group(1))
                        bus.emit(EventType.TRAINING_PROGRESS, {
                            "epoch": epoch_count,
                            "epochs_total": epochs,
                            "loss": loss,
                            "examples": num_examples,
                        })
                except Exception:
                    pass

            if "epoch" in line.lower() and "save" in line.lower():
                epoch_count += 1
                bus.emit(EventType.TRAINING_PROGRESS, {
                    "epoch": epoch_count,
                    "epochs_total": epochs,
                    "examples": num_examples,
                })

        proc.wait()

        if proc.returncode == 0:
            # Register model with Ollama
            print("[Training] Registering model with Ollama...")
            _register_with_ollama()

            bus.emit(EventType.TRAINING_COMPLETE, {
                "status": "success",
                "epochs": epochs,
                "examples": num_examples,
                "model": "campus-expert",
            })
            return True
        else:
            bus.emit(EventType.TRAINING_COMPLETE, {
                "status": "failed",
                "return_code": proc.returncode,
            })
            return False

    except Exception as e:
        print(f"[Training] Error: {e}")
        bus.emit(EventType.TRAINING_COMPLETE, {"status": "error", "error": str(e)})
        return False


def _register_with_ollama():
    """Create the fine-tuned model in Ollama."""
    if not GGUF_PATH.exists():
        print("[Training] GGUF not found, skipping Ollama registration")
        return

    try:
        result = subprocess.run(
            ["ollama", "create", "campus-expert", "-f", str(MODELFILE_PATH)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            print("[Training] Model 'campus-expert' registered with Ollama!")
        else:
            print(f"[Training] Ollama create failed: {result.stderr}")
    except Exception as e:
        print(f"[Training] Ollama registration error: {e}")


def get_training_info() -> dict:
    """Get current training state for dashboard."""
    info = {
        "dataset_exists": DATASET_PATH.exists(),
        "dataset_size": 0,
        "chatml_exists": CHATML_PATH.exists(),
        "chatml_size": 0,
        "adapter_exists": ADAPTER_DIR.exists(),
        "gguf_exists": GGUF_PATH.exists(),
        "model_registered": False,
    }

    if DATASET_PATH.exists():
        with open(DATASET_PATH, "r", encoding="utf-8") as f:
            info["dataset_size"] = sum(1 for _ in f)

    if CHATML_PATH.exists():
        with open(CHATML_PATH, "r", encoding="utf-8") as f:
            info["chatml_size"] = sum(1 for _ in f)

    # Check if campus-expert model exists in Ollama
    try:
        r = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=10,
        )
        info["model_registered"] = "campus-expert" in r.stdout
        info["qwen3_available"] = "qwen3:8b" in r.stdout
    except Exception:
        pass

    # Hybrid model info
    info["hybrid_mode"] = True
    info["knowledge_model"] = "campus-expert"
    info["knowledge_model_desc"] = "Qwen2.5-1.5B fine-tuned on campus design data (ChatML)"
    info["tool_model"] = "qwen3:8b"
    info["tool_model_desc"] = "Qwen3 8B with native tool-calling support"
    info["brain_model"] = "claude-sonnet-4-20250514"
    info["brain_model_desc"] = "Claude Sonnet for complex reasoning (Architect, Art Director, QA)"

    return info
