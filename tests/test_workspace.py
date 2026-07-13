from pathlib import Path

from micar_linter.workspace import build_whitepaper_workspace


def test_workspace_builds_local_batch_vault_with_source_hashes() -> None:
    workspace = build_whitepaper_workspace(
        [Path("examples/incomplete.json"), Path("examples/other-crypto-asset.json")]
    )
    vault = workspace["vault"]
    assert vault["document_count"] == 2
    assert all(document["source_sha256"] for document in vault["documents"])
    assert vault["external_action_allowed"] is False


def test_workspace_builds_interactive_conditional_review_table() -> None:
    workspace = build_whitepaper_workspace([Path("examples/incomplete.json")])
    table = workspace["review_table"]
    assert table["rows"]
    assert all(row["condition"]["result"] == "applied" for row in table["rows"])
    assert all(row["manual_input"]["decision"] == "pending" for row in table["rows"])
    assert table["summary"]["pending_manual_decisions"] == table["summary"]["rows"]
    assert table["external_action_allowed"] is False


def test_workspace_builds_reusable_review_playbook() -> None:
    workspace = build_whitepaper_workspace(
        [Path("examples/incomplete.json"), Path("examples/art-stablecoin.json")]
    )
    playbook = workspace["playbook"]
    assert playbook["rule_count"] > 0
    assert all(rule["citation"] for rule in playbook["rules"])
    assert all(rule["review_gate"] for rule in playbook["rules"])
    assert playbook["external_action_allowed"] is False
