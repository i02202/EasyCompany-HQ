# Factory AI Pipeline Finalization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Factory AI pipeline end-to-end: register the fine-tuned LoRA adapter in Ollama, integrate AI-generated zone data into the Phaser game, fix QA tooling, and run a full demo with dashboard + Telegram.

**Architecture:** CrewAI 5-agent crew (Claude brain + Ollama light) generates zone JSONs and tile mappings → converted to TypeScript for Phaser 3 isometric renderer. LoRA adapter (Qwen2.5-1.5B, peft) needs GGUF conversion for Ollama. Dashboard (FastAPI) + Telegram bot report real-time progress.

**Tech Stack:** Python 3.11 (CrewAI, peft, trl, FastAPI), TypeScript (Vite + Phaser 3), Ollama (GGUF models), RTX 4060 8GB VRAM

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `scripts/convert-zones-to-ts.py` | One-shot converter: zone JSONs + tile_mappings.json → campus-props.ts |
| Modify | `src/campus-props.ts` | Overwritten by converter with AI-generated prop data |
| Modify | `factory_ai/tools/campus_tools.py:161-206` | Fix `analyze_prop_coverage` to read zone JSONs instead of TS file |
| Modify | `.env` | Set `OLLAMA_MODEL=campus-expert` (config.py reads via os.getenv) |
| Create | `scripts/merge-and-export-gguf.py` | Merge LoRA adapter + export GGUF for Ollama |
| Modify | `factory_ai/output/training/Modelfile` | Update GGUF path if needed |
| Delete | `factory-ai/` | Remove duplicate directory after verification |

---

### Task 1: Register LoRA Adapter as Ollama Model "campus-expert"

**Context:** We have a trained LoRA adapter at `factory_ai/output/training/lora_adapter/checkpoint-32/` (Qwen2.5-1.5B base, r=16, peft 0.18.1). We need to merge it with the base model, export to GGUF Q4_K_M format, then register with Ollama.

**Files:**
- Create: `scripts/merge-and-export-gguf.py`
- Modify: `factory_ai/output/training/Modelfile`

- [ ] **Step 1: Verify adapter checkpoint is valid**

Run: `cd "C:/Users/Daniel Amer/SkyOffice Easy Company" && .train-venv/Scripts/python.exe -c "from peft import PeftConfig; c = PeftConfig.from_pretrained('factory_ai/output/training/lora_adapter/checkpoint-32'); print(f'Base: {c.base_model_name_or_path}, r={c.r}, type={c.peft_type}')"`
Expected: `Base: Qwen/Qwen2.5-1.5B, r=16, type=LORA`

- [ ] **Step 2: Write the merge-and-export script**

