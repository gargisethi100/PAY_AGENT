# Design Document

## 1. Problem Understanding

<<<<<<< HEAD
PAYgent is an LLM-first conversational payment collection agent. It follows the required `Agent.next(user_input: str) -> {"message": str}` interface and keeps all conversation state inside each `Agent` instance.

The implementation uses the LLM only for structured understanding of messy user input. A custom deterministic state-machine orchestrator still controls identity verification, payment validation, balance disclosure, user-facing responses, and API calls.
=======
The assignment asks for a conversational AI agent that handles payment collection end-to-end. The problem is deceptively simple on the surface but has significant depth:

- **Users don't type clean data.** "my dob is 14th May 90" is how real people talk. A rigid parser fails; a fully LLM-driven approach loses determinism and control.
- **Security is non-negotiable.** Balance must never be shown before verification. Sensitive data must never be echoed. Payment must never be attempted without complete, validated card details.
- **Failures must be graceful.** An invalid CVV shouldn't force the user to re-enter their card number. A canceled flow shouldn't happen because someone said "don't stop" (which contains the word "stop").
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

These constraints shaped every design decision.

<<<<<<< HEAD
```text
Agent.next(user_input)
  |
  |-- cancellation detection
  |-- local sensitive-value extraction and masking
  |-- LLM-first structured understanding
  |-- policy gates
  |-- state-machine orchestrator
        |
        |-- validators
        |-- strict verification
        |-- API tools
        |-- response builder
```

The understanding layer recognizes messy user input such as `meri account numbel heinnnn acc1001`, `mera naam Nithin Jain hein`, `DOB is May 14, 90`, `CVV is one two three`, and `expires 12/27`. Extracted values are only candidates. The policy layer decides whether the current state is allowed to use them.

Normal interactive usage is configured with `PAYGENT_LLM_MODE=required` and `OPENAI_API_KEY` in a local `.env` file. The LLM returns structured candidates, never writes responses, and cannot bypass validation, verification, or payment gates. Before LLM calls, raw DOB, Aadhaar, pincode, card number, CVV, and expiry values are replaced with placeholders. The real `.env` file is ignored by git; only `.env.example` is committed. Tests inject fake/no-op providers and never call OpenAI.
=======
## 2. Architecture

### Why a State Machine (Not ReAct/LangGraph)

I deliberately chose a deterministic state machine over an LLM-driven agent loop. Here's why:

**ReAct/LangGraph approach:** The LLM decides what tool to call and when. Great for open-ended tasks, but for payment collection:
- How do you guarantee the LLM never shows balance before verification?
- How do you guarantee it never skips card validation?
- How do you test it deterministically across repeated runs?
- How do you audit it when a payment goes wrong?

**My approach:** The LLM is *only* used for extraction (understanding messy text). Every decision -- when to call an API, what state to transition to, whether to show balance -- is made by deterministic code that can be tested, audited, and trusted.

```
User Input
    |
    v
+-------------------+
| Field Extraction   |  <-- Rule-based + optional LLM fallback
| (what did they say) |     LLM sees digit-masked text only
+-------------------+
    |
    v
+-------------------+
| Policy Gates       |  <-- Deterministic checks
| (is this allowed?) |     can_show_balance? can_process_payment?
+-------------------+
    |
    v
+-------------------+
| State Machine      |  <-- Deterministic transitions
| (what happens next) |    10 active + 7 terminal states
+-------------------+
    |
    v
+-------------------+
| Response Builder   |  <-- Template-based, never leaks data
| (what to tell user) |
+-------------------+
```

### State Machine Design
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

```
START --> AWAIT_ACCOUNT_ID --> [lookup API] --> AWAIT_FULL_NAME
    --> AWAIT_SECONDARY_FACTOR --> [verify] --> AWAIT_PAYMENT_AMOUNT
    --> AWAIT_CARD_DETAILS --> [validate all] --> [payment API]
    --> SUCCESS_CLOSE

Terminal states: SUCCESS_CLOSE, CANCELLED_CLOSE, ZERO_BALANCE_CLOSE,
                 VERIFICATION_FAILED_CLOSE, PAYMENT_FAILED_CLOSE,
                 ACCOUNT_LOOKUP_FAILED_CLOSE, API_UNAVAILABLE_CLOSE
```

Key design choice: **7 distinct terminal states** instead of a single "CLOSED" state. This allows the agent to give contextually appropriate responses when a user types after the flow ends (e.g., offering to start a new account flow vs. suggesting they contact support).

## 3. Extraction Strategy: Rules First, LLM as Safety Net

### Rule-Based Extraction
The extraction layer handles ~95% of real inputs through carefully crafted regex patterns and heuristics:

- **Account ID:** Normalizes "ACC 1001", "acc1001", "account id: ACC1001"
- **Names:** Strips fillers ("i guess", "I think"), handles "it's Nithin, Nithin Jain", requires 2+ tokens for full legal name
- **DOB:** Supports YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY, "14th May 1990", "May 14, 90", with MM-DD-YYYY fallback
- **Aadhaar/Pincode:** Keyword-based + word-form digits ("four three two one" -> "4321") + bare digit inference by length in context
- **Amounts:** Numeric, word-form ("five hundred", "two thousand"), relative ("half", "quarter", "25%"), colloquial ("all of it", "everything", "clear it all")
- **Card details:** Luhn validation, word-form CVV, context-aware expiry extraction
- **Cancellation:** Intent-aware with negation detection ("cancel" triggers, "don't cancel" doesn't)

### Optional LLM Fallback
When rule-based extraction fails for the current stage's expected field, the agent can optionally call Azure OpenAI:

<<<<<<< HEAD
Invalid account IDs, invalid amounts, Luhn-invalid cards, expired cards, invalid CVVs, and malformed identity factors are rejected before API calls.
=======
1. **Mask all digits** in the user's text (preserving positions): "born 1990-05-14" -> "born 9999-99-99"
2. Send masked text + current stage + expected fields to the LLM
3. LLM returns either span indices or direct values
4. Local code maps results back to original text
5. Only medium/high confidence results are accepted
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

**Critical safety property:** The LLM never sees account data, previous conversation context, or sensitive values. It cannot verify identity, show balance, or trigger payment. It's a pure text-understanding tool.

## 4. Key Design Decisions

### Collect-All-Then-Validate for Card Details
**Problem:** If you validate each card field immediately, a user providing fields one by one gets interrupted by validation errors before they finish. Worse: if the API returns "invalid CVV" and you've already cleared all sensitive data, the user must re-enter everything.

**Solution:** Accumulate all card fields progressively. Show what's been collected ("Collected so far: Name: Nithin Jain, Card: ****0366"). Only validate when all 4 fields are present. On API failure, clear only the failing field.

<<<<<<< HEAD
Input validation is stricter than extraction. Names must use letters and spaces only, DOB must be a real date, Aadhaar last 4 must be exactly 4 digits, pincode exactly 6 digits, card number exactly 16 digits after removing spaces/hyphens, and CVV exactly 3 digits. User-facing prompts explain the invalid field without echoing the sensitive value.

## Failure Handling
=======
### Verification: Strict but Fair
- **Exact name match** (case-sensitive, as required by spec)
- Name mismatches don't burn verification attempts (allows unlimited retries for typos)
- But name mismatches have their own limit (5) to prevent brute-force
- Only complete attempts (name + secondary factor both present) count toward the 3-attempt limit
- On failure, all identity fields are cleared (prevents brute-forcing secondary factors)
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

### Intent-Aware Cancellation
**Problem:** Simple keyword matching on "cancel", "stop", "exit" causes false positives. "Don't stop the payment" or "I need to cancel my other subscription" would destroy the session.

**Solution:** Three tiers of cancellation detection:
1. **Standalone commands:** "cancel", "stop", "exit" as the entire message
2. **Explicit intent:** "cancel this payment", "I want to cancel", "I don't want to continue"
3. **Negation override:** "don't cancel", "don't stop" suppresses cancellation

## 5. Failure Handling

Every failure is classified:

| Type | Examples | Handling |
|---|---|---|
| **Retryable technical** | API timeout, 503, network error | Retry once internally, then close cleanly |
| **User-correctable** | Invalid card (Luhn), expired expiry, insufficient balance | Ask user to fix specific field, keep other data |
| **Invalid format** | "30th February 1988", "CVV is abc" | Give specific feedback ("that date is invalid") |
| **Terminal** | 3 failed verifications, 3 failed payments | Close with "contact support" message |

**No silent failures.** If the user tried to provide a date but it was invalid (Feb 30), they get told why instead of a generic "please provide your DOB."

## 6. Sensitive Data Protection

| Data | Storage | Display | Logging |
|---|---|---|---|
| DOB, Aadhaar, Pincode | In state during verification, never persisted | Never echoed in responses | Redacted |
| Card Number | In state until payment attempt | Shown as ****0366 (last 4 only) | Redacted |
| CVV | In state until payment attempt | Shown as *** | Redacted |
| Balance | In state after verification | Shown only after verification passes | Safe |

<<<<<<< HEAD
LLM-first understanding is more flexible for user phrasing, but it is deliberately not the policy engine. The trade-off is that normal interactive usage needs an API key, while tests use fake providers. Runtime LLM failures fall back to deterministic extraction where possible, and all extracted values still pass deterministic validators before any sensitive action.
=======
In the Streamlit UI, user input is masked before display: card numbers show first 4 + last 4, CVV shows first digit only.

## 7. Assumptions and Ambiguities

The assignment is intentionally underspecified in places. These are the assumptions I made and why:

| Ambiguity | Assumption | Rationale |
|---|---|---|
| **Retry limits** | 3 for verification, 5 for name mismatch, 3 for payment, 3 for account lookup | 3 is standard for security-sensitive operations. Name mismatch gets 5 because typos are common and don't leak information. |
| **Name matching strictness** | Exact match including case, after outer whitespace trimming only | Spec says "no fuzzy matching, no case-insensitive workarounds." The agent prompts users for "exact registered full legal name, including capitalization." |
| **Two-digit year interpretation** | DOB: `>= 30` maps to 1900s, `< 30` maps to 2000s. Expiry: always 2000s. | No one alive was born after 2030. All card expiry dates are in the 2000s. |
| **"Full amount" phrases** | "full amount", "all of it", "everything", "clear it all", "pay the total" etc. | Real users use many colloquial variations. The agent recognizes ~15 phrases. |
| **Zero-balance accounts** | Verify identity first, then inform user and close. No payment collected. | Security: don't reveal balance status to unverified users. UX: don't ask for card details when no payment is needed. |
| **`cardholder_name` validation** | Accepted as-is, not validated against account holder name | Matches the API spec: "cardholder_name is accepted as-is and not validated against the account holder's name." |
| **Partial payments** | Allowed. Amount must be > 0 and <= balance. | Matches API spec: "Partial payments (amount < balance) are allowed." |
| **Balance persistence** | Balance does not update after payment. | Matches API spec: "The server does not persist balance updates." |
| **Cancellation scope** | Requires intent, not just keyword presence. "don't cancel" does NOT cancel. | "cancel" in "don't cancel the payment" is a false positive. Intent-aware detection prevents accidental session loss. |
| **Account change** | Allowed before verification (state reset). From terminal state, starts fresh flow. | Users may realize they have the wrong account. Allowing switches before verification is safe since no sensitive data has been disclosed. |
| **Identity cleared on verification failure** | All identity fields wiped after a failed verification attempt | Security: prevents brute-forcing secondary factors while holding a known name. Trade-off: user must re-enter name. |
| **Card validation timing** | All card fields collected first, validated together when complete | UX: don't reject a card number before the user has entered CVV/expiry. Validate everything at once for a coherent error report. |
| **LLM determinism** | Default mode (no LLM) is fully deterministic. LLM fallback is opt-in. | Spec says "must behave consistently and deterministically." The default satisfies this. LLM fallback is for enhanced robustness, clearly opt-in. |

## 8. Trade-offs Accepted

1. **Rule-based extraction is brittle for rare phrasings** -- mitigated by LLM fallback, but the fallback adds latency and requires Azure credentials.
2. **Exact name matching rejects valid users with wrong capitalization** -- required by spec. The agent prompts for "exact registered full legal name, including capitalization."
3. **No persistent sessions** -- each Agent instance is ephemeral. A production system would need session management.
4. **Decimal-to-float conversion** for the payment API -- explicitly quantized to 2 decimal places, but JSON serialization could theoretically introduce artifacts.

## 8. What I Would Improve With More Time

1. **Broader LLM provider support** -- currently only Azure OpenAI; would add Anthropic, OpenAI direct, and local model support
2. **Session management** -- persistent session IDs with timeout and secure resumption
3. **PCI-compliant card collection** -- hosted payment fields or tokenization instead of direct card collection
4. **OpenTelemetry tracing** -- structured traces with automatic PII redaction
5. **Rate limiting and abuse detection** -- prevent brute-force attacks on verification
6. **Human handoff** -- when the user is genuinely stuck, route to a human agent
7. **Multi-language support** -- currently handles some Hinglish patterns; would add full Hindi and regional language support
8. **Conversation summarization** -- for handoff to human agents or session resumption

## 9. Testing and Evaluation

### Test Layers

| Layer | Count | What it tests | Speed |
|---|---|---|---|
| **Unit tests** (`tests/`) | 117 | Extraction, validation, verification, state transitions, sensitive data, UI | < 1 second |
| **Eval scenarios** (`eval/run_scenarios.py`) | 16 | End-to-end flows against all 4 test accounts | < 1 second |
| **Stress tests** (`eval/stress_test.py`) | 24 | Messy inputs, edge cases, adversarial scenarios | < 1 second |

Every test uses the exact `Agent.next()` interface that the evaluator will use.

### What "Correct" Means at Each Step

| Step | Correctness Criteria |
|---|---|
| **Greeting** | Agent asks for account ID. No information disclosed. |
| **Account lookup** | API called only with valid ACC-format ID. 404 communicated clearly. No re-ask for data already provided. |
| **Name collection** | Extracted from messy input (fillers stripped). Exact match enforced. Mismatch gives guidance without leaking the registered name. |
| **Verification** | Strict: exact name + exact secondary factor. Partial inputs don't count as failed attempts. Retry limit enforced. Balance never shown before verification passes. |
| **Balance disclosure** | Shown only after verification. Zero balance closes without payment collection. |
| **Amount collection** | Validates > 0, <= balance, max 2 decimals. Word-form and relative amounts supported. |
| **Card collection** | All 4 fields collected before validation. Missing fields listed with masked summary. Luhn, expiry, CVV validated together. No API call until locally valid. |
| **Payment** | On failure: only the bad field cleared, others retained. On success: card data cleared, transaction ID + card last 4 in recap. |
| **Sensitive data** | DOB, Aadhaar, pincode, raw card number, CVV never appear in any response or log. |

### Where the Agent Struggles (Honest Assessment)

1. **Non-ASCII names** -- Diacritics and Devanagari characters are not supported by the rule-based extractor. The LLM fallback helps but is opt-in.
2. **Ambiguous dates** -- "05-06-1990" could be May 6 or June 5. The agent assumes DD-MM-YYYY (Indian convention) and falls back to MM-DD-YYYY if invalid.
3. **Complex word-form amounts** -- "twelve fifty" works, but "one lakh twenty thousand" does not. The word-form dictionary covers common amounts up to 10,000.
4. **Conversational memory** -- The agent tracks extracted fields but not discourse nuance (e.g., "I already told you my name").
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
