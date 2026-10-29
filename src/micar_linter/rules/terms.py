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
# issuer for), a contract or wallet address, or the verb ("addresses the risks").
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

# ANNEX_II.D: Art. 39 Abs. 1 MiCAR grants the right of redemption "at all times" ("jederzeit") and calls it
# permanent ("dauerhaft"). "At all times" and "jederzeit" count only beside the redemption, within the same
# sentence and a few words; "permanently" and "auf einem dauerhaften Datenträger" do not count.
PERMANENT_EN = (
    r"(?P<permanent>\bpermanent(?!ly)"
    r"|(?:redemption|redeem\w*)(?:[^\w.;!?]+\w+){0,4}?[^\w.;!?]+at\s+all\s+times"
    r"|at\s+all\s+times(?:[^\w.;!?]+\w+){0,4}?[^\w.;!?]+(?:redemption|redeem))"
)
PERMANENT_DE = (
    r"(?P<dauerhaft>dauerhaft(?!\w*\s+datenträger)"
    r"|jederzeit(?:[^\w.;!?]+\w+){0,5}?[^\w.;!?]+\w*rücktausch"
    r"|rücktausch\w*(?:[^\w.;!?]+\w+){0,5}?[^\w.;!?]+jederzeit)"
)
# ANNEX_II.I: a fee ("Gebühr"), but not "feed", "feedback" or "gebührend"; the suspension as a noun or a verb
# ("temporarily suspend", Art. 46 Abs. 4; "auszusetzen", "ausgesetzt"), but not "Voraussetzung".
FEE_EN = r"(?P<fee>\bfees?\b)"
FEE_DE = r"(?P<gebühr>gebühr(?!end))"
SUSPENSION_EN = r"(?P<suspension>\bsuspen(?:sions?|ds?|ded|ding)\b)"
SUSPENSION_DE = r"(?P<aussetzung>(?<!vor)(?<!vorr)aussetz|ausgesetzt|auszusetzen)"
# ANNEX_II.G.VALUATION_AUDIT: each referenced asset in either word order and any inflection, also as German
# MiCAR words it ("Vermögenswerte, auf die sich der Token bezieht"), but not "asset referenced token"; the
# valuation as a noun or a verb, but not "evaluation", "devaluation" or "our valued holders".
REFERENCED_ASSET_EN = r"(?P<referenced_asset>referenced\s+assets?|assets?\s+referenced(?!\s+tokens?\b))"
REFERENCED_ASSET_DE = (
    r"(?P<referenzierter_vermögenswert>referenziert\w*\s+vermögenswert|referenzvermögenswert"
    r"|vermögenswert\w*,?\s+auf\s+die\s+[^.;]{0,80}?\b(?:bezieh\w*|bezug\s+nehm\w*))"
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
