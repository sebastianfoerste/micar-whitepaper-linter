import hashlib
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import docx
import pytest
from docx.opc.constants import RELATIONSHIP_TYPE
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from lxml import etree

from micar_linter.collaboration_workspace import (
    build_change_set,
    build_review_sidecar,
    build_workflow_pack,
    decide_change,
    lock_cell,
    reconcile_sidecar,
    render_tracked_docx,
    update_cell,
)
from micar_linter.workspace import build_whitepaper_workspace


def _workspace() -> dict:
    return build_whitepaper_workspace([Path("examples/incomplete.json")])


def test_sidecar_uses_stable_cells_and_stale_lock_conflicts() -> None:
    sidecar = build_review_sidecar(_workspace())
    locked = lock_cell(
        sidecar, sidecar["cells"][0]["target_id"], "Reviewer", 1, datetime(2026, 7, 13, tzinfo=UTC)
    )
    with pytest.raises(ValueError, match="409 Conflict"):
        lock_cell(locked, locked["cells"][0]["target_id"], "Other", 1, datetime(2026, 7, 13, tzinfo=UTC))
    changed = _workspace()
    changed["vault"]["documents"][0]["source_sha256"] = "changed"
    assert reconcile_sidecar(sidecar, changed)["stale"] is True
    updated = update_cell(
        locked,
        locked["cells"][0]["target_id"],
        "Reviewer",
        2,
        datetime(2026, 7, 13, tzinfo=UTC),
        assignee="Reviewer",
        comment="Source checked",
        decision="approved",
    )
    assert updated["cells"][0]["comments"][0]["body"] == "Source checked"
    with pytest.raises(ValueError, match="409 Conflict"):
        update_cell(
            updated,
            updated["cells"][0]["target_id"],
            "Reviewer",
            2,
            datetime(2026, 7, 13, tzinfo=UTC),
            decision="approved",
        )


