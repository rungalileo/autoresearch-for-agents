What changed: Replaced the generic 4-step instructions and key principles with a 9-step priority decision order with stop-at-first-match. Added explicit no-lookup directive. Each step maps to a common failure mode from baseline.

Why: Baseline scored 0.05. 7/10 cases failed because the model called check_eligibility or lookup_order instead of acting. TC-1 and TC-6 failed because of wrong escalation target (compliance vs billing). TC-4 failed because model didn't detect missing verification.

Thesis: The no-lookup directive should fix TC-2,3,5,7,9,10 (all used lookup tools). Priority ordering should fix TC-1 (wire→billing not compliance), TC-6 (chargeback→billing). Identity check should fix TC-4. TC-8 was already partial. Expecting 0.5+ overall.

Learnings: This is experiment 006 after 5 prior attempts (001-005). Previous experiments tried similar approaches but scored between 0.20-0.45. The key differences here: (1) explicit stop-at-first-match, (2) wire transfer routing explicitly says not-compliance, (3) sales promise step is high priority.

If fails: Try making the no-lookup directive even more emphatic, or restructure as a flowchart rather than numbered steps.