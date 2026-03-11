# Autoresearch for Agents

Autonomous prompt optimization for a customer support agent — adapted from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch). An AI agent iteratively improves a support agent's system prompt overnight while you sleep.

![Experiment Progress](experiments/progress.png)

## The Idea

Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) showed that an AI agent can run ML research autonomously: modify `train.py`, run a training experiment, check `val_bpb`, keep or revert, repeat 100+ times overnight. The human writes `program.md` (the meta-instructions) and goes to sleep.

**We apply the same loop to prompt engineering.** Instead of optimizing model weights via code changes, we optimize agent behavior via system prompt changes. Instead of `val_bpb`, we use deterministic tool-call accuracy against a test suite of hard support scenarios.

| Karpathy's autoresearch | This project |
|---|---|
| Modifies `train.py` | Modifies `system_prompt.md` |
| Metric: `val_bpb` (validation loss) | Metric: tool-call accuracy (0.0–1.0) |
| Evaluation: run training for 5 min | Evaluation: run 10 API calls (~30s) |
| Search space: hyperparameters, architecture | Search space: instructions, reasoning frameworks, decision logic |
| Cost: GPU compute | Cost: ~$0.10/experiment in API calls |
| `program.md` tells agent how to think about ML research | `program.md` tells agent how to think about prompt engineering |

The core insight is the same: **a well-written `program.md` turns an AI agent into an autonomous researcher.** The agent forms hypotheses, runs experiments, analyzes failures, and iterates without human intervention.

## What It Does

A frozen test suite of 10 adversarial support scenarios tests a Claude Sonnet agent on complex policy decisions: chargeback handling, partner referral windows, wire transfer routing, absent field detection, multi-request prioritization. Each test case exploits a genuine LLM limitation (attention dilution, strong signal inhibition, temporal ambiguity, etc.).

The optimizer agent (Claude Opus, running in Claude Code) iteratively edits a <1000 character system prompt, evaluates it, keeps improvements, and reverts failures. Every experiment is logged with detailed hypotheses and results.

**Results so far:** 0.05 → 0.80 in 15 experiments.

## Two-Phase Architecture

```
PHASE 1: Build the Exam (adversarial test generation)
  → Generate test cases that cause failures even with good prompting
  → Human reviews and freezes test suite
  → Run once

PHASE 2: Study for the Exam (autonomous prompt optimization)
  → Agent iterates on system_prompt.md overnight
  → Keeps improvements, reverts failures
  → You wake up to a better prompt and experiment history
  → Runs autonomously, like autoresearch
```

Phase 1 and Phase 2 never run simultaneously. The adversarial agent builds the exam. The optimizer agent studies for it.

See [research-spec.md](research-spec.md) for the full design document.

## Setup

```bash
# Install dependencies
pip install anthropic python-dotenv

# Set API key
export ANTHROPIC_API_KEY="your-key-here"
# or add to .env file
```

## Running the Optimizer

In Claude Code, run:

```
run @program.md
```

This starts the autonomous optimization loop. Claude Code will:
1. Create a branch and copy the default prompt as a starting point
2. Run a baseline evaluation
3. Iteratively edit `agent/system_prompt.md`, evaluate, keep improvements, revert failures
4. Save every experiment to `experiments/`
5. Stop after 5 iterations (or specify more: "run @program.md, 20 iterations")

## Project Structure

```
├── agent/                          # The support agent under test
│   ├── system_prompt.md            # THE THING BEING OPTIMIZED (only mutable file)
│   ├── system_prompt_default.md    # Starting point (do not modify)
│   ├── policies.md                 # Fixed support policies (~2500 words)
│   ├── tools_schema.json           # Fixed tool definitions (13 tools)
│   └── run_agent.py                # Calls support agent LLM (Sonnet 4.6)
├── tests/                          # Test cases (frozen after Phase 1)
│   ├── 1.json ... 10.json          # Individual test case files
├── evaluate.py                     # Deterministic scorer (no LLM judge)
├── program.md                      # Optimizer agent instructions
├── plot_results.py                 # Generate experiment progress plot
├── test_generator.md               # Test case generator instructions
├── research-spec.md                # Full design document
└── experiments/                    # Experiment history (gitignored)
    ├── <datetime>/                 # Timestamped experiment
    │   ├── system_prompt.md        # Prompt version tested
    │   ├── scores.json             # Full evaluation results
    │   ├── description.txt         # Short description
    │   └── notes.md                # Detailed hypothesis and learnings
    ├── best/                       # Current best prompt + scores
    └── results.tsv                 # Flat experiment log
```

## Manual Commands

```bash
# Run the full evaluation
python3 evaluate.py --description "what you tried" --notes "detailed hypothesis"

# Run a single test case
python3 agent/run_agent.py TC-1

# Generate the progress plot
python3 plot_results.py

# View experiment log
cat experiments/results.tsv

# View best score
cat experiments/best/scores.json | python3 -m json.tool
```

## Key Design Decisions

- **Single mutable surface**: Only `agent/system_prompt.md` changes. Everything else is frozen — just like autoresearch only modifies `train.py`.
- **No LLM judge**: Scoring is deterministic Python comparison. Wrong tool = 0.0, right tool = proportional arg credit. As clean as `val_bpb`.
- **Genuinely hard tests**: Each test case is iteratively refined until the model fails — we keep tweaking scenarios until they exploit a real LLM limitation (attention dilution, deep reasoning chains, signal inhibition, absence detection, temporal ambiguity).
- **<1000 char constraint**: Forces conciseness and prevents overfitting through verbose instructions.
- **No reward hacking**: The optimizer agent is instructed to write general rules, not sample-specific instructions. The system prompt must never reference test case IDs, specific customer names, or hardcoded values from the test suite — only policy-level logic that would generalize to unseen cases.
- **Detailed experiment notes**: Every experiment includes hypothesis, reasoning, and fallback plans — the agent's lab notebook.
- **Model**: Support agent uses `claude-sonnet-4-6` at temperature 0 for determinism.
- **Parallel eval**: Test cases run concurrently (max 10) for fast iteration.

## Cost

~$0.05-0.15 per evaluation run (10 cases × 1 API call each). ~$5-15 for 100 experiments overnight.
