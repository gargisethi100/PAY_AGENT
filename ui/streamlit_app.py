from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
import re
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent import Agent
from paygent.azure_openai_extractor import (
    AzureMaskedSpanExtractor,
    AzureOpenAIConfig,
    load_azure_openai_config,
)


STAGE_LABELS = {
    "START": "Starting",
    "AWAIT_ACCOUNT_ID": "Awaiting account ID",
    "LOOKUP_ACCOUNT": "Looking up account",
    "AWAIT_FULL_NAME": "Awaiting full name",
    "AWAIT_SECONDARY_FACTOR": "Awaiting verification detail",
    "VERIFIED_SHOW_BALANCE": "Verified",
    "AWAIT_PAYMENT_AMOUNT": "Awaiting payment amount",
    "AWAIT_CARD_DETAILS": "Awaiting card details",
    "PROCESS_PAYMENT": "Processing payment",
    "SUCCESS_CLOSE": "Payment complete",
    "CANCELLED_CLOSE": "Cancelled",
    "ZERO_BALANCE_CLOSE": "No payment due",
    "ACCOUNT_LOOKUP_FAILED_CLOSE": "Account lookup failed",
    "VERIFICATION_FAILED_CLOSE": "Verification failed",
    "PAYMENT_FAILED_CLOSE": "Payment failed",
    "API_UNAVAILABLE_CLOSE": "Service unavailable",
}


@dataclass(frozen=True)
class AzureUiSettings:
    enabled: bool
    endpoint: str
    deployment: str
    api_version: str
    api_key: str

    def signature(self) -> tuple[str, str, str, bool]:
        return (self.endpoint, self.deployment, self.api_version, self.enabled)


def default_azure_ui_settings() -> AzureUiSettings:
    config = load_azure_openai_config(ROOT / ".env")
    return AzureUiSettings(
        enabled=config.is_complete(),
        endpoint=config.endpoint,
        deployment=config.deployment,
        api_version=config.api_version,
        api_key=config.api_key,
    )


def build_llm_extractor(settings: AzureUiSettings):
    if not settings.enabled:
        return None
    config = AzureOpenAIConfig(
        endpoint=settings.endpoint,
        deployment=settings.deployment,
        api_version=settings.api_version,
        api_key=settings.api_key,
    )
    if not config.is_complete():
        return None
    return AzureMaskedSpanExtractor(config)


def create_agent(settings: AzureUiSettings) -> Agent:
    return Agent(llm_extractor=build_llm_extractor(settings))


def initialize_session() -> None:
    if "azure_settings" not in st.session_state:
        st.session_state.azure_settings = default_azure_ui_settings()
    if "agent" not in st.session_state:
        st.session_state.agent = create_agent(st.session_state.azure_settings)
    if "messages" not in st.session_state:
        greeting = st.session_state.agent.next("Hi")["message"]
        st.session_state.messages = [{"role": "assistant", "content": greeting}]


def reset_conversation() -> None:
    st.session_state.agent = create_agent(st.session_state.azure_settings)
    greeting = st.session_state.agent.next("Hi")["message"]
    st.session_state.messages = [{"role": "assistant", "content": greeting}]


def stage_label(stage) -> str:
    raw_stage = stage.value if hasattr(stage, "value") else str(stage)
    return STAGE_LABELS.get(raw_stage, raw_stage.replace("_", " ").title())


def friendly_error_code(error_code: str) -> str:
    return error_code.replace("_", " ").capitalize()


def payment_status_for_state(state) -> tuple[str, str]:
    if state.transaction_id:
        return "Successful", "good"
    if state.last_error_code:
        return f"Error: {friendly_error_code(state.last_error_code)}", "error"
    if state.payment_attempts:
        return "Attempted", "warn"
    return "Not started", "neutral"


