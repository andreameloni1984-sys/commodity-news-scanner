def position_monitor_loop() -> None:
    """Periodic forecast and position monitor; Telegram is transition-only."""
    from engine.position_monitor import evaluate_positions, list_positions
    from telegram.commodity_direction_alert import run_directional_commodity_alert
    from telegram.aggressive_alert import run_aggressive_alert
    from engine.energy_confluence import stamp_energy, format_energy_alert

    interval = 15 * 60
    print("Gagarin market monitor | interval=15min | deduplicated forecast + position alerts", flush=True)
    last_energy_alert = None
    while True:
        try:
            states = _run_analysis(on_demand=False)
            if states:
                # Energy complex shock alert (once per unique event)
                try:
                    energy = stamp_energy(states)
                    alert_text = format_energy_alert(energy)
                    if alert_text and alert_text != last_energy_alert:
                        if send_telegram(alert_text):
                            last_energy_alert = alert_text
                            print("ENERGY SHOCK alert delivered", flush=True)
                        else:
                            print("ENERGY SHOCK alert delivery failed", flush=True)
                except Exception as energy_exc:
                    print(f"ENERGY ALERT ERROR | {type(energy_exc).__name__}: {energy_exc}", flush=True)

                # Score old paper forecasts first, then register newly approved
                # forecasts from this exact market snapshot. The tracker never
                # changes the governor decision or sends routine Telegram alerts.
                try:
                    from engine.feedback import record_forecasts, summarize, update_open_outcomes, format_summary, storage_backend
                    decisions = evaluate_states(states)
                    by_symbol = {decision.symbol: decision for decision in decisions}
                    for state in states:
                        decision = by_symbol.get(str(getattr(state, "symbol", "")).upper())
                        metadata = getattr(state, "metadata", None)
                        if not isinstance(metadata, dict):
                            metadata = {}
                            state.metadata = metadata
                        metadata["gagarin_action"] = decision.action if decision else "WAIT"
                        metadata["gagarin_reason"] = decision.reason if decision else "NO_DECISION"
                    updated = update_open_outcomes(states)
                    recorded = record_forecasts(states)
                    summary = summarize()
                    print(
                        f"GAGARIN FEEDBACK STORAGE | backend={storage_backend()}",
                        flush=True,
                    )
                    print(
                        "GAGARIN FEEDBACK | " + format_summary(summary) +
                        f" | updated={updated} new_forecasts={recorded}",
                        flush=True,
                    )
                except Exception as feedback_exc:
                    print(
                        f"GAGARIN FEEDBACK ERROR | {type(feedback_exc).__name__}: {feedback_exc}",
                        flush=True,
                    )
                # New/meaningfully changed directional forecasts only; no no-signal heartbeat.
                run_directional_commodity_alert(states)
                # Pattern/exit alerts run in the actual Render service, not only in GitHub Actions.
                run_aggressive_alert(states)
                if list_positions():
                    for alert in evaluate_positions(states):
                        if send_telegram(alert):
                            print("Gagarin position monitor | transition alert delivered", flush=True)
                        else:
                            print("Gagarin position monitor | transition alert delivery failed", flush=True)
        except Exception as exc:
            # Diagnostics only: never send routine error/status spam to Telegram.
            print(f"Gagarin market monitor error | {type(exc).__name__}: {exc}", flush=True)
        time.sleep(interval)
