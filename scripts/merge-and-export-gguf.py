"""
merge-and-export-gguf.py
========================
Task 1: Merge LoRA adapter with base model, export to GGUF, register in Ollama.

Usage:
    .train-venv/Scripts/python.exe scripts/merge-and-export-gguf.py

NOTES:
- device_map="cpu" is required on Windows (device_map="auto" crashes)
- Merge requires ~6GB RAM, runs entirely on CPU
- GGUF conversion requires llama.cpp (see instructions if missing)
"""

import os
import sys
import subprocess
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — all relative to the repo root so the script is portable
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT_DIR = REPO_ROOT / "factory_ai/output/training/lora_adapter/checkpoint-32"
MERGED_DIR = REPO_ROOT / "factory_ai/output/training/merged_model"
GGUF_PATH = REPO_ROOT / "factory_ai/output/training/campus-expert.gguf"
MODELFILE_PATH = REPO_ROOT / "factory_ai/output/training/Modelfile"

BASE_MODEL = "Qwen/Qwen2.5-1.5B"

# Common install locations for llama.cpp convert script
LLAMA_CPP_CANDIDATES = [
    Path(r"C:\Users\Daniel Amer\llama.cpp\convert_hf_to_gguf.py"),
    Path(r"C:\llama.cpp\convert_hf_to_gguf.py"),
    Path(r"C:\tools\llama.cpp\convert_hf_to_gguf.py"),
]

# Also honour an env var override
if os.environ.get("LLAMA_CPP_CONVERT"):
    LLAMA_CPP_CANDIDATES.insert(0, Path(os.environ["LLAMA_CPP_CONVERT"]))


def banner(msg: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# Part A — Merge LoRA adapter into the base model
# ---------------------------------------------------------------------------
def merge_lora() -> bool:
    banner("Part A: Merging LoRA adapter into base model (CPU)")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print(f"Base model  : {BASE_MODEL}")
    print(f"Adapter     : {CHECKPOINT_DIR}")
    print(f"Output dir  : {MERGED_DIR}")
    print()

    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    print(f"Compute dtype: {compute_dtype}")

    print("\nLoading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

    print("Loading base model on CPU (this may take a few minutes)...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        dtype=compute_dtype,
        device_map="cpu",
        trust_remote_code=True,
    )

    print("Attaching LoRA adapter...")
    model = PeftModel.from_pretrained(model, str(CHECKPOINT_DIR))

    print("Merging and unloading LoRA weights...")
    model = model.merge_and_unload()

    print(f"Saving merged model to: {MERGED_DIR}")
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(MERGED_DIR))
    tokenizer.save_pretrained(str(MERGED_DIR))

    print("\nMerge complete.")
    return True


# ---------------------------------------------------------------------------
# Part B — Convert merged model to GGUF via llama.cpp
# ---------------------------------------------------------------------------
def find_llama_convert() -> Path | None:
    for p in LLAMA_CPP_CANDIDATES:
        if p.exists():
            return p
    return None


def print_llama_instructions() -> None:
    print("\n" + "!"*60)
    print("  llama.cpp not found — GGUF conversion skipped.")
    print("!"*60)
    print("""
To enable GGUF export, do ONE of the following:

Option 1 — Clone llama.cpp locally:
  git clone https://github.com/ggerganov/llama.cpp C:\\Users\\Daniel Amer\\llama.cpp
  .train-venv\\Scripts\\pip install gguf sentencepiece
  Re-run this script.

Option 2 — Set env var to your convert script:
  set LLAMA_CPP_CONVERT=C:\\path\\to\\llama.cpp\\convert_hf_to_gguf.py
  Re-run this script.

Option 3 — Use HuggingFace online converter:
  https://huggingface.co/spaces/ggml-org/gguf-my-repo
  Upload the merged model from:
    {MERGED_DIR}

The merged model is ready — only the GGUF step is missing.
""".format(MERGED_DIR=MERGED_DIR))


def convert_to_gguf() -> bool:
    banner("Part B: Converting merged model to GGUF")

    convert_script = find_llama_convert()
    if convert_script is None:
        print_llama_instructions()
        return False

    print(f"Found convert script: {convert_script}")
    print(f"Output GGUF: {GGUF_PATH}")

    cmd = [
        sys.executable,
        str(convert_script),
        str(MERGED_DIR),
        "--outfile", str(GGUF_PATH),
        "--outtype", "q8_0",   # 8-bit quantised — fits Ollama well
    ]
    print(f"Running: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"\nERROR: GGUF conversion failed (exit code {result.returncode}).")
        print("The merged model is still available; try running the convert script manually.")
        return False

    print(f"\nGGUF written to: {GGUF_PATH}")
    return True


# ---------------------------------------------------------------------------
# Part C — Register the GGUF model with Ollama
# ---------------------------------------------------------------------------
def register_with_ollama() -> bool:
    banner("Part C: Registering with Ollama as 'campus-expert'")

    if not GGUF_PATH.exists():
        print(f"GGUF file not found at {GGUF_PATH} — skipping Ollama registration.")
        print("Run GGUF conversion first, then re-run this script.")
        return False

    if not MODELFILE_PATH.exists():
        print(f"Modelfile not found at {MODELFILE_PATH} — cannot register.")
        return False

    print(f"Modelfile: {MODELFILE_PATH}")
    print("Running: ollama create campus-expert ...\n")

    result = subprocess.run(
        ["ollama", "create", "campus-expert", "-f", str(MODELFILE_PATH)],
        check=False,
    )

    if result.returncode != 0:
        print(f"\nWARNING: ollama create exited with code {result.returncode}.")
        print("Is Ollama installed and running? https://ollama.com/download")
        return False

    print("\nOllama registration successful.")
    print("Test with: ollama run campus-expert 'Describe zone 3'")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    print(f"Repo root  : {REPO_ROOT}")
    print(f"Python     : {sys.executable}")

    merge_ok = False
    gguf_ok = False
    ollama_ok = False

    # ---- Part A ----
    try:
        merge_ok = merge_lora()
    except Exception as exc:
        print(f"\nFATAL: Merge failed — {exc}")
        import traceback
        traceback.print_exc()
        return 1

    # ---- Part B ----
    try:
        gguf_ok = convert_to_gguf()
    except Exception as exc:
        print(f"\nERROR: GGUF conversion raised an exception — {exc}")
        import traceback
        traceback.print_exc()

    # ---- Part C ----
    try:
        ollama_ok = register_with_ollama()
    except Exception as exc:
        print(f"\nERROR: Ollama registration raised an exception — {exc}")
        import traceback
        traceback.print_exc()

    # ---- Summary ----
    banner("Summary")
    print(f"  Merge  : {'OK' if merge_ok  else 'FAILED'}")
    print(f"  GGUF   : {'OK' if gguf_ok   else 'SKIPPED / FAILED'}")
    print(f"  Ollama : {'OK' if ollama_ok else 'SKIPPED / FAILED'}")
    print()

    if merge_ok and gguf_ok and ollama_ok:
        print("All steps completed successfully.")
        return 0
    elif merge_ok:
        print("Merge succeeded. Install llama.cpp and re-run to finish GGUF + Ollama steps.")
        return 2   # non-zero but not a hard failure
    else:
        print("Merge failed — check errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
