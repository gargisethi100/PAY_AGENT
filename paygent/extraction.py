from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation

from paygent.stages import Stage


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

DIGIT_WORDS = {
    "zero": "0",
    "oh": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}

_DIGIT_WORD_PATTERN = "|".join(DIGIT_WORDS.keys())


def _words_to_digits(text: str) -> str | None:
    """Convert word-form digit sequences to numeric string.

    E.g. "four three two one" -> "4321", "one two three" -> "123".
    Returns None if no digit words found.
    """
    words = re.findall(_DIGIT_WORD_PATTERN, text, re.I)
    if not words:
        return None
    return "".join(DIGIT_WORDS[w.lower()] for w in words)


@dataclass
class ExtractedFields:
    account_id: str | None = None
    account_change_requested: bool = False
    full_name: str | None = None
    alias_name_attempt: bool = False
    dob: str | None = None
    aadhaar_last4: str | None = None
    pincode: str | None = None
    amount: Decimal | None = None
    relative_amount_fraction: Decimal | None = None
    full_amount_requested: bool = False
    cardholder_name: str | None = None
    card_number: str | None = None
    cvv: str | None = None
    expiry_month: int | None = None
    expiry_year: int | None = None
<<<<<<< HEAD
    invalid_fields: set[str] = field(default_factory=set)
=======
    bare_cvv_detected: bool = False
    invalid_cvv_attempt: bool = False
    invalid_expiry_attempt: bool = False
    invalid_dob_attempt: bool = False
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d


def extract_fields(text: str, stage: Stage | str | None = None) -> ExtractedFields:
    normalized_stage = Stage(stage) if stage and not isinstance(stage, Stage) else stage
    account_id = extract_account_id(text)
    full_name = extract_name(text, normalized_stage)
    dob = extract_dob(text)
    aadhaar_last4 = extract_aadhaar_last4(text)
    pincode = extract_pincode(text)
    amount = extract_amount(text, normalized_stage)
    cardholder_name = extract_cardholder_name(text)
    card_number = extract_card_number(text)
    cvv = extract_cvv(text)
    expiry_month, expiry_year = extract_expiry(text)
    invalid_fields = detect_invalid_fields(
        text,
        normalized_stage,
        full_name=full_name,
        dob=dob,
        aadhaar_last4=aadhaar_last4,
        pincode=pincode,
        cardholder_name=cardholder_name,
        card_number=card_number,
        cvv=cvv,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
    )
    return ExtractedFields(
<<<<<<< HEAD
        account_id=account_id,
        full_name=full_name,
        dob=dob,
        aadhaar_last4=aadhaar_last4,
        pincode=pincode,
        amount=amount,
        full_amount_requested=bool(re.search(r"\b(full|entire|complete)\s+amount\b|\bclear\s+the\s+full\b", text, re.I)),
        cardholder_name=cardholder_name,
        card_number=card_number,
        cvv=cvv,
        expiry_month=expiry_month,
        expiry_year=expiry_year,
        invalid_fields=invalid_fields,
=======
        account_id=extract_account_id(text),
        account_change_requested=detect_account_change_request(text),
        full_name=extract_name(text, normalized_stage),
        alias_name_attempt=detect_alias_name_attempt(text, normalized_stage),
        dob=extract_dob(text),
        aadhaar_last4=extract_aadhaar_last4(text, normalized_stage),
        pincode=extract_pincode(text, normalized_stage),
        amount=extract_amount(text, normalized_stage),
        relative_amount_fraction=extract_relative_amount_fraction(text, normalized_stage),
        full_amount_requested=extract_full_amount_requested(text),
        cardholder_name=extract_cardholder_name(text, normalized_stage),
        card_number=extract_card_number(text),
        cvv=extract_cvv(text, normalized_stage),
        expiry_month=extract_expiry(text, normalized_stage)[0],
        expiry_year=extract_expiry(text, normalized_stage)[1],
        bare_cvv_detected=detect_bare_cvv(text, normalized_stage),
        invalid_cvv_attempt=detect_invalid_cvv_attempt(text, normalized_stage),
        invalid_expiry_attempt=detect_invalid_expiry_attempt(text, normalized_stage),
        invalid_dob_attempt=detect_invalid_dob_attempt(text),
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
    )


