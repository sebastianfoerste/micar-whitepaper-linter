"""The hand-maintained proof contract must name the interfaces the package actually ships."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "micar-whitepaper-linter.proof.v1.json"


def _contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_names_every_console_script_and_the_action():
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    contract = _contract()
    assert contract["schema"] == "micar-whitepaper-linter.proof.v1"
    assert sorted(contract["interfaces"]) == sorted([*scripts, "action.yml"])
    assert (ROOT / "action.yml").is_file()


def test_contract_verification_points_at_real_checks():
    verification = _contract()["verification"]
    assert verification["command"] == "make check"
    assert re.search(r"^check:", (ROOT / "Makefile").read_text(encoding="utf-8"), re.M)
    assert verification["contractTest"] == f"tests/{Path(__file__).name}"


def test_contract_output_schema_exists_in_the_source():
    schema = _contract()["outputContract"]
    assert any(
        schema in path.read_text(encoding="utf-8") for path in (ROOT / "src" / "micar_linter").glob("*.py")
    )
