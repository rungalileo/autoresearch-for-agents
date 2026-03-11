What changed: Added 'Always use tool calls, not text replies' (from exp 010 which helped TC-5,9). Added 'Don't ask to verify' to step 4 for TC-4. Changed step 8 to 'out of scope' for TC-8. Kept the proven structure from exp 009 (the best at 0.50) including wire-before-refund and partner escalation reason.

Why: Exp 009 (best, 0.50) gets TC-1,2,6,7,10 perfect but TC-3,4,5,8,9 score 0 because model produces text instead of tool calls. Exp 010 (0.50) added act-immediately which helped TC-5(0.75),TC-9(0.75),TC-8(0.5) but lost TC-7,TC-10.

Thesis: The minimal change from 009 — adding 'use tool calls not text' and 'don't ask to verify' — should convert TC-4,5,8,9 from text to tool calls while preserving TC-1,2,6,7,10. The key difference from 010: keeping 'one action only' framing (which 010 removed) to preserve TC-7,10. Expecting 0.65+.

Learnings: Exp 010 showed that 'act immediately never ask confirmation' was too aggressive and broke Enterprise escalation. The sweet spot is 'use tool calls not text' which is about output format, not about removing the priority logic.

If fails: The issue may be that 'one action only' conflicts with 'always tool call'. Try removing 'one action only' but keeping all the priority steps.