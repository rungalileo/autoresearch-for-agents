What changed: (1) Moved wire transfer check (step 6) before refund computation (step 7) so TC-1 Brazil wire hits escalate-billing before any cooling period logic. (2) Added 'do only that action' emphasis and 'escalate account management only' for sales promises. (3) Step 9 now says 'deny via no_action tool' explicitly. (4) Step 7 has more explicit prorate formula hint.

Why: Exp 006 (best, 0.35) had TC-1 routing to compliance (wire+cooling conflation), TC-2 doing both refund+escalate, TC-3/5/9 using lookup tools, TC-4 using no_action instead of escalating, TC-8 wrong no_action args.

Thesis: Wire before refund ordering should fix TC-1 (Brazil wire → billing before cooling logic). 'Only' for sales promise should fix TC-2. Explicit no_action tool mention should fix TC-8. Prorate formula hint may help TC-5/9. TC-3/10 (partner referral) depends on model reading partner dates. Expecting 0.50+.

Learnings: Exp 006 showed the model follows the priority framework but conflates wire+cooling and multi-acts. Exp 007 tried exact-one-tool but scored lower (0.25), losing TC-10. The single-tool constraint was too rigid. This attempt keeps the ordering but makes wire an explicit early-exit before refund math.

If fails: Try restructuring to have explicit blocker/escalation section separate from computation section.