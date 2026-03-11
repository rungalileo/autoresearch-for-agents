#!/usr/bin/env python3
"""
evaluate.py - Deterministic scorer that runs all test cases through the support
agent and reports results. No LLM judge - pure Python comparison.

Scoring per the spec:
- Wrong tool = 0.0 always. No partial credit for similar tools.
- Right tool = proportional credit based on argument correctness.
- Score per test case = average of per-call scores.
- ordered=True: positional matching (call i vs call i).
- ordered=False: best-match without reuse (greedy).
"""

import argparse
import asyncio
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.run_agent import run_test_case

BASE_DIR = Path(__file__).parent

MAX_CONCURRENT = 10


def _load_json(filepath):
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def _load_test_suite():
    """Load all test cases from tests/ directory (tests/1.json, tests/2.json, ...)."""
    tests_dir = BASE_DIR / "tests"
    cases = []
    if not tests_dir.is_dir():
        print("Error: tests/ directory not found.", file=sys.stderr)
        sys.exit(1)
    for path in sorted(tests_dir.glob("*.json"), key=lambda p: int(p.stem)):
        cases.append(_load_json(path))
    return cases


def score_single_call(expected_call, actual_call):
    """
    Score a single tool call. Returns 0.0 to 1.0.
    Wrong tool = 0.0, always. No exceptions.
    Right tool = proportional credit based on argument correctness.
    """
    if actual_call["tool"] != expected_call["tool"]:
        return 0.0

    # Right tool. Now check arguments.
    expected_args = expected_call.get("args", {})
    if not expected_args:
        return 1.0  # right tool, no args required, full credit

    correct = sum(
        1 for k, v in expected_args.items()
        if actual_call.get("args", {}).get(k) == v
    )
    return correct / len(expected_args)


def score_test_case(expected_calls, actual_calls, ordered):
    """
    Score a full test case. Returns 0.0 to 1.0.

    Each expected call contributes equally: 1/N of the total score.

    ordered=True:  positional matching (call 1 vs call 1, call 2 vs call 2)
    ordered=False: best-match without reuse (each expected finds its best actual)
    """
    n = len(expected_calls)
    if n == 0:
        return 1.0  # no calls expected, vacuously correct

    total = 0.0

    if ordered:
        # Positional: expected[i] matched against actual[i]
        # Missing actual calls score 0.0
        for i, exp in enumerate(expected_calls):
            if i < len(actual_calls):
                total += score_single_call(exp, actual_calls[i])
            # else: missing call contributes 0.0
    else:
        # Best-match: each expected call finds highest-scoring actual
        # Each actual call can only be used once (greedy, no reuse)
        used = set()
        for exp in expected_calls:
            best_score = 0.0
            best_idx = -1
            for j, act in enumerate(actual_calls):
                if j not in used:
                    s = score_single_call(exp, act)
                    if s > best_score:
                        best_score = s
                        best_idx = j
            if best_idx >= 0:
                used.add(best_idx)
            total += best_score

    return total / n


async def _run_case_with_semaphore(semaphore, case):
    """Run a single test case with concurrency limiting."""
    async with semaphore:
        actual_calls = await run_test_case(case["user_message"], case["account_context"])
        return {
            "id": case["id"],
            "category": case.get("category", "unknown"),
            "ordered": case.get("ordered", False),
            "expected_calls": case["expected_tool_calls"],
            "actual_calls": actual_calls,
        }


async def run_evaluation():
    # type: () -> Dict[str, Any]
    """Run all test cases and compute scores. Returns evaluation data dict."""
    test_suite = _load_test_suite()
    start_time = time.time()

    # Run all cases in parallel with rate limiting
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = [_run_case_with_semaphore(semaphore, case) for case in test_suite]
    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # Score each case
    scores = []  # type: List[float]
    per_case = []  # type: List[Dict[str, Any]]
    category_scores = defaultdict(list)  # type: defaultdict

    for r in results:
        s = score_test_case(r["expected_calls"], r["actual_calls"], r["ordered"])
        scores.append(s)
        category_scores[r["category"]].append(s)

        per_case.append({
            "id": r["id"],
            "score": s,
            "expected": r["expected_calls"],
            "actual": r["actual_calls"],
        })

        # Per-case details to stderr
        expected_tools = [c["tool"] for c in r["expected_calls"]]
        actual_tools = [c["tool"] for c in r["actual_calls"]]
        if s == 1.0:
            tag = "PERFECT"
        elif s > 0.0:
            tag = "PARTIAL"
        else:
            tag = "ZERO"
        print(
            f"[{tag}] {r['id']}: expected={expected_tools}, "
            f"actual={actual_tools}, score={s:.3f}",
            file=sys.stderr,
        )

    # Compute aggregates
    overall_score = sum(scores) / len(scores) if scores else 0.0
    perfect = sum(1 for s in scores if s == 1.0)
    partial = sum(1 for s in scores if 0.0 < s < 1.0)
    zero = sum(1 for s in scores if s == 0.0)

    cat_means = {}  # type: Dict[str, float]
    for cat in sorted(category_scores.keys()):
        cat_means[cat] = sum(category_scores[cat]) / len(category_scores[cat])

    # Print results in the required format to stdout
    print("---")
    print(f"overall_score:                {overall_score:.6f}")

    for cat in sorted(cat_means.keys()):
        label = f"category_{cat}:"
        padding = max(1, 26 - len(label))
        print(f"{label}{' ' * padding}{cat_means[cat]:.6f}")

    print(f"total_cases:                  {len(scores)}")
    print(f"perfect_cases:                {perfect}")
    print(f"partial_cases:                {partial}")
    print(f"zero_cases:                   {zero}")
    print(f"eval_time_seconds:            {elapsed:.1f}")
    print("---")

    return {
        "overall_score": overall_score,
        "category_scores": cat_means,
        "per_case": per_case,
        "eval_time_seconds": elapsed,
        "total_cases": len(scores),
        "perfect_cases": perfect,
        "partial_cases": partial,
        "zero_cases": zero,
    }