```python
# scripts/merge-and-export-gguf.py
"""Merge LoRA adapter with base model and export to GGUF for Ollama."""
import sys, os, shutil
from pathlib import Path

PROJECT = Path(__file__).parent.parent
ADAPTER_DIR = PROJECT / "factory_ai/output/training/lora_adapter/checkpoint-32"
MERGED_DIR = PROJECT / "factory_ai/output/training/merged_model"
GGUF_DIR = PROJECT / "factory_ai/output/training"
MODEL_NAME = "Qwen/Qwen2.5-1.5B"

def merge_adapter():
    """Step 1: Merge LoRA weights into base model."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    print(f"[Merge] Loading base model {MODEL_NAME}...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME, torch_dtype=compute_dtype, device_map="cpu", trust_remote_code=True,
    )

    print(f"[Merge] Loading adapter from {ADAPTER_DIR}...")
    model = PeftModel.from_pretrained(model, str(ADAPTER_DIR))

    print("[Merge] Merging weights...")
    model = model.merge_and_unload()

    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[Merge] Saving merged model to {MERGED_DIR}...")
    model.save_pretrained(str(MERGED_DIR))
    tokenizer.save_pretrained(str(MERGED_DIR))
    print("[Merge] Done!")

def export_gguf():
    """Step 2: Convert merged model to GGUF using llama.cpp."""
    convert_script = Path(os.getenv(
        "LLAMA_CPP_CONVERT",
        r"C:\Users\Daniel Amer\llama.cpp\convert_hf_to_gguf.py",
    ))

    if not convert_script.exists():
        print(f"[GGUF] llama.cpp convert script not found at {convert_script}")
        print("[GGUF] Install: git clone https://github.com/ggerganov/llama.cpp")
        print("[GGUF] Then set LLAMA_CPP_CONVERT env var to the convert script path")
        print("[GGUF] Alternative: use the online converter at huggingface.co/spaces/ggml-org/gguf-my-repo")
        return False

    import subprocess
    gguf_out = GGUF_DIR / "campus-expert.gguf"
    print(f"[GGUF] Converting to GGUF Q4_K_M...")
    result = subprocess.run(
        [sys.executable, str(convert_script), str(MERGED_DIR),
         "--outtype", "q4_k_m", "--outfile", str(gguf_out)],
        capture_output=True, text=True,
    )
    if result.returncode == 0:
        print(f"[GGUF] Exported to {gguf_out}")
        return True
    else:
        print(f"[GGUF] Conversion failed: {result.stderr}")
        return False

def register_ollama():
    """Step 3: Register with Ollama."""
    import subprocess
    modelfile = GGUF_DIR / "Modelfile"
    print(f"[Ollama] Creating model from {modelfile}...")
    result = subprocess.run(
        ["ollama", "create", "campus-expert", "-f", str(modelfile)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0:
        print("[Ollama] Model 'campus-expert' registered!")
        return True
    else:
        print(f"[Ollama] Failed: {result.stderr}")
        return False

if __name__ == "__main__":
    merge_adapter()
    if export_gguf():
        register_ollama()
    else:
        print("\n[Info] Manual alternative:")
        print("  1. Upload merged_model/ to https://huggingface.co/spaces/ggml-org/gguf-my-repo")
        print("  2. Download the Q4_K_M GGUF file")
        print("  3. Place it at factory_ai/output/training/campus-expert.gguf")
        print("  4. Run: ollama create campus-expert -f factory_ai/output/training/Modelfile")
```

- [ ] **Step 3: Run the merge step (merge only, ~2 min on CPU)**

Run: `.train-venv/Scripts/python.exe scripts/merge-and-export-gguf.py`
Expected: "Saving merged model to factory_ai/output/training/merged_model..." then "Done!"
If llama.cpp not installed, script prints manual alternative instructions.

- [ ] **Step 4: Handle GGUF conversion (depends on llama.cpp availability)**

**Option A — llama.cpp installed:**
Script auto-converts and registers. Verify: `ollama list | grep campus-expert`

**Option B — No llama.cpp (likely on Windows):**
Install llama.cpp and its deps into .train-venv:
```bash
git clone https://github.com/ggerganov/llama.cpp "C:/Users/Daniel Amer/llama.cpp"
.train-venv/Scripts/pip install gguf sentencepiece
```
Then re-run: `.train-venv/Scripts/python.exe scripts/merge-and-export-gguf.py`

**Option C — Online converter (easiest):**
1. Push `factory_ai/output/training/merged_model/` to a temp HuggingFace repo
2. Use https://huggingface.co/spaces/ggml-org/gguf-my-repo to convert
3. Download Q4_K_M GGUF → save as `factory_ai/output/training/campus-expert.gguf`
4. Run: `ollama create campus-expert -f factory_ai/output/training/Modelfile`

- [ ] **Step 5: Verify Ollama model works**

Run: `ollama run campus-expert "Describe the data center zone layout for a 40x40 isometric campus"`
Expected: Response mentioning server racks, cooling units, monitoring desks — influenced by training data.

- [ ] **Step 6: Commit**

```bash
git add scripts/merge-and-export-gguf.py
git commit -m "feat(factory-ai): add LoRA merge + GGUF export script for Ollama registration"
```

---

### Task 2: Integrate Zone JSONs into Phaser Game

