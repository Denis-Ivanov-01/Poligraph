import argparse
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID


def _json_default(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))


def parse_uuid(value: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid UUID: {value}") from exc


def read_json_input(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")


def add_target_arguments(parser: argparse.ArgumentParser) -> None:
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--program-id", type=parse_uuid, help="Use the whole program structure workflow.")
    target.add_argument("--section-id", type=parse_uuid, help="Use the selected section/subsection refinement workflow.")


def add_invocation_telemetry_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model-name", help="Model name supplied by the invocation adapter, not by model output.")
    parser.add_argument("--input-tokens", type=int)
    parser.add_argument("--output-tokens", type=int)
    parser.add_argument("--tool-calls", type=int)


def with_db_session(callback):
    from app.database import SessionLocal
    from app.services.program_workflow_actions import ProgramWorkflowError

    db = SessionLocal()
    try:
        return callback(db)
    except ProgramWorkflowError as exc:
        print_json({"ok": False, "status_code": exc.status_code, "error": exc.message})
        return 1
    finally:
        db.close()


def command_prompt(args: argparse.Namespace) -> int:
    def run(db):
        from app.services.program_workflow_actions import generate_program_structure_prompt, generate_section_refinement_prompt

        result = (
            generate_program_structure_prompt(db, args.program_id, None)
            if args.program_id
            else generate_section_refinement_prompt(db, args.section_id, None)
        )
        if args.raw:
            print(result.prompt)
        else:
            print_json(result.to_dict(include_prompt=True))
        return 0

    return with_db_session(run)


def command_import_json(args: argparse.Namespace) -> int:
    raw_json = read_json_input(args.json_file)

    def run(db):
        from app.services.program_workflow_actions import import_program_structure_json, import_section_refinement_json

        result = (
            import_program_structure_json(db, args.program_id, raw_json, args.ai_run_id, None)
            if args.program_id
            else import_section_refinement_json(db, args.section_id, raw_json, args.ai_run_id, None)
        )
        print_json(result.to_dict(include_response=args.echo_response))
        return 0 if result.ok else 1

    return with_db_session(run)


def command_approve_structure(args: argparse.Namespace) -> int:
    def run(db):
        from app.services.program_workflow_actions import approve_program_structure

        result = approve_program_structure(db, args.program_id, args.status, args.note, None)
        print_json(result.to_dict())
        return 0

    return with_db_session(run)


def command_publish(args: argparse.Namespace) -> int:
    def run(db):
        from app.services.program_workflow_actions import publish_program

        result = publish_program(db, args.program_id, None)
        print_json(result.to_dict())
        return 0

    return with_db_session(run)


def command_sections(args: argparse.Namespace) -> int:
    def run(db):
        from app.services.program_workflow_actions import list_program_sections

        sections = list_program_sections(db, args.program_id)
        print_json(
            {
                "ok": True,
                "program_id": str(args.program_id),
                "sections": [
                    {
                        "id": str(section.id),
                        "parent_section_id": str(section.parent_section_id) if section.parent_section_id else None,
                        "title": section.title,
                        "section_code": section.section_code,
                        "display_order": section.display_order,
                        "structural_status": section.structural_status,
                    }
                    for section in sections
                ],
            }
        )
        return 0

    return with_db_session(run)


def command_status_prompt(args: argparse.Namespace) -> int:
    def run(db):
        from app.services.program_workflow_actions import generate_commitment_status_prompt

        result = generate_commitment_status_prompt(db, args.commitment_id, None)
        if args.raw:
            print(result.prompt)
        else:
            print_json(result.to_dict(include_prompt=True))
        return 0

    return with_db_session(run)


def command_status_import(args: argparse.Namespace) -> int:
    raw_json = read_json_input(args.json_file)

    def run(db):
        from app.services.program_workflow_actions import import_commitment_status_json

        result = import_commitment_status_json(
            db,
            args.commitment_id,
            raw_json,
            args.ai_run_id,
            None,
            model_name=args.model_name,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            tool_call_count=args.tool_calls,
        )
        print_json(result.to_dict(include_response=args.echo_response))
        return 0 if result.ok else 1

    return with_db_session(run)


def command_batch_start(args: argparse.Namespace) -> int:
    def run(db):
        from app.services.program_workflow_actions import start_section_status_batch

        result = start_section_status_batch(
            db,
            args.section_id,
            None,
            recursive=args.scope == "recursive",
            tranche_size=args.tranche_size,
        )
        print_json(result.to_dict(include_prompts=args.include_prompts))
        return 0

    return with_db_session(run)


def command_batch_show(args: argparse.Namespace) -> int:
    def run(db):
        from app.services.program_workflow_actions import load_section_status_batch

        result = load_section_status_batch(db, args.section_id, args.batch_id)
        print_json(result.to_dict(include_prompts=args.include_prompts))
        return 0

    return with_db_session(run)


def command_batch_import_item(args: argparse.Namespace) -> int:
    raw_json = read_json_input(args.json_file)

    def run(db):
        from app.services.program_workflow_actions import import_section_status_batch_item_json

        result = import_section_status_batch_item_json(
            db,
            args.section_id,
            args.batch_id,
            raw_json,
            item_id=args.item_id,
            item_ref=args.item_ref,
            user=None,
            model_name=args.model_name,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            tool_call_count=args.tool_calls,
        )
        print_json(result.to_dict(include_response=args.echo_response))
        return 0 if result.ok else 1

    return with_db_session(run)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="Internal operational CLI for PoliticalAiFilter.")
    subparsers = parser.add_subparsers(dest="resource", required=True)

    programs = subparsers.add_parser("programs", help="Program AI workflow actions.")
    program_commands = programs.add_subparsers(dest="command", required=True)

    prompt = program_commands.add_parser("prompt", help="Generate a prompt for a program or section target.")
    add_target_arguments(prompt)
    prompt.add_argument("--raw", action="store_true", help="Print only the prompt text.")
    prompt.set_defaults(func=command_prompt)

    import_json = program_commands.add_parser("import-json", help="Import an AI JSON response for a program or section target.")
    add_target_arguments(import_json)
    import_json.add_argument("--json-file", required=True, help="Path to the AI JSON response, or '-' for stdin.")
    import_json.add_argument("--ai-run-id", type=parse_uuid, help="Existing AI run id. Defaults to the latest matching run.")
    import_json.add_argument("--echo-response", action="store_true", help="Include raw and parsed AI response JSON in command output.")
    import_json.set_defaults(func=command_import_json)

    approve = program_commands.add_parser("approve-structure", help="Approve or reject a program structural review.")
    approve.add_argument("--program-id", required=True, type=parse_uuid)
    approve.add_argument("--status", choices=["passed", "failed", "needs_fix"], default="passed")
    approve.add_argument("--note", default="")
    approve.set_defaults(func=command_approve_structure)

    publish = program_commands.add_parser("publish", help="Publish a structurally approved program.")
    publish.add_argument("--program-id", required=True, type=parse_uuid)
    publish.set_defaults(func=command_publish)

    sections = program_commands.add_parser("sections", help="List section/subsection targets for a program.")
    sections.add_argument("--program-id", required=True, type=parse_uuid)
    sections.set_defaults(func=command_sections)

    status_prompt = program_commands.add_parser("status-prompt", help="Generate the canonical prompt for one commitment.")
    status_prompt.add_argument("--commitment-id", required=True, type=parse_uuid)
    status_prompt.add_argument("--raw", action="store_true", help="Print only the prompt text.")
    status_prompt.set_defaults(func=command_status_prompt)

    status_import = program_commands.add_parser("status-import", help="Validate and import one commitment analysis response.")
    status_import.add_argument("--commitment-id", required=True, type=parse_uuid)
    status_import.add_argument("--json-file", required=True, help="Path to the response, or '-' for stdin.")
    status_import.add_argument("--ai-run-id", type=parse_uuid)
    status_import.add_argument("--echo-response", action="store_true")
    add_invocation_telemetry_arguments(status_import)
    status_import.set_defaults(func=command_status_import)

    batch_start = program_commands.add_parser("batch-start", help="Create an item-level analysis batch; web import processes it in tranches.")
    batch_start.add_argument("--section-id", required=True, type=parse_uuid)
    batch_start.add_argument("--scope", choices=["direct", "recursive"], default="recursive")
    batch_start.add_argument("--tranche-size", type=int, default=50)
    batch_start.add_argument("--include-prompts", action="store_true")
    batch_start.set_defaults(func=command_batch_start)

    batch_show = program_commands.add_parser("batch-show", help="Show persisted batch progress and item runs.")
    batch_show.add_argument("--section-id", required=True, type=parse_uuid)
    batch_show.add_argument("--batch-id", required=True, type=parse_uuid)
    batch_show.add_argument("--include-prompts", action="store_true")
    batch_show.set_defaults(func=command_batch_show)

    batch_import = program_commands.add_parser("batch-import-item", help="Import one independently generated batch-item response.")
    batch_import.add_argument("--section-id", required=True, type=parse_uuid)
    batch_import.add_argument("--batch-id", required=True, type=parse_uuid)
    item_target = batch_import.add_mutually_exclusive_group(required=True)
    item_target.add_argument("--item-id", type=parse_uuid)
    item_target.add_argument("--item-ref")
    batch_import.add_argument("--json-file", required=True, help="Path to the response, or '-' for stdin.")
    batch_import.add_argument("--echo-response", action="store_true")
    add_invocation_telemetry_arguments(batch_import)
    batch_import.set_defaults(func=command_batch_import_item)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