def _experiment_id():
    """Generate a datetime-based experiment ID like 2026-03-11_143025."""
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _build_scores_json(eval_data):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """Build the scores.json structure from evaluation data."""
    return {
        "overall_score": eval_data["overall_score"],
        "category_scores": eval_data["category_scores"],
        "per_case": [
            {
                "id": pc["id"],
                "score": pc["score"],
                "expected": pc["expected"],
                "actual": pc["actual"],
            }
            for pc in eval_data["per_case"]
        ],
        "eval_time_seconds": eval_data["eval_time_seconds"],
        "total_cases": eval_data["total_cases"],
        "perfect_cases": eval_data["perfect_cases"],
        "partial_cases": eval_data["partial_cases"],
        "zero_cases": eval_data["zero_cases"],
    }


def _save_experiment(eval_data, description, update_best, notes=""):
    # type: (Dict[str, Any], str, bool, str) -> str
    """Save experiment results to experiments/<datetime>/. Returns experiment ID."""
    experiments_dir = BASE_DIR / "experiments"
    experiments_dir.mkdir(exist_ok=True)

    exp_id = _experiment_id()
    exp_dir = experiments_dir / exp_id
    exp_dir.mkdir()

    # Copy current system_prompt.md
    src_prompt = BASE_DIR / "agent" / "system_prompt.md"
    if src_prompt.exists():
        shutil.copy2(str(src_prompt), str(exp_dir / "system_prompt.md"))

    # Save scores.json
    scores_data = _build_scores_json(eval_data)
    with open(exp_dir / "scores.json", "w", encoding="utf-8") as f:
        json.dump(scores_data, f, indent=2)

    # Save description.txt
    with open(exp_dir / "description.txt", "w", encoding="utf-8") as f:
        f.write(description)

    # Save notes.md if provided
    if notes:
        with open(exp_dir / "notes.md", "w", encoding="utf-8") as f:
            f.write(notes)

    print(f"Experiment saved to {exp_dir}", file=sys.stderr)

    # Update best if requested
    if update_best:
        best_dir = experiments_dir / "best"
        is_new_best = False

        if best_dir.exists():
            best_scores_path = best_dir / "scores.json"
            if best_scores_path.exists():
                with open(best_scores_path, encoding="utf-8") as f:
                    prev_best = json.load(f)
                if eval_data["overall_score"] > prev_best.get("overall_score", 0.0):
                    is_new_best = True
            else:
                is_new_best = True
        else:
            is_new_best = True

        if is_new_best:
            best_dir.mkdir(exist_ok=True)
            shutil.copy2(
                str(exp_dir / "scores.json"),
                str(best_dir / "scores.json"),
            )
            prompt_src = exp_dir / "system_prompt.md"
            if prompt_src.exists():
                shutil.copy2(
                    str(prompt_src),
                    str(best_dir / "system_prompt.md"),
                )
            print(
                f"New best score: {eval_data['overall_score']:.6f}",
                file=sys.stderr,
            )

    return exp_id


def _append_tsv(exp_id, eval_data, description, update_best):
    # type: (str, Dict[str, Any], str, bool) -> None
    """Append a row to results.tsv."""
    tsv_path = BASE_DIR / "experiments" / "results.tsv"
    write_header = not tsv_path.exists()

    # Compact category scores: "cat1=0.85,cat2=0.90"
    compact_cats = ",".join(
        f"{cat}={score:.4f}"
        for cat, score in sorted(eval_data["category_scores"].items())
    )

    # Determine status
    if update_best:
        best_scores_path = BASE_DIR / "experiments" / "best" / "scores.json"
        if best_scores_path.exists():
            with open(best_scores_path, encoding="utf-8") as f:
                best_data = json.load(f)
            if eval_data["overall_score"] >= best_data.get("overall_score", 0.0):
                status = "keep"
            else:
                status = "discard"
        else:
            status = "keep"
    else:
        status = "keep"

    with open(tsv_path, "a", encoding="utf-8") as f:
        if write_header:
            f.write("experiment\toverall_score\tcategory_scores\tstatus\tdescription\n")
        f.write(
            f"{exp_id}\t{eval_data['overall_score']:.6f}\t"
            f"{compact_cats}\t{status}\t{description}\n"
        )


def main():
    parser = argparse.ArgumentParser(description="Evaluate the support agent.")
    parser.add_argument(
        "--description",
        type=str,
        default="no description",
        help="Short description of this experiment",
    )
    parser.add_argument(
        "--notes",
        type=str,
        default="",
        help="Detailed notes/hypothesis for this experiment (saved to notes.md)",
    )
    args = parser.parse_args()

    eval_data = asyncio.run(run_evaluation())

    # Always save experiment, update best, and append to TSV
    exp_id = _save_experiment(eval_data, args.description, True, args.notes)
    _append_tsv(exp_id, eval_data, args.description, True)


if __name__ == "__main__":
    main()
    sys.exit(0)
