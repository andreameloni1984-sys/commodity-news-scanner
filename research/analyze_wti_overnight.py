"""Run a PAPER-ONLY WTI overnight evaluation from a saved collector archive.

Examples:
  python -m research.analyze_wti_overnight
  python -m research.analyze_wti_overnight --input data/wti_overnight_sessions.json --cost-bps 8
  python -m research.analyze_wti_overnight --fetch

Network collection is opt-in via --fetch. This tool does not emit trading signals.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from research.wti_overnight_evaluation import build_wti_research_report
from research.wti_overnight_validation import chronological_validation_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/wti_overnight_sessions.json")
    parser.add_argument("--output", default="data/wti_overnight_evaluation.json")
    parser.add_argument("--cost-bps", type=float, default=5.0,
                        help="Hypothetical round-trip cost scenario in basis points.")
    parser.add_argument("--minimum-samples", type=int, default=30)
    parser.add_argument("--fetch", action="store_true",
                        help="Explicitly fetch public Yahoo CL=F data before evaluation.")
    args = parser.parse_args()

    if args.minimum_samples < 1:
        parser.error("--minimum-samples must be >= 1")
    if args.cost_bps < 0:
        parser.error("--cost-bps must be >= 0")

    if args.fetch:
        from engine.overnight_wti import collect_wti_overnight_sessions, write_wti_overnight_archive
        collected = collect_wti_overnight_sessions()
        if collected.get("status") != "OK":
            print(json.dumps({"paper_only": True, "status": "FETCH_FAILED",
                              "detail": collected.get("error", collected.get("status"))}, indent=2))
            raise SystemExit(2)
        saved = write_wti_overnight_archive(collected, args.input)
        if saved.get("status") != "SAVED":
            print(json.dumps(saved, indent=2))
            raise SystemExit(2)

    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"Input archive not found: {input_path}. Supply --input or explicitly use --fetch.")
    try:
        source = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot read input archive: {exc}")
    observations = source.get("sessions") if isinstance(source, dict) else None
    if not isinstance(observations, list):
        parser.error("Input must be a collector report JSON containing a 'sessions' list.")

    report = build_wti_research_report(
        observations, round_trip_cost_bps=args.cost_bps,
        minimum_samples=args.minimum_samples,
    )
    report["input_file"] = str(input_path)
    report["source_provider"] = source.get("source") if isinstance(source, dict) else None
    report["cost_assumption_note"] = "Hypothetical scenario only; replace with realistic measured spread/fees/slippage."
    report["chronological_validation"] = chronological_validation_report(
        observations, round_trip_cost_bps=args.cost_bps
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "paper_only": True, "status": report["status"],
        "input_file": str(input_path), "output_file": str(output_path),
        "complete_paired_sessions": report["complete_paired_sessions"],
        "volatility_samples": report["volatility_relationship"]["samples"],
        "direction_samples": report["direction_by_regime"]["overall"]["samples"],
    }, indent=2))


if __name__ == "__main__":
    main()