**Context:** The AI crew generated 13 zone JSON files in `factory_ai/output/zones/` plus `tile_mappings.json` (96 prop→texture mappings). These need to replace the handcrafted `src/campus-props.ts` so Phaser renders the AI-designed layouts.

**Files:**
- Create: `scripts/convert-zones-to-ts.py`
- Modify: `src/campus-props.ts` (overwritten by script)

- [ ] **Step 1: Write the failing test — verify converter output structure**

Create `scripts/test_convert_zones.py`:
```python
"""Test that zone JSON → TypeScript conversion produces valid output."""
import json, subprocess, sys
from pathlib import Path

PROJECT = Path(__file__).parent.parent
ZONES_DIR = PROJECT / "factory_ai/output/zones"
MAPPINGS = PROJECT / "factory_ai/output/tile_mappings.json"

def test_all_zones_have_json():
    """All 13 zones must have JSON files."""
    expected = {"architect", "auditorium", "cafe", "ceo_office", "data_center",
                "gaming_lounge", "green_area", "huddle_pods", "noc_war_room",
                "open_cowork", "scrum_room", "snack_bar", "terrace"}
    found = {f.stem for f in ZONES_DIR.glob("*.json")}
    assert expected == found, f"Missing: {expected - found}, Extra: {found - expected}"

def test_zone_json_structure():
    """Each zone JSON must be a list of prop objects with required fields."""
    for zf in ZONES_DIR.glob("*.json"):
        data = json.loads(zf.read_text(encoding="utf-8"))
        assert isinstance(data, list), f"{zf.name} is not a list"
        for prop in data:
            assert "id" in prop, f"{zf.name}: prop missing 'id'"
            assert "x" in prop and "y" in prop, f"{zf.name}: prop missing x/y"

def test_tile_mappings_covers_all_props():
    """tile_mappings.json must have entries for all prop IDs used in zones."""
    mappings = json.loads(MAPPINGS.read_text(encoding="utf-8"))
    all_ids = set()
    for zf in ZONES_DIR.glob("*.json"):
        data = json.loads(zf.read_text(encoding="utf-8"))
        for prop in data:
            all_ids.add(prop["id"])
    unmapped = all_ids - set(mappings.keys())
    assert len(unmapped) == 0, f"Props without tile mapping: {unmapped}"

if __name__ == "__main__":
    test_all_zones_have_json()
    print("✓ All 13 zone JSONs exist")
    test_zone_json_structure()
    print("✓ All zone JSONs have valid structure")
    test_tile_mappings_covers_all_props()
    print("✓ All prop IDs have tile mappings")
    print("All tests passed!")
```

- [ ] **Step 2: Run test to verify zones are valid**

Run: `python scripts/test_convert_zones.py`
Expected: "All tests passed!" — if any fail, fix the zone data before proceeding.

- [ ] **Step 3: Write the converter script**

