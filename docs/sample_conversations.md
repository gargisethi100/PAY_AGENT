# Sample Conversations

All transcripts below are actual agent output from automated test runs using the `Agent.next()` interface with a mock API client.

---

## Scenario 1: Successful Payment (Messy Natural Language)

Demonstrates handling of conversational, imperfect inputs throughout the flow.

```
User: hey there
Agent: Hello! Please share your account ID to get started.

User: yeah my account number is ACC1001 I think
Agent: Got it. Could you please confirm your full name?

User: i am nithin, Nithin Jain
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: I was born on 14th May 1990
Agent: Identity verified. Your outstanding balance is Rs. 1,250.75. How much would you like to pay today?

User: I want to pay a thousand rupees
Agent: Please provide the cardholder name, card number, expiry, and CVV to process the payment.

User: cardholder name Nithin Jain, card 4532 0151 1283 0366, expires December 2027, CVV one two three
Agent: Payment of Rs. 1,000.00 was successful. Card used: ****0366. Transaction ID: txn_test_success. Thank you.
```

**What this shows:**
- "ACC1001 I think" -- extracts account ID from conversational filler
- "i am nithin, Nithin Jain" -- handles the "it's X, X Y" repeat pattern, extracts full legal name
- "14th May 1990" -- parses non-standard date format with ordinal suffix
- "a thousand rupees" -- word-form amount recognition
- "CVV one two three" -- word-form digit conversion for CVV

---

## Scenario 2: Verification Failure (Retries Exhausted)

Demonstrates the verification retry limit and clean failure handling.

```
User: Hi
Agent: Hello! Please share your account ID to get started.

User: ACC1001
Agent: Got it. Could you please confirm your full name?

User: Nithin Jain
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: DOB is 1990-01-01
Agent: I could not verify those details. Please try again with your full name and one verification detail.

User: Nithin Jain
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: DOB is 1985-03-15
Agent: I could not verify those details. Please try again with your full name and one verification detail.

User: Nithin Jain
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: pincode 999999
Agent: I could not verify your identity after multiple attempts. Please contact support for help.
```

**What this shows:**
- Name match succeeds but secondary factor (DOB, pincode) is wrong
- After 3 complete failed attempts, the agent closes permanently
- Balance is never disclosed -- the user never learns the outstanding amount

---

## Scenario 3: Payment Failure with Recovery

Demonstrates graceful handling of API payment errors with field-specific recovery.

```
User: Hi
Agent: Hello! Please share your account ID to get started.

User: ACC1001
Agent: Got it. Could you please confirm your full name?

User: Nithin Jain
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: pincode 400001
Agent: Identity verified. Your outstanding balance is Rs. 1,250.75. How much would you like to pay today?

User: 500
Agent: Please provide the cardholder name, card number, expiry, and CVV to process the payment.

User: cardholder name Nithin Jain, card 4532 0151 1283 0366, expiry 12/27, CVV 999
Agent: The CVV was declined by the payment processor. Please check the CVV and try again.

User: CVV 123
Agent: Payment of Rs. 500.00 was successful. Card used: ****0366. Transaction ID: txn_test_success. Thank you.
```

**What this shows:**
- API returns `invalid_cvv` error -- only CVV is cleared, card number and expiry are retained
- User only needs to re-provide the CVV, not all card details
- Successful retry with corrected CVV

---

## Scenario 4: Zero Balance Account

Demonstrates clean handling when no payment is needed.

```
User: Hello
Agent: Hello! Please share your account ID to get started.

User: ACC1003
Agent: Got it. Could you please confirm your full name?

User: Priya Agarwal
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: my dob is 10th August 1992
Agent: Identity verified. There is no outstanding balance on this account, so no payment is needed.
```

**What this shows:**
- Verification still required even for zero-balance accounts
- No payment collection attempted -- flow closes cleanly

---

## Scenario 5: Leap Year DOB + Invalid Date Feedback

Demonstrates edge case handling for ACC1004 (DOB: 1988-02-29, a leap year date).

```
User: Hi
Agent: Hello! Please share your account ID to get started.

User: ACC1004
Agent: Got it. Could you please confirm your full name?

User: Rahul Mehta
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: my dob is 30th february 1988
Agent: That date does not appear to be valid. Please provide your date of birth in a format like DD-MM-YYYY, YYYY-MM-DD, or 14th May 1990.

User: my dob is 29th february 1988
Agent: Identity verified. Your outstanding balance is Rs. 3,200.50. How much would you like to pay today?

User: half of it
Agent: That comes to Rs. 1,600.25. Please confirm if you want to pay this amount, or enter a different amount.

User: yes
Agent: Please provide the cardholder name, card number, expiry, and CVV to process the payment.

User: name is Rahul Mehta
User: card 4532 0151 1283 0366
User: CVV 123
User: expiry 12/27
Agent: Payment of Rs. 1,600.25 was successful. Card used: ****0366. Transaction ID: txn_test_success. Thank you.
```

**What this shows:**
- Feb 30 is correctly identified as invalid with clear feedback (not silent failure)
- Feb 29, 1988 is a valid leap year date -- verification succeeds
- "half of it" calculates 50% of balance with confirmation
- Multi-line card input: all fields extracted from a single multi-line message

---

## Scenario 6: Account Change Mid-Flow

Demonstrates switching accounts during the verification stage.

```
User: Hi
Agent: Hello! Please share your account ID to get started.

User: ACC1001
Agent: Got it. Could you please confirm your full name?

User: would like to change my acc id
Agent: I have started a fresh account flow. Please share the new account ID.

User: ACC1004
Agent: Got it. Could you please confirm your full name?

User: Rahul Mehta
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: aadhar last four digits are one three five seven
Agent: Identity verified. Your outstanding balance is Rs. 3,200.50. How much would you like to pay today?

User: all of it
Agent: Please provide the cardholder name, card number, expiry, and CVV to process the payment.

User: cardholder name Rahul Mehta, card 4532 0151 1283 0366, expires 12/27, CVV 123
Agent: Payment of Rs. 3,200.50 was successful. Card used: ****0366. Transaction ID: txn_test_success. Thank you.
```

**What this shows:**
- "change my acc id" detected as account change intent (not treated as a name)
- All prior state is cleared for the fresh flow
- "aadhar last four digits are one three five seven" -- word-form digit extraction
- "all of it" -- colloquial full-amount recognition

---

## Scenario 7: Incremental Card Details

Demonstrates providing card fields one at a time with progressive confirmation.

```
User: Hi
Agent: Hello! Please share your account ID to get started.

User: ACC1001
Agent: Got it. Could you please confirm your full name?

User: Nithin Jain
Agent: Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode.

User: 4321
Agent: Identity verified. Your outstanding balance is Rs. 1,250.75. How much would you like to pay today?

User: five hundred
Agent: Please provide the cardholder name, card number, expiry, and CVV to process the payment.

User: name is Nithin Jain
Agent: Please provide the missing card detail(s): card number, CVV, expiry. Collected so far: Name: Nithin Jain.

User: card number is 4532 0151 1283 0366
Agent: Please provide the missing card detail(s): CVV, expiry. Collected so far: Name: Nithin Jain, Card: ****0366.

User: 123
Agent: Please provide the missing card detail(s): expiry. Collected so far: Name: Nithin Jain, Card: ****0366, CVV: ***.

User: 12/27
Agent: Payment of Rs. 1,000.00 was successful. Card used: ****0366. Transaction ID: txn_test_success. Thank you.
```

**What this shows:**
- Bare "4321" during verification stage -- inferred as Aadhaar last 4 by digit count
- "five hundred" -- word-form amount
- Each card field provided separately, with masked summary showing progress
- Bare "123" recognized as CVV (3 digits in card collection stage)
- Bare "12/27" recognized as expiry
- Card number only validated (Luhn check) after all fields are present -- no premature rejection
