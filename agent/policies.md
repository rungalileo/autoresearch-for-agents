# Nexus Platform -- Customer Support Policy Manual

**Document ID:** NXS-POL-2025-004
**Effective Date:** January 15, 2025
**Last Revised:** November 3, 2025
**Classification:** Internal Use -- Support Operations
**Approved By:** Rachel Simmons, VP of Customer Operations

---

## 1.0 Scope and Applicability

This document governs all customer-facing support interactions for the Nexus platform, including billing inquiries, account modifications, cancellations, refunds, regulatory compliance requests, and escalation procedures. All support agents and automated systems acting on behalf of agents must adhere to the policies described herein.

Nexus offers three plan types: **Monthly** (rolling 30-day billing cycle), **Annual** (billed once per year at a locked rate), and **Enterprise** (custom-negotiated via a Master Services Agreement). Enterprise plans may include MSA provisions that override standard policy, but only where the MSA explicitly states so. Otherwise, Enterprise accounts follow Annual plan policies with the additions noted in this document.

### 1.1 Account Classification

Each account is classified along the following dimensions:

- **Plan type:** Monthly, Annual, or Enterprise.
- **Verification status:** Verified Business Account (requires business registration document and billing contact confirmation) or Unverified Account.
- **Payment method:** Credit/debit card, ACH transfer, or wire transfer.
- **Region:** Determined by the billing address on file. EEA or UK accounts are subject to additional regulatory requirements (Section 5.0).
- **Referral status:** Standard or Partner Referral. Partner Referral accounts are those onboarded through an authorized Nexus channel partner, recorded at account creation and not retroactively applicable.
- **Subscription count:** Single or Multi-Subscription (Section 8.0).

### 1.2 Identity Verification Requirements

Identity verification requires the requester to confirm at least two of: the account's registered email, the last four digits of the payment method on file, or the company name on the account.

Verification is **required** for: all cancellation requests, refund requests exceeding $500, any plan change, payment method removal or replacement, and billing contact changes.

Verification may be **skipped** for: general information queries, credit issuance under $100, invoice/receipt resend requests, and ticket status inquiries.

If the requester is authenticated via a SAML-based SSO integration, their identity is considered auto-verified regardless of the action being requested. Accounts flagged for suspected fraud (Section 6.2) are excluded from auto-verification and always require manual verification by a senior agent before any account-modifying action.

---

## 2.0 Refund Policy

All refund eligibility windows are calculated from the date of the charge being disputed, not the date of the support request.

### 2.1 Standard Refund Windows

**0-30 calendar days from charge date:** Full refund eligible (100% of the charge amount).

**31-90 calendar days:** Partial refund on a prorated basis. The refund equals the remaining unused portion of the billing period in whole calendar days, divided by the total period length (30 for Monthly, 365 for Annual), multiplied by the charge amount. Prorated refunds are rounded down to the nearest cent.

**91+ calendar days:** No monetary refund. The customer may receive account credit for the prorated unused portion, valid for 12 months and non-transferable.

### 2.2 Plan-Type Specific Conditions

**Monthly:** Standard windows apply without modification. Customers who cancel mid-cycle and receive a prorated refund lose access at the end of the current billing day.

**Annual:** Refunds in the 31-90 day window carry a 5% early termination fee, waived if the customer is downgrading to Monthly rather than cancelling. Full refunds (0-30 day window) require forfeiture of onboarding credits or bonus features granted at annual commitment.

**Enterprise:** Refund requests are reviewed against the MSA. If the MSA is silent on refunds, Enterprise accounts follow the Annual schedule. Enterprise accounts with annual contract value exceeding $50,000 are eligible for courtesy exceptions at account management's discretion, including extended refund windows or fee waivers, but these must be documented with a justification.

### 2.3 Payment Method Considerations

Refunds are issued to the original payment method. Card refunds process in 5-10 business days; ACH in 7-14 business days.

Wire transfer payments require special handling. Wire transfer refunds cannot be processed automatically and must be routed to Finance via an internal ticket with subject "Wire Refund -- [Account ID]". Wire refunds may take up to 30 business days and are subject to a $25 processing fee deducted from the refund amount. International wire transfers carry an additional $40 fee, and the customer bears any currency conversion loss between payment and refund dates.

### 2.4 Partner Referral Account Refund Extensions

Partner Referral accounts receive an extended full-refund window of 45 calendar days instead of 30. The partial refund window runs from day 46 through day 90. The credit-only policy at day 91 is unchanged. Partner Referral status must have been recorded prior to the charge in question.

---

## 3.0 Cancellation Policy

Cancellation terminates access at the end of the current billing period unless immediate cancellation is explicitly requested and confirmed.

### 3.1 Self-Service Cancellation

Verified Business Account holders may cancel via the account settings dashboard by re-entering their password or completing an SSO re-authentication challenge.

### 3.2 Assisted Cancellation and Escalation

