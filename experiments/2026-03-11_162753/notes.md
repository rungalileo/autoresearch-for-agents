What changed: Rule 3 narrowed from 'names a sales rep or claims terms beyond standard policy' to 'names a specific sales rep who made a promise.' Added back '(partner)' reason hint. Single-line change targeting TC-2 and TC-9 simultaneously.

Why: Exp 017 (best, 0.675) has TC-2 at 0.5 (reason=enterprise_negotiation instead of partner_escalation) and TC-9 at 0.0 (escalated instead of computing partial refund). TC-2: removing '(partner)' hint made model pick wrong reason. TC-9: 'claims terms beyond standard policy' matched because customer claims extended window that doesn't apply.

Thesis: 'Names a specific sales rep' catches TC-2 (customer names 'Sarah') but NOT TC-9 (customer says 'were told' passively, no named person). This should: (a) restore TC-2 to 1.0 (correct tool + partner reason), (b) unblock TC-9 to fall through to rule 7 where model computes partner onboarded after charge → standard window → 35d partial → issue_partial_refund. Expecting 0.80+.

Learnings: The sales promise rule has been the trickiest to calibrate. Original 'cites rep promise' (exp 011): caught TC-2 but also caught TC-9. 'Names a sales rep or claims beyond policy' (exp 017): caught TC-2 (wrong reason) and still caught TC-9. The insight: TC-9's customer uses passive voice ('were told') about a standard program benefit, while TC-2 names a specific person. Named-person is the cleanest discriminator.

If fails: If TC-9 still escalates, the model may interpret 'were told' as implying a named person. Try removing rule 3 entirely and handling sales promises within the refund computation step.