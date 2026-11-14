
from datetime import timezone


REQUIRED_FIELDS = [
    "sport",
    "event",
    "start_time",
    "player",
    "market",
    "line",
    "operator",
    "ontario_authorized_checked",
    "ontario_available",
    "status",
    "over_american",
    "under_american",
    "observed_at",
    "source_url",
    "model_probability",
    "observations"
]


def parse_timestamp(value):
    from datetime import datetime

    timestamp = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if timestamp.tzinfo is None:
        raise ValueError("Timezone is required")

    return timestamp.astimezone(timezone.utc)


def validate_quote(
    quote,
    now,
    allowed_operators,
    max_age_minutes=15,
    min_observations=20
):
    errors = []

    for field in REQUIRED_FIELDS:
        if field not in quote:
            errors.append(f"Missing field: {field}")

    if errors:
        return errors

    if quote["operator"] not in allowed_operators:
        errors.append("Operator not in candidate list")

    if quote["ontario_authorized_checked"] is not True:
        errors.append("Ontario authorization not confirmed")

    if quote["ontario_available"] is not True:
        errors.append("Ontario market availability not confirmed")

    if quote["status"] != "open":
        errors.append("Market is not open")

    try:
        observed = parse_timestamp(quote["observed_at"])
        now_utc = now.astimezone(timezone.utc)

        age = (now_utc - observed).total_seconds() / 60

        if age < -2:
            errors.append("Quote timestamp is in the future")

        elif age > max_age_minutes:
            errors.append("Quote is stale")

    except Exception as error:
        errors.append(f"Invalid timestamp: {error}")

    try:
        if int(quote["observations"]) < min_observations:
            errors.append("Insufficient historical observations")
    except Exception:
        errors.append("Invalid observation count")

    try:
        probability = float(quote["model_probability"])

        if not 0 <= probability <= 1:
            errors.append("Invalid model probability")

    except Exception:
        errors.append("Model probability must be numeric")

    try:
        if float(quote["over_american"]) == 0:
            errors.append("Invalid over odds")

        if float(quote["under_american"]) == 0:
            errors.append("Invalid under odds")

    except Exception:
        errors.append("Both over and under odds are required")

    if not str(quote["source_url"]).startswith(
        ("https://", "http://")
    ):
        errors.append("A valid source URL is required")

    return errors
  
