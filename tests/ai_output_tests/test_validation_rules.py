"""AI output tests: the validator must reject invented numbers and advice, and accept honest answers."""
import pytest

from backend.services import validation

CTX = {
    "metrics": {"total_pnl_pct": 5.2, "holdings_count": 8, "total_value": 790900.0},
    "alert_count": 1,
}


def good(**overrides):
    answer = {
        "summary": "Your portfolio is worth Rs 790,900 with a gain of 5.2% across 8 holdings.",
        "key_drivers": ["One risk flag is listed for review."],
        "risk_note": "This is educational information only.",
    }
    answer.update(overrides)
    return answer


def test_honest_answer_passes():
    ok, issues = validation.validate(good(), CTX)
    assert ok, issues


def test_invented_number_is_rejected():
    ok, issues = validation.validate(good(summary="The portfolio gained 9.9% this year."), CTX)
    assert not ok
    assert any("9.9" in i for i in issues)


@pytest.mark.parametrize(
    "phrase",
    [
        "You should buy more shares.",
        "Sell now before it drops.",
        "This outcome is guaranteed.",
        "The price will rise soon.",
        "A sure-shot pick.",
    ],
)
def test_advice_and_prediction_language_is_rejected(phrase):
    ok, issues = validation.validate(good(risk_note=phrase), CTX)
    assert not ok
    assert any("advice" in i for i in issues)


def test_loss_written_in_words_matches_a_negative_number():
    ctx = {"metrics": {"total_pnl_pct": -5.2}}
    ok, issues = validation.validate(good(summary="The portfolio shows a loss of 5.2%."), ctx)
    assert ok, issues


def test_thousands_separators_are_understood():
    ctx = {"metrics": {"total_value": 1234567}}
    ok, issues = validation.validate(good(summary="The portfolio is worth Rs 1,234,567."), ctx)
    assert ok, issues


def test_rounded_numbers_are_rejected_by_design():
    # Known strictness: 88 is not accepted for 88.4. Safe, but it triggers the template fallback.
    ctx = {"sector_pct": {"IT": 88.4}}
    ok, _ = validation.validate(good(summary="About 88% sits in IT."), ctx)
    assert not ok


def test_missing_field_is_rejected():
    answer = good()
    del answer["risk_note"]
    ok, issues = validation.validate(answer, CTX)
    assert not ok
    assert "missing field: risk_note" in issues


def test_digits_inside_ticker_names_are_ignored():
    ctx = {"metrics": {"holdings_count": 3}}
    ok, issues = validation.validate(
        good(summary="SMALLCAP1 is a small holding in a portfolio of 3 stocks."), ctx
    )
    assert ok, issues