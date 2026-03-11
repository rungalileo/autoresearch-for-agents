What changed: (1) Identity framing: 'You are a tool-calling agent' instead of just instructions. (2) Stronger prohibition: 'NEVER call lookup, eligibility, or order-search tools' — explicitly naming the category of tools to avoid. (3) Step 7 now says 'Issue the refund tool' as explicit action directive. (4) Removed 'one action only' to see if it helps TC-10 (which needs multi-action). (5) Simplified step 4 to 'Verification field absent or unverified, no active SSO'.

Why: Exp 011 (best, 0.55) gets 6 cases right but TC-3,10 still call lookup/eligibility despite directive. TC-4,5 still produce text. The model seems to ignore the no-lookup instruction for complex multi-request scenarios.

Thesis: 'You are a tool-calling agent' identity should prevent text-only replies (TC-4,5). NEVER + naming tool categories should be stronger than just 'never call'. 'Issue the refund tool' should push TC-3 to act. Removing 'one action only' may help TC-10. Risk: may hurt TC-2 (which needs single action). Expecting 0.65+.

Learnings: Exp 009-011 showed incremental progress: 009 (0.50) → 011 (0.55) by adding tool-call directive and out-of-scope. The stubborn cases (TC-3,10) use lookup tools for complex requests with multiple distracting sub-requests. TC-4,5 convert to text when the model wants to ask for more info. Identity framing may work better than instructions alone.

If fails: Try a completely different structure — instead of numbered steps, use a flowchart/if-then format. Or try adding 'If you find yourself wanting to look up information, the answer is already in the account context.'