def build_status_summary(state) -> list[tuple[str, str, str]]:
    payment_status, payment_tone = payment_status_for_state(state)
    return [
        ("Stage", stage_label(state.stage), "active"),
        ("Account", "Loaded" if state.account is not None else "Not loaded", "good" if state.account else "neutral"),
        ("Verification", "Verified" if state.verified else "Pending", "good" if state.verified else "neutral"),
        ("Payment", payment_status, payment_tone),
        ("Verification retries", str(state.verification_attempts), "neutral"),
        ("Payment attempts", str(state.payment_attempts), "neutral"),
    ]


def render_app_css() -> str:
    return """
    <style>
      :root {
        --pg-bg: #f6f7f9;
        --pg-panel: #ffffff;
        --pg-ink: #111827;
        --pg-muted: #5b6472;
        --pg-line: #d8dee7;
        --pg-teal: #0f766e;
        --pg-teal-soft: #e7f5f1;
        --pg-amber: #92400e;
        --pg-amber-soft: #fff7ed;
        --pg-red: #991b1b;
        --pg-red-soft: #fef2f2;
      }

      .stApp {
        background: var(--pg-bg);
        color: var(--pg-ink);
      }

      .block-container {
        max-width: 980px;
        padding-top: 1.25rem;
        padding-bottom: 6rem;
      }

      h1, h2, h3, p {
        letter-spacing: 0;
      }

      .paygent-header {
        background: var(--pg-panel);
        border: 1px solid var(--pg-line);
        border-radius: 8px;
        padding: 1rem 1.125rem;
        margin-bottom: 1rem;
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 1rem;
        box-shadow: 0 10px 28px rgba(17, 24, 39, 0.06);
      }

      .paygent-title {
        font-size: 1.6rem;
        line-height: 1.1;
        font-weight: 750;
        margin: 0;
        color: var(--pg-ink);
      }

      .paygent-subtitle {
        margin-top: 0.35rem;
        font-size: 0.96rem;
        color: var(--pg-muted);
      }

      .paygent-badges {
        display: flex;
        gap: 0.5rem;
        justify-content: flex-end;
        flex-wrap: wrap;
      }

      .paygent-stage-badge,
      .paygent-privacy-badge {
        display: inline-flex;
        align-items: center;
        min-height: 2rem;
        padding: 0.35rem 0.65rem;
        border-radius: 8px;
        font-size: 0.82rem;
        font-weight: 650;
        white-space: nowrap;
      }

      .paygent-stage-badge {
        color: var(--pg-teal);
        background: var(--pg-teal-soft);
        border: 1px solid #b7ded7;
      }

      .paygent-privacy-badge {
        color: var(--pg-amber);
        background: var(--pg-amber-soft);
        border: 1px solid #fed7aa;
      }

      .paygent-chat-frame {
        background: var(--pg-panel);
        border: 1px solid var(--pg-line);
        border-radius: 8px;
        padding: 0.875rem;
        min-height: 56vh;
        box-shadow: 0 10px 28px rgba(17, 24, 39, 0.05);
      }

      .paygent-message-row {
        display: flex;
        margin: 0.75rem 0;
      }

      .paygent-message-row:first-child {
        margin-top: 0;
      }

      .paygent-message-assistant {
        justify-content: flex-start;
      }

      .paygent-message-user {
        justify-content: flex-end;
      }

      .paygent-message {
        max-width: min(76%, 720px);
        border-radius: 8px;
        padding: 0.75rem 0.875rem;
        border: 1px solid var(--pg-line);
        line-height: 1.45;
        font-size: 0.96rem;
      }

      .paygent-message-assistant .paygent-message {
        background: #f9fafb;
        color: var(--pg-ink);
      }

      .paygent-message-user .paygent-message {
        background: var(--pg-teal-soft);
        border-color: #b7ded7;
        color: #0b3f3a;
      }

      .paygent-message-label {
        display: block;
        margin-bottom: 0.25rem;
        color: var(--pg-muted);
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
      }

      .paygent-sidebar-title {
        font-size: 0.95rem;
        font-weight: 750;
        margin: 0.2rem 0 0.75rem;
      }

      .paygent-status-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0.45rem;
        margin-bottom: 0.75rem;
      }

      .paygent-status-row {
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        border: 1px solid var(--pg-line);
        border-radius: 8px;
        padding: 0.55rem 0.65rem;
        background: #ffffff;
      }

      .paygent-status-label {
        color: var(--pg-muted);
        font-size: 0.78rem;
      }

      .paygent-status-value {
        color: var(--pg-ink);
        font-size: 0.8rem;
        font-weight: 700;
        text-align: right;
      }

      .paygent-status-good .paygent-status-value {
        color: var(--pg-teal);
      }

      .paygent-status-warn .paygent-status-value {
        color: var(--pg-amber);
      }

      .paygent-status-error .paygent-status-value {
        color: var(--pg-red);
      }

      div[data-testid="stChatInput"] {
        max-width: 980px;
        margin: 0 auto;
      }

      div[data-testid="stSidebar"] {
        background: #f9fafb;
        border-right: 1px solid var(--pg-line);
      }

      @media (max-width: 720px) {
        .block-container {
          padding-left: 0.75rem;
          padding-right: 0.75rem;
          padding-top: 0.75rem;
        }

        .paygent-header {
          flex-direction: column;
          padding: 0.875rem;
        }

        .paygent-badges {
          justify-content: flex-start;
        }

        .paygent-message {
          max-width: 92%;
        }
      }
    </style>
    """


def render_fintech_header(stage_text: str) -> str:
    safe_stage = escape(stage_text)
    return f"""
    <section class="paygent-header" aria-label="PAYgent overview">
      <div>
        <div class="paygent-title">PAYgent</div>
        <div class="paygent-subtitle">Secure payment assistant</div>
      </div>
      <div class="paygent-badges">
        <span class="paygent-stage-badge">{safe_stage}</span>
        <span class="paygent-privacy-badge">Privacy locked</span>
      </div>
    </section>
    """


def render_status_summary(rows: list[tuple[str, str, str]]) -> str:
    items = []
    for label, value, tone in rows:
        safe_label = escape(label)
        safe_value = escape(value)
        safe_tone = escape(tone)
        items.append(
            f'<div class="paygent-status-row paygent-status-{safe_tone}">'
            f'<span class="paygent-status-label">{safe_label}</span>'
            f'<span class="paygent-status-value">{safe_value}</span>'
            "</div>"
        )
    return f'<div class="paygent-status-grid">{"".join(items)}</div>'


def render_chat_transcript(messages: list[dict[str, str]]) -> str:
    rows = []
    for message in messages:
        role = "user" if message.get("role") == "user" else "assistant"
        label = "You" if role == "user" else "PAYgent"
        content = escape(message.get("content", "")).replace("\n", "<br>")
        rows.append(
            f'<div class="paygent-message-row paygent-message-{role}">'
            f'<div class="paygent-message">'
            f'<span class="paygent-message-label">{label}</span>'
            f"{content}"
            f"</div>"
            f"</div>"
        )
    return f'<section class="paygent-chat-frame" aria-label="Conversation">{"".join(rows)}</section>'


def render_demo_accounts() -> list[str]:
    return [
        "ACC1001 - standard balance scenario",
        "ACC1002 - long-name verification scenario",
        "ACC1003 - zero-balance scenario",
        "ACC1004 - leap-year verification scenario",
    ]


def render_field_diagnostics(diagnostics: dict) -> str:
    labels = [
        ("account_switch_requested", "Account switch requested"),
        ("account_reset_performed", "Account reset performed"),
        ("alias_name_mismatch", "Alias/name mismatch"),
        ("full_name_detected", "Full name detected"),
        ("full_name_exact_match", "Full name exact match"),
        ("name_mismatch", "Name mismatch"),
        ("secondary_factor_detected", "Secondary factor detected"),
        ("zero_balance_close_reached", "Zero balance close reached"),
        ("terminal_followup_detected", "Terminal follow-up detected"),
        ("terminal_account_switch_requested", "Terminal account switch requested"),
        ("card_number_detected", "Card number detected"),
        ("card_number_valid", "Card number valid"),
        ("card_number_local_failures", "Card number local failures"),
        ("cvv_detected", "CVV detected"),
        ("cvv_format_valid", "CVV format valid"),
        ("cvv_local_failures", "CVV local failures"),
        ("bare_cvv_detected", "Bare CVV detected"),
        ("expiry_detected", "Expiry detected"),
        ("expiry_valid", "Expiry valid"),
        ("expiry_local_failures", "Expiry local failures"),
    ]
    lines = []
    for key, label in labels:
        value = diagnostics.get(key)
        if value is None:
            rendered = "Unknown"
        else:
            rendered = "Yes" if value else "No"
        lines.append(f"{label}: {rendered}")
    return "\n".join(lines)


