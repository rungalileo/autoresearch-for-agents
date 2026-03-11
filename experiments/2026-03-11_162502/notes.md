What changed: Single targeted change from exp 015 (best, 0.60): added 'one action only' back to the rules header. Trimmed 'action' from 'call the action tool' to fit.

Why: Exp 015 scored 0.60 but lost TC-7 (Enterprise→AM) which exp 011 had at 1.0. The only structural differences between 011 and 015 are: (a) 'one action only' was in 011 but not 015, (b) 015 had NEVER (caps) and think-then-act. TC-7 is an Enterprise customer making a refund request — the model should hit rule 5 (Enterprise + refund/cancel → AM) but instead called lookup tools. Hypothesis: 'one action only' was the key constraint preventing the model from attempting multi-step info gathering for TC-7.

Thesis: Adding 'one action only' back should recover TC-7 (1.0) while keeping 015's improvements on TC-5 (0.75), TC-9 (0.75), TC-10 (1.0). The NEVER caps, think-then-act, and issue-refund-tool directives should still be active. Risk: TC-10 might regress since it actually produces multiple tool calls. Expecting 0.70+.

Learnings: The 'one action only' constraint has a dual effect: it prevents unnecessary lookup calls (good for TC-7) but may constrain multi-action responses (bad for TC-10). The unordered matching in scoring means TC-10 works even with multiple calls as long as the expected tool is among them. So 'one action only' may actually be fine for TC-10 too.

If fails: The interaction between 'one action only' and 'think which rule applies' may conflict. Try removing the think directive and relying solely on the priority rules with one-action-only.