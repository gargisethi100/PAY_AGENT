<<<<<<< HEAD
# PAYgent: LLM-First Payment Collection Agent
=======
# PAYgent -- Production-Ready Payment Collection Agent
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

A conversational AI agent that handles end-to-end payment collection: account lookup, identity verification, balance disclosure, card payment processing, and graceful failure handling -- all through natural, messy, real-world user input.

## Quick Start

<<<<<<< HEAD
```python
class Agent:
    def next(self, user_input: str) -> dict:
        return {"message": "..."}
```

The application uses an LLM-first understanding layer for messy natural-language input, while verification, validation, policy gates, and payment execution remain deterministic. Normal app usage should be configured with an OpenAI key in a local `.env` file.

## Setup

```powershell
=======
```bash
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Run tests (117 unit + integration tests)
pytest -q

# Run stress test (24 robustness scenarios)
python eval/stress_test.py

# Run evaluation scenarios (16 scenarios)
python eval/run_scenarios.py

# Interactive CLI (offline mock mode)
python cli.py --mock

# Interactive CLI (live API)
python cli.py

# Interactive CLI with debug logging
python cli.py --mock --debug

# Interactive Streamlit UI
streamlit run ui/streamlit_app.py

# Streamlit UI with debug logging in terminal
PAYGENT_DEBUG=1 streamlit run ui/streamlit_app.py
```

## Agent Interface

The agent exposes the exact interface required for automated evaluation:

```python
from agent import Agent

agent = Agent()

agent.next("Hi")
# {"message": "Hello! Please share your account ID to get started."}

agent.next("My account ID is ACC1001")
# {"message": "Got it. Could you please confirm your full name?"}

agent.next("i am nithin, Nithin Jain")
# {"message": "Thanks. Please provide one verification detail..."}

agent.next("I was born on 14th May 1990")
# {"message": "Identity verified. Your outstanding balance is Rs. 1,250.75..."}
```

<<<<<<< HEAD
Tests inject a fake API client, so the test suite never calls the live Prodigal API.
Tests also inject fake/no-op LLM providers, so the test suite never calls OpenAI.

The Streamlit UI is a thin wrapper around `Agent`. It stores the agent and chat messages in `st.session_state`, includes a reset button, and shows only non-sensitive status in the sidebar. Sensitive identity and card details are not displayed in the UI.
=======
Each `Agent` instance maintains all conversation state internally. No external setup between turns.
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

## LLM Configuration

Create a local `.env` file for LLM-first understanding:

```powershell
Copy-Item .env.example .env
```

Then edit `.env` locally:

```dotenv
PAYGENT_LLM_MODE=required
OPENAI_API_KEY=your_key_here
PAYGENT_LLM_MODEL=gpt-4o-mini
```

The `.env` file is ignored by git and must never be committed. `.env.example` is safe to commit because it contains placeholders only.

The LLM layer is backend-only and extraction-only. It never generates user-facing responses and never bypasses validation or policy gates. Before any LLM call, raw DOB, Aadhaar last 4, pincode, card number, CVV, and expiry values are replaced with placeholders. Local deterministic extraction keeps those sensitive values for validation/payment handling.

## Architecture

```
Agent.next(user_input)
  |
  +-- Cancellation check (intent-aware, not keyword-only)
  +-- Field extraction (rule-based + optional LLM fallback)
  |     +-- Account ID, name, DOB, Aadhaar, pincode
  |     +-- Amount (numeric, word-form, relative: "half", "all of it")
  |     +-- Card number, CVV (including word-form), expiry, cardholder name
  |
  +-- Policy gates (can_show_balance, can_process_payment)
  +-- State machine orchestrator
  |     +-- 10 active states + 7 terminal states
  |     +-- Strict verification (exact name + secondary factor)
  |     +-- Collect-all-then-validate for card details
  |     +-- Retry limits: 3 verification, 5 name mismatch, 3 payment
  |
  +-- API tools (lookup-account, process-payment)
  +-- Response builder (never leaks sensitive data)