Unverified Accounts must contact support. If identity verification (Section 1.2) succeeds, the agent processes the cancellation. If it fails, the request must be escalated to a senior agent.

Enterprise cancellations, regardless of verification status, must be escalated to the assigned account manager, who will review the MSA for notice periods and termination provisions.

### 3.3 Regulatory Cooling Periods

EEA and UK accounts are entitled to a mandatory 14-day cooling period following any new subscription purchase or renewal, during which the customer may cancel and receive a full refund regardless of the standard windows in Section 2.1. The cooling period also applies to plan upgrades, treating the incremental charge as a new purchase. Downgrades are not subject to a cooling period.

For accounts that have activated a SAML-based SSO integration after the purchase or renewal, the 14-day cooling period is considered waived, as SSO activation constitutes substantive use under EU digital content regulations. However, this waiver applies only when the subscription was paid by credit or debit card. Subscriptions paid by wire transfer retain the full 14-day cooling period even after SSO activation, because wire transfer refund processing timelines make it impractical to confirm the waiver in real time. ACH payments are treated as card payments for purposes of this waiver provision.

### 3.4 Cancellation Effective Date

Unless immediate cancellation is requested, the customer retains access until the end of the paid period. Immediate cancellation with a refund follows Section 2.0; without a refund, the remaining paid period is forfeited.

---

## 4.0 Escalation Routing

### 4.1 Domain-Specific Routing

**Billing disputes** (charges, invoice accuracy, duplicate payments, refund amounts): escalate using `escalate_to_billing`. Billing has authority to override refund calculations, issue ad hoc credits, and negotiate payment plans.

**Regulatory, data, and legal requests** (DSAR, data deletion, GDPR, subpoenas, privacy complaints): escalate using `escalate_to_compliance`. Agents must not fulfill data deletion or export requests directly.

**Relationship and commercial matters** (contract renegotiation, custom pricing, renewal terms, executive complaints, or claims about sales promises): escalate using `escalate_to_account_manager`.

### 4.2 Cross-Domain Priority

When a request involves multiple domains, route by this priority:

1. **Compliance** (highest) -- always routed to Compliance first regardless of other dimensions.
2. **Legal hold** -- all actions except compliance escalations are suspended until the hold is cleared.
3. **Billing** -- billing disputes resolved before account management concerns.
4. **Account Management** -- addressed after compliance and billing dimensions are resolved.

When uncertain, default to escalating to Billing as general intake.

---

## 5.0 Regulatory Compliance

### 5.1 EU Data Subject Rights

EEA and UK customers may exercise GDPR rights including: right of access (escalate via `escalate_to_compliance`, 30-day fulfillment), right to erasure (data deletion requests override retention policies unless a legal hold exists, in which case deletion is deferred until hold release), right to portability (30-day fulfillment), and right to rectification (agents may handle simple corrections directly; billing record corrections go to Compliance).

### 5.2 Regional Cooling Period Regulations

The EU 14-day cooling period (Section 3.3) is mandated by the EU Consumer Rights Directive. Agents must not dissuade customers from exercising this right.

Customers in Brazil are entitled to a 7-day cooling period under the Brazilian Consumer Protection Code. The SSO activation waiver does not apply to Brazilian cooling periods; Brazilian customers retain the full 7-day period regardless of service usage.

### 5.3 Data Retention and Deletion

After cancellation, data is retained 90 days for reactivation, then enters a 30-day deletion queue. Customers may request immediate deletion at cancellation, bypassing the 90-day window but still subject to the 30-day queue. GDPR deletion requests bypass both windows and are processed within 30 calendar days.

---

## 6.0 Blocker Conditions

Agents must check for blocker conditions before processing any account-modifying action.

### 6.1 Active Chargeback Investigations

During an active chargeback investigation, no refunds may be issued on the account for any charge, including charges unrelated to the disputed transaction. This restriction applies to all plan types and all refund windows, including the EU cooling period refund. If an EU customer requests a cooling period refund while a chargeback is active, the agent must inform the customer the refund will be processed within 5 business days of chargeback resolution, and must escalate to Compliance to document the regulatory obligation. Chargeback flags are set and cleared by Finance; agents cannot override them.

### 6.2 Fraud Flags

Fraud-flagged accounts require enhanced verification by a senior agent (government-issued ID matching the billing contact name) before any action. Until completed, the account is read-only. SSO auto-verification does not apply.

### 6.3 Legal Holds

A legal hold freezes all account modifications: no cancellations, refunds, plan changes, or data deletions. The only exception is compliance-related escalations -- GDPR requests under legal hold must still be escalated via `escalate_to_compliance`, where Compliance and Legal coordinate the response. As stated in Section 4.2, compliance escalations take priority even over legal holds.

---

## 7.0 Trial Accounts

### 7.1 Standard Trial Terms

New customers may start a 14-day free trial with access to all Annual plan features. No payment information required. Unconverted trials are terminated and data is deleted per Section 5.3.