def _mask_card_number_in_text(text: str) -> str:
    """Replace card numbers with first4****last4 format."""
    def _mask(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if len(digits) < 8:
            return "****"
        return digits[:4] + " **** **** " + digits[-4:]
    return re.sub(r"(?:\d[\s-]*){13,19}", _mask, text)


def _mask_cvv_in_text(text: str) -> str:
    """Replace CVV digits with first char visible, rest masked."""
    # CVV followed by digits
    result = re.sub(
        r"\bcvv\b[^\d]*(\d{3,4})\b",
        lambda m: "CVV " + m.group(1)[0] + "*" * (len(m.group(1)) - 1),
        text,
        flags=re.I,
    )
    # CVV followed by word-form digits (with optional filler like "is", ":")
    result = re.sub(
        r"\bcvv\b[^,.;\n]*?((?:(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)\s*){3,4})",
        lambda m: "CVV " + m.group(1).split()[0][0] + "**",
        result,
        flags=re.I,
    )
    return result


def sanitize_user_message_for_display(message: str) -> str:
    text = message.strip()
    result = text

    # Mask CVV before card (CVV regex is more specific, avoids card masking eating CVV digits)
    if _has_cvv_value(result):
        result = _mask_cvv_in_text(result)
    if _has_card_number_value(result):
        result = _mask_card_number_in_text(result)
    if _has_dob_value(result):
        result = re.sub(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b", "****-**-**", result)
        result = re.sub(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", "**-**-****", result)
    if _has_aadhaar_value(result):
        result = re.sub(r"(\b(?:aadhaar|aadhar)\b[^,.;\n]*?)(\d(?:[\s-]*\d){3,})", r"\1****", result, flags=re.I)
    if _has_pincode_value(result):
        result = re.sub(r"(\b(?:pin\s*code|pincode|pin)\b[^\d,.;\n]*)(\d(?:[\s-]*\d){5})", r"\1******", result, flags=re.I)

    return result


def submit_user_message(agent: Agent, messages: list[dict[str, str]], user_input: str) -> str:
    messages.append({"role": "user", "content": user_input})
    response = agent.next(user_input)["message"]
    messages.append({"role": "assistant", "content": response})
    return response


def _has_dob_value(text: str) -> bool:
    lower = text.lower()
    if any(label in lower for label in ["dob", "date of birth", "born"]):
        return True
    return bool(re.search(r"\b\d{4}-\d{1,2}-\d{1,2}\b|\b\d{1,2}-\d{1,2}-\d{2,4}\b", text))


def _has_aadhaar_value(text: str) -> bool:
    return bool(re.search(r"\b(?:aadhaar|aadhar)\b[^,.;\n]*(?:\d[\s-]*){4,}", text, re.I))


def _has_pincode_value(text: str) -> bool:
    return bool(re.search(r"\b(?:pin\s*code|pincode|pin)\b[^,.;\n]*(?:\d[\s-]*){6}\b", text, re.I))


def _has_card_number_value(text: str) -> bool:
    return bool(re.search(r"\b(?:card(?:\s+number)?\b[^,.;\n]*)?(?:\d[\s-]*){13,19}\b", text, re.I))


def _has_cvv_value(text: str) -> bool:
    return bool(
        re.search(
            r"\bcvv\b[^,.;\n]*(?:\d{3,4}|(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)(?:\s+(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)){2,3})",
            text,
            re.I,
        )
    )


def render_sidebar() -> None:
    state = st.session_state.agent._core.state

    with st.sidebar:
<<<<<<< HEAD
        st.header("Status")
        st.write("Current stage:", stage_label(state.stage))
        st.write("Account loaded:", "Yes" if state.account is not None else "No")
        st.write("User verified:", "Yes" if state.verified else "No")
        st.write("Payment status:", payment_status)
        st.write("Verification attempts used:", state.verification_attempts)
        st.write("Payment attempts used:", state.payment_attempts)
        st.caption("Sensitive values may appear in your chat transcript, but are not shown in sidebar status or sent raw to the LLM.")
=======
        st.markdown('<div class="paygent-sidebar-title">Session status</div>', unsafe_allow_html=True)
        st.markdown(render_status_summary(build_status_summary(state)), unsafe_allow_html=True)
        st.caption("Sensitive identity and card details stay hidden.")
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

        with st.expander("Demo accounts", expanded=False):
            for account in render_demo_accounts():
                st.markdown(f"- {account}")

        with st.expander("Debug field detection", expanded=False):
            st.code(render_field_diagnostics(state.last_diagnostics), language="text")

        render_azure_settings_controls()
        st.button("Reset conversation", on_click=reset_conversation, use_container_width=True, type="primary")


def render_azure_settings_controls() -> None:
    current = st.session_state.azure_settings
    with st.expander("Azure OpenAI extraction", expanded=False):
        enabled = st.checkbox("Enable LLM extraction", value=current.enabled)
        endpoint = st.text_input("Azure endpoint", value=current.endpoint)
        deployment = st.text_input("Deployment", value=current.deployment)
        api_version = st.text_input("API version", value=current.api_version)
        if current.api_key:
            st.caption("API key loaded from environment or prior password input.")
            override_key = st.text_input("API key override", value="", type="password")
            api_key = override_key or current.api_key
        else:
            api_key = st.text_input("API key", value="", type="password")

        candidate = AzureUiSettings(
            enabled=enabled,
            endpoint=endpoint.strip(),
            deployment=deployment.strip(),
            api_version=api_version.strip(),
            api_key=api_key.strip(),
        )
        if build_llm_extractor(candidate):
            st.success("Azure extraction is configured.")
        elif enabled:
            st.warning("Add endpoint, deployment, API version, and API key to enable extraction.")
        else:
            st.info("LLM extraction is disabled.")

        if st.button("Apply Azure settings", use_container_width=True):
            st.session_state.azure_settings = candidate
            reset_conversation()


def main() -> None:
    st.set_page_config(page_title="PAYgent", page_icon=None, layout="centered")
    st.markdown(render_app_css(), unsafe_allow_html=True)

    initialize_session()
    state = st.session_state.agent._core.state
    st.markdown(render_fintech_header(stage_label(state.stage)), unsafe_allow_html=True)
    render_sidebar()

    st.markdown(render_chat_transcript(st.session_state.messages), unsafe_allow_html=True)

    user_input = st.chat_input("Type your message")
    if user_input:
<<<<<<< HEAD
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
=======
        display_user_input = sanitize_user_message_for_display(user_input)
        st.session_state.messages.append({"role": "user", "content": display_user_input})
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

        response = st.session_state.agent.next(user_input)["message"]
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


if __name__ == "__main__":
    main()
