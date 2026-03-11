What changed: (1) Added 'Act immediately — never ask for confirmation. Always use a tool call, not a text-only reply.' (2) Step 4 now says 'Don't verify yourself' to prevent TC-4 from attempting verification. (3) Step 7 says 'Issue refund directly' to prevent TC-3,5,9 from asking confirmation. (4) Step 9 says 'out of scope' for trial max.

Why: Exp 009 (best, 0.50) showed the model correctly analyzing TC-3,4,5,9 but producing text responses instead of tool calls. TC-3 computed partner refund correctly but asked for confirmation. TC-4 asked for verification instead of escalating. TC-5 computed partial refund but asked confirmation. TC-8 used wrong no_action reason (already_resolved vs out_of_scope). TC-9 identified partner-after-charge but asked confirmation.

Thesis: The 'act immediately, always tool call' directives should convert TC-3,5,9 from text responses to actual refund tool calls. TC-4 'don't verify yourself' should convert to escalation. TC-8 'out of scope' should fix the reason. Expecting 0.75+.

Learnings: Exp 009 proved the priority framework and wire-before-refund ordering works (5/10 perfect). The remaining failures are all cases where the model does the right analysis but doesn't execute. This is a common pattern in support agent prompting — the model defaults to conversational mode.

If fails: Try adding 'You are a tool-calling agent, not a chatbot' framing. Or try 'Your only output should be tool calls.'