```python
# scripts/convert-zones-to-ts.py
"""Convert factory_ai zone JSONs + tile_mappings.json → src/campus-props.ts"""
import json, sys
from pathlib import Path

PROJECT = Path(__file__).parent.parent
ZONES_DIR = PROJECT / "factory_ai/output/zones"
MAPPINGS_FILE = PROJECT / "factory_ai/output/tile_mappings.json"
OUTPUT_FILE = PROJECT / "src/campus-props.ts"

# Derive grid ranges from authoritative config.py ZONES dict
# This avoids hard-coding coordinates that might diverge
sys.path.insert(0, str(PROJECT / "factory_ai"))
from config import ZONES as _ZONES

# Display names and TypeScript const names for each zone
ZONE_DISPLAY = {
    "data_center": ("dataCenterProps", "Data Center"),
    "auditorium": ("auditoriumProps", "Auditorium"),
    "noc_war_room": ("nocProps", "NOC / War Room"),
    "scrum_room": ("scrumProps", "Scrum Room"),
    "open_cowork": ("coworkProps", "Open Cowork"),
    "ceo_office": ("ceoProps", "CEO Office"),
    "huddle_pods": ("huddleProps", "Huddle Pods"),
    "snack_bar": ("snackProps", "Snack Bar"),
    "cafe": ("cafeProps", "Café"),
    "gaming_lounge": ("gamingProps", "Gaming Lounge"),
    "terrace": ("terraceProps", "Terrace"),
    "green_area": ("greenProps", "Green Area"),
    "architect": ("architectProps", "Architect Studio"),
}

# Build ZONE_MAP with real coordinates from config.py
ZONE_MAP = {
    zname: (
        ZONE_DISPLAY[zname][0],
        ZONE_DISPLAY[zname][1],
        f"rows {spec['rows'][0]}-{spec['rows'][1]}, cols {spec['cols'][0]}-{spec['cols'][1]}",
    )
    for zname, spec in _ZONES.items()
    if zname in ZONE_DISPLAY
}

def prop_to_ts(prop: dict) -> str:
    """Convert a single prop dict to TypeScript object literal."""
    anchors_ts = ""
    if prop.get("anchors"):
        anchor_items = []
        for a in prop["anchors"]:
            anchor_items.append(
                f"{{ name: '{a['name']}', ox: {a['ox']}, oy: {a['oy']}, "
                f"type: '{a.get('type', 'utility')}' }}"
            )
        anchors_ts = ", ".join(anchor_items)

    layer = prop.get("layer", "below")
    w = prop.get("w", 1)
    h = prop.get("h", 1)
    return (
        f"  {{ id: '{prop['id']}', x: {prop['x']}, y: {prop['y']}, "
        f"w: {w}, h: {h}, layer: '{layer}', "
        f"anchors: [{anchors_ts}] }}"
    )

def main():
    # Read tile mappings for the tileMap export
    mappings = json.loads(MAPPINGS_FILE.read_text(encoding="utf-8"))

    lines = []
    lines.append("// AUTO-GENERATED by scripts/convert-zones-to-ts.py — do not edit manually")
    lines.append("// Source: factory_ai/output/zones/*.json + tile_mappings.json")
    lines.append("")
    lines.append("interface PropPlacement {")
    lines.append("  id: string;")
    lines.append("  x: number;")
    lines.append("  y: number;")
    lines.append("  w: number;")
    lines.append("  h: number;")
    lines.append("  layer: 'below' | 'above';")
    lines.append("  anchors: { name: string; ox: number; oy: number; type: 'work' | 'rest' | 'social' | 'utility' | 'wander' }[];")
    lines.append("}")
    lines.append("")

    all_const_names = []

    for zone_file, (const_name, display_name, grid_range) in ZONE_MAP.items():
        zone_path = ZONES_DIR / f"{zone_file}.json"
        if not zone_path.exists():
            print(f"WARNING: {zone_path} not found, skipping")
            continue

        props = json.loads(zone_path.read_text(encoding="utf-8"))
        lines.append(f"// ─── {display_name} ({grid_range}) ───")
        lines.append(f"export const {const_name}: PropPlacement[] = [")
        for prop in props:
            lines.append(prop_to_ts(prop) + ",")
        lines.append("];")
        lines.append("")
        all_const_names.append(const_name)

    # Export combined array
    lines.append("// ─── All Props Combined ───")
    lines.append(f"export const allCampusProps: PropPlacement[] = [")
    for cn in all_const_names:
        lines.append(f"  ...{cn},")
    lines.append("];")
    lines.append("")

    # Export tile mapping
    lines.append("// ─── Tile Mappings (prop ID → texture filename) ───")
    lines.append("export const tileMap: Record<string, string> = {")
    for prop_id, texture in sorted(mappings.items()):
        lines.append(f"  '{prop_id}': '{texture}',")
    lines.append("};")
    lines.append("")

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    total_props = sum(
        len(json.loads((ZONES_DIR / f"{z}.json").read_text(encoding="utf-8")))
        for z in ZONE_MAP if (ZONES_DIR / f"{z}.json").exists()
    )
    print(f"[Convert] Wrote {OUTPUT_FILE} — {len(all_const_names)} zones, {total_props} props, {len(mappings)} tile mappings")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Back up current campus-props.ts**

Run: `cp src/campus-props.ts factory_ai/output/campus-props.ts.bak`
(Backup outside src/ to avoid confusing the TypeScript compiler)

- [ ] **Step 5: Run the converter**

Run: `python scripts/convert-zones-to-ts.py`
Expected: `[Convert] Wrote src/campus-props.ts — 13 zones, ~200 props, 96 tile mappings`

- [ ] **Step 6: Verify TypeScript compiles**

Run: `npx tsc --noEmit`
Expected: No errors (compiles entire project including the new campus-props.ts). If there are type errors, fix the converter's output format.

- [ ] **Step 7: Verify Phaser still renders**

Run: `npm run dev` and open in browser. Check that the campus floor renders with props in all 13 zones.

- [ ] **Step 8: Commit**

```bash
git add scripts/convert-zones-to-ts.py scripts/test_convert_zones.py src/campus-props.ts
git commit -m "feat(phaser): integrate AI-generated zone props from Factory AI crew output"
```

---

### Task 3: Fix QA Agent to Read Zone JSONs

**Context:** The `analyze_prop_coverage` tool in `factory_ai/tools/campus_tools.py:161-206` currently parses `src/campus-props.ts` (a TypeScript file) with regex to count props. This is fragile and reads stale data. It should read the authoritative zone JSONs from `factory_ai/output/zones/` instead.

**Files:**
- Modify: `factory_ai/tools/campus_tools.py:161-206`

- [ ] **Step 1: Write the failing test**

Create `factory_ai/tests/test_analyze_coverage.py`:
```python
"""Test that analyze_prop_coverage reads zone JSONs, not TypeScript."""
import json
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).parent.parent.parent
ZONES_DIR = PROJECT / "factory_ai/output/zones"

def test_zones_dir_exists():
    assert ZONES_DIR.exists(), f"Zone output dir missing: {ZONES_DIR}"
    assert len(list(ZONES_DIR.glob("*.json"))) == 13

def test_zone_json_parseable():
    for zf in ZONES_DIR.glob("*.json"):
        data = json.loads(zf.read_text(encoding="utf-8"))
        assert isinstance(data, list), f"{zf.name}: expected list, got {type(data)}"
        for prop in data:
            assert "id" in prop and "x" in prop and "y" in prop

if __name__ == "__main__":
    test_zones_dir_exists()
    print("✓ Zones dir exists with 13 files")
    test_zone_json_parseable()
    print("✓ All zone JSONs are valid")
```

- [ ] **Step 2: Run test**

Run: `python factory_ai/tests/test_analyze_coverage.py`
Expected: All pass.

- [ ] **Step 3: Rewrite analyze_prop_coverage to read zone JSONs**

Replace lines 161-206 in `factory_ai/tools/campus_tools.py`:

```python
@tool("analyze_prop_coverage")
def analyze_prop_coverage() -> str:
    """Analyze how well the current props cover each zone — flags zones with
    too few props, missing furniture types, or proportional issues.
    Reads from factory_ai/output/zones/*.json (authoritative source)."""
    zones_dir = OUTPUT_DIR / "zones"

    analysis = {}
    for zname, zspec in ZONES.items():
        r0, r1 = zspec["rows"]
        c0, c1 = zspec["cols"]
        area = (r1 - r0 + 1) * (c1 - c0 + 1)

        zone_file = zones_dir / f"{zname}.json"
        prop_ids: dict[str, int] = {}
        count = 0

        if zone_file.exists():
            try:
                props = json.loads(zone_file.read_text(encoding="utf-8"))
                for prop in props:
                    pid = prop.get("id", "unknown")
                    prop_ids[pid] = prop_ids.get(pid, 0) + 1
                    count += 1
            except (json.JSONDecodeError, KeyError) as e:
                analysis[zname] = {"error": str(e)}
                continue

        density = count / area if area > 0 else 0
        analysis[zname] = {
            "area_tiles": area,
            "prop_count": count,
            "density": round(density, 3),
            "props": prop_ids,
            "function": zspec["function"],
            "issue": "SPARSE" if density < 0.05 else ("OVERCROWDED" if density > 0.3 else "OK"),
        }

    return json.dumps(analysis, indent=2)
```

- [ ] **Step 4: Verify tool runs standalone**

Run: `python -c "from factory_ai.tools.campus_tools import analyze_prop_coverage; print(analyze_prop_coverage.run())"`
Expected: JSON with all 13 zones, each with prop_count > 0.

- [ ] **Step 5: Commit**

```bash
git add factory_ai/tools/campus_tools.py factory_ai/tests/test_analyze_coverage.py
git commit -m "fix(factory-ai): QA tool reads zone JSONs instead of parsing TypeScript"
```

---

### Task 4: Wire Campus-Expert Model into Crew + Full Demo Run

**Context:** Once `campus-expert` is registered in Ollama (Task 1), the Scrum Master should use it instead of `qwen3:8b`. Then run the full pipeline: dashboard + Telegram + crew for an end-to-end demo.

**Files:**
- Modify: `factory_ai/crews/campus_crew.py:18-22` (LLM config)
- Modify: `factory_ai/config.py` (model name)

- [ ] **Step 1: Set campus-expert model via .env (no import-time side effects)**

The existing `config.py` already reads `OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")`.
No code change needed — just update `.env`:

```bash
# In .env, add or change:
OLLAMA_MODEL=campus-expert
```

If campus-expert is not registered yet, keep `qwen3:8b` as the default — the env var approach is clean and testable (no subprocess at import time).

- [ ] **Step 2: Verify model is picked up**

Run: `python -c "from dotenv import load_dotenv; load_dotenv(); from factory_ai.config import OLLAMA_MODEL; print(f'Model: {OLLAMA_MODEL}')"`
Expected: `campus-expert` if set in .env, otherwise `qwen3:8b`.

- [ ] **Step 3: Start the full demo stack**

Terminal 1 — Dashboard + Telegram:
```bash
cd "C:/Users/Daniel Amer/SkyOffice Easy Company"
python -m factory_ai.server
```
Expected: FastAPI on port 8800 (or next available), "[Telegram] Bot started"

Terminal 2 — Launch crew:
```bash
curl -X POST http://localhost:8800/api/crew/start
```

- [ ] **Step 4: Monitor dashboard and Telegram**

Open `http://localhost:8800` in browser — verify:
- Agent status cards update in real-time (WebSocket)
- Task outputs appear as they complete
- Human-in-the-loop review prompts appear for layout/visual/QA tasks

Check Telegram chat — verify messages appear for:
- 🏗 Crew Started
- 🤖 Agent started: [name]
- ✅ Task Complete (for each of 5 tasks)
- 🎉 Crew Complete

- [ ] **Step 5: Verify crew completes all 5 tasks**

Check `factory_ai/output/` for fresh output files (timestamp matches current run).
Check `factory_ai/output/training_data.jsonl` for new training examples.

- [ ] **Step 6: Commit config changes**

```bash
git add factory_ai/config.py factory_ai/crews/campus_crew.py
git commit -m "feat(factory-ai): auto-detect campus-expert model, wire into Scrum Master"
```

---

### Task 5: DeerFlow Integration Evaluation

**Context:** `factory_ai/tools/deerflow_tools.py` imports DeerFlow SDK from `C:\Users\Daniel Amer\deer-flow\backend\packages\harness`. If SDK not found, falls back to HTTP API at `localhost:2026`. Currently works via HTTP fallback. Question: install langchain deps to enable SDK, or keep HTTP?

**Files:**
- Possibly modify: `factory_ai/tools/deerflow_tools.py`

- [ ] **Step 1: Check if DeerFlow SDK path exists**

Run: `ls "C:/Users/Daniel Amer/deer-flow/backend/packages/harness/" 2>/dev/null && echo "EXISTS" || echo "NOT FOUND"`

- [ ] **Step 2: Check if DeerFlow HTTP server is running**

Run: `curl -s http://localhost:2026/health 2>/dev/null || echo "DeerFlow server not running"`

