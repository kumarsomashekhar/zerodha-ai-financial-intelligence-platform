# Validation and policy controls

What is checked, where, and what is not. The limits are listed on purpose: a safeguard that is described honestly is easier to trust than one that is oversold.

## Where the checks happen

| Check | Applies to | What it does | If it fails |
|---|---|---|---|
| Prompt rules | Every AI call | The system prompt forbids advice, predictions and new numbers, and tells the model to treat headlines as untrusted text | Preventive only. Nothing is enforced at this point |
| Structure check | Portfolio analysis | The answer must contain `summary`, `key_drivers` and `risk_note` | Template used |
| Number check | Portfolio analysis | Every number in the answer must match a number in the analytics data, within 0.05. Minus signs are ignored, so "a loss of 5.2%" matches -5.2. Thousands separators are understood. Digits inside names such as `SMALLCAP1` are ignored | Template used, recorded as `fallback_used` with the offending number |
| Wording check | Portfolio analysis and benchmark explanation | Rejects advice and prediction wording: buy, sell, guarantee or guaranteed, "will rise", "will fall", "will double", sure-shot | Template used |
| Number check | Benchmark explanation | Every number must appear in the benchmark figures it was given, compared to one decimal place | Template used |
| Card policy check | Every insight card | The same wording check on each card's title, rationale and details | The text is replaced by a fixed safe sentence and the card is marked `policy_check: replaced` |
| Error handling | All AI calls | Network errors, bad keys, unknown models and unreadable answers are caught | Template used |

A template is plain text built in code from the same figures, so it can never contain an invented number.

## Policy controls

| Control | How it works |
|---|---|
| Disclaimers | Every card carries a disclaimer. The compliance panel shows the full disclosures. Every explanation says it is educational |
| Human review | The compliance panel lists failed jobs and rejected AI answers. A reviewer approves each one or marks it for follow-up. Every review is kept |
| Reviewer key | Recording a review needs a key. On a public server with no key configured, reviews are refused |
| Demo mode | On a public server the real Zerodha portfolio is hidden and every Zerodha route is refused |
| Secrets | Keys live only in `backend/.env` or the host's settings, never in Git. `scripts/check_secrets.py` and `scripts/check_history_secrets.py` search the files and the history for them |
| Cost and abuse | A per-visitor limit on analysis and AI requests, and a cache for explanations |
| Audit trail | Each analysis stores its AI provider, prompt version, validation result and issues, the data the AI was given, and a snapshot of the holdings |

## What data the AI provider receives

- **Portfolio analysis:** holding symbols and sectors, weights, profit or loss percentages, totals (including total value and amount invested), the alerts, and data age. No names, account numbers or contact details. For the `LIVE` portfolio, which runs only on a person's own computer, the totals are that person's real amounts.
- **Benchmark explanation:** return, volatility and drawdown figures, sector weights, each stock's weight and return, and up to two recent public headlines per stock.
- The data goes to the provider chosen in the settings (Google Gemini or Anthropic) over their API. The portfolio-analysis context is also stored in the audit trail, in the app's own database.

## Limits

- The checks look at **numbers and a short list of words**. They cannot judge whether a sentence is fair or true. During development the AI called small holdings "heavy". Instructions in the prompt reduced this, but code does not catch it.
- The number check is strict. It rejects sensible rounding (88 for 88.4), which is safe but sends the user to the template more often than needed.
- The wording list is short. It does not catch every way of phrasing advice.
- Headlines are untrusted text. The prompt tells the model to ignore instructions in them and not to copy their numbers, and the number check rejects any number the model copies. This lowers the risk but is not a guarantee.
- "Confidence" is a rule-based level and score (data age and number of holdings). It is not statistically calibrated.
- Benchmark explanations are cached for six hours and are not saved in the audit trail, so they have no prompt version recorded.
- The reviewer key is a single shared key, not a login system. Anyone who holds it can approve flags.

## Not implemented

- Retention rules (jobs, snapshots and logs are kept until the database is reset)
- Encryption of stored data
- Role-based access control beyond the reviewer key
- Monitoring of AI answers over time beyond the counts on the operations dashboard
- Per-tool permissions on the MCP server