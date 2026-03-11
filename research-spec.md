# AutoSupport: Autonomous Support Agent Optimization

## Inspiration and Origin

This project adapts the core loop from [Karpathy's autoresearch](https://github.com/karpathy/autoresearch) to a completely different domain: optimizing a customer support agent's system prompt. In autoresearch, an AI agent iteratively modifies a training script (`train.py`), runs a 5-minute training experiment, checks whether `val_bpb` improved, keeps or reverts the change, and repeats indefinitely. The human's only job is writing `program.md`, the meta-instructions that tell the agent how to think about research. The agent runs 100+ experiments overnight while the human sleeps.

We transplant this exact pattern into support agent optimization. Instead of optimizing model weights via code changes, we optimize agent behavior via system prompt changes. Instead of `val_bpb` as the metric, we use deterministic tool-call accuracy against a pre-built test suite. The result is an autonomous prompt engineering loop that improves a support agent overnight without human intervention.

---

## Core Design Principles

### 1. Single Mutable Surface

In autoresearch, the agent only edits `train.py`. Everything else (`prepare.py`, the evaluation harness, the data) is read-only. This keeps the search space manageable and prevents the agent from gaming the metric by modifying the evaluation.

In AutoSupport, the agent only edits `system_prompt.md`. The policy document, tool definitions, test suite, and evaluation script are all frozen. This is deliberate: if the optimizer could also modify the retrieval pipeline, the tool schemas, and the evaluation rubric, you'd lose the ability to know what's actually improving things. The system prompt is the highest-leverage single surface to optimize. It controls tone, reasoning strategy, escalation behavior, hallucination guardrails, formatting, tool selection logic, and more.

Few-shot examples embedded within the system prompt are allowed. The optimizer agent is free to add, remove, or modify example interactions inside the system prompt. This is still "just the system prompt" technically, but it's a distinct and powerful lever that prompt optimization research (DSPy and similar) has shown to be extremely effective.

### 2. Deterministic, Computable Evaluation (No LLM Judge)

We deliberately avoid using an LLM-as-judge for evaluation. Evaluating free-form text with another LLM creates turtles-all-the-way-down problems: you end up worrying about whether the judge itself is reliable, whether its scoring is consistent, whether it can be gamed.

Instead, the support agent's job is always to produce structured outputs:
- Select the correct tool (or explicitly select "no tool / escalate")
- With the correct arguments
- In the correct sequence (for multi-step cases)

This makes the evaluation function as clean as `val_bpb`: deterministic, cheap (zero API calls for scoring), scalar, and meaningful. Either the agent called `issue_partial_refund(order_id="ORD-7842", amount=99.99, reason="policy_30_90_day")` or it didn't. Python string comparison handles the scoring. No judge needed.

### 3. Genuinely Hard Test Cases

The test suite must be hard enough that a frontier model with a well-crafted system prompt still fails on a meaningful fraction of cases. Without failures, there is nothing to optimize. The difficulty must be intrinsic to the scenarios, not solvable just by adding clever instructions to the prompt.

This means test cases must exploit genuine computational limitations of LLMs, not just trick questions that a good prompt can resolve. A dedicated adversarial agent builds these cases in a separate phase before the optimization loop begins.

---

## Two-Phase Architecture

```
PHASE 1: Build the Exam (Adversarial Test Generation)
  Adversarial agent + frontier model + strong system prompt
  → Generates test cases that fail DESPITE good prompting
  → Human reviews and freezes test_suite.json
  → Run once, with human in the loop

PHASE 2: Study for the Exam (Autonomous Prompt Optimization)
  Optimizer agent + frozen test suite
  → Iterates on system_prompt.md overnight
  → Keeps improvements, reverts failures
  → You wake up to a better prompt, results.tsv, and experiments/
  → Runs autonomously, like autoresearch
```

Phase 1 and Phase 2 never run simultaneously. The adversarial agent builds the exam. The optimizer agent studies for it. Mixing them would be like letting a student edit the test while taking it.

---

## Project File Structure

```
autosupport/
├── program.md                  # Optimizer agent meta-instructions (Phase 2)
├── adversarial_program.md      # Adversarial agent meta-instructions (Phase 1)
├── system_prompt.md            # THE THING BEING OPTIMIZED (only mutable file)
├── policies.md                 # Fixed support policies (rich, complex, ~2000-3000 words)
├── tools_schema.json           # Fixed tool definitions (12-15 tools with semantic overlap)
├── difficulty_levels.md        # Escalation strategies for adversarial agent
Phase 2
├── evaluate.py                 # Deterministic scorer (tool call comparison, no LLM judge)
├── run_agent.py                # Calls the support agent LLM with system prompt + tools
├── run_adversarial.py          # Runs adversarial generation loop (Phase 1)
├── results.tsv                 # Flat experiment log for quick scanning (Phase 2)
├── experiments/                # Source of truth for all optimizer experiments (Phase 2)
│   ├── 001/
│   │   ├── system_prompt.md    # The prompt version tested
│   │   ├── scores.json         # Full evaluation results
│   │   └── description.txt     # What this experiment tried
│   ├── 002/
│   │   ├── system_prompt.md
│   │   ├── scores.json
│   │   └── description.txt
│   ├── ...
│   └── best/
│       └── system_prompt.md    # Copy of the best-scoring prompt
└── README.md                   # Setup and usage instructions
```

### File Roles (autoresearch mapping)

| AutoSupport File | autoresearch Equivalent | Role | Mutable? |
|---|---|---|---|
| `system_prompt.md` | `train.py` | The thing being optimized | Yes (optimizer agent only) |
| `evaluate.py` | `evaluate_bpb()` in `prepare.py` | Ground truth metric | No |
| `tests` | Validation tests | The test data | No (frozen after Phase 1) |
| `policies.md` | N/A (domain knowledge) | Complex rules the agent must follow | No |
| `tools_schema.json` | N/A (domain structure) | Available actions and their schemas | No |
| `program.md` | `program.md` | Meta-instructions for optimizer | Human-edited only |
| `adversarial_program.md` | N/A | Meta-instructions for adversarial agent | Human-edited only |
| `results.tsv` | `results.tsv` | Flat experiment log for quick scanning | Append-only |
| `experiments/` | N/A | Source of truth for all experiments (prompt versions, scores, descriptions) | Append-only |

---

## Phase 1: Adversarial Test Generation

### Goal

Build a test suite of 10 test cases where each case causes a frontier model (even with a well-crafted system prompt) to make an incorrect tool call. The difficulty is intrinsic to the scenario, not solvable by better prompting alone.

### Why Genuine Hardness Matters

If you throw a straightforward "I want to cancel my subscription" at a strong model, it'll nail the tool call every time. The test suite would score 98% on day one and the optimizer would have nothing to chew on. The adversarial agent's job is to find the cases where models systematically fail due to real computational limitations.

### What Makes LLMs Genuinely Fail at Tool Selection

These are the actual computational bottlenecks that prompting alone can't fully solve. The adversarial agent targets these specifically.

#### Bottleneck 1: Attention Dilution (Working Memory Overload)

LLMs process the system prompt, policy document, user message, and account context all at once. When the total relevant information exceeds what the model can hold in active attention, it starts dropping things. Not randomly, but predictably: information in the middle of a long prompt gets less attention than information at the beginning or end. Conditions mentioned once, briefly, get less weight than conditions mentioned repeatedly.

A genuinely hard test case isn't one where the rule is tricky. It's one where the rule that matters is the 14th of 20 rules, mentioned in passing, and the user's message strongly activates 5 other rules that don't actually apply. The model has to suppress strong signals and follow a weak one. That's hard at an architectural level, not a prompting level.

**Construction approach:** Build account contexts with 10-15 fields where only 2-3 are relevant. The rest are realistic but irrelevant. User messages reference 2-3 issues, only one of which maps to the current tool call. Signal-to-noise ratio is deliberately low.

**Example:** Account has integration settings, team member lists, usage stats, billing history with 6 past invoices, three active feature flags, a compliance region, a partner referral code, and a pending support ticket from last month about a completely unrelated issue. User says "Hey, so we're thinking about changes to our account given everything that's going on, and also Jim from our team mentioned something about the invoice?" The actual issue is a duplicate charge on invoice #4 of 6, and the correct action is `lookup_order` with that specific invoice ID before doing anything else. Everything else is noise.

#### Bottleneck 2: Deep Reasoning Chains (Compositionality Failure)

Models are good at applying one rule. They're okay at applying two rules sequentially. They start failing at three or more rules that need to be composed, especially when the output of rule 1 becomes the input to rule 2's condition.

**Critical design requirement:** The adversarial agent must verify that resolving the chain at step N gives a DIFFERENT answer than resolving it fully. If the shortcut happens to give the same answer as the full chain, the test case isn't actually hard.

**Construction approach:** Find sequences of 3+ policy rules that interact. Verify that premature termination at every intermediate step leads to a different (wrong) tool call than the full resolution.

**Example:**
- Step 1: What plan type? → Annual enterprise
- Step 2: Annual enterprise in which region? → EU
- Step 3: EU enterprise plans have a mandatory 14-day cooling period per regulation. Does the request fall within it? → Yes (signed 10 days ago)
- Step 4: But the cooling period is waived if the customer activated a custom SSO integration → Check: SSO integration is active
- Step 5: So the cooling period waiver applies, fall back to standard refund policy → 30-day full refund → `issue_full_refund`

Stopping at step 3 gives `issue_full_refund` with a different reason code. Stopping at step 4 gives `escalate_to_compliance`. Only the full chain gives the correct call. The adversarial agent checks each truncation point.

#### Bottleneck 3: Strong-Signal Inhibition (Negation Difficulty)

"Do X unless Y" is fundamentally harder for LLMs than "Do X when Z." When the positive signal (the user clearly wants a refund, the account clearly qualifies) is strong, the negation condition (but there's a pending fraud investigation) has to overcome that strong activation.

**Construction approach:** Build scenarios where 90% of the evidence supports Tool A, but the correct answer is Tool B (or `no_action`) because of one blocking condition. Rate the "pull strength" toward the wrong answer. If the wrong answer seems obviously right on first reading even to a human, that's a genuinely hard test case.

**Example:** User qualifies for a refund on every dimension. Clear request, within the window, correct plan type, everything lines up. But the account has `chargeback_pending: true`. Policy says: never issue refunds during active chargeback investigations. Correct answer: `escalate_to_billing(reason="active_chargeback")`. The pull toward `issue_full_refund` is extremely strong.

#### Bottleneck 4: Absence Detection

Noticing that something is NOT present in the context is harder than noticing something that IS present. If the correct answer depends on the fact that the account does NOT have a verified email or does NOT have a specific field at all, the model needs to notice the absence.

**Construction approach:** Design policy rules where a missing field changes the tool selection. The account context has many fields present, making the absence of one specific field easy to overlook.

**Example:** Policy says "verified business accounts can self-serve cancellation. Unverified accounts require escalation." The account context has name, plan, billing, usage, region... but no `verified_business` field. Its absence means unverified. Correct answer: `escalate_to_account_manager`, not `cancel_subscription`. Models will often proceed with the action because they don't notice the missing field.

#### Bottleneck 5: Temporal Reasoning Under Ambiguity

Users give vague time references. Account data has precise dates. The model must use the precise dates, not the user's vague description, and correctly compute whether a time window applies.

**Construction approach:** User says "a couple months ago" or "around when we onboarded." Account shows precise dates. The time computation puts the case just outside a window (e.g., 73 days when the window is 60 days), making the vague description plausible but the precise calculation disqualifying.

**Example:** User says "a couple months ago." Account onboarding date: November 3, 2025. Current date: January 15, 2026. That's 73 days. The 60-day full refund window has passed. Correct action: `issue_partial_refund` (30-90 day rule), not `issue_full_refund`. The user's vague "couple months" makes the full refund feel right, but the math says otherwise.

### Adversarial Agent Generation Process

For each test case, the adversarial agent follows this process:

#### Step 1: Choose a Computational Bottleneck
Select which LLM limitation to target. This is the primary difficulty mechanism.

#### Step 2: Identify the Target Rule Chain
Find a sequence of 3+ policy rules that interact. Verify that resolving the chain at step N gives a DIFFERENT answer than resolving it fully. This is what makes the shortcut dangerous.

#### Step 3: Construct the Scenario
- `account_context`: include the deciding factors PLUS at least 5-8 irrelevant but realistic fields
- `user_message`: natural language, possibly vague, possibly mentioning multiple concerns
- The signal pointing toward the WRONG tool should be strong
- The signal pointing toward the RIGHT tool should be weak, buried, or dependent on absence

#### Step 4: Derive Golden Answer (Proof-Style)
Walk through the policy logic step by step, showing full work:
```
Rule 1 applies because [field] = [value] → intermediate conclusion
Rule 2 modifies this because [condition] → updated conclusion
Rule 3 blocks/overrides because [condition] → final tool call with exact arguments
```
Mark each point where premature termination gives a different (wrong) answer.

#### Step 5: Verify Against Strong Prompt
Run the case against the support agent with a detailed, well-crafted system prompt. This is NOT a minimal prompt. It's the best prompt the adversarial agent can write.
- If the agent gets it RIGHT: the case is not hard enough. Add complications, escalate difficulty, retry.
- If the agent gets it WRONG: candidate for the test suite.

#### Step 6: Cross-Verify Golden Answer
Re-derive the answer starting from the policy document fresh, from a different entry point if possible. If the two derivations disagree, the policy might be ambiguous. Either tighten the policy wording or discard the case.

#### Step 7: Record
Append verified failure to `test_suite.json` with:
- The test case (`user_message`, `account_context`)
- The golden tool call with exact arguments
- The full reasoning chain (serves as documentation)
- Which computational bottleneck it targets
- What the wrong-but-tempting answer is and why it's tempting

### Adversarial Iteration Loop (run_adversarial.py)

The adversarial generation process above describes the conceptual steps. `run_adversarial.py` implements the concrete iterative loop that the adversarial Claude Code agent follows when a human asks it to generate the test suite. This is NOT a script that runs automatically. It is the procedure the agent follows, using `run_agent.py` to verify that cases are genuinely hard (not just theoretically hard).

The key insight: the adversarial agent must actually call `run_agent.py` to test each candidate case against a real support agent. A case that looks hard on paper may be trivially solved by a model with a good prompt. Only cases that survive live verification belong in the test suite.

#### The Loop

```
1. Read policies.md, tools_schema.json, difficulty_levels.md
2. Write a strong system prompt — the best the adversarial agent can
   craft — to use as the "strong prompt" for verification. Save this
   as strong_prompt.md alongside the test suite.

3. FOR EACH bottleneck type (attention_dilution, deep_chain,
   strong_signal_inhibition, absence_detection, temporal_ambiguity):
   FOR EACH difficulty level (starting at Level 3, escalating up):

   a. Construct a candidate test case:
      - user_message
      - account_context
      - expected_tool_calls
      - reasoning_chain (proof-style derivation)

   b. Run the candidate against the support agent:
      python run_agent.py --system-prompt strong_prompt.md \
        --user-message <message> --account-context <context>

   c. Score the result using evaluate.py's scoring functions:
      Compare actual tool calls against expected_tool_calls

   d. IF score < 0.9 (agent got it WRONG or partially wrong):
      → The case is hard enough
      → Cross-verify the golden answer by re-deriving from policy
      → If golden answer confirmed: add to test_suite.json
      → If golden answer ambiguous: tighten policy or discard

   e. IF score >= 0.9 (agent got it RIGHT):
      → The case is NOT hard enough
      → Escalate difficulty:
        - Add more distractor fields to account_context
        - Make the user message more ambiguous
        - Add a second issue that activates a competing tool
        - Extend the reasoning chain by one more rule
        - Combine with a second bottleneck type
      → Re-run from step (b) with the escalated version
      → If 3 escalation attempts fail to produce a failure,
        move to the next difficulty level

   f. AFTER adding a case, check coverage:
      → If this bottleneck type has 8-10 cases, move to next type
      → If all types have sufficient coverage, move to compound cases

4. Generate 5-8 compound cases (combining multiple bottleneck types)
   using the same verify-then-add loop

5. Continue until coverage targets are met (40-60 cases total)

6. Save strong_prompt.md alongside test_suite.json for reference
```

#### Why Live Verification Matters

Without live verification, the adversarial agent is guessing about difficulty. A case designed to exploit attention dilution might fail because the model happens to attend well to that particular pattern. A case designed around a 5-step reasoning chain might be solved because the model finds a shortcut. Only by running the case against a real agent can you know whether the difficulty is genuine.

The strong prompt used for verification should be the best the adversarial agent can write. This ensures that cases which survive verification are genuinely hard, not just hard for a weak prompt. When the optimizer later starts from a baseline prompt and works up, these cases will provide real challenge.

### Difficulty Escalation Ladder

The adversarial agent climbs this ladder until it finds failures at each level:

**Level 1: Single Rule, Clean Input**
Straightforward application of one policy rule with clear user input. Models will pass these. These become regression tests, not the improvement frontier.

**Level 2: Single Rule, Ambiguous Input**
One rule applies but the user input is vague. Agent needs to call a lookup tool or ask for clarification rather than guessing. Models sometimes skip the lookup and hallucinate values.

**Level 3: Two Rules in Conflict**
Two policy rules apply simultaneously and give different answers. The policy specifies a priority ordering. Models must identify and apply the priority.

**Level 4: Exception Chains (Depth 3+)**
User qualifies for rule A, which triggers exception B, which is overridden by condition C. Three or more levels of conditional depth. Even strong models start dropping conditions here.

**Level 5: Distractor Context**
Relevant factors buried in a sea of irrelevant but realistic account data. Multiple issues mentioned, only one actionable. Low signal-to-noise ratio.

**Level 6: Ordering Traps**
Correct answer requires calling tools in a specific sequence (verify first, then lookup, then act). User's message makes the final action so obvious that the model wants to skip straight to it.

**Level 7: Negative Action (Inhibition)**
Everything screams "take action!" but one policy clause mandates human escalation or no action. The correct tool call is `escalate_to_human(reason="...")` or `no_action`. Models are biased toward action when action seems available.

**Level 8: Cross-Domain Policy Interaction**
Request touches two policy domains (billing AND compliance, or support AND legal hold). Each domain individually suggests a different tool. Priority ordering between domains is specified in a single line buried in the policies.

**Level 9: Compound (Multiple Bottlenecks)**
Combine two or more of the above strategies in a single test case. For example, attention dilution (lots of noise) plus a depth-3 reasoning chain plus an absence-based decision point.

If the adversarial agent generates 5 cases at a level and the agent passes all of them, move to the next level. If all strategies are exhausted and the agent still passes, combine two strategies simultaneously.

### Human Review Gate (Between Phase 1 and Phase 2)

Before freezing the test suite, a human reviews:

1. **Are the golden answers actually correct?** Since the adversarial agent derived them by construction, most should be fine. But policy interpretation edge cases can be genuinely ambiguous. If two reasonable interpretations exist, either tighten the policy language or remove the case.

2. **Are the scenarios realistic?** Higher difficulty levels might generate technically valid but practically absurd combinations (a user with 7 active subscriptions across 3 currencies with a legal hold in one jurisdiction). If it would never happen in real life, it's not a useful test case even if the model fails it.

3. **Good coverage across failure modes?** Ensure no single bottleneck type dominates the suite.

After review, `test_suite.json` is frozen. No modifications during Phase 2.

---

## Phase 2: Autonomous Prompt Optimization

### Goal

Iteratively improve `system_prompt.md` to maximize the aggregate score on the frozen test suite. The optimizer agent runs autonomously overnight, exactly like autoresearch.

### The Experiment Loop

This mirrors autoresearch's loop, with an `experiments/` directory as the source of truth for all experiment history:

```
LOOP FOREVER:

1. Review current system prompt, recent results in results.tsv, and experiments/ history
2. Form a hypothesis about what to change
3. Edit system_prompt.md (the working copy at the project root)
4. git commit -m "descriptive message of what changed"
5. Run: python evaluate.py > run.log 2>&1
6. Read: grep "^overall_score:" run.log
7. Save the experiment to experiments/NNN/ (next sequential 3-digit number):
   - Copy system_prompt.md → experiments/NNN/system_prompt.md
   - Save full eval results → experiments/NNN/scores.json
   - Write short description → experiments/NNN/description.txt
8. If score improved (higher):
   - Keep the commit
   - Copy system_prompt.md → experiments/best/system_prompt.md
9. If score is equal or worse:
   - Revert root system_prompt.md to experiments/best/system_prompt.md
   - git commit the revert
10. Record results in results.tsv (flat log for quick scanning)
11. Repeat
```

### Experiments Directory

Each optimizer experiment is saved to a sequentially numbered directory under `experiments/`. This is the source of truth for all experiment history.

- **`experiments/NNN/system_prompt.md`**: The exact prompt version that was tested. This makes every experiment fully reproducible.
- **`experiments/NNN/scores.json`**: Full evaluation results including `overall_score`, per-category scores, per-case results, and `eval_time`.
- **`experiments/NNN/description.txt`**: A short description of what this experiment tried (the hypothesis).
- **`experiments/best/system_prompt.md`**: Always a copy of the highest-scoring prompt. Used to revert the working copy when an experiment doesn't improve the score.

The `experiments/` directory serves several purposes: it makes every experiment reproducible (you can re-test any past prompt), it stores richer data than `results.tsv` (per-case results, not just aggregates), and it provides the revert target without requiring git history navigation. `results.tsv` is still maintained as a flat log for quick scanning, but the experiments directory is canonical.

### What the Optimizer CAN Do
- Modify `system_prompt.md`. Everything is fair game: tone instructions, reasoning frameworks, few-shot examples, guardrails, escalation rules, formatting guidelines, chain-of-thought strategies, self-check instructions, XML/markdown structuring, decision trees, role-playing framing, etc.

### What the Optimizer CANNOT Do
- Modify `evaluate.py`, `test_suite.json`, `policies.md`, `tools_schema.json`, or `run_agent.py`
- Install new packages or add dependencies
- Change the scoring rubric or evaluation harness

### Optimizer's program.md

The optimizer's meta-instructions should be lean. Do not spoon-feed failure patterns or tell it what to try. The challenge should be in the exam, and the optimizer must earn its improvements through genuine prompt engineering insight.

```markdown
# Support Agent Prompt Optimizer

You are an autonomous prompt engineer. Your job is to iteratively
improve a support agent's system prompt to maximize its evaluation
score on a fixed test suite of tool-call scenarios.

## Setup

1. Create branch: git checkout -b autosupport/<tag> from current master
2. Read the in-scope files for full context:
   - system_prompt.md (the file you modify)
   - policies.md (the support policies the agent must follow)
   - tools_schema.json (available tools and their parameters)
   - test_suite.json (what the agent is being tested on)
   - evaluate.py (how scoring works)
   - experiments/ (past experiment history, if any)
3. Create experiments/ directory if it doesn't exist (mkdir -p experiments/best)
4. Run baseline: python evaluate.py > run.log 2>&1
5. Save baseline to experiments/001/ and experiments/best/
6. Record baseline score in results.tsv
7. Begin the experiment loop

## What You Modify
- system_prompt.md only. This is the support agent's full system prompt.
  Everything is fair game: instructions, examples, reasoning frameworks,
  guardrails, structure, formatting, decision logic, etc.

## What You Cannot Modify
- evaluate.py, test_suite.json, policies.md, tools_schema.json, run_agent.py
- No new packages or dependencies

## The Loop

LOOP FOREVER:

1. Look at current branch/commit state and experiments/ history
2. Edit system_prompt.md with an experimental idea
3. git commit
4. Run: python evaluate.py > run.log 2>&1
5. Read: grep "^overall_score:\|^category_" run.log
6. If grep is empty, the run crashed. Run tail -n 50 run.log for the
   stack trace and attempt a fix. If you can't fix it after a few
   attempts, revert and move on.
7. Save experiment to experiments/NNN/ (next sequential 3-digit dir):
   - cp system_prompt.md experiments/NNN/system_prompt.md
   - Save scores.json with: overall_score, per-category scores,
     per-case results, eval_time
   - Write description.txt with what this experiment tried
8. Record results in results.tsv (do not commit this file)
9. If overall_score improved (higher):
   - Keep the commit
   - cp system_prompt.md experiments/best/system_prompt.md
10. If overall_score is equal or worse:
   - cp experiments/best/system_prompt.md system_prompt.md
   - git commit -m "revert to best prompt"
11. Continue

## Logging

results.tsv format (tab-separated, flat log for quick scanning):

commit  experiment  overall_score  category_scores  status  description

- commit: short git hash (7 chars)
- experiment: experiment directory number (e.g. 001, 002)
- overall_score: e.g. 0.823000
- category_scores: compact summary of per-category scores
- status: keep / discard / crash
- description: short text of what this experiment tried

The experiments/ directory is the source of truth. Each experiment dir
(experiments/001/, experiments/002/, etc.) contains:
- system_prompt.md: the exact prompt version tested
- scores.json: full results (overall_score, per-category, per-case, eval_time)
- description.txt: what this experiment tried

experiments/best/system_prompt.md always contains the current best prompt.

## Simplicity Criterion

All else being equal, simpler prompts are better. A small improvement
that adds 500 words of convoluted instructions is probably not worth
it. A small improvement from removing instructions is definitely worth
keeping. When evaluating, weigh complexity cost against improvement
magnitude.

## NEVER STOP

Once the loop has begun, do NOT pause to ask the human if you should
continue. Do NOT ask "should I keep going?" The human might be asleep
and expects you to continue working indefinitely until manually
stopped. You are autonomous. If you run out of ideas, think harder:
re-read the policies for subtle rules, study the test cases for
patterns, try combining previous near-misses, try radically different
prompt structures. The loop runs until the human interrupts you.
```

---

## The Domain: Support for "Nexus" (B2B SaaS Platform)

The fictional product is Nexus, a B2B SaaS platform with workspaces, seats, billing tiers, integrations, and compliance features. This gives enough surface area for complex policy interactions across multiple domains.

### Tool Set Design (tools_schema.json)

15 tools with deliberate semantic overlap. The correct choice between similar tools depends on multiple contextual factors.

**Money-Back Cluster** (4 tools, overlapping):
- `issue_full_refund` - complete refund of a charge
- `issue_partial_refund` - percentage or fixed amount refund
- `issue_credit` - account credit for future use (not a refund)
- `escalate_to_billing` - billing disputes requiring human review

Correct choice depends on: amount, timing, plan type, payment method, regulatory jurisdiction, and blocker conditions. Five factors for one cluster.

**Escalation Cluster** (3 tools, overlapping):
- `escalate_to_billing` - disputes over charges
- `escalate_to_compliance` - regulatory, data, legal hold issues
- `escalate_to_account_manager` - relationship/commercial issues

Correct classification requires identifying the nature of the problem, not just recognizing that escalation is needed.

**Account Action Cluster** (4 tools):
- `cancel_subscription` - terminate a subscription
- `downgrade_plan` - move to a lower tier
- `pause_subscription` - temporary suspension
- `extend_trial` - extend a trial period

**Prerequisite/Lookup Cluster** (3 tools):
- `lookup_order` - find order details by ID or approximate info
- `verify_identity` - confirm user is authorized
- `check_eligibility` - determine what actions are available

**Response Cluster** (2 tools):
- `send_template_response` - canned response for known scenarios
- `no_action` - explicitly do nothing (acknowledge, clarify, etc.)

The `no_action` tool is critical. It's the "inhibition" tool. The model must sometimes choose NOT to act, which is harder than choosing which action to take.

### Policy Document Design (policies.md)

The policy document should be 2000-3000 words. Rich enough that no model can hold all of it in active attention simultaneously. Critical rules that the hardest test cases depend on should be buried in the middle, stated once, with no emphasis.

The policy should cover:
- Refund rules with time windows, plan-type conditions, and exceptions
- Cancellation rules with verification requirements and cooling periods
- Escalation routing rules with domain-specific criteria
- Regulatory rules (EU data rights, GDPR, regional cooling periods)
- Blocker conditions (fraud flags, chargebacks, legal holds)
- Exception-to-exception patterns (waivers that override exceptions)
- Cross-domain priority orderings (compliance trumps billing, etc.)
- Identity verification requirements and when they can be skipped
- Trial-specific policies with conversion conditions
- Multi-subscription handling rules

The goal: enough conditional depth and cross-rule interaction that even a model with perfect instructions will struggle with the deepest chains.

---

## Test Suite Format (test_suite.json)

Each test case specifies one or more expected tool calls, with an `ordered` flag that controls how the scoring matches expected calls to actual calls.

### Single-Call Example

```json
{
  "id": "TC-042",
  "category": "strong_signal_inhibition",
  "difficulty_level": 7,
  "bottlenecks": ["inhibition", "absence_detection"],
  "ordered": false,

  "user_message": "Hi, I'd like a full refund for our annual plan. We signed up about two weeks ago and it's just not working out for the team.",

  "account_context": {
    "customer_id": "CUST-8842",
    "plan": "enterprise_annual",
    "signup_date": "2026-02-25",
    "region": "EU",
    "seats": 25,
    "monthly_spend_usd": 2499.00,
    "last_charge_id": "CHG-19283",
    "last_charge_amount": 29988.00,
    "payment_method": "wire_transfer",
    "integrations_active": ["sso_okta", "slack", "jira"],
    "feature_flags": ["beta_analytics", "custom_branding"],
    "usage_last_30d": {"api_calls": 14200, "active_users": 18},
    "support_tickets_open": 1,
    "support_tickets_closed": 3,
    "chargeback_pending": false,
    "fraud_flag": false,
    "legal_hold": false,
    "courtesy_credit_issued": false,
    "partner_referral": "PARTNER-ACME"
  },

  "expected_tool_calls": [
    {
      "tool": "escalate_to_compliance",
      "args": {
        "customer_id": "CUST-8842",
        "reason": "eu_cooling_period_wire_transfer",
        "charge_id": "CHG-19283"
      }
    }
  ],

  "reasoning_chain": [
    "Step 1: Plan type is enterprise_annual, refund policy section 3.2 applies",
    "Step 2: Signup was 14 days ago, within 30-day full refund window",
    "Step 3: BUT region is EU, mandatory 14-day cooling period (policy 6.1) applies",
    "Step 4: EU cooling period for wire transfers requires compliance review, not self-serve refund (policy 6.1.3)",
    "Step 5: SSO integration is active, but the waiver for SSO activation (policy 6.1.4) only applies to card payments, not wire transfers",
    "Step 6: Correct action: escalate_to_compliance with eu_cooling_period_wire_transfer reason"
  ],

  "wrong_but_tempting": {
    "tool": "issue_full_refund",
    "why_tempting": "User clearly qualifies for full refund by time window and plan type. The EU compliance requirement for wire transfers is buried in a sub-clause and easy to miss."
  }
}
```

### Multi-Call Ordered Example (Sequence Matters)

```json
{
  "id": "TC-078",
  "category": "ordering_trap",
  "difficulty_level": 6,
  "bottlenecks": ["ordering", "inhibition"],
  "ordered": true,

  "user_message": "My account email is sarah@acme.com. Can you cancel our subscription and process a refund for last month's charge?",

  "account_context": {
    "customer_id": "CUST-3310",
    "plan": "team_monthly",
    "email": "sarah@acme.com",
    "signup_date": "2025-06-15",
    "last_charge_id": "CHG-40122",
    "last_charge_amount": 299.00,
    "region": "US",
    "verified_identity": false
  },

  "expected_tool_calls": [
    {
      "tool": "verify_identity",
      "args": { "customer_id": "CUST-3310" }
    },
    {
      "tool": "cancel_subscription",
      "args": { "customer_id": "CUST-3310", "reason": "customer_request" }
    },
    {
      "tool": "issue_full_refund",
      "args": { "charge_id": "CHG-40122", "amount": 299.00, "reason": "cancellation_refund" }
    }
  ],

  "reasoning_chain": [
    "Step 1: User provides email but verified_identity is false, must verify first (policy 1.2)",
    "Step 2: After verification, process cancellation before refund (policy 4.1: cancel first to prevent next billing cycle)",
    "Step 3: Last charge was monthly, within 30-day window, standard full refund applies"
  ],

  "wrong_but_tempting": {
    "tool": "cancel_subscription",
    "why_tempting": "User gives their email directly, making it feel like identity is already confirmed. The temptation is to skip verify_identity and go straight to cancellation."
  }
}
```

### Multi-Call Unordered Example (Sequence Does Not Matter)

```json
{
  "id": "TC-091",
  "category": "attention_dilution",
  "difficulty_level": 5,
  "bottlenecks": ["attention_dilution"],
  "ordered": false,

  "user_message": "Two things: we need to downgrade from Enterprise to Team tier, and can you also extend the trial on our sandbox workspace?",

  "account_context": {
    "customer_id": "CUST-5567",
    "workspaces": [
      {"id": "WS-001", "plan": "enterprise_annual", "status": "active"},
      {"id": "WS-002", "plan": "trial", "status": "active", "trial_ends": "2026-03-15"}
    ]
  },

  "expected_tool_calls": [
    {
      "tool": "downgrade_plan",
      "args": { "workspace_id": "WS-001", "target_plan": "team" }
    },
    {
      "tool": "extend_trial",
      "args": { "workspace_id": "WS-002", "extension_days": 14 }
    }
  ],

  "reasoning_chain": [
    "Step 1: Two independent requests, neither blocks the other",
    "Step 2: Downgrade applies to WS-001 (the enterprise workspace)",
    "Step 3: Trial extension applies to WS-002 (the trial workspace)",
    "Step 4: Order does not matter since these are independent actions on different workspaces"
  ],

  "wrong_but_tempting": {
    "tool": "downgrade_plan",
    "why_tempting": "Agent might handle the first request and forget the second, or confuse which workspace gets which action."
  }
}
```

### The `ordered` Flag

- `ordered: true` - Sequence matters. There is a dependency chain between calls (e.g., must verify identity before acting, must cancel before refunding). Scoring uses **positional matching**: expected call 1 is compared against actual call 1, expected call 2 against actual call 2, etc. Wrong order = wrong position = zero credit for that slot.
- `ordered: false` - Sequence does not matter. The calls are independent actions that can happen in any order. Scoring uses **best-match**: each expected call finds its highest-scoring match among actual calls, without reuse.

**When to use each:**
- `ordered: true` when any call depends on the output or precondition of a previous call (verify then act, lookup then process, cancel then refund)
- `ordered: false` when all calls are independent operations that happen to be requested together (downgrade workspace A and extend trial on workspace B)

For single-call test cases, the flag has no effect (both matching strategies produce the same result with one expected call).

### Required Fields

- `id`: Unique identifier
- `category`: Primary bottleneck being tested (attention_dilution, deep_chain, strong_signal_inhibition, absence_detection, temporal_ambiguity, ordering_trap, compound)
- `difficulty_level`: 1-9 per the escalation ladder
- `bottlenecks`: List of computational bottlenecks this case exercises
- `ordered`: Boolean flag controlling whether call sequence matters for scoring
- `user_message`: What the user says (natural language, possibly vague)
- `account_context`: Full account state (including irrelevant fields as distractors)
- `expected_tool_calls`: Array of expected tool calls, each with `tool` and `args`
- `reasoning_chain`: Step-by-step derivation proving the golden answer is correct
- `wrong_but_tempting`: What the model will likely do wrong and why

### Optional Fields

- `notes`: Additional context for human reviewers

---

## Evaluation System (evaluate.py)

### Scoring Philosophy

No LLM judge. Pure Python comparison. The score for a test case is "what fraction of the required tool calls did the agent execute correctly." This is clean, intuitive, and provides gradient for the optimizer.

The core rules:
- **Wrong tool = zero credit for that call.** Always. No partial credit for calling a semantically similar tool. In a real support system, `issue_full_refund` when the answer is `issue_partial_refund` is a real mistake with real consequences.
- **Right tool, partial arguments = proportional credit.** This is where the gradient lives. The optimizer can see the difference between "right tool, 1/3 args correct" and "right tool, 2/3 args correct."
- **Score per test case = average of per-call scores.** Each expected call contributes equally. If 4 calls are expected and the agent nails 1 with all arguments correct, score is 0.25.
- **Matching strategy depends on the `ordered` flag.** Ordered cases use positional matching. Unordered cases use best-match without reuse.

### Scoring Functions

```python
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
        # Missing actual calls (agent made fewer calls) score 0.0
        # Wrong order = wrong position = zero for that slot
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
```

### Concrete Scoring Examples

**Single-call case:** Expected: `issue_partial_refund(charge_id="CHG-19283", amount=99.99, reason="policy_30_90_day")` (3 arguments)

| Agent Output | Score | Why |
|---|---|---|
| Exact match, all 3 args correct | 1.0 | 3/3 args on 1/1 calls |
| Right tool, 2 of 3 args correct | 0.667 | 2/3 args on 1/1 calls |
| Right tool, 1 of 3 args correct | 0.333 | 1/3 args on 1/1 calls |
| Right tool, 0 of 3 args correct | 0.0 | 0/3 args = 0 |
| Wrong tool entirely | 0.0 | wrong tool = 0, always |

**Multi-call ordered case:** Expected: `verify_identity(...)` then `cancel_subscription(...)` then `issue_full_refund(...)`

| Agent Output | Score | Why |
|---|---|---|
| All 3 correct in order | 1.0 | (1.0 + 1.0 + 1.0) / 3 |
| Calls 1 and 2 correct, skips 3 | 0.667 | (1.0 + 1.0 + 0.0) / 3 |
| Skips verify, calls cancel then refund | 0.0 | Position 1: cancel vs expected verify = 0. Position 2: refund vs expected cancel = 0. Position 3: missing = 0. Total: 0.0/3. |
| Correct tools but wrong order: cancel, verify, refund | 0.333 | Position 1: cancel vs expected verify = 0. Position 2: verify vs expected cancel = 0. Position 3: refund vs expected refund = 1.0. Total: 1.0/3. |

Note: the ordered scoring is intentionally harsh on misordering. Skipping the verification step and calling the right tools in positions 2 and 3 scores zero because positional matching sees wrong tools at each position. This correctly penalizes the agent for skipping mandatory prerequisites.

**Multi-call unordered case:** Expected: `downgrade_plan(workspace_id="WS-001", ...)` and `extend_trial(workspace_id="WS-002", ...)`

| Agent Output | Score | Why |
|---|---|---|
| Both correct, any order | 1.0 | Best match finds each |
| Only downgrade, forgot extend_trial | 0.5 | (1.0 + 0.0) / 2 |
| Both tools correct, but workspace IDs swapped | 0.5 | Each call has right tool but wrong workspace_id: ~0.5 each depending on other args |

### Why This Scoring Works for the Optimizer

The gradient concern: can the optimizer see incremental progress?

Yes, because across 48 test cases, the optimizer gets signal at multiple levels simultaneously. Some test cases will flip from 0 to 1 (binary wins). Others will move from 0.333 to 0.667 (argument improvements). The aggregate score captures both. Even if individual cases have coarse resolution (0, 0.333, 0.667, 1.0 for a 3-argument call), across 48 cases the overall score has fine-grained gradient.

The harshness concern: will zero-credit for wrong tools cause the optimizer to stall?

Only if ALL test cases have wrong tools. In practice, the optimizer will find cases where the tool is already correct but arguments are wrong (earning partial credit) and cases where it can flip the tool selection with a prompt change. The diversity of the test suite provides enough signal at every stage of optimization.

### Aggregate Scoring

```python
overall_score = mean(score_test_case(...) for each test case)
```

Per-category breakdowns provide additional signal for the optimizer:

```
overall_score:                0.720000
category_attention_dilution:  0.680000
category_deep_chain:          0.610000
category_inhibition:          0.790000
category_absence:             0.710000
category_temporal:            0.820000
category_ordering_trap:       0.650000
category_compound:            0.580000
```

### Output Format

evaluate.py prints a summary block similar to autoresearch's format:

```
---
overall_score:                0.720000
category_attention_dilution:  0.680000
category_deep_chain:          0.610000
category_inhibition:          0.790000
category_absence:             0.710000
category_temporal:            0.820000
category_ordering_trap:       0.650000
category_compound:            0.580000
total_cases:                  48
perfect_cases:                22
partial_cases:                14
zero_cases:                   12
eval_time_seconds:            42.3
---
```

`perfect_cases` = score of 1.0 (all calls correct with all arguments). `partial_cases` = score between 0.0 and 1.0 exclusive. `zero_cases` = score of 0.0 (all calls wrong). This three-way breakdown gives more signal than just pass/fail.

### Extracting Results

```bash
grep "^overall_score:" run.log
```

---

## Support Agent Execution (run_agent.py)

This script calls the support agent LLM with:
1. The current `system_prompt.md` as the system prompt
2. The policy document (`policies.md`) included in the system prompt or as context
3. The tool definitions from `tools_schema.json` as function/tool schemas
4. A test case's `user_message` and `account_context` as the user turn

The agent must respond with a structured tool call in a fixed JSON schema:

```json
{
  "tool": "tool_name",
  "args": {
    "arg1": "value1",
    "arg2": "value2"
  }
}
```

The output format is fixed. The optimizer agent cannot change how the output is parsed. It can only change how the system prompt instructs the model to reason its way TO that output.

**Temperature: 0** (or as low as possible) for determinism. Each eval run should produce the same results for the same system prompt.

**Model:** Use the same model for the support agent throughout all experiments. The optimizer is improving the prompt, not choosing between models.

### Parallel Execution

Run test cases in parallel (asyncio with rate limiting) to keep total evaluation time under 60-90 seconds. Each evaluation should be fast enough to match autoresearch's ~5 minute experiment cadence (most of that time is the eval run itself, since there's no training step).

---

## Constraints and Budgets

The optimization loop operates under hard constraints that parallel the compute budget in autoresearch. In autoresearch, the 5-minute training budget forces the agent to find algorithmic improvements rather than just training longer. Here, analogous constraints force the agent to find genuinely better prompting strategies rather than overfitting to specific test cases.

### Compute Budget
Each evaluation run: ~50 test cases x 1 API call each = ~50 LLM API calls.
At ~500 tokens in + ~200 tokens out per call: approximately $0.05-$0.15 per run depending on model.
100 experiments overnight: $5-$15 total. Very cheap compared to training runs.

The bottleneck is API latency, not cost. With parallel execution, each eval run should take 30-90 seconds. This means the optimizer can run 40-120 experiments per hour, matching or exceeding autoresearch's throughput.

### System Prompt Constraints

These act as hard optimization constraints, just like the 5-minute compute budget in autoresearch:

1. **General instructions only.** The system prompt must contain general principles, reasoning frameworks, and decision logic — not test-case-specific content. No hardcoded dates, exact dollar amounts, worked calculation examples, exact expected output text, or references to specific test scenarios. The prompt must generalize: it should work for any set of test cases that follow the same policies, not just the current suite. This prevents the optimizer from "memorizing" the test suite (the prompt engineering equivalent of overfitting to validation data).

2. **Under 1000 characters.** The system prompt must be less than 1000 characters total. This forces conciseness and prevents the optimizer from brute-forcing improvements by dumping the entire policy manual into the prompt. Just as autoresearch's 5-minute budget means you can't just train for longer, the character budget means you can't just add more instructions — you have to choose the right ones.

---

## Adversarial Agent Configuration (adversarial_program.md)

```markdown
# Adversarial Test Case Generator

You generate test cases that are genuinely hard for LLMs to solve
correctly, even with well-crafted system prompts. Your cases exploit
real computational limitations: attention dilution, deep reasoning
chains, strong-signal inhibition, absence detection, and temporal
ambiguity.

You do NOT just write test cases on paper. You verify every candidate
by running it against a real support agent using run_agent.py. A case
only qualifies for the test suite if the agent actually fails it.

## Your Inputs (do not modify)
- policies.md: the support policies the agent must follow
- tools_schema.json: available tools and their parameters
- difficulty_levels.md: the escalation ladder of complication strategies
- run_agent.py: the script to run the support agent on a test case
- evaluate.py: the scoring functions to check results

## Your Outputs
- test_suite.json: verified failing test cases
- strong_prompt.md: the strong system prompt used for verification

## Initial Setup

Before generating any test cases:

1. Read policies.md thoroughly. Map out all rule interactions,
   exception chains, and cross-domain priority orderings.
2. Read tools_schema.json. Identify tool clusters with semantic
   overlap (the refund cluster, escalation cluster, etc.).
3. Read difficulty_levels.md for escalation strategies.
4. Write strong_prompt.md — the best system prompt you can craft.
   This prompt should include detailed instructions for handling
   every policy rule, exception, and edge case you can identify.
   This is your verification baseline: cases must fool THIS prompt.

## The Iterative Verification Loop

FOR EACH bottleneck type (attention_dilution, deep_chain,
strong_signal_inhibition, absence_detection, temporal_ambiguity):
  FOR EACH difficulty level (start at Level 3, escalate upward):

  ### 1. Choose a Computational Bottleneck
  Select which LLM limitation you are targeting. This is your primary
  difficulty mechanism.

  ### 2. Identify the Target Rule Chain
  Find a sequence of 3+ policy rules that interact. Verify that
  resolving the chain at step N gives a DIFFERENT answer than resolving
  it fully. This is what makes the shortcut dangerous.

  ### 3. Construct the Scenario
  - account_context: include the deciding factors PLUS at least 5-8
    irrelevant but realistic fields
  - user_message: natural language, possibly vague, possibly mentioning
    multiple concerns
  - The signal pointing toward the WRONG tool should be strong
  - The signal pointing toward the RIGHT tool should be weak, buried,
    or dependent on absence

  ### 4. Derive Golden Answer (Proof-Style)
  Write the complete reasoning chain:
    Rule 1 applies because [field] = [value] → intermediate conclusion
    Rule 2 modifies this because [condition] → updated conclusion
    Rule 3 blocks/overrides because [condition] → final tool call
  Mark each point where premature termination gives a wrong answer.

  ### 5. Verify Against Strong Prompt (MANDATORY)
  This is the critical step. Actually run the case:

    python run_agent.py --system-prompt strong_prompt.md \
      --user-message "<message>" --account-context '<context_json>'

  Score the result using evaluate.py's scoring functions.

  - IF score < 0.9 (agent got it WRONG): → proceed to step 6
  - IF score >= 0.9 (agent got it RIGHT): → the case is NOT hard
    enough. Escalate difficulty:
    - Add more distractor fields to account_context
    - Make the user message more ambiguous
    - Add a competing issue that activates a wrong tool
    - Extend the reasoning chain by one more rule
    - Combine with a second bottleneck type
    Re-run verification with the escalated version.
    If 3 escalation attempts all pass, move to the next difficulty
    level or bottleneck type.

  ### 6. Cross-Verify Golden Answer
  Re-derive the answer starting from the policy document fresh. If your
  two derivations disagree, the policy might be ambiguous. Either
  tighten the policy or discard the case.

  ### 7. Record
  Append to test_suite.json with full metadata:
  - The test case (user_message, account_context)
  - The golden tool call with exact arguments
  - The full reasoning chain
  - The targeted bottleneck(s)
  - What the wrong-but-tempting answer is and why it's tempting

  ### 8. Check Coverage
  After each case, check coverage for the current bottleneck type.
  - If 8-10 cases for this type: move to next bottleneck type
  - After all types: generate 5-8 compound cases using the same loop

## Difficulty Criterion
A test case qualifies ONLY if a frontier model with your strong system
prompt gets it wrong (score < 0.9) when tested via run_agent.py. If
it's solvable with good prompting, it's not hard enough. Theoretical
hardness is insufficient — you must demonstrate empirical failure.

## Coverage Targets
Roughly equal coverage across bottleneck types:
- 8-10 attention dilution cases
- 8-10 deep chain cases
- 8-10 strong-signal inhibition cases
- 5-8 absence detection cases
- 5-8 temporal ambiguity cases
- 5-8 compound (multiple bottleneck) cases
Total: 40-60 cases

## Quality Checks
- Every test case must be realistic (could plausibly happen)
- The golden answer must be unambiguous (only one correct tool call)
- Account context must be internally consistent (no impossible states)
- User messages should sound like real users, not like trick questions
- Every case MUST have been verified via run_agent.py (no untested cases)

## IMPORTANT
Do not skip the verification step. The entire value of this process
depends on live testing. A test suite of "theoretically hard" cases
that were never actually run against an agent is worthless — you have
no evidence they are genuinely hard.
```

---

## Implementation Priorities

### Build Order

1. **policies.md** and **tools_schema.json** first. These are the foundation. The quality of the policy document determines whether the adversarial agent can generate genuinely hard cases. The tool definitions determine the resolution of the evaluation.

2. **run_agent.py** and **evaluate.py** next. These are the infrastructure. Get the agent calling, the output parsing working, and the deterministic scorer correct before generating any test cases.

3. **adversarial_program.md** and **difficulty_levels.md** next. Then run Phase 1 to generate the test suite.

4. **program.md** and **system_prompt.md** last. The optimizer loop is the simplest piece. It's just the autoresearch loop with a different metric.

### Key Technical Decisions

- **LLM Provider/Model:** Use the Anthropic API (Claude) for the support agent. Use the same model consistently across all optimizer experiments.
- **Structured Output:** Use Claude's tool use / function calling to get structured tool call responses. This is more reliable than asking the model to output JSON in free text.
- **Git Workflow:** Same as autoresearch. Dedicated branch per optimization run. Commits for each experiment. Revert on failures.
- **Concurrency:** Run test cases in parallel with asyncio. Rate limit to avoid API throttling.
- **Temperature:** 0 for the support agent (determinism). The adversarial agent and optimizer agent can use default temperature since they need creativity.

---

## What Success Looks Like

After Phase 1: A test suite where a frontier model with a naive system prompt scores around 40-60%. Hard enough that there's significant room for improvement, but not so hard that it's impossible.

After Phase 2 (overnight run): The optimized system prompt scores 70-85%. The results.tsv shows a clear improvement curve. The git log shows which prompt engineering techniques made the biggest difference. The per-category breakdowns show which failure modes were most and least addressable through prompting alone.

The gap between 85% and 100% represents the genuinely irreducible difficulty: cases where the computational bottleneck is deep enough that no prompt can fully compensate for it. That gap is itself interesting data about the limits of prompt engineering.

---

## Open Questions and Future Extensions

1. **Multi-turn conversations.** The current design tests single-turn tool calls. Extending to multi-turn (where the agent asks clarifying questions, gets answers, then makes the call) would be more realistic but significantly increases evaluation complexity.

2. **Dynamic test suite evolution.** After Phase 2, the optimized prompt might solve most cases. Running Phase 1 again with the improved prompt would generate a new set of harder cases. This creates an iterative arms race between the adversarial agent and the optimizer. Whether this converges or spirals is an open question.

3. **Transfer testing.** Does a system prompt optimized on one test suite generalize to new, unseen cases? Or does it overfit to the specific test patterns? Testing on a held-out set would answer this.

4. **Cross-model transfer.** Does a system prompt optimized for Claude also improve performance on GPT-4 or Gemini? Prompt techniques often transfer across models, but the degree varies.

5. **Prompt length vs. performance tradeoff.** The optimizer might keep adding instructions until the prompt is 10,000 words. At some point, length itself causes attention dilution on the prompt. Tracking prompt length alongside score would reveal this curve.