```

<<<<<<< HEAD
- A deterministic state-machine orchestrator.
- An LLM-first structured understanding layer.
- Local deterministic extraction for sensitive values and runtime fallback.
- Validators for account IDs, dates, amounts, cards, CVV, and expiry.
- A policy layer that gates balance disclosure, verification, and payment calls.
- API tools for account lookup and payment processing.
- Central response templates that avoid sensitive-data leakage.

This is intentionally not a ReAct or free-form chatbot. The LLM understands user intent and extracts structured candidates, but only the state machine and policy layer decide what action is allowed. User-facing messages come from fixed response templates.

## Important Rules Implemented

- Balance is never shown before verification.
- Payment is never attempted before verification.
- Invalid local inputs do not trigger API calls.
- Full-name verification is exact after trimming only outer whitespace.
- Names must use letters and spaces only, and the agent guides users to match capitalization exactly.
- Verification succeeds only with exact full name plus DOB, Aadhaar last 4, or pincode.
- Partial verification inputs do not count as failed attempts.
- DOB must be a valid date, Aadhaar last 4 must be exactly 4 digits, and pincode must be exactly 6 digits.
- Card numbers must be exactly 16 digits after removing spaces/hyphens and must pass Luhn validation.
- CVV must be exactly 3 digits.
- Account changes before verification reset account-specific state.
- Account changes after verification require restarting the flow.
- Cancellation is supported at any stage.
- Closed conversations do not continue payment flow.
=======
**Why a state machine, not ReAct/LangGraph?** Payment collection has strict sequencing and privacy rules. The agent separates *extraction* (what did the user say?) from *control* (what action is allowed?). Extractors handle messy input; the state machine enforces that balance is never shown before verification and payment never happens without valid card details. This makes the system deterministic, testable, and auditable.

## Key Design Decisions

| Decision | Rationale |
|---|---|
| **Collect-all-then-validate** for card details | Don't reject a card number immediately; wait until all 4 fields are present, then validate together. On API failure, only clear the failing field -- user doesn't re-enter valid data. |
| **Intent-aware cancellation** | "cancel" alone cancels, but "don't cancel the payment" does not. Prevents accidental session destruction. |
| **Word-form digit support** | "CVV is one two three" -> 123. "Aadhaar last four are four three two one" -> 4321. Handles real user speech patterns. |
| **Trailing filler stripping** | "I am Nithin Jain I guess" -> extracts "Nithin Jain". Strips hedging phrases without breaking names. |
| **Invalid date feedback** | "30th February 1988" gets "That date does not appear to be valid" instead of a generic re-prompt. |
| **Optional LLM fallback** | Azure OpenAI masked-span extraction for edge cases. LLM sees only digit-masked text, cannot verify identity, show balance, or trigger payment. |
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

## Sensitive Data Handling

- DOB, Aadhaar, pincode, raw card number, and CVV are **never echoed** in agent responses
- Card number and CVV are **cleared from state** after payment attempt
- In the Streamlit UI, user input is **masked on display**: card shows `4532 **** **** 0366`, CVV shows `1**`
- Success message shows only last 4 digits: `Card used: ****0366`
- Logs use `safe_log()` with automatic redaction

## What Real Users Sound Like

The agent handles all input styles from the assignment:

<<<<<<< HEAD
- Normal interactive usage is LLM-first and uses `PAYGENT_LLM_MODE=required` with `OPENAI_API_KEY` in `.env`.
- If the configured LLM call fails at runtime, deterministic extraction is used as a resilience fallback.
- Retry limits are 3 for account lookup failures, complete verification failures, and payment API user-correctable failures.
- Zero-balance accounts are verified, then closed with a no-payment-needed message.
- Two-digit DOB years use a deterministic split: `90 -> 1990`, `27 -> 2027` for expiry.
- The API does not persist balance updates, matching the assignment note.
=======
| Clean Input | Messy Input (Handled) |
|---|---|
| `ACC1001` | `"yeah my account number is ACC1001 I think"` |
| `Nithin Jain` | `"i am nithin, Nithin Jain"`, `"Nithin Jain i guess"` |
| `1990-05-14` | `"born on 14th May 1990"`, `"14/05/1990"`, `"DOB is May 14, 90"` |
| `4321` | `"aadhar last four digits are four three two one"` |
| `1000.00` | `"a thousand rupees"`, `"five hundred"`, `"all of it"`, `"half of it"` |
| `CVV: 123` | `"CVV is one two three"` |
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

## Project Structure

<<<<<<< HEAD
- Add secure persistent session IDs for multi-session deployment.
- Add OpenTelemetry traces with strict redaction.
- Replace direct card collection with PCI-compliant tokenized collection.
- Add rate limiting and a human handoff path.
=======
```
paygent/
  agent_core.py          # State machine orchestrator (main logic)
  extraction.py          # Rule-based field extraction from messy text
  verification.py        # Strict identity verification
  validators.py          # Input validators (Luhn, expiry, amounts)
  policy.py              # Policy gates and cancellation detection
  responses.py           # Response templates (no sensitive data leaks)
  state.py               # Conversation state model
  stages.py              # State enum and terminal state set
  config.py              # Constants (retry limits, API URL)
  llm_extraction.py      # LLM fallback orchestration
  azure_openai_extractor.py  # Azure OpenAI masked-span extractor
  logging_utils.py       # Safe logging with redaction
  tools/
    api_client.py        # HTTP client for lookup and payment APIs