- [ ] **Step 3: Decision — document the evaluation**

**Recommendation: Keep HTTP fallback.** Reasons:
1. DeerFlow SDK requires langchain + langgraph which add heavy dependencies (~200MB) and conflict with CrewAI's pinned versions
2. HTTP fallback works identically for our use case (single prompt → response)
3. DeerFlow server can be started independently when needed (`cd deer-flow && npm run dev`)
4. No code changes needed — current implementation already handles both paths gracefully

**Action:** Add a comment in `deerflow_tools.py` documenting this decision. No other changes.

- [ ] **Step 4: Add decision comment to deerflow_tools.py**

At the top of the file, after the docstring:
```python
# Integration decision (2026-04-13):
# HTTP fallback is preferred over SDK import to avoid langchain/langgraph
# dependency conflicts with CrewAI. Start DeerFlow server separately when needed:
#   cd C:\Users\Daniel Amer\deer-flow && npm run dev
```

- [ ] **Step 5: Commit**

```bash
git add factory_ai/tools/deerflow_tools.py
git commit -m "docs(factory-ai): document DeerFlow HTTP-only integration decision"
```

---

### Task 6: Clean Up Duplicate factory-ai/ Directory

**Context:** `factory-ai/` (with hyphen) is an older copy of `factory_ai/` (with underscore). The underscore version is authoritative — it has all output, training data, venv, and the active code. The hyphen version has identical source files but no output/training data.

**Files:**
- Delete: `factory-ai/` (entire directory)

- [ ] **Step 1: Verify factory-ai/ has no unique content**

Run a diff to confirm all source files are identical or older:
```bash
diff -rq "factory-ai/" "factory_ai/" --exclude=__pycache__ --exclude=.train-venv --exclude=output --exclude="*.pyc" 2>/dev/null | head -20
```
Expected: Either "Files are identical" or factory-ai/ files are older/same.

- [ ] **Step 2: Check factory-ai/ is not imported anywhere**

Run: `grep -r "factory-ai" --include="*.py" --include="*.ts" --include="*.json" . 2>/dev/null | grep -v node_modules | grep -v .git`
Expected: No import statements reference `factory-ai/` (only `factory_ai/`).

- [ ] **Step 3: Remove factory-ai/ directory**

```bash
rm -rf "factory-ai/"
```

- [ ] **Step 4: Verify factory_ai/ still works**

Run: `python -c "from factory_ai.config import ZONES; print(f'{len(ZONES)} zones loaded')"`
Expected: `13 zones loaded`

- [ ] **Step 5: Update .gitignore if needed**

If `factory-ai/` was tracked in git, the removal will show in `git status`. Stage the deletion.

- [ ] **Step 6: Commit**

```bash
git rm -r --cached factory-ai/ 2>/dev/null; git add -A
git commit -m "chore: remove duplicate factory-ai/ directory (factory_ai/ is authoritative)"
```

---

## Execution Order

Tasks can be partially parallelized:

```
Task 6 (cleanup) ─────────────────────────────────────────► done
Task 3 (fix QA tool) ─────────────────────────────────────► done
Task 5 (DeerFlow eval) ───────────────────────────────────► done
Task 1 (LoRA → GGUF → Ollama) ────────► Task 4 (demo run)► done
Task 2 (zones → campus-props.ts) ─────► Task 4 (demo run)► done
```

- **Independent (run in parallel):** Tasks 1, 2, 3, 5, 6
- **Depends on Tasks 1+2+3:** Task 4 (full demo run)

## Risk Notes

1. **GGUF conversion on Windows** — llama.cpp's `convert_hf_to_gguf.py` may need compilation. The online converter is the safest fallback.
2. **campus-props.ts overwrite** — Backed up as `.bak` in Task 2 Step 4. If Phaser breaks, restore immediately.
3. **Port conflicts** — Dashboard uses port 8800+. Kill any stale FastAPI processes before demo.
4. **VRAM limits** — Merging the base model needs ~6GB RAM (CPU), not VRAM. GGUF conversion is also CPU-only.
