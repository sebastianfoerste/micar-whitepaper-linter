"""Inline XBRL format checks.

Art. 2 of Implementing Regulation (EU) 2024/2984 requires a single XHTML file whose
fields are marked up in Inline XBRL 1.1 with the elements of ESMA's MiCA taxonomy.
This module checks the format preconditions only. Which facts a white paper must
carry is defined by the existence and value assertions of the taxonomy's formula
linkbase, which is not evaluated here, so a file never passes on this check alone.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

# Inline XBRL 1.1. The 1.0 namespace (2008) does not satisfy Art. 2(1).
IX_NAMESPACE = "http://www.xbrl.org/2013/inlineXBRL"
IX_LEGACY_NAMESPACE = "http://www.xbrl.org/2008/inlineXBRL"
# targetNamespace of mica_cor.xsd in ESMA's "MiCA White Papers Taxonomy 2025",
# the only taxonomy version published when this was checked on 2026-10-09.
ESMA_MICA_NAMESPACE = "https://www.esma.europa.eu/taxonomy/2025-03-31/mica/"

COMPLETENESS_NOTE = (
    "Tag completeness is not checked here. Validate the file against the ESMA MiCA taxonomy "
    "(existence and value assertions of the applicable table) before notification."
)


def validate_ixbrl(path: Path) -> list[str]:
    """Check the Inline XBRL preconditions of an XHTML white paper. Never returns an empty list."""
    try:
        tree = etree.parse(str(path), etree.XMLParser(recover=False))
    except etree.XMLSyntaxError as exc:
        return [f"XHTML is not well-formed XML: {exc}"]
    except Exception as exc:
        return [f"Failed to parse XHTML file: {exc}"]

    declared = {
        uri for element in tree.iter() if isinstance(element.tag, str) for uri in element.nsmap.values()
    }
    if IX_NAMESPACE not in declared:
        if IX_LEGACY_NAMESPACE in declared:
            return [
                "The file declares Inline XBRL 1.0 (2008 namespace). "
                f"Inline XBRL 1.1 is required: xmlns:ix='{IX_NAMESPACE}'."
            ]
        return [f"Missing Inline XBRL (iXBRL) namespace declaration. Expected xmlns:ix='{IX_NAMESPACE}'."]

    issues: list[str] = []
    taxonomy_facts = 0
    other_namespaces: set[str] = set()
    for fact in tree.xpath("//ix:nonNumeric | //ix:nonFraction", namespaces={"ix": IX_NAMESPACE}):
        prefix, _, _ = (fact.get("name") or "").rpartition(":")
        namespace = fact.nsmap.get(prefix or None, "")
        if namespace == ESMA_MICA_NAMESPACE:
            taxonomy_facts += 1
        elif namespace:
            other_namespaces.add(namespace)

    if not taxonomy_facts:
        issues.append(f"No fact is tagged with an element of the ESMA MiCA taxonomy ({ESMA_MICA_NAMESPACE}).")
        if other_namespaces:
            issues.append("Facts use other namespaces: " + ", ".join(sorted(other_namespaces)) + ".")

    issues.append(COMPLETENESS_NOTE)
    return issues
