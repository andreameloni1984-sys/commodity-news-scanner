SOYUZ GAGARIN — DATA ENGINE v4.1 PATCH

1) In engine/data.py change:
EFFECTIVE_LIVE_MAX_AGE_SECONDS = max(
    float(LIVE_MAX_AGE_SECONDS),
    360.0,
)

to:

EFFECTIVE_LIVE_MAX_AGE_SECONDS = max(
    float(LIVE_MAX_AGE_SECONDS),
    420.0,
)

BAR_INTERVAL_SECONDS = 5 * 60

2) In _freshness(), replace the current age check with:

live_limit = max(
    EFFECTIVE_LIVE_MAX_AGE_SECONDS,
    BAR_INTERVAL_SECONDS + 60.0,
)

if age <= live_limit:
    return (
        True,
        age,
        "LIVE",
    )

3) In _finalize(), replace the metadata assignment with:

state.metadata[
    "effective_live_max_age_seconds"
] = max(
    EFFECTIVE_LIVE_MAX_AGE_SECONDS,
    BAR_INTERVAL_SECONDS + 60.0,
)

state.metadata[
    "bar_interval_seconds"
] = BAR_INTERVAL_SECONDS
