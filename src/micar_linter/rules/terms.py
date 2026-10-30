"""Listed terms that a plain substring would also find inside other words.

Each pattern has one named group, the term that linter.py reports as missing when the pattern does not
match (underscores read as spaces). Each pattern matches its own group name, which is how the rule pages
build their passing examples (tests/test_rules.py checks this). A rule that gives English drafts a pattern
also gives German drafts their own pattern list, because without one they are checked against the English
patterns.
"""

from __future__ import annotations

# The competent court ("Gericht"), but not "gerichtet", "ausgerichtet" or "eingerichtet".
COURT_DE = r"(?P<gericht>gericht(?!et))"
# A postal address, but not an e-mail address (as Table 2 field A.9 and Table 4 field A.10 ask the offeror or
# issuer for), a contract or wallet address, or the verb before "the", "this", "risks" and similar objects
# ("addresses the risks").
ADDRESS_EN = (
    r"(?P<address>(?<!e-mail[ -])(?<!email[ -])(?<!contract )(?<!wallet )\baddress(?:es)?\b"
    r"(?!\s+(?:the|this|these|those|risks?|issues?)\b))"
)
ADDRESS_DE = r"(?P<anschrift>(?<!e-mail-)(?<!e-mail )anschrift)"
# The offer to the public or the admission to trading, but not "offeror", "offer and demand" or "Angebot und
# Nachfrage".
OFFER_EN = (
    r"(?P<offer_or_admission_to_trading>\boffer(?!or)(?!\s+and\s+demand)"
    r"|admission\s+(?:of\s+(?:[\w-]+\s+){1,3})?to\s+trading)"
)
OFFER_DE = (
    r"(?P<angebot_oder_zulassung_zum_handel>\bangebot(?!\s+und\s+nachfrage)"
    r"|zulassung\s+(?:[\w-]+\s+){0,3}zum\s+handel)"
)

# ANNEX_II.D: Art. 39 Abs. 1 MiCAR and Anhang II Teil D Nr. 9 call the right of redemption permanent
# ("dauerhaft"); "permanently" and "auf einem dauerhaften Datenträger" do not count. "At all times" and
# "jederzeit" do not count either: they also describe the reserve, the policy or complaints.
PERMANENT_EN = r"(?P<permanent>\bpermanent(?!ly))"
PERMANENT_DE = r"(?P<dauerhaft>dauerhaft(?!\w*\s+datenträger))"
# ANNEX_II.I: a fee ("Gebühr"), but not "feed", "feedback" or "gebührend"; the suspension as a noun
# ("Aussetzung"), but not "Voraussetzung". The verbs ("ausgesetzt") also mean "exposed to" a risk.
FEE_EN = r"(?P<fee>\bfees?\b)"
FEE_DE = r"(?P<gebühr>gebühr(?!end))"
SUSPENSION_DE = r"(?P<aussetzung>(?<!vor)(?<!vorr)aussetzung)"
# ANNEX_II.G.VALUATION_AUDIT: each referenced asset in either word order and any inflection, also in the
# relative clauses of German MiCAR ("Vermögenswerte, auf die die vermögenswertereferenzierten Token Bezug
# nehmen", Art. 39 Abs. 2; "auf die sich der vermögenswertereferenzierte Token bezieht", Art. 38 Abs. 5
# Buchst. b), but not "asset referenced token" or the "Vermögenswertreserve"; the valuation as a noun or a
# verb, but not "evaluation", "devaluation" or "our valued holders".
REFERENCED_ASSET_EN = r"(?P<referenced_asset>referenced\s+assets?|assets?\s+referenced(?!\s+tokens?\b))"
REFERENCED_ASSET_DE = (
    r"(?P<referenzierter_vermögenswert>referenziert\w*\s+vermögenswert|referenzvermögenswert"
    r"|vermögenswert(?:e|es|s|en)?\b,?\s+auf\s+d(?:ie|en)\s+[^.;]{0,80}?\b"
    r"(?:bezieh\w*|bezug\s+(?:nehm\w*|nimmt|genommen)))"
)
VALUATION_EN = (
    r"(?P<valuation>(?<![a-z])(?:re)?valuation|\bvaluing\b|\b(?:is|are|was|were|be|been|being)\s+valued\b"
    r"|\bvalued\s+(?:at|on|by|daily|weekly|monthly|using|according|in)\b)"
)
VALUATION_DE = r"(?P<bewertung>bewert)"
# COMMON.MANAGEMENT_STATEMENT: the Title of MiCAR the white paper complies with, as the templates write it
# ("erfüllt Titel II") or as Art. 6 Abs. 6, Art. 19 Abs. 5 and Art. 51 Abs. 5 do ("diesem Titel", "des
# vorliegenden Titels"), but not the white paper's own title ("mit dem Titel"). The pattern does not check
# that the Title fits the regime (II, III or IV).
TITLE_DE = r"(?P<titel_ii_iii_oder_iv>titels?\s+(?:ii|iii|iv)\b|(?:diese[mrs]?|vorliegenden)\s+titels?\b)"
