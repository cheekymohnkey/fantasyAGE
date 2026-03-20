import json
import sys
from pathlib import Path

try:
    import jsonschema
except Exception as e:
    print("Missing dependency: jsonschema. Please install it and re-run the test.")
    raise

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "work-process" / "schemas" / "command_event.schema.json"
FIXTURE_PATH = ROOT / "work-process" / "design" / "contract_fixtures" / "command_event_example.json"

def load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def main():
    schema = load(SCHEMA_PATH)
    fixture = load(FIXTURE_PATH)


    definitions = schema.get("definitions", {})

    cmd_schema_ref = {"$ref": "#/definitions/Command", "definitions": definitions}
    ev_schema_ref = {"$ref": "#/definitions/Event", "definitions": definitions}

    errors = []

    cmd = fixture.get("example_command")
    ev = fixture.get("example_event")

    if cmd is None:
        print("No example_command in fixture.")
        sys.exit(2)
    if ev is None:
        print("No example_event in fixture.")
        sys.exit(2)

    cmd_validator = jsonschema.Draft7Validator(cmd_schema_ref)
    ev_validator = jsonschema.Draft7Validator(ev_schema_ref)

    for error in cmd_validator.iter_errors(cmd):
        errors.append(("command", error))

    for error in ev_validator.iter_errors(ev):
        errors.append(("event", error))

    if not errors:
        print("Schema validation passed for example_command and example_event")
        sys.exit(0)

    print("Schema validation FAILED:\n")
    for kind, err in errors:
        print(f"[{kind}] {err.message}")
        print("  at:", " -> ".join(str(p) for p in err.absolute_path))
        print()

    sys.exit(1)

if __name__ == '__main__':
    main()
