"""Inline XBRL format checks.

Art. 2 of Implementing Regulation (EU) 2024/2984 requires a single XHTML file whose
fields are marked up in Inline XBRL 1.1 with the elements of ESMA's MiCA taxonomy.
This module checks the format preconditions only. Which facts a white paper must
carry is defined by the existence and value assertions of the taxonomy's formula
linkbase, which is not evaluated here, so a file never passes on this check alone.
"""

from __future__ import annotations

import re
from pathlib import Path

from lxml import etree

# Inline XBRL 1.1. The 1.0 namespace (2008) does not satisfy Art. 2(1).
IX_NAMESPACE = "http://www.xbrl.org/2013/inlineXBRL"
IX_LEGACY_NAMESPACE = "http://www.xbrl.org/2008/inlineXBRL"
# targetNamespace of mica_cor.xsd in ESMA's "MiCA White Papers Taxonomy 2025",
# the only taxonomy version published when this was checked on 2026-10-09. In the package
# published on 5 August 2025 (mica_taxonomy_2025.zip, read on 2026-10-31) mica_cor.xsd declares
# every fact concept (719 xbrli:item elements); the entry-point schemas of Tables 2 to 4
# (targetNamespaces .../mica/table2, table3, table4) and mica_all.xsd (.../mica/all) declare no
# element and import the core, so a fact named in an entry-point namespace is no taxonomy fact.
ESMA_MICA_NAMESPACE = "https://www.esma.europa.eu/taxonomy/2025-03-31/mica/"
# The taxonomy versions this module knows. On 2026-11-10 the ESMA MiCA page and the document page of the
# 2025 taxonomy still linked mica_taxonomy_2025.zip only, so 2025-03-31 was the newest version.
KNOWN_MICA_NAMESPACES = (ESMA_MICA_NAMESPACE,)
# Section 3.5.1 of ESMA's taxonomy documentation (ESMA65-955014868-14829, July 2025): "Taxonomy releases
# will be distinguished using a date component on the root folder and in the taxonomy namespace". A fact in
# a namespace of that shape with another date is tagged with a release this module has not read; it is
# named as such instead of as an untagged file, and the gate still does not pass.
_DATED_MICA_NAMESPACE = re.compile(r"https://www\.esma\.europa\.eu/taxonomy/(\d{4}-\d{2}-\d{2})/mica/?")

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
    unknown_versions: set[str] = set()
    other_namespaces: set[str] = set()
    for fact in tree.xpath("//ix:nonNumeric | //ix:nonFraction", namespaces={"ix": IX_NAMESPACE}):
        prefix, _, _ = (fact.get("name") or "").rpartition(":")
        namespace = fact.nsmap.get(prefix or None, "")
        dated = _DATED_MICA_NAMESPACE.fullmatch(namespace)
        if namespace in KNOWN_MICA_NAMESPACES:
            taxonomy_facts += 1
        elif dated:
            unknown_versions.add(dated.group(1))
        elif namespace:
            other_namespaces.add(namespace)

    if unknown_versions:
        issues.append(
            "Facts are tagged with an ESMA MiCA taxonomy version this linter does not know ("
            + ", ".join(sorted(unknown_versions))
            + f"; it knows {', '.join(KNOWN_MICA_NAMESPACES)}). Check that ESMA has published that version "
            "and validate the file against it."
        )
    if not taxonomy_facts and not unknown_versions:
        issues.append(f"No fact is tagged with an element of the ESMA MiCA taxonomy ({ESMA_MICA_NAMESPACE}).")
    if not taxonomy_facts and other_namespaces:
        issues.append("Facts use other namespaces: " + ", ".join(sorted(other_namespaces)) + ".")

    issues.append(COMPLETENESS_NOTE)
    return issues
