"""Inline XBRL validation logic."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

MANDATORY_MICA_TAGS = {
    "mica:IssuerLegalName",
    "mica:WhitepaperTitle",
    "mica:CryptoAssetSymbol",
    "mica:CryptoAssetType",
    "mica:ConsensusMechanism",
    "mica:RiskWarningStatement",
    "mica:ManagementBodyDeclaration",
}


def validate_ixbrl(path: Path) -> list[str]:
    """Validate an XHTML file for iXBRL compliance and required ESMA MiCA tags."""
    issues = []

    # 1. XML Well-formedness check
    try:
        parser = etree.XMLParser(recover=False)
        tree = etree.parse(str(path), parser=parser)
    except etree.XMLSyntaxError as exc:
        return [f"XHTML is not well-formed XML: {exc}"]
    except Exception as exc:
        return [f"Failed to parse XHTML file: {exc}"]

    # 2. Namespace verification
    root = tree.getroot()
    ns_map = root.nsmap

    ix_ns = None
    for _prefix, uri in ns_map.items():
        if uri in ("http://www.xbrl.org/2013/inlineXBRL", "http://www.xbrl.org/2008/inlineXBRL"):
            ix_ns = uri
            break

    if not ix_ns:
        issues.append(
            "Missing Inline XBRL (iXBRL) namespace declaration. "
            "Expected xmlns:ix='http://www.xbrl.org/2013/inlineXBRL'."
        )
        return issues

    # 3. Find and check all tags
    tags_found = set()
    for elem in tree.xpath("//ix:*", namespaces={"ix": ix_ns}):
        tag_name = elem.get("name")
        if tag_name:
            tags_found.add(tag_name)

    # 4. Check against mandatory tags
    for mandatory in MANDATORY_MICA_TAGS:
        matched = False
        for found in tags_found:
            if found.split(":")[-1].lower() == mandatory.split(":")[-1].lower():
                matched = True
                break
        if not matched:
            issues.append(f"Missing mandatory ESMA metadata tag: '{mandatory}'.")

    return issues
