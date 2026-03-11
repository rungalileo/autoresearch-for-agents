What changed: (1) Added 'call exactly one tool' to prevent multi-tool calls like TC-2. (2) Added 'Use the no_action tool when declining' to fix TC-8. (3) Added 'Brazil is NOT EU; dont send Brazilian wire to compliance' for TC-1. (4) Made verification absence check more explicit for TC-4. (5) Kept no-lookup directive for TC-3,5,9.

Why: Exp 006 scored 0.35 with TC-6,7,10 perfect. TC-2 called both refund+escalate. TC-1 routed Brazil to compliance. TC-4 used no_action instead of escalating. TC-8 gave text instead of no_action tool. TC-3,5,9 still used lookup tools.

Thesis: 'Exactly one tool' should fix TC-2 (only escalate). Brazil!=EU should fix TC-1. Verification absence should fix TC-4. no_action directive should fix TC-8. TC-3,5,9 may still struggle with direct refund computation. Expecting 0.55+.

Learnings: Exp 006 showed the model partially follows priority ordering but still multi-calls and misroutes Brazil. The explicit single-tool constraint + Brazil carveout targets the specific failure modes.

If fails: Try moving the no-lookup directive to be even more prominent, or add explicit instruction to compute refund amounts from account context data.