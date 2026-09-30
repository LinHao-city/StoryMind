from lib.film_retry import next_take_action


def test_policy_never_auto_retries():
    assert next_take_action("policy", attempts=1, estimated_next_usd=1, remaining_usd=10) == "human_review"
    assert next_take_action("privacy", attempts=1) == "human_review"


def test_quality_and_technical_retries_are_bounded_by_attempts_and_budget():
    assert next_take_action("quality", attempts=1, estimated_next_usd=1, remaining_usd=2) == "retry"
    assert next_take_action("technical", attempts=3, estimated_next_usd=1, remaining_usd=2) == "human_review"
    assert next_take_action("quality", attempts=1, estimated_next_usd=3, remaining_usd=2) == "block"