agent.py                 # Public Agent class (required interface)
cli.py                   # Interactive CLI (--mock, --debug flags)
ui/streamlit_app.py      # Interactive Streamlit chat UI

tests/                   # 117 unit + integration tests
eval/
  stress_test.py         # 24-scenario robustness harness
  run_scenarios.py       # 16-scenario evaluation runner

docs/
  design.md              # Architecture, decisions, assumptions, evaluation
  sample_conversations.md  # 7 annotated conversation transcripts
```

## Testing

```bash
# Unit + integration tests (117 tests, <1 second)
pytest -q

# Stress test (24 scenarios covering happy paths, failures, edge cases)
python eval/stress_test.py

# Verbose stress test (prints full conversation transcripts)
python eval/stress_test.py --verbose

# Basic scenario runner
python eval/run_scenarios.py
```

## Optional LLM Fallback

The agent works fully without any LLM API key. To enable the optional Azure OpenAI extraction fallback:

```bash
cp .env.example .env
# Fill in your Azure OpenAI credentials
```

The LLM extractor masks all digits before sending to the model, accepts only medium/high-confidence results, and cannot override any state machine decision. It supplements rule-based extraction for unusual phrasing that the rule parser doesn't cover.

## Deliverables

| # | Deliverable | Location |
|---|---|---|
| 1 | **Working Code** | |
|   | Agent class with `next()` interface | `agent.py` |
|   | Supporting modules | `paygent/` (11 modules) |
|   | Dependencies | `requirements.txt` |
|   | Setup and run instructions | This file (`README.md`) |
|   | Interactive CLI | `cli.py` (use `--mock` for offline, `--debug` for logging) |
|   | Interactive Streamlit UI | `ui/streamlit_app.py` |
| 2 | **Sample Conversations** | `docs/sample_conversations.md` |
|   | Successful end-to-end payment | Scenario 1 (messy inputs) |
|   | Verification failure (retries exhausted) | Scenario 2 |
|   | Payment failure (invalid CVV, recovery) | Scenario 3 |
|   | Zero balance | Scenario 4 |
|   | Leap year DOB + invalid date feedback | Scenario 5 |
|   | Account change mid-flow | Scenario 6 |
|   | Incremental card details | Scenario 7 |
| 3 | **Design Document** | `docs/design.md` |
|   | Architecture overview | Section 2 |
|   | Key decisions and rationale | Sections 3-4 |
|   | Assumptions documented | Section 7 |
|   | Trade-offs accepted | Section 8 |
|   | Improvements with more time | Section 9 |
| 4 | **Evaluation** | `eval/` |
|   | Test suite (117 tests) | `tests/` |
|   | Evaluation scenarios (16) | `eval/run_scenarios.py` |
|   | Stress test (24 scenarios) | `eval/stress_test.py` |
|   | Correctness criteria | `docs/design.md` Section 10 |
|   | Honest assessment of weaknesses | `docs/design.md` Section 10 |

## Debug Mode

To see how the agent perceives each input, enable debug logging:

```bash
# CLI
python cli.py --mock --debug

# Streamlit (prints to terminal)
PAYGENT_DEBUG=1 streamlit run ui/streamlit_app.py
```

Debug output shows: turn number, current stage, extracted fields (masked), state transitions, and response -- without exposing sensitive data.
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
