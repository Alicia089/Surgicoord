"""
SurgiCoord Surgery Briefing Agent

Gives a surgeon the complete readiness picture for their case
before they walk into the OR.

Usage:
    python agent/case_agent.py --case CR-2026-0841
    python agent/case_agent.py --case CR-2026-0842
"""

import json
import argparse
from datetime import datetime, timezone

from agent.models import SurgeryBrief, DimensionStatus, ReadinessLevel
from agent.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from agent.prompts import SYSTEM_PROMPT


def _run_tool(tool_name: str, tool_input: dict) -> str:
    fn = TOOL_FUNCTIONS.get(tool_name)
    if not fn:
        return json.dumps({"error": f"Unknown tool: {tool_name}"})
    return json.dumps(fn(**tool_input), indent=2)


def _parse_brief(raw: str, case_id: str) -> SurgeryBrief:
    """Parse JSON output into a SurgeryBrief. Falls back gracefully."""
    try:
        text = raw.strip()
        if "```" in text:
            import re
            match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
            if match:
                text = match.group(1).strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        data = json.loads(text)
        return SurgeryBrief(**data)
    except Exception:
        return SurgeryBrief(
            case_id=case_id,
            patient_name="Unknown",
            procedure="Unknown",
            surgeon="Unknown",
            or_time="Unknown",
            or_room="Unknown",
            overall_status=ReadinessLevel.AT_RISK,
            vendor=DimensionStatus(status=ReadinessLevel.AT_RISK, summary="Could not parse output"),
            spd=DimensionStatus(status=ReadinessLevel.AT_RISK, summary="Could not parse output"),
            inventory=DimensionStatus(status=ReadinessLevel.AT_RISK, summary="Could not parse output"),
            preference_card=DimensionStatus(status=ReadinessLevel.AT_RISK, summary="Could not parse output"),
            patient_prep=DimensionStatus(status=ReadinessLevel.AT_RISK, summary="Could not parse output"),
            critical_actions=["Review raw output"],
            surgeon_notes=raw[:500],
            generated_at=datetime.now(timezone.utc).isoformat(),
        )


def brief_surgeon(case_id: str) -> SurgeryBrief:
    """
    Run the SurgiCoord agent for a given case ID.
    Returns a structured SurgeryBrief with full readiness status.

    To wire in your preferred model, replace this function body with:

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Generate a complete surgery brief for case {case_id}. "
                "Check all five readiness dimensions and return a structured JSON SurgeryBrief."},
        ]

        # Agentic loop — keep calling the model until it stops issuing tool calls
        while True:
            response = <your_client>.chat(model=<your_model>, messages=messages, tools=TOOL_DEFINITIONS)
            tool_calls = response.tool_calls  # adjust to your SDK's response shape

            if not tool_calls:
                return _parse_brief(response.text, case_id)

            messages.append({"role": "assistant", "tool_calls": tool_calls})
            for tc in tool_calls:
                result = _run_tool(tc.name, json.loads(tc.arguments))
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
    """
    raise NotImplementedError("Briefing backend not configured")


def print_brief(brief: SurgeryBrief) -> None:
    """Print a formatted surgery brief to the terminal."""
    STATUS_COLOR = {
        ReadinessLevel.READY: "\033[92m",
        ReadinessLevel.AT_RISK: "\033[93m",
        ReadinessLevel.BLOCKED: "\033[91m",
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def badge(level: ReadinessLevel) -> str:
        return f"{STATUS_COLOR[level]}{level.value}{RESET}"

    SEP = "=" * 64
    DIV = "-" * 64
    print(f"\n{SEP}")
    print(f"{BOLD}  SURGICOORD SURGERY BRIEF{RESET}")
    print(SEP)
    print(f"  Case:      {brief.case_id}")
    print(f"  Patient:   {brief.patient_name}")
    print(f"  Procedure: {brief.procedure}")
    print(f"  Surgeon:   {brief.surgeon}")
    print(f"  OR Time:   {brief.or_time}  |  Room: {brief.or_room}")
    print(f"  Status:    {badge(brief.overall_status)}")
    print(DIV)

    dimensions = [
        ("Vendor / Rep",        brief.vendor),
        ("SPD / Sterilization", brief.spd),
        ("Implant Inventory",   brief.inventory),
        ("Preference Card",     brief.preference_card),
        ("Patient Prep",        brief.patient_prep),
    ]

    for name, dim in dimensions:
        print(f"\n  {BOLD}{name}{RESET}  [{badge(dim.status)}]")
        print(f"    {dim.summary}")
        for flag in dim.flags:
            print(f"    {STATUS_COLOR[ReadinessLevel.BLOCKED]}⚠  {flag}{RESET}")
        if dim.action_required:
            print(f"    → {dim.action_required}")

    if brief.critical_actions:
        print(f"\n{DIV}")
        print(f"  {BOLD}CRITICAL ACTIONS{RESET}")
        for i, action in enumerate(brief.critical_actions, 1):
            print(f"  {i}. {action}")

    if brief.surgeon_notes:
        print(f"\n  {BOLD}SURGEON NOTES{RESET}")
        print(f"  {brief.surgeon_notes}")

    print(f"\n{DIV}")
    print(f"  Generated: {brief.generated_at}")
    print(f"{SEP}\n")


def main():
    parser = argparse.ArgumentParser(description="SurgiCoord Surgery Briefing Agent")
    parser.add_argument("--case", required=True, help="Case ID (e.g. CR-2026-0841)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted brief")
    args = parser.parse_args()

    print(f"Running SurgiCoord briefing for {args.case}...")
    brief = brief_surgeon(args.case)

    if args.json:
        print(brief.model_dump_json(indent=2))
    else:
        print_brief(brief)


if __name__ == "__main__":
    main()