def extract_account_id(text: str) -> str | None:
    match = re.search(r"\bACC\s*[- ]?\s*(\d+)\b", text, re.I)
    if not match:
        return None
    return f"ACC{match.group(1)}".upper()


def detect_account_change_request(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:change|switch|update|replace)\s+(?:my\s+)?(?:account|acc)(?:\s+id)?\b"
            r"|\b(?:use|using)\s+(?:a\s+)?(?:different|another|new)\s+(?:account|acc)(?:\s+id)?\b"
            r"|\b(?:use|using)\s+(?:another|new)\s+(?:account\s+|acc\s+)?id\b"
            r"|\b(?:different|another|new)\s+(?:account|acc)(?:\s+id)?\b",
            text,
            re.I,
        )
    )


def extract_name(text: str, stage: Stage | None = None) -> str | None:
    text = _strip_wrapping_quotes_and_punctuation(text)
    if _has_alias_without_full_name(text):
        return None

    explicit_patterns = [
        r"\b(?:mera|meri)\s+naam\s+(.+?)\s+hai\b",
        r"\bfull\s+name\s+(?:is|:)\s*([^,.;\n]+)",
        r"\bmy\s+name\s+is\s+([^,.;\n]+)",
        r"\bname\s+(?:is|:)\s*([^,.;\n]+)",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            name = _clean_name(match.group(1))
            if name and _looks_like_full_legal_name(name):
                return name

    informal_repeat = re.search(r"\b(?:it'?s|it\s+is)\s+([^,.;\n]+),\s*([^,.;\n]+)", text, re.I)
    if informal_repeat:
        name = _clean_name(informal_repeat.group(2))
        if name and _looks_like_full_legal_name(name):
            return name

    if stage == Stage.AWAIT_FULL_NAME:
        self_intro = re.search(
            r"\b(?:hi|hey|hello)?\s*(?:i\s+am|i'm|this\s+is|myself)\s+([^,.;\n]+)",
            text,
            re.I,
        )
        if self_intro:
            name = _clean_name(self_intro.group(1))
            if name and _looks_like_full_legal_name(name):
                return name

        if _has_conversational_name_marker(text):
            return None
        candidate = _strip_leading_name_phrase(text)
        candidate = _TRAILING_FILLER.sub("", candidate).strip(" \t\r\n,.;:")
        if _looks_like_full_legal_name(candidate):
            return candidate
    return None


def detect_alias_name_attempt(text: str, stage: Stage | None = None) -> bool:
    if stage != Stage.AWAIT_FULL_NAME:
        return False
    stripped = _strip_wrapping_quotes_and_punctuation(text)
    if not stripped or any(ch.isdigit() for ch in stripped):
        return False
    if re.search(r"\b(account|acc|dob|aadhaar|aadhar|pincode|pin|card|cvv|amount|pay|change|switch)\b", stripped, re.I):
        return False
    if re.search(r"\b(?:hi|hey|hello)\s+(?:i\s+am|i'm|my\s+name\s+is|name\s+is)\s+[A-Za-z][A-Za-z .'-]*$", stripped, re.I):
        return True
    if re.search(r"\b(?:i\s+am|i'm)\s+[A-Za-z][A-Za-z .'-]*$", stripped, re.I):
        return True
    if re.search(r"\b(?:you\s+can\s+)?call\s+me\s+[A-Za-z][A-Za-z .'-]*$", stripped, re.I):
        return True
    return False


def _has_alias_without_full_name(value: str) -> bool:
    lower = value.lower()
    return bool(re.search(r"\b(?:you\s+can\s+)?call\s+me\b", lower)) and "full name" not in lower


def _has_conversational_name_marker(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:hey|hi|hello|my\s+name\s+is|name\s+is|full\s+name\s+is|call\s+me)\b",
            value,
            re.I,
        )
    )


def _strip_wrapping_quotes_and_punctuation(value: str) -> str:
    value = value.strip()
    wrapping_chars = "\"'`“”‘’"
    while len(value) >= 2 and value[0] in wrapping_chars and value[-1] in wrapping_chars:
        value = value[1:-1].strip()
    return value.strip(" \t\r\n,.;:")


def _strip_leading_name_phrase(value: str) -> str:
    value = _strip_wrapping_quotes_and_punctuation(value)
    value = re.sub(r"^(?:it'?s|it\s+is)\s+", "", value, flags=re.I).strip()
    if "," in value:
        value = value.split(",")[-1].strip()
    return _strip_wrapping_quotes_and_punctuation(value)


_TRAILING_FILLER = re.compile(
    r"\s+\b(?:i\s+(?:guess|think|believe|suppose|hope|reckon)"
    r"|i'm\s+(?:guessing|thinking|pretty\s+sure)"
    r"|maybe|probably|actually|right|though|ya|na|no|yes"
    r"|hai|hain|hoga|shayad)\b.*$",
    re.I,
)

_LEADING_FILLER = re.compile(
    r"^(?:i\s+(?:guess|think|believe|suppose)\s+"
    r"|(?:sorry|ok|okay|well|actually|so|um|hmm)\s*,?\s*)*",
    re.I,
)


def _clean_name(value: str) -> str | None:
    value = _strip_wrapping_quotes_and_punctuation(value)
    value = re.split(
        r"\b(?:dob|date of birth|aadhaar|aadhar|pincode|pin code|amount|pay|card|cvv|expires?)\b",
        value,
        maxsplit=1,
        flags=re.I,
    )[0].strip(" \t\r\n,.;:")
    # Strip trailing filler phrases like "i guess", "I think", "maybe"
    value = _TRAILING_FILLER.sub("", value).strip(" \t\r\n,.;:")
    return value or None


def _looks_like_plain_name(value: str) -> bool:
    if not value or any(ch.isdigit() for ch in value):
        return False
    blocked = ["dob", "aadhaar", "aadhar", "pincode", "card", "cvv", "amount", "pay", "account"]
    if any(word in value.lower() for word in blocked):
        return False
    return bool(re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)*", value.strip()))


def _looks_like_full_legal_name(value: str) -> bool:
    if not _looks_like_plain_name(value):
        return False
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", value)
    return len(tokens) >= 2


def extract_dob(text: str) -> str | None:
    patterns = [
        r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b",
        r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        parts = [int(part) for part in match.groups()]
        if len(str(match.group(1))) == 4:
            year, month, day = parts
        else:
            # Try DD-MM-YYYY first
            day, month, year = parts
            year = _normalize_two_digit_year(year)
            result = _format_date(year, month, day)
            if result:
                return result
            # Fall back to MM-DD-YYYY if DD-MM-YYYY was invalid
            month_alt, day_alt = parts[0], parts[1]
            return _format_date(year, month_alt, day_alt)
        return _format_date(year, month, day)

    month_day_year = re.search(
        r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:st|nd|rd|th)?[,]?\s+(\d{2,4})\b",
        text,
        re.I,
    )
    if month_day_year:
        month = MONTHS[month_day_year.group(1).lower()]
        day = int(month_day_year.group(2))
        year = _normalize_two_digit_year(int(month_day_year.group(3)))
        return _format_date(year, month, day)

    day_month_year = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\s+(\d{2,4})\b",
        text,
        re.I,
    )
    if day_month_year:
        day = int(day_month_year.group(1))
        month = MONTHS[day_month_year.group(2).lower()]
        year = _normalize_two_digit_year(int(day_month_year.group(3)))
        return _format_date(year, month, day)
    return None


def _normalize_two_digit_year(year: int) -> int:
    if year >= 100:
        return year
    return 1900 + year if year >= 30 else 2000 + year


def _format_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None


def detect_invalid_dob_attempt(text: str) -> bool:
    """Return True if text looks like a DOB attempt but the date is invalid."""
    if extract_dob(text) is not None:
        return False  # Valid DOB extracted
    # Check if user tried to provide a date (has date keywords + date-like patterns)
    has_dob_keyword = bool(re.search(r"\b(?:dob|date\s+of\s+birth|born|birthday)\b", text, re.I))
    has_date_pattern = bool(
        re.search(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:" + "|".join(MONTHS) + r")", text, re.I)
        or re.search(r"\b(?:" + "|".join(MONTHS) + r")\s+\d{1,2}", text, re.I)
        or re.search(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", text)
    )
    return has_dob_keyword or has_date_pattern


def extract_aadhaar_last4(text: str, stage: Stage | None = None) -> str | None:
    explicit_patterns = [
        r"\b(?:aadhaar|aadhar)\s+(?:last\s+(?:4|four)|ends?\s+with)[^\d]*(\d(?:[\s-]*\d){3})\b",
        r"\blast\s+(?:4|four)\s+of\s+(?:my\s+)?(?:aadhaar|aadhar)[^\d]*(\d(?:[\s-]*\d){3})\b",
        r"\b(?:aadhaar|aadhar)[^\d]*(\d(?:[\s-]*\d){3})\b",
    ]
    for pattern in explicit_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if len(digits) == 4:
                return digits
    # Word-form digits: "aadhaar last four digits are four three two one"
    if re.search(r"\b(?:aadhaar|aadhar)\b", text, re.I):
        # Strip everything up to and including the aadhaar context phrase
        after_prefix = re.sub(
            r".*\b(?:last\s+(?:4|four)\s*(?:digits?)?\s*(?:of\s+)?(?:my\s+)?(?:aadhaar|aadhar)\s*(?:is|are|:)?\s*"
            r"|(?:aadhaar|aadhar)\s+(?:last\s+(?:4|four)\s*(?:digits?)?\s*(?:is|are|:)?|ends?\s+with)\s*)",
            "",
            text,
            flags=re.I,
        )
        if not after_prefix.strip():
            after_prefix = re.sub(r".*\b(?:aadhaar|aadhar)\s*", "", text, flags=re.I)
        word_digits = _words_to_digits(after_prefix)
        if word_digits and len(word_digits) == 4:
            return word_digits
    # In AWAIT_SECONDARY_FACTOR, a 4-digit number (without other long digit sequences) is likely aadhaar last 4
    if stage == Stage.AWAIT_SECONDARY_FACTOR:
        # Don't match if there's a 6-digit sequence (that's a pincode)
        if not re.search(r"\b\d{5,}\b", re.sub(r"[\s-]", "", text)):
            bare = re.search(r"\b(\d(?:[\s-]*\d){3})\b", text)
            if bare:
                digits = re.sub(r"\D", "", bare.group(1))
                if len(digits) == 4:
                    return digits
        # Also handle word-form digits without aadhaar keyword
        # Strip "last four/4 (digits) (are/is)" prefix to avoid counting "four" twice
        stripped = re.sub(r"\b(?:my\s+)?last\s+(?:4|four)\s*(?:digits?)?\s*(?:is|are|:)?\s*", "", text, flags=re.I)
        word_digits = _words_to_digits(stripped)
        if word_digits and len(word_digits) == 4:
            if not re.search(r"\b(?:aadhaar|aadhar|pin\s*code|pincode|dob|date)\b", text, re.I):
                return word_digits
    return None


def extract_pincode(text: str, stage: Stage | None = None) -> str | None:
    match = re.search(r"\b(?:pin\s*code|pincode|pin)[^\d]*(\d(?:[\s-]*\d){5})\b", text, re.I)
    if not match:
        match = re.search(r"\b(\d(?:[\s-]*\d){5})[^\d]*(?:pin\s*code|pincode|pin)\b", text, re.I)
    if match:
        return re.sub(r"\D", "", match.group(1))
    # Word-form digits: "pincode is four zero zero zero zero one"
    if re.search(r"\b(?:pin\s*code|pincode|pin)\b", text, re.I):
        word_digits = _words_to_digits(text)
        if word_digits and len(word_digits) == 6:
            return word_digits
    # In AWAIT_SECONDARY_FACTOR, a 6-digit number is likely a pincode
    if stage == Stage.AWAIT_SECONDARY_FACTOR:
        bare = re.search(r"\b(\d(?:[\s-]*\d){5})\b", text)
        if bare:
            digits = re.sub(r"\D", "", bare.group(1))
            if len(digits) == 6:
                return digits
    return None


def extract_full_amount_requested(text: str) -> bool:
    return bool(
        re.search(
            r"\b(full|entire|complete)\s+(amount|balance|outstanding)\b"
            r"|\bclear\s+(the\s+full|it|everything|all)\b"
            r"|\b(?:poora|pura)\s+(?:amount|balance)\b"
            r"|\ball\s+of\s+it\b"
            r"|\b(?:pay|clear)\s+(?:it\s+)?all\b"
            r"|\beverything\b"
            r"|\bthe\s+whole\s+(?:amount|thing|balance)\b"
            r"|\bjust\s+clear\s+(?:the\s+)?(?:full\s+)?(?:amount|balance)\b"
            r"|\bsettle\s+(?:the\s+)?(?:full|entire|complete)?\s*(?:amount|balance|dues?|outstanding)?\b"
            r"|\bpay\s+(?:the\s+)?(?:full|total|complete)\b",
            text,
            re.I,
        )
    )


def extract_relative_amount_fraction(text: str, stage: Stage | None = None) -> Decimal | None:
    if stage != Stage.AWAIT_PAYMENT_AMOUNT:
        return None
    if re.search(r"\b(?:half|aadha)\b", text, re.I):
        return Decimal("0.5")
    if re.search(r"\bquarter\b", text, re.I):
        return Decimal("0.25")
    percent = re.search(r"\b(25|50)\s*%", text)
    if percent:
        return Decimal(percent.group(1)) / Decimal("100")
    return None


WORD_AMOUNTS = {
    "hundred": 100,
    "two hundred": 200,
    "three hundred": 300,
    "four hundred": 400,
    "five hundred": 500,
    "six hundred": 600,
    "seven hundred": 700,
    "eight hundred": 800,
    "nine hundred": 900,
    "thousand": 1000,
    "a thousand": 1000,
    "one thousand": 1000,
    "two thousand": 2000,
    "three thousand": 3000,
    "four thousand": 4000,
    "five thousand": 5000,
    "six thousand": 6000,
    "seven thousand": 7000,
    "eight thousand": 8000,
    "nine thousand": 9000,
    "ten thousand": 10000,
    "fifteen hundred": 1500,
    "twelve fifty": 1250,
    "twelve hundred": 1200,
}


def extract_amount(text: str, stage: Stage | None = None) -> Decimal | None:
    # Check word-form amounts (sorted longest-first to match "two thousand" before "thousand")
    for phrase in sorted(WORD_AMOUNTS, key=len, reverse=True):
        if re.search(r"\b" + phrase + r"(?:\s+rupees?)?\b", text, re.I):
            return Decimal(str(WORD_AMOUNTS[phrase]))
    amount_context = re.search(
        r"(?:pay|payment|amount|do|clear|rupees?|rs\.?|₹)[^\d-]*(-?\d[\d,]*(?:\.\d+)?)",
        text,
        re.I,
    )
    if amount_context:
        return _to_decimal(amount_context.group(1))
    standalone = re.search(r"(?<!ACC)\b-?\d[\d,]*(?:\.\d+)?\b", text, re.I)
    if standalone and re.search(r"\b(pay|payment|amount|rupees?|rs\.?|₹|for now)\b", text, re.I):
        return _to_decimal(standalone.group(0))

    if stage == Stage.AWAIT_PAYMENT_AMOUNT:
        # Accept a bare number as amount (e.g. "1700", "no, 1700", "maybe 500")
        # Capture leading minus sign so negative amounts reach validation
        bare_match = re.search(r"(-?\d[\d,]*(?:\.\d+)?)", text)
        if bare_match:
            return _to_decimal(bare_match.group(1))

    return None


def _to_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def extract_cardholder_name(text: str, stage: Stage | None = None) -> str | None:
    match = re.search(r"\bcardholder\s+(?:name\s+)?(?:is|:)?\s*([^,.;\n]+)", text, re.I)
    if match:
        return _clean_name(match.group(1))
    if stage == Stage.AWAIT_CARD_DETAILS:
        match = re.search(r"\b(?:name|naam)\s+(?:is|:)?\s*([^,.;\n]+?)(?:\s+hai)?$", text, re.I | re.MULTILINE)
        if match:
            return _clean_name(match.group(1))
        # Accept a bare full name when in AWAIT_CARD_DETAILS and input looks like
        # just a name (no digits, no card/cvv/expiry keywords)
        stripped = _strip_wrapping_quotes_and_punctuation(text)
        if (
            stripped
            and _looks_like_full_legal_name(stripped)
            and not re.search(r"\b(?:card|cvv|expir|account|acc|amount|pay|pin)\b", stripped, re.I)
        ):
            return stripped
    return None


def extract_card_number(text: str) -> str | None:
    match = re.search(r"\bcard(?:\s+number)?\D*((?:\d[\s-]*){16})\b", text, re.I)
    if not match:
        match = re.search(r"\b((?:\d[\s-]*){16})\b", text)
    if not match:
        return None
    return re.sub(r"\D", "", match.group(1))


def extract_cvv(text: str, stage: Stage | None = None) -> str | None:
    match = re.search(r"\bcvv\D*(\d{3,4})\b", text, re.I)
    if match:
        return match.group(1)

    word_match = re.search(
        r"\bcvv\D*((?:(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)\s*){3,4})\b",
        text,
        re.I,
    )
    if word_match:
        words = re.findall(r"zero|oh|one|two|three|four|five|six|seven|eight|nine", word_match.group(1), re.I)
        return "".join(DIGIT_WORDS[word.lower()] for word in words)

    if detect_bare_cvv(text, stage):
        return text.strip()

    return None


def detect_bare_cvv(text: str, stage: Stage | None = None) -> bool:
    return bool(stage == Stage.AWAIT_CARD_DETAILS and re.fullmatch(r"\s*\d{3,4}\s*", text))


def extract_expiry(text: str, stage: Stage | None = None) -> tuple[int | None, int | None]:
    if _has_date_like_month_phrase(text):
        return None, None

    has_expiry_keyword = bool(re.search(r"\bexpir(?:y|es|ation)?\b", text, re.I))
    in_card_stage = stage == Stage.AWAIT_CARD_DETAILS

    # With explicit "expiry"/"expires" keyword, extract freely
    if has_expiry_keyword:
        numeric = re.search(r"\bexpir(?:y|es|ation)?\D*(\d{1,2})\s*/\s*(\d{2,4})\b", text, re.I)
        if numeric:
            return int(numeric.group(1)), _normalize_expiry_year(int(numeric.group(2)))
        named = re.search(
            r"\bexpir(?:y|es|ation)?\D*(" + "|".join(MONTHS) + r")\s+(\d{2,4})\b",
            text,
            re.I,
        )
        if named:
            return MONTHS[named.group(1).lower()], _normalize_expiry_year(int(named.group(2)))

    # Without keyword, only extract in AWAIT_CARD_DETAILS stage
    if in_card_stage:
        numeric = re.search(r"\b(\d{1,2})\s*/\s*(\d{2,4})\b", text, re.I)
        if numeric:
            month = int(numeric.group(1))
            year = int(numeric.group(2))
            # Only treat as expiry if month is plausible (1-12)
            if 1 <= month <= 12:
                return month, _normalize_expiry_year(year)
        named = re.search(
            r"\b(" + "|".join(MONTHS) + r")\s+(\d{2,4})\b",
            text,
            re.I,
        )
        if named:
            return MONTHS[named.group(1).lower()], _normalize_expiry_year(int(named.group(2)))

    return None, None


def _normalize_expiry_year(year: int) -> int:
    return 2000 + year if year < 100 else year


<<<<<<< HEAD
def detect_invalid_fields(
    text: str,
    stage: Stage | None,
    *,
    full_name: str | None,
    dob: str | None,
    aadhaar_last4: str | None,
    pincode: str | None,
    cardholder_name: str | None,
    card_number: str | None,
    cvv: str | None,
    expiry_month: int | None,
    expiry_year: int | None,
) -> set[str]:
    invalid: set[str] = set()
    if stage == Stage.AWAIT_FULL_NAME and _looks_like_name_attempt(text) and full_name is None:
        invalid.add("full_name")
    if _looks_like_dob_attempt(text) and dob is None:
        invalid.add("dob")
    if _looks_like_aadhaar_attempt(text) and aadhaar_last4 is None:
        invalid.add("aadhaar_last4")
    if _looks_like_pincode_attempt(text) and pincode is None:
        invalid.add("pincode")
    if _looks_like_cardholder_attempt(text) and cardholder_name is None:
        invalid.add("cardholder_name")
    if _looks_like_card_number_attempt(text) and card_number is None:
        invalid.add("card_number")
    if _looks_like_cvv_attempt(text) and cvv is None:
        invalid.add("cvv")
    if _looks_like_expiry_attempt(text) and expiry_month is None and expiry_year is None:
        invalid.add("expiry")
    return invalid


def _looks_like_name_attempt(text: str) -> bool:
    if _has_alias_without_full_name(text):
        return True
    if re.search(r"\b(?:my\s+name\s+is|name\s+is|full\s+name\s+is|it'?s|it\s+is)\b", text, re.I):
        return True
    stripped = _strip_leading_name_phrase(text)
    return bool(stripped and re.fullmatch(r"[A-Za-z0-9 .'-]{1,80}", stripped))


def _looks_like_dob_attempt(text: str) -> bool:
    return bool(
        re.search(r"\b(?:dob|date of birth|born)\b", text, re.I)
        or re.search(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b", text)
    )


def _looks_like_aadhaar_attempt(text: str) -> bool:
    return bool(re.search(r"\b(?:aadhaar|aadhar)\b", text, re.I) and re.search(r"\d", text))


def _looks_like_pincode_attempt(text: str) -> bool:
    return bool(re.search(r"\b(?:pin\s*code|pincode|pin)\b", text, re.I) and re.search(r"\d", text))


def _looks_like_cardholder_attempt(text: str) -> bool:
    return bool(re.search(r"\bcardholder\s+name\b", text, re.I))


def _looks_like_card_number_attempt(text: str) -> bool:
    return bool(
        re.search(r"\bcard(?:\s+number)?\b", text, re.I)
        and re.search(r"(?:\d[\s-]*){1,19}", text)
    )


def _looks_like_cvv_attempt(text: str) -> bool:
    return bool(re.search(r"\bcvv\b", text, re.I))


def _looks_like_expiry_attempt(text: str) -> bool:
    return bool(re.search(r"\b(?:expir(?:y|es)?)\b", text, re.I))
=======
def detect_invalid_cvv_attempt(text: str, stage: Stage | None = None) -> bool:
    return bool(stage == Stage.AWAIT_CARD_DETAILS and re.search(r"\bcvv\b", text, re.I) and not extract_cvv(text))


def detect_invalid_expiry_attempt(text: str, stage: Stage | None = None) -> bool:
    if stage != Stage.AWAIT_CARD_DETAILS:
        return False
    if _has_date_like_month_phrase(text):
        return True
    if re.search(r"\bexpir(?:y|es)?\b", text, re.I) and extract_expiry(text, stage) == (None, None):
        return True
    return False


def _has_date_like_month_phrase(text: str) -> bool:
    return bool(
        re.search(
            r"\b\d{1,2}(?:st|nd|rd|th)?\s+(" + "|".join(MONTHS) + r")\s+\d{2,4}\b",
            text,
            re.I,
        )
    )
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