### 7.2 Trial Extensions

Trials may be extended up to 2 times per account (lifetime), each adding 7 days (maximum total: 28 days). Any agent may grant extensions without escalation. Extensions are unavailable for accounts that previously held a paid subscription.

### 7.3 Trial-to-Paid Conversion Disputes

If a conversion charge is disputed within 48 hours of the charge timestamp, the customer receives a full refund and the subscription reverts to cancelled. After 48 hours, the standard refund policy (Section 2.0) applies using the conversion date as the charge date.

Conversion disputes within the 48-hour window are processed without escalation even if the amount exceeds $500, though identity verification is still required for amounts over $500. After the 48-hour window, normal escalation and verification rules apply.

---

## 8.0 Multi-Subscription Accounts

### 8.1 Independence of Subscriptions

Actions on one subscription do not affect others on the same account. Cancelling Subscription A does not cancel Subscription B; refunds on one do not entitle refunds on another.

### 8.2 Bundle Discounts and Repricing

Customers with bundle discounts who cancel one subscription trigger repricing of remaining subscriptions to standard (non-bundled) rates at the next billing cycle. The agent must inform the customer of this impact before confirming cancellation.

### 8.3 Consolidated Billing

Enterprise accounts may use consolidated billing. Refunds apply to the specific line item, not the consolidated total. Multi-subscription refund requests are evaluated independently per subscription under Section 2.0.

---

## 9.0 Edge Case Resolution Framework

When multiple policies intersect, apply in this order:

1. Check blocker conditions (Section 6.0).
2. Determine escalation routing (Section 4.0).
3. Verify identity (Section 1.2).
4. Apply substantive policy with all modifiers (plan type, region, referral status, payment method).
5. For multi-subscription accounts, evaluate each independently (Section 8.0).

When two policies conflict, the more restrictive governs unless this document states a specific exception. A chargeback restriction (Section 6.1) defers but does not permanently deny an EU cooling period refund.

---

## 10.0 Agent Conduct and Documentation

### 10.1 Record Keeping

Every customer interaction must be documented in the ticketing system, including the customer's request, actions taken, outcome, and policy sections referenced. Escalation records must include the reason and target team.

### 10.2 Commitments and Promises

Agents must not make commitments that exceed their authority or contradict this document. If a customer references a promise from a sales representative, the agent should note the claim and escalate to Account Management for verification without confirming or denying validity.

### 10.3 Tone and Communication

Agents should maintain a professional, empathetic, and solution-oriented tone. When denying a request, explain the relevant policy, offer available alternatives (e.g., account credit instead of refund), and provide escalation options.

---

## 11.0 Illustrative Compound Scenarios

The following scenarios demonstrate how multiple policy dimensions interact. They are for training purposes and are not exhaustive.

**Scenario A:** A Partner Referral account in Germany, paying by wire transfer, requests cancellation and a full refund on day 40 of an Annual subscription. The partner referral extension (Section 2.4) provides a 45-day full-refund window, so the customer is eligible for a full refund. However, wire transfer payment requires routing to Finance (Section 2.3), and the $25 processing fee applies. The EU cooling period (Section 3.3) is moot as the 14-day window has passed. The agent verifies identity (Section 1.2), processes the cancellation, opens a wire refund ticket with Finance, and informs the customer of the processing fee and timeline.

**Scenario B:** An EU-based Monthly plan customer with an active chargeback on last month's charge requests a cooling period refund on this month's renewal (day 3 of the new cycle). The chargeback flag (Section 6.1) blocks all refunds on the account, including the cooling period refund. The agent informs the customer the refund will be processed after chargeback resolution and escalates to Compliance to document the EU regulatory obligation. The refund is deferred, not denied.

**Scenario C:** A Partner Referral account in France with an active chargeback, paying by wire transfer, requests a refund on day 35 of an Annual subscription. Multiple rules intersect: the partner referral extension (Section 2.4) means the customer is within the 45-day full-refund window, the EU cooling period (Section 3.3) has expired (day 35 > 14 days), and the wire transfer payment method triggers Finance routing (Section 2.3). However, the active chargeback (Section 6.1) blocks all refund processing. The agent must first inform the customer that no refund can be issued until the chargeback is resolved, then escalate to Compliance given the EU account status, and note in the ticket that once the chargeback clears, the refund should be processed via wire transfer with the applicable $25 fee (plus the $40 international wire fee if the original transfer was international). The 5% early termination fee (Section 2.2) does not apply because the customer falls within the full-refund window per the partner referral extension.

---

## 12.0 Document Governance

This policy is reviewed quarterly by Customer Operations, Legal, Compliance, and Finance. Changes require approval from the VP of Customer Operations and General Counsel. Agents are notified of material changes via the internal policy update channel and must review updates within 5 business days of publication. Prior versions are archived and available from the Operations team.

**End of Document**