def test_docx_redline_uses_tracked_insertions_and_deletions(tmp_path) -> None:
    source = tmp_path / "source.docx"
    document = docx.Document()
    document.add_paragraph("Original clause survives")
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Original table survives"
    document.save(source)
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    change_set = build_change_set(_workspace())
    change_set["source_digests"] = {"source": source_digest}
    change_set = decide_change(change_set, change_set["changes"][0]["id"], "accepted")
    for change in list(change_set["changes"][1:]):
        change_set = decide_change(change_set, change["id"], "rejected")
    output = render_tracked_docx(source, tmp_path / "reviewed.docx", change_set)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == source_digest
    with zipfile.ZipFile(output) as package:
        xml = etree.fromstring(package.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    assert xml.xpath("count(.//w:ins)", namespaces=ns) > 0
    assert xml.xpath("count(.//w:del)", namespaces=ns) > 0
    text = "".join(xml.xpath(".//w:t/text()", namespaces=ns))
    assert "Original clause survives" in text
    assert "Original table survives" in text
    assert xml.xpath("count(.//w:ins)", namespaces=ns) == 1
    inserted_changes = [
        "".join(node.xpath(".//w:t/text()", namespaces=ns)) for node in xml.xpath(".//w:ins", namespaces=ns)
    ]
    assert inserted_changes == [change_set["changes"][0]["proposed_text"]]


def test_docx_replaces_matching_paragraph_inside_table_cell(tmp_path) -> None:
    source = tmp_path / "table-source.docx"
    document = docx.Document()
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Replace this table clause"
    document.save(source)
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    change_set = {
        "source_digests": {"source": source_digest},
        "export_allowed": True,
        "changes": [
            {
                "decision": "accepted",
                "original_text": "Replace this table clause",
                "proposed_text": "Literal <replacement> & text",
            }
        ],
    }
    output = render_tracked_docx(source, tmp_path / "table-reviewed.docx", change_set)
    with zipfile.ZipFile(output) as package:
        xml = etree.fromstring(package.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    table_text = "".join(xml.xpath(".//w:tc//w:t/text()", namespaces=ns))
    assert table_text == "Literal <replacement> & text"


def test_tracked_docx_rejects_out_of_range_source_epoch(tmp_path, monkeypatch) -> None:
    source = tmp_path / "source.docx"
    docx.Document().save(source)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "999999999999999999999")
    with pytest.raises(ValueError, match="valid integer Unix timestamp"):
        render_tracked_docx(
            source,
            tmp_path / "reviewed.docx",
            {"source_digests": {"source": digest}, "export_allowed": True, "changes": []},
        )


def test_workflow_pack_blocks_unreviewed_cells() -> None:
    workspace = _workspace()
    sidecar = build_review_sidecar(workspace)
    pack = build_workflow_pack(workspace, sidecar, build_change_set(workspace))
    assert pack["run"]["status"] == "blocked"
    assert pack["run"]["external_action_allowed"] is False


def _accepted_change_set(source: Path, original: str, proposed: str) -> dict:
    return {
        "source_digests": {"source": hashlib.sha256(source.read_bytes()).hexdigest()},
        "export_allowed": True,
        "changes": [{"decision": "accepted", "original_text": original, "proposed_text": proposed}],
    }


def _paragraph_views(paragraph) -> tuple[str, str]:
    """Text of the paragraph with every change accepted, and with every change rejected."""
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    accepted = "".join(paragraph.xpath(".//w:t[not(ancestor::w:del)]/text()", namespaces=ns))
    rejected = "".join(
        paragraph.xpath(".//w:t[not(ancestor::w:ins)]/text() | .//w:delText/text()", namespaces=ns)
    )
    return accepted, rejected


def test_docx_partial_paragraph_match_keeps_surrounding_text(tmp_path) -> None:
    source = tmp_path / "partial-source.docx"
    document = docx.Document()
    paragraph = document.add_paragraph("The issuer ", style="List Bullet")
    paragraph.add_run("Example Issuer AG").bold = True
    paragraph.add_run(" is TBD and will notify BaFin.")
    document.add_paragraph("Next paragraph stays.")
    document.save(source)
    change_set = _accepted_change_set(source, "AG is TBD", "AG is incorporated in Germany")
    output = render_tracked_docx(source, tmp_path / "partial-reviewed.docx", change_set)
    with zipfile.ZipFile(output) as package:
        xml = etree.fromstring(package.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert _paragraph_views(paragraphs[0]) == (
        "The issuer Example Issuer AG is incorporated in Germany and will notify BaFin.",
        "The issuer Example Issuer AG is TBD and will notify BaFin.",
    )
    assert _paragraph_views(paragraphs[1]) == ("Next paragraph stays.", "Next paragraph stays.")
    assert paragraphs[0].xpath("string(w:pPr/w:pStyle/@w:val)", namespaces=ns) == "ListBullet"
    kept_bold = paragraphs[0].xpath(
        ".//w:r[not(ancestor::w:del) and not(ancestor::w:ins)][w:rPr/w:b]//w:t/text()", namespaces=ns
    )
    assert "".join(kept_bold) == "Example Issuer "
    deleted_bold = paragraphs[0].xpath(".//w:del/w:r[w:rPr/w:b]/w:delText/text()", namespaces=ns)
    assert "".join(deleted_bold) == "AG"
    ids = xml.xpath(".//w:ins/@w:id | .//w:del/@w:id", namespaces=ns)
    assert len(ids) == len(set(ids))


def test_docx_redlines_two_changes_in_one_paragraph(tmp_path) -> None:
    source = tmp_path / "two-source.docx"
    document = docx.Document()
    document.add_paragraph("Name TBD, address TBC, LEI pending.")
    document.save(source)
    change_set = _accepted_change_set(source, "Name TBD", "Name Example AG")
    change_set["changes"].append(
        {"decision": "accepted", "original_text": "address TBC", "proposed_text": "address Berlin"}
    )
    output = render_tracked_docx(source, tmp_path / "two-reviewed.docx", change_set)
    with zipfile.ZipFile(output) as package:
        xml = etree.fromstring(package.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert len(paragraphs) == 1
    assert _paragraph_views(paragraphs[0]) == (
        "Name Example AG, address Berlin, LEI pending.",
        "Name TBD, address TBC, LEI pending.",
    )


def test_docx_redline_splits_pending_insertion_of_another_author(tmp_path) -> None:
    source = tmp_path / "pending-source.docx"
    document = docx.Document()
    paragraph = document.add_paragraph("Start ")
    pending = paragraph._p.makeelement(qn("w:ins"), {qn("w:id"): "1", qn("w:author"): "Other reviewer"})
    pending_run = paragraph._p.makeelement(qn("w:r"), {})
    pending_run.append(paragraph._p.makeelement(qn("w:t"), {}))
    pending_run[0].text = "inserted words"
    pending.append(pending_run)
    paragraph._p.append(pending)
    paragraph.add_run(" end.")
    document.save(source)
    change_set = _accepted_change_set(source, "inserted", "added")
    output = render_tracked_docx(source, tmp_path / "pending-reviewed.docx", change_set)
    with zipfile.ZipFile(output) as package:
        xml = etree.fromstring(package.read("word/document.xml"))
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraph_xml = xml.xpath(".//w:body/w:p", namespaces=ns)[0]
    assert "".join(paragraph_xml.xpath(".//w:t[not(ancestor::w:del)]/text()", namespaces=ns)) == (
        "Start added words end."
    )
    assert xml.xpath("count(//w:ins//w:ins)", namespaces=ns) == 0
    assert xml.xpath("string(//w:ins[@w:author='Other reviewer']//w:delText)", namespaces=ns) == "inserted"
    ids = xml.xpath("//w:ins/@w:id | //w:del/@w:id", namespaces=ns)
    assert len(ids) == len(set(ids))


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_DECLARATIONS = (
    f'xmlns:w="{_W}" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:v="urn:schemas-microsoft-com:vml" '
    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)


def _docx_with_paragraphs(path: Path, *paragraphs: str) -> None:
    document = docx.Document()
    body = document.element.body
    for paragraph in paragraphs:
        body.insert(len(body) - 1, parse_xml(f"<w:p {_DECLARATIONS}>{paragraph}</w:p>"))
    document.save(path)


def _run(text: str) -> str:
    return f'<w:r><w:t xml:space="preserve">{text}</w:t></w:r>'


def _field_char(kind: str) -> str:
    return f'<w:r><w:fldChar w:fldCharType="{kind}"/></w:r>'


def _render(tmp_path: Path, source: Path, changes: list[tuple[str, str]]) -> etree._Element:
    change_set = _accepted_change_set(source, *changes[0])
    for original, proposed in changes[1:]:
        change_set["changes"].append({"decision": "accepted", "original_text": original, "proposed_text": proposed})
    output = render_tracked_docx(source, tmp_path / f"{source.stem}-reviewed.docx", change_set)
    with zipfile.ZipFile(output) as package:
        return etree.fromstring(package.read("word/document.xml"))


def test_docx_redline_leaves_field_results_and_codes_alone(tmp_path) -> None:
    source = tmp_path / "fields.docx"
    _docx_with_paragraphs(
        source,
        _run("Issuer: ")
        + '<w:fldSimple w:instr=" DOCPROPERTY IssuerName ">'
        + _run("TBD")
        + "</w:fldSimple>"
        + _run(" is registered."),
        _run("Name ")
        + _field_char("begin")
        + '<w:r><w:instrText xml:space="preserve"> REF _RefIssuer \\h </w:instrText></w:r>'
        + _field_char("separate")
        + _run("TBD")
        + _field_char("end")
        + _run(" is pending."),
        _run("Status TBD."),
    )
    xml = _render(tmp_path, source, [("TBD", "confirmed"), ("Name TBD is pending", "Name confirmed")])
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    for field_paragraph in paragraphs[:2]:
        assert field_paragraph.xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    assert _paragraph_views(paragraphs[2]) == ("Status confirmed.", "Status TBD.")
    assert paragraphs[-1].xpath("string(w:del//w:delText)", namespaces=ns) == "Name TBD is pending"


def test_docx_redline_skips_table_of_contents_and_hidden_fallback_copy(tmp_path) -> None:
    source = tmp_path / "toc.docx"
    _docx_with_paragraphs(
        source,
        _field_char("begin")
        + '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" </w:instrText></w:r>'
        + _field_char("separate")
        + _run("Risk factors"),
        _run("Summary") + _field_char("end"),
        "<w:r><mc:AlternateContent><mc:Choice Requires=\"wps\"><w:drawing/></mc:Choice><mc:Fallback>"
        "<w:pict><v:shape><v:textbox><w:txbxContent><w:p>"
        + _run("Risk factors")
        + "</w:p></w:txbxContent></v:textbox></v:shape></w:pict></mc:Fallback></mc:AlternateContent></w:r>",
        _run("Risk factors"),
    )
    xml = _render(tmp_path, source, [("Risk factors", "Risk factors and mitigations")])
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert len(paragraphs) == 4
    assert xml.xpath("count(//w:del)", namespaces=ns) == 1
    assert _paragraph_views(paragraphs[3]) == ("Risk factors and mitigations", "Risk factors")


def test_docx_redline_skips_moved_away_text_and_splits_the_move(tmp_path) -> None:
    source = tmp_path / "move.docx"
    revision = 'w:author="Other reviewer" w:date="2026-10-01T00:00:00Z"'
    _docx_with_paragraphs(
        source,
        _run("Moved away: ") + f'<w:moveFrom w:id="20" {revision}>' + _run("Issuer TBD") + "</w:moveFrom>",
        _run("Moved here: ") + f'<w:moveTo w:id="21" {revision}>' + _run("Issuer TBD here") + "</w:moveTo>",
    )
    xml = _render(tmp_path, source, [("Issuer TBD", "Issuer Example AG")])
    ns = {"w": _W}
    moved_away, moved_here = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert moved_away.xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    assert moved_here.xpath("string(w:moveTo/w:del//w:delText)", namespaces=ns) == "Issuer TBD"
    assert moved_here.xpath("count(.//w:moveTo//w:ins)", namespaces=ns) == 0
    accepted = "".join(moved_here.xpath(".//w:t[not(ancestor::w:del)]/text()", namespaces=ns))
    assert accepted == "Moved here: Issuer Example AG here"
    ids = xml.xpath("//@w:id", namespaces=ns)
    assert len(ids) == len(set(ids))


def test_docx_redline_skips_bound_content_controls_and_hidden_text(tmp_path) -> None:
    source = tmp_path / "bound.docx"
    binding = (
        '<w:dataBinding w:xpath="/ns1:coreProperties[1]/ns0:title[1]" '
        'w:storeItemID="{6C3C8BC8-F283-45AE-878A-BAB7291924A1}"/>'
    )
    _docx_with_paragraphs(
        source,
        _run("Title: ") + f"<w:sdt><w:sdtPr>{binding}</w:sdtPr><w:sdtContent>" + _run("Token TBD") + "</w:sdtContent></w:sdt>",
        '<w:r><w:rPr><w:vanish/></w:rPr><w:t xml:space="preserve">Guidance: replace Token TBD.</w:t></w:r>',
        _run("Token ") + '<w:r><w:rPr><w:vanish w:val="1"/></w:rPr><w:t>[note] </w:t></w:r>' + _run("TBD is pending."),
        _run("The Token TBD is offered."),
    )
    xml = _render(tmp_path, source, [("Token TBD", "Token EXT")])
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    for untouched in paragraphs[:3]:
        assert untouched.xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    assert _paragraph_views(paragraphs[3]) == ("The Token EXT is offered.", "The Token TBD is offered.")
    assert xml.xpath("count(//w:ins//w:vanish)", namespaces=ns) == 0


def test_docx_redline_skips_managed_content_controls_and_equations(tmp_path) -> None:
    source = tmp_path / "controls.docx"
    _docx_with_paragraphs(
        source,
        _run("Issuer: ")
        + "<w:sdt><w:sdtPr><w:showingPlcHdr/><w:text/></w:sdtPr><w:sdtContent>"
        + '<w:r><w:rPr><w:rStyle w:val="PlaceholderText"/></w:rPr><w:t>Issuer name TBD</w:t></w:r>'
        + "</w:sdtContent></w:sdt>"
        + _run(" (registered)."),
        _run("Date: ")
        + '<w:sdt><w:sdtPr><w:date><w:dateFormat w:val="dd.MM.yyyy"/></w:date></w:sdtPr><w:sdtContent>'
        + _run("01.01.2026")
        + "</w:sdtContent></w:sdt>",
        _run("The reserve rate ") + "<m:oMath><m:r><m:t>r=0.05</m:t></m:r></m:oMath>" + _run(" is TBD for holders."),
        _run("Issuer name TBD") + '<w:bookmarkStart w:id="40" w:name="Offer"/>' + _run(" offers from 01.01.2026."),
    )
    changes = [("Issuer name TBD", "Example Issuer AG"), ("01.01.2026", "31.12.2026"), ("rate  is TBD", "rate is set")]
    xml = _render(tmp_path, source, changes)
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    for untouched in paragraphs[:3]:
        assert untouched.xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    assert _paragraph_views(paragraphs[3]) == (
        "Example Issuer AG offers from 31.12.2026.",
        "Issuer name TBD offers from 01.01.2026.",
    )
    assert paragraphs[-1].xpath("string(w:del//w:delText)", namespaces=ns) == "rate  is TBD"


def test_docx_redline_stays_within_links_and_content_controls_and_deletes_soft_hyphens(tmp_path) -> None:
    source = tmp_path / "links.docx"
    link = '<w:hyperlink w:anchor="Offer">' + _run("example.invalid/token") + "</w:hyperlink>"
    control = '<w:sdt><w:sdtPr><w:tag w:val="issuer_name"/></w:sdtPr><w:sdtContent>'
    _docx_with_paragraphs(
        source,
        _run("Details are published at ") + link + _run(" every quarter."),
        _run("Mirror at ") + link.replace("example.invalid", "mirror.invalid") + _run("."),
        control + _run("Example Issuer AG") + "</w:sdtContent></w:sdt>" + _run(" is the issuer."),
        '<w:r><w:t xml:space="preserve">Der vermögenswert</w:t><w:softHyphen/><w:t>referenzierte Token gilt.</w:t></w:r>',
    )
    changes = [
        ("published at example.invalid", "posted at example.invalid"),
        ("mirror.invalid/token", "mirror.invalid/token-v2"),
        ("Example Issuer AG is", "Example Issuer SE is"),
        ("vermögenswertreferenzierte Token", "E-Geld-Token"),
    ]
    xml = _render(tmp_path, source, changes)
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert paragraphs[0].xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    assert paragraphs[1].xpath("string(w:hyperlink/w:ins)", namespaces=ns) == "mirror.invalid/token-v2"
    assert paragraphs[2].xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    assert _paragraph_views(paragraphs[3])[0] == "Der E-Geld-Token gilt."
    assert paragraphs[3].xpath("count(.//w:softHyphen[not(ancestor::w:del)])", namespaces=ns) == 0
    fallbacks = ["".join(p.xpath("w:del//w:delText/text()", namespaces=ns)) for p in paragraphs[4:]]
    assert fallbacks == ["published at example.invalid", "Example Issuer AG is"]


def test_docx_redline_runs_through_a_whole_link_and_smart_tags(tmp_path) -> None:
    source = tmp_path / "whole-link.docx"
    mail = '<w:hyperlink w:anchor="Contact"><w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
    _docx_with_paragraphs(
        source,
        _run("Write to ") + mail + "<w:t>info@example.invalid</w:t></w:r></w:hyperlink>" + _run(" within ten days."),
        _run("The offer starts on ")
        + '<w:smartTag w:uri="urn:schemas-microsoft-com:office:smarttags" w:element="date">'
        + _run("1 March 2027")
        + "</w:smartTag>"
        + _run(" in Berlin."),
    )
    changes = [
        ("Write to info@example.invalid within ten days", "Write to the complaints desk within five days"),
        ("March 2027 in Berlin", "April 2027 in Leipzig"),
    ]
    xml = _render(tmp_path, source, changes)
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert len(paragraphs) == 2
    assert _paragraph_views(paragraphs[0]) == (
        "Write to the complaints desk within five days.",
        "Write to info@example.invalid within ten days.",
    )
    assert paragraphs[0].xpath("string(w:hyperlink/w:del//w:delText)", namespaces=ns) == "info@example.invalid"
    assert paragraphs[0].xpath("count(w:ins//w:rStyle)", namespaces=ns) == 0
    assert _paragraph_views(paragraphs[1]) == (
        "The offer starts on 1 April 2027 in Leipzig.",
        "The offer starts on 1 March 2027 in Berlin.",
    )


def test_docx_redline_replaces_external_link_after_it_and_keeps_custom_xml_extent(tmp_path) -> None:
    source = tmp_path / "external.docx"
    document = docx.Document()
    target = document.part.relate_to("mailto:info@old.invalid", RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    website = document.part.relate_to("https://www.old.invalid", RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    style = '<w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
    link = f'<w:hyperlink r:id="{target}"><w:r>{style}<w:t>info@old.invalid</w:t></w:r></w:hyperlink>'
    body = document.element.body
    for paragraph in (
        '<w:bookmarkStart w:id="\u00b2" w:name="Odd"/>'
        + '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">Contact: </w:t></w:r>'
        + link
        + _run("."),
        _run("Mail ") + link + _run(" today."),
        _run("The fee is ") + '<w:customXml w:element="feeAmount">' + _run("EUR 5") + "</w:customXml>" + _run(" per token."),
        _run("Web: ")
        + f'<w:hyperlink r:id="{website}"><w:r>{style}<w:t>www.old.invalid</w:t></w:r><w:r><w:br/></w:r></w:hyperlink>'
        + _run("Phone: 000"),
    ):
        body.insert(len(body) - 1, parse_xml(f"<w:p {_DECLARATIONS}>{paragraph}</w:p>"))
    document.save(source)
    changes = [
        ("info@old.invalid", "info@new.invalid"),
        ("old.invalid", "new.invalid"),
        ("EUR 5 per token", "EUR 7 per token"),
        ("www.old.invalid", "www.new.invalid"),
    ]
    xml = _render(tmp_path, source, changes)
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert _paragraph_views(paragraphs[0]) == ("Contact: info@new.invalid.", "Contact: info@old.invalid.")
    assert paragraphs[0].xpath("count(w:hyperlink//w:ins)", namespaces=ns) == 0
    assert paragraphs[0].xpath("count(w:ins/w:r/w:rPr/w:b)", namespaces=ns) == 1
    assert paragraphs[0].xpath("count(w:ins//w:rStyle)", namespaces=ns) == 0
    for untouched in paragraphs[1:4]:
        assert untouched.xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    fallbacks = ["".join(p.xpath("w:del//w:delText/text()", namespaces=ns)) for p in paragraphs[4:]]
    assert fallbacks == ["old.invalid", "EUR 5 per token", "www.old.invalid"]


def test_docx_later_change_does_not_match_an_earlier_insertion(tmp_path) -> None:
    source = tmp_path / "chain.docx"
    _docx_with_paragraphs(source, _run("The issuer is TBD."))
    changes = [("is TBD", "is Example AG, seat TBC"), ("TBC", "Berlin"), ("Missing clause", "Seat TBA"), ("TBA", "Leipzig")]
    xml = _render(tmp_path, source, changes)
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert _paragraph_views(paragraphs[0]) == ("The issuer is Example AG, seat TBC.", "The issuer is TBD.")
    fallbacks = ["".join(p.xpath("w:del//w:delText/text()", namespaces=ns)) for p in paragraphs[1:]]
    assert fallbacks == ["TBC", "Missing clause", "TBA"]


def test_docx_redline_spans_markers_and_stays_inside_tagged_controls_and_custom_xml(tmp_path) -> None:
    source = tmp_path / "markers.docx"
    _docx_with_paragraphs(
        source,
        _run("The Tokken ")
        + '<w:proofErr w:type="spellStart"/>'
        + _run("Exmple")
        + '<w:proofErr w:type="spellEnd"/>'
        + '<w:bookmarkStart w:id="5" w:name="Term"/><w:commentRangeStart w:id="6"/>'
        + _run(" is")
        + '<w:bookmarkEnd w:id="5"/><w:commentRangeEnd w:id="6"/>'
        + '<w:r><w:t xml:space="preserve"> offered</w:t><w:lastRenderedPageBreak/><w:commentReference w:id="6"/>'
        + "<w:t> now.</w:t></w:r>",
        _run("Issuer: ")
        + '<w:sdt><w:sdtPr><w:tag w:val="issuer_name"/></w:sdtPr><w:sdtContent>'
        + _run("Example Issuer AG")
        + "</w:sdtContent></w:sdt>",
        _run("The fee is ") + '<w:customXml w:element="feeAmount">' + _run("EUR 5") + "</w:customXml>" + _run(" per token."),
        _run("Kind: ")
        + "<w:sdt><w:sdtPr><w:dropDownList/></w:sdtPr><w:sdtContent>"
        + _run("Utility token")
        + "</w:sdtContent></w:sdt>"
        + "<w:sdt><w:sdtPr><w:comboBox/></w:sdtPr><w:sdtContent>"
        + _run(" (Utility token)")
        + "</w:sdtContent></w:sdt>"
        + '<w:sdt><w:sdtPr><w14:checkbox xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"/>'
        + "</w:sdtPr><w:sdtContent>"
        + _run(" Utility token")
        + "</w:sdtContent></w:sdt>",
    )
    changes = [
        ("Tokken Exmple is offered now", "Token Example is offered today"),
        ("Example Issuer", "Sample Issuer"),
        ("fee is EUR 5 per", "fee is EUR 7 per"),
        ("Utility token", "Payment token"),
    ]
    xml = _render(tmp_path, source, changes)
    ns = {"w": _W}
    paragraphs = xml.xpath(".//w:body/w:p", namespaces=ns)
    assert _paragraph_views(paragraphs[0]) == ("The Token Example is offered today.", "The Tokken Exmple is offered now.")
    assert paragraphs[1].xpath("string(w:sdt/w:sdtContent/w:ins)", namespaces=ns) == "Sample Issuer"
    assert _paragraph_views(paragraphs[2]) == ("The fee is EUR 7 per token.", "The fee is EUR 5 per token.")
    assert paragraphs[3].xpath("count(.//w:del | .//w:ins)", namespaces=ns) == 0
    assert "".join(paragraphs[4].xpath("w:del//w:delText/text()", namespaces=ns)) == "Utility token"
