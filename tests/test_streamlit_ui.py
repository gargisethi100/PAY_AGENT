from paygent.azure_openai_extractor import AzureMaskedSpanExtractor
from ui.streamlit_app import (
    AzureUiSettings,
    build_status_summary,
    build_llm_extractor,
    render_app_css,
    render_demo_accounts,
    render_field_diagnostics,
    render_fintech_header,
    render_chat_transcript,
    render_status_summary,
    sanitize_user_message_for_display,
    submit_user_message,
)


class RecordingAgent:
    def __init__(self):
        self.received = []

    def next(self, user_input: str) -> dict:
        self.received.append(user_input)
        return {"message": "ok"}


<<<<<<< HEAD
def test_pincode_display_sanitizer_remains_available():
    assert sanitize_user_message_for_display("pincode? it's 4 0 0 0 0 2") == "Pincode provided"
=======
class FakeAccount:
    account_id = "ACC1001"


class FakeState:
    stage = "AWAIT_CARD_DETAILS"
    account = FakeAccount()
    verified = True
    transaction_id = None
    last_error_code = None
    payment_attempts = 2
    verification_attempts = 1


def test_pincode_display_sanitizer_is_user_friendly():
    result = sanitize_user_message_for_display("pincode? it's 4 0 0 0 0 2")
    assert "400002" not in result  # Raw pincode must not appear
    assert "pincode" in result.lower()  # Context preserved
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d


def test_submit_user_message_displays_and_passes_raw_input_to_agent():
    agent = RecordingAgent()
    messages = []
    raw = "pincode? it's 4 0 0 0 0 2"

    submit_user_message(agent, messages, raw)

    assert agent.received == [raw]
<<<<<<< HEAD
    assert messages[0] == {"role": "user", "content": raw}
    assert messages[1] == {"role": "assistant", "content": "ok"}


def test_submit_user_message_displays_raw_card_details_to_user():
    agent = RecordingAgent()
    messages = []
    raw = "card number 4532015112830366 CVV 123"

    submit_user_message(agent, messages, raw)

    assert agent.received == [raw]
    assert messages[0] == {"role": "user", "content": raw}
=======
    assert "400002" not in messages[0]["content"]  # Masked in display
    assert messages[1] == {"role": "assistant", "content": "ok"}


def test_build_llm_extractor_requires_enabled_and_complete_config():
    disabled = AzureUiSettings(
        enabled=False,
        endpoint="https://example.openai.azure.com/",
        deployment="model-router",
        api_version="2025-01-01-preview",
        api_key="secret",
    )
    missing_key = AzureUiSettings(
        enabled=True,
        endpoint="https://example.openai.azure.com/",
        deployment="model-router",
        api_version="2025-01-01-preview",
        api_key="",
    )
    complete = AzureUiSettings(
        enabled=True,
        endpoint="https://example.openai.azure.com/",
        deployment="model-router",
        api_version="2025-01-01-preview",
        api_key="secret",
    )

    assert build_llm_extractor(disabled) is None
    assert build_llm_extractor(missing_key) is None
    assert isinstance(build_llm_extractor(complete), AzureMaskedSpanExtractor)


def test_render_field_diagnostics_is_redacted():
    diagnostics = {
        "card_number_detected": True,
        "card_number_valid": False,
        "cvv_detected": True,
        "cvv_format_valid": False,
        "expiry_detected": True,
        "expiry_valid": True,
        "account_switch_requested": True,
        "account_reset_performed": True,
        "alias_name_mismatch": True,
        "full_name_detected": True,
        "full_name_exact_match": False,
        "name_mismatch": True,
        "secondary_factor_detected": True,
        "zero_balance_close_reached": True,
        "terminal_followup_detected": True,
        "terminal_account_switch_requested": True,
        "bare_cvv_detected": True,
        "card_number_local_failures": True,
        "raw_full_name": "Priya Agarwal",
        "raw_dob": "1992-08-10",
        "raw_aadhaar": "2468",
        "raw_pincode": "400003",
        "raw_card_number": "4532015112830366",
        "raw_cvv": "123",
    }

    rendered = render_field_diagnostics(diagnostics)

    assert "Card number detected: Yes" in rendered
    assert "Card number valid: No" in rendered
    assert "CVV format valid: No" in rendered
    assert "Expiry valid: Yes" in rendered
    assert "Account switch requested: Yes" in rendered
    assert "Account reset performed: Yes" in rendered
    assert "Alias/name mismatch: Yes" in rendered
    assert "Full name detected: Yes" in rendered
    assert "Full name exact match: No" in rendered
    assert "Name mismatch: Yes" in rendered
    assert "Secondary factor detected: Yes" in rendered
    assert "Zero balance close reached: Yes" in rendered
    assert "Terminal follow-up detected: Yes" in rendered
    assert "Terminal account switch requested: Yes" in rendered
    assert "Bare CVV detected: Yes" in rendered
    assert "Card number local failures: Yes" in rendered
    assert "Priya Agarwal" not in rendered
    assert "1992-08-10" not in rendered
    assert "2468" not in rendered
    assert "400003" not in rendered
    assert "4532015112830366" not in rendered
    assert "123" not in rendered


def test_render_app_css_contains_fintech_layout_hooks():
    css = render_app_css()

    assert "paygent-header" in css
    assert "paygent-stage-badge" in css
    assert "paygent-chat-frame" in css
    assert "@media" in css
    assert "linear-gradient" not in css


def test_fintech_header_is_compact_and_safe():
    rendered = render_fintech_header("Awaiting card details")

    assert "PAYgent" in rendered
    assert "Secure payment assistant" in rendered
    assert "Awaiting card details" in rendered
    assert "Privacy locked" in rendered
    assert "4532015112830366" not in rendered
    assert "1992-08-10" not in rendered


def test_status_summary_is_redacted_and_scan_friendly():
    rows = build_status_summary(FakeState())
    rendered = "\n".join(f"{label}: {value}" for label, value, _tone in rows)

    assert ("Stage", "Awaiting card details", "active") in rows
    assert ("Account", "Loaded", "good") in rows
    assert ("Verification", "Verified", "good") in rows
    assert ("Payment", "Attempted", "warn") in rows
    assert "ACC1001" not in rendered


def test_status_summary_html_is_compact_for_streamlit_markdown():
    html = render_status_summary([("Stage", "Awaiting account ID", "active")])

    assert "\n" not in html
    assert "paygent-status-row" in html


def test_chat_transcript_html_is_compact_and_escapes_content():
    html = render_chat_transcript(
        [
            {"role": "user", "content": "<script>alert('x')</script>"},
            {"role": "assistant", "content": "Got it."},
        ]
    )

    assert "\n" not in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "paygent-message-user" in html
    assert "paygent-message-assistant" in html


def test_demo_accounts_copy_has_no_sensitive_values():
    rendered = "\n".join(render_demo_accounts())

    assert "ACC1001" in rendered
    assert "standard balance" in rendered.lower()
    assert "1990-05-14" not in rendered
    assert "4321" not in rendered
    assert "400001" not in rendered
    assert "Nithin" not in rendered
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
