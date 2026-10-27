"""Saved iXBRL viewer pages pack the white paper into a script; the XHTML loader unpacks it."""

import base64
import gzip
import hashlib
import json
import re
import zlib
from pathlib import Path

import pytest

from micar_linter.cli import main
from micar_linter.linter import lint_whitepaper
from micar_linter.numbered_fields import MERGED_LABELS_NOTE
from micar_linter.whitepaper import VIEWER_EMPTY_NOTE, VIEWER_PAGE_NOTE, WhitepaperType, load_whitepaper
from micar_linter.xhtml_parser import (
    MAX_UNPACKED_BYTES,
    PackedPageTooLarge,
    is_script_packed,
    unpack_script_payload,
)

ROOT = Path(__file__).resolve().parents[1]


def _clauses(count: int) -> str:
    # Varied fictional text, so a compressed payload keeps the length of a real white paper's.
    return " ".join(
        f"Clause {i} sets out fictional term {hashlib.sha256(str(i).encode()).hexdigest()[:12]}."
        for i in range(count)
    )


# A fictional heading-based white paper.
SYNTHETIC_PAPER = (
    "<!DOCTYPE html><html><head><title>Synthetic white paper</title></head><body>"
    "<h1>Summary</h1>"
    "<p>This plain-language summary describes the fictional Example Token and its main risks. "
    f"{_clauses(150)}</p>"
    "<h2>Information about the Issuer</h2>"
    "<p>The issuer is Example Issuer AG, a fictional company registered in Frankfurt.</p>"
    "</body></html>"
).encode()


def _packed_page(literal: str, body: str = '<div id="loader">Loading document...</div>', runtime: int = 12_000) -> str:
    # The viewer decodes the string, inflates it and writes the result into the page. Real viewer
    # pages also carry their own script code, which runtime stands in for.
    return (
        "<!DOCTYPE html><html><head><title>iXBRL Viewer</title></head><body>"
        f'{body}<script>const b64 = "{literal}";'
        " const ds = new DecompressionStream('gzip'); document.write(b64);"
        f" /* {'viewer runtime ' * (runtime // 15)}*/</script>"
        "</body></html>"
    )


def _write_page(tmp_path: Path, markup: bytes, encode=gzip.compress, name: str = "viewer.html") -> Path:
    page = tmp_path / name
    page.write_text(_packed_page(base64.b64encode(encode(markup)).decode()), encoding="utf-8")
    return page


def test_gzip_viewer_page_is_unpacked_and_its_format_left_unchecked(tmp_path: Path):
    page = _write_page(tmp_path, SYNTHETIC_PAPER)

    whitepaper = load_whitepaper(page, WhitepaperType.OTHER)
    report = lint_whitepaper(whitepaper)

    assert "Example Token" in whitepaper.sections["summary"]
    assert "Example Issuer AG" in whitepaper.sections["issuer"]
    assert whitepaper.title == "Viewer"
    assert whitepaper.metadata["source_file"] == str(page)
    assert whitepaper.metadata["script_packed_source"] is True
    assert whitepaper.metadata["ixbrl_validated"] is False
    assert report.warnings[0] == VIEWER_PAGE_NOTE
    ixbrl = next(finding for finding in report.findings if finding.rule.rule_id == "COMMON.IXBRL_TAGGING")
    assert ixbrl.status == "missing"
    assert ixbrl.issues[0].startswith("Saved iXBRL viewer page:")


@pytest.mark.parametrize("encode", [zlib.compress, lambda markup: markup], ids=["zlib", "uncompressed"])
def test_zlib_and_uncompressed_payloads_are_unpacked(tmp_path: Path, encode):
    page = _write_page(tmp_path, SYNTHETIC_PAPER, encode)

    assert unpack_script_payload(page) == SYNTHETIC_PAPER
    assert "Example Issuer AG" in load_whitepaper(page, WhitepaperType.OTHER).sections["issuer"]


def test_unpadded_literal_and_bare_data_script_are_unpacked(tmp_path: Path):
    padded = base64.b64encode(SYNTHETIC_PAPER).decode()
    assert padded.endswith("=")
    unpadded = tmp_path / "unpadded.html"
    unpadded.write_text(_packed_page(padded.rstrip("=")), encoding="utf-8")
    literal = base64.b64encode(gzip.compress(SYNTHETIC_PAPER)).decode()
    bare = tmp_path / "bare.html"
    wrapped = "\n".join(literal[i : i + 76] for i in range(0, len(literal), 76))
    bare.write_text(
        _packed_page("").replace("</body>", f'<script type="application/octet-stream">{wrapped}</script></body>'),
        encoding="utf-8",
    )

    assert unpack_script_payload(unpadded) == SYNTHETIC_PAPER
    assert unpack_script_payload(bare) == SYNTHETIC_PAPER
    whitepaper = load_whitepaper(bare, WhitepaperType.OTHER)
    assert whitepaper.metadata["script_packed_source"] is True
    assert "Example Issuer AG" in whitepaper.sections["issuer"]


def _raw_deflate(markup: bytes) -> bytes:
    compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    return compressor.compress(markup) + compressor.flush()


def test_data_uri_json_escaped_and_raw_deflate_payloads_are_unpacked(tmp_path: Path):
    literal = base64.b64encode(gzip.compress(SYNTHETIC_PAPER)).decode()
    assert "/" in literal
    data_uri = tmp_path / "data-uri.html"
    data_uri.write_text(_packed_page(f"data:text/html;base64,{literal}"), encoding="utf-8")
    escaped = tmp_path / "escaped.html"
    escaped.write_text(_packed_page(literal.replace("/", "\\/")), encoding="utf-8")
    raw = _write_page(tmp_path, SYNTHETIC_PAPER, _raw_deflate, "raw.html")

    for page in (data_uri, escaped, raw):
        assert unpack_script_payload(page) == SYNTHETIC_PAPER, page.name


def test_multi_member_gzip_is_read_whole_and_trailing_bytes_are_refused(tmp_path: Path):
    half = len(SYNTHETIC_PAPER) // 2
    members = _write_page(
        tmp_path, SYNTHETIC_PAPER, lambda m: gzip.compress(m[:half]) + gzip.compress(m[half:]), "members.html"
    )
    trailing = _write_page(tmp_path, SYNTHETIC_PAPER, lambda m: gzip.compress(m) + b"junk", "trailing.html")

    assert unpack_script_payload(members) == SYNTHETIC_PAPER
    assert unpack_script_payload(trailing) is None


def test_uncompressed_markup_split_over_literals_is_refused(tmp_path: Path):
    literal = base64.b64encode(SYNTHETIC_PAPER).decode()
    cut = len(literal) // 2 // 4 * 4
    page = tmp_path / "chunks.html"
    page.write_text(_packed_page(f'{literal[:cut]}", "{literal[cut:]}'), encoding="utf-8")

    assert unpack_script_payload(page) is None


@pytest.mark.parametrize(
    "other",
    [
        # base64 of binary data, such as an inlined icon or font
        base64.b64encode(bytes(range(256)) * 8).decode(),
        # a compressed JSON blob
        base64.b64encode(gzip.compress(json.dumps({"facts": list(range(2000))}).encode())).decode(),
        # the same document a second time
        base64.b64encode(gzip.compress(SYNTHETIC_PAPER)).decode(),
    ],
    ids=["binary", "json", "duplicate"],
)
def test_other_literals_on_the_page_do_not_hide_the_white_paper(tmp_path: Path, other: str):
    assert len(other) >= 1024
    payload = base64.b64encode(gzip.compress(SYNTHETIC_PAPER)).decode()
    page = tmp_path / "decoy.html"
    page.write_text(_packed_page(f'{other}"; const b64 = "{payload}'), encoding="utf-8")

    assert unpack_script_payload(page) == SYNTHETIC_PAPER


def test_page_packing_two_documents_is_refused(tmp_path: Path):
    # Which one is the white paper is unclear, for example with a loading page packed ahead of it.
    shell = base64.b64encode(gzip.compress(f"<html><body><p>{_clauses(100)}</p></body></html>".encode())).decode()
    assert len(shell) >= 1024
    payload = base64.b64encode(gzip.compress(SYNTHETIC_PAPER)).decode()
    page = tmp_path / "two.html"
    page.write_text(_packed_page(f'{shell}"; const b64 = "{payload}'), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        load_whitepaper(page, WhitepaperType.OTHER)

    assert str(exc.value).startswith("two.html is a saved iXBRL viewer page that packs more than one document")


def test_text_in_noscript_is_read_directly(tmp_path: Path):
    page = tmp_path / "noscript.html"
    literal = base64.b64encode(gzip.compress(b"<html><body><p>x</p></body></html>")).decode()
    page.write_text(
        _packed_page(literal, f"<noscript><h1>Summary</h1><p>{_clauses(20)}</p></noscript>"), encoding="utf-8"
    )

    assert is_script_packed(page) is False
    assert "Clause 3" in load_whitepaper(page, WhitepaperType.OTHER).sections["summary"]


def test_viewer_page_without_sections_says_why_everything_is_missing(tmp_path: Path):
    page = _write_page(tmp_path, f"<html><body><p>{_clauses(150)}</p></body></html>".encode())

    whitepaper = load_whitepaper(page, WhitepaperType.OTHER)

    assert whitepaper.sections == {}
    assert whitepaper.metadata["extraction_notes"] == (VIEWER_PAGE_NOTE, VIEWER_EMPTY_NOTE)


def test_viewer_page_warns_when_field_labels_run_into_answers(tmp_path: Path):
    # A PDF rendering puts each field number in its own text run, so the label joins the answer.
    rows = "".join(
        f"<div><span>{part}.{number}</span></div><div><span>Field {part}{number} label "
        f"{'N/A' if part == 'C' else f'answer {_clauses(1)}'}</span></div>"
        for part in "ABCDE"
        for number in range(1, 5)
    )
    page = _write_page(tmp_path, f"<html><body>{rows}<p>{_clauses(120)}</p></body></html>".encode())

    whitepaper = load_whitepaper(page, WhitepaperType.OTHER)

    notes = whitepaper.metadata["extraction_notes"]
    assert notes[:2] == (VIEWER_PAGE_NOTE, MERGED_LABELS_NOTE)
    # The risk the note names: the "N/A" field reads as answered, label included.
    assert "Field C1 label N/A" in whitepaper.sections["trading_platform_operator"]


def test_huge_viewer_page_is_detected_and_refused(tmp_path: Path):
    # libxml2 drops a text node above about 10 million characters unless huge_tree is set.
    markup = b"<html><body><p>" + b"a" * MAX_UNPACKED_BYTES + b"</p></body></html>"
    page = _write_page(tmp_path, markup, lambda raw: raw)
    assert page.stat().st_size > 10_000_000

    with pytest.raises(SystemExit) as exc:
        load_whitepaper(page, WhitepaperType.OTHER)

    assert "more than 8 MB" in str(exc.value)


def test_unpacking_limit_matches_the_playground_limit():
    model = (ROOT / "docs" / "playground" / "model.mjs").read_text()
    factors = re.search(r"export const MAX_XHTML_BYTES = ([\d *]+);", model).group(1).split("*")

    product = 1
    for factor in factors:
        product *= int(factor)
    assert product == MAX_UNPACKED_BYTES
    page = (ROOT / "docs" / "playground" / "index.html").read_text()
    assert f"XHTML up to {MAX_UNPACKED_BYTES // 2**20} MB" in page


def test_ordinary_xhtml_keeps_the_format_check(tmp_path: Path):
    page = tmp_path / "plain.xhtml"
    page.write_bytes(SYNTHETIC_PAPER)

    whitepaper = load_whitepaper(page, WhitepaperType.OTHER)

    assert whitepaper.metadata["script_packed_source"] is False
    assert whitepaper.metadata["ixbrl_validated"] is True
    assert VIEWER_PAGE_NOTE not in whitepaper.metadata["extraction_notes"]


def test_page_with_text_and_a_large_script_is_still_read_directly(tmp_path: Path):
    page = tmp_path / "draft.html"
    summary = "This plain-language summary describes the token, its issuer and the main risks. " * 8
    literal = base64.b64encode(gzip.compress(SYNTHETIC_PAPER)).decode()
    page.write_text(_packed_page(literal, f"<h1>Summary</h1><p>{summary}</p>"), encoding="utf-8")

    whitepaper = load_whitepaper(page, WhitepaperType.OTHER)

    assert whitepaper.sections["summary"].startswith("This plain-language summary describes the token")
    assert whitepaper.metadata["script_packed_source"] is False


def test_short_page_without_a_large_script_is_not_called_packed(tmp_path: Path):
    page = tmp_path / "short.html"
    page.write_text(_packed_page("QUJD" * 10, "<h1>Summary</h1><p>Short.</p>", runtime=0), encoding="utf-8")

    assert is_script_packed(page) is False


@pytest.mark.parametrize(("script_chars", "packed"), [(10_000, False), (10_001, True)])
def test_a_page_counts_as_packed_only_above_the_script_threshold(tmp_path: Path, script_chars: int, packed: bool):
    page = tmp_path / "threshold.html"
    page.write_text(
        f"<html><body><div>Loading document...</div><script>{'x' * script_chars}</script></body></html>",
        encoding="utf-8",
    )

    assert is_script_packed(page) is packed


def test_cli_lints_a_viewer_page_and_keeps_its_outputs_free_of_draft_lines(tmp_path: Path, capsys):
    page = _write_page(tmp_path, SYNTHETIC_PAPER)
    sarif = tmp_path / "report.sarif"

    status = main([str(page), "--type", "other", "--strict", "--sarif-output", str(sarif)])

    assert status == 1
    assert VIEWER_PAGE_NOTE in capsys.readouterr().out
    lines = {
        location["physicalLocation"]["region"]["startLine"]
        for result in json.loads(sarif.read_text())["runs"][0]["results"]
        for location in result["locations"]
    }
    assert lines == {1}


def test_audit_log_and_review_bundle_list_the_viewer_page_note(tmp_path: Path):
    page = _write_page(tmp_path, SYNTHETIC_PAPER)
    log_path, bundle = tmp_path / "audit.md", tmp_path / "bundle"

    status = main(
        [str(page), "--type", "other", "--audit-log", str(log_path), "--review-bundle-dir", str(bundle)]
    )

    assert status == 0
    bundle_files = ("compliance-checklist.md", "review-table.md", "reviewer-signoff.md")
    for path in (log_path, *(bundle / name for name in bundle_files)):
        assert f"- {VIEWER_PAGE_NOTE}" in path.read_text(encoding="utf-8").splitlines(), path.name


def test_numbered_layout_inside_a_viewer_page_reads_like_the_file_itself(tmp_path: Path):
    example = ROOT / "examples" / "numbered-other-draft.xhtml"
    page = _write_page(tmp_path, example.read_bytes())

    with pytest.raises(SystemExit) as exc:
        load_whitepaper(page)
    assert str(exc.value).startswith("The white paper packed in viewer.html uses the numbered fields")

    unpacked = load_whitepaper(page, WhitepaperType.OTHER)
    direct = load_whitepaper(example, WhitepaperType.OTHER)
    assert unpacked.sections == direct.sections
    assert unpacked.metadata["extraction_notes"] == (VIEWER_PAGE_NOTE, *direct.metadata["extraction_notes"])


def test_german_viewer_page_explains_the_format_gate_in_german(tmp_path: Path):
    paper = (
        "<html><body><h1>Zusammenfassung</h1>"
        "<p>Die Zusammenfassung ist eine fiktive Darstellung und beschreibt die Rechte der Inhaber. " * 12
        + f"{_clauses(100)}</p></body></html>"
    ).encode()
    report = lint_whitepaper(load_whitepaper(_write_page(tmp_path, paper), WhitepaperType.OTHER))

    ixbrl = next(finding for finding in report.findings if finding.rule.rule_id == "COMMON.IXBRL_TAGGING")
    assert ixbrl.status == "missing"
    assert ixbrl.issues[0].startswith("Gespeicherte iXBRL-Viewer-Seite:")


def test_payload_above_the_cap_is_refused_with_the_limit(tmp_path: Path):
    markup = b"<html><body><p>" + b"a" * MAX_UNPACKED_BYTES + b"</p></body></html>"
    page = _write_page(tmp_path, markup)

    with pytest.raises(SystemExit) as exc:
        load_whitepaper(page, WhitepaperType.OTHER)

    message = str(exc.value)
    assert message.startswith("viewer.html is a saved iXBRL viewer page")
    assert "more than 8 MB" in message
    assert "ESMA register" in message


def test_inflation_stops_at_the_limit(tmp_path: Path):
    markup = f"<html><body><p>{_clauses(150)}</p></body></html>".encode()
    page = _write_page(tmp_path, markup)

    assert unpack_script_payload(page, limit=len(markup)) == markup
    with pytest.raises(PackedPageTooLarge):
        unpack_script_payload(page, limit=len(markup) - 1)


@pytest.mark.parametrize(
    "literal",
    [
        # gzip magic followed by zeros: no valid stream and no markup
        "H4sI" + "A" * 20_000,
        # a complete gzip stream that holds JSON, not markup
        base64.b64encode(gzip.compress(json.dumps({"facts": list(range(2000))}).encode())).decode(),
        # a gzip stream cut short, which would hide the end of the white paper
        base64.b64encode(gzip.compress(SYNTHETIC_PAPER)[:-200]).decode(),
        # uncompressed markup cut short, which has no end marker of its own
        base64.b64encode(SYNTHETIC_PAPER[:-200]).decode(),
        # a page that unpacks into another packed page
        base64.b64encode(
            gzip.compress(_packed_page(base64.b64encode(gzip.compress(SYNTHETIC_PAPER)).decode()).encode())
        ).decode(),
    ],
    ids=["not-a-stream", "not-markup", "truncated", "truncated-uncompressed", "packed-twice"],
)
def test_page_that_cannot_be_unpacked_is_refused_with_a_reason(tmp_path: Path, literal: str):
    page = tmp_path / "viewer.html"
    page.write_text(_packed_page(literal), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        load_whitepaper(page, WhitepaperType.EMT)

    message = str(exc.value)
    assert message.startswith("viewer.html holds no white paper text that can be read")
    assert "ESMA register" in message


def test_cli_stops_with_the_reason(tmp_path: Path):
    page = tmp_path / "viewer.html"
    page.write_text(_packed_page("H4sI" + "A" * 20_000), encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        main([str(page), "--type", "emt"])

    assert str(exc.value.code).startswith("viewer.html holds no white paper text")


def test_json_draft_cannot_claim_to_be_a_viewer_page(tmp_path: Path):
    draft = json.loads((ROOT / "examples" / "art-stablecoin.json").read_text())
    draft["script_packed_source"] = True
    path = tmp_path / "draft.json"
    path.write_text(json.dumps(draft), encoding="utf-8")

    whitepaper = load_whitepaper(path)
    ixbrl = next(f for f in lint_whitepaper(whitepaper).findings if f.rule.rule_id == "COMMON.IXBRL_TAGGING")

    assert "script_packed_source" not in whitepaper.metadata
    assert ixbrl.issues[0].startswith("Draft format:")
