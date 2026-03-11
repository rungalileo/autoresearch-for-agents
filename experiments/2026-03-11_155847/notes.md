What changed: (1) Wire transfer (step 6) now before refund math (step 7) to catch TC-1 Brazil wire before cooling period. (2) Sales promise step explicitly says 'partner escalation' reason for TC-2. (3) Added 'compute refund amounts yourself' to discourage lookup tools. (4) Cooling periods merged into refund step 7 as a sub-check. (5) Trial step says 'no_action tool' explicitly.

Why: Best (exp 006) scores 0.35. TC-1 fails because cooling period logic fires before wire transfer check. TC-2 gets 0.5 because wrong escalation reason. TC-3,5,9 use lookup tools. TC-4 does no_action instead of escalating. TC-8 uses no_action but wrong format.

Thesis: Wire-before-refund fixes TC-1. Partner escalation reason fixes TC-2 to 1.0. Compute-yourself should push TC-3,5,9 to compute. TC-4 should be caught by step 4. TC-8 by explicit no_action tool mention. Expecting 0.55+.

Learnings: Exp 006 (0.35) established the priority framework works for TC-6,7,10. Exp 007 (0.25) showed single-tool constraint was too rigid. Exp 008 (0.25) showed wire-before-refund helped TC-1 but made model over-use no_action. This attempt keeps the proven structure from 006 but reorders wire/refund and adds compute directive.

If fails: The fundamental issue may be that the model needs more explicit guidance on HOW to compute partial refunds. Try adding a brief worked-example pattern.