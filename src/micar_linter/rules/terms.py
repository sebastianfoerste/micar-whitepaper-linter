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
# A postal address, but not the e-mail address every party section gives (template field A.9 of Table 2).
ADDRESS_EN = r"(?P<address>(?<!e-mail )(?<!email )address)"
ADDRESS_DE = r"(?P<anschrift>(?<!e-mail-)anschrift)"
# The offer to the public or the admission to trading, but not "offeror" or "Angebot und Nachfrage".
OFFER_EN = r"(?P<offer>\boffer(?!or)|admission to trading)"
OFFER_DE = r"(?P<angebot>\bangebot(?!\s+und\s+nachfrage)|zulassung zum handel)"

# ANNEX_II.D: Art. 39 Abs. 1 MiCAR grants the right of redemption "at all times" ("jederzeit") and calls it
# permanent ("dauerhaft"), but not "permanently" or "auf einem dauerhaften Datenträger".
PERMANENT_EN = r"(?P<permanent>\bpermanent(?!ly)|at all times)"
PERMANENT_DE = r"(?P<dauerhaft>dauerhaft(?!\w*\s+datenträger)|jederzeit)"
# ANNEX_II.I: a fee ("Gebühr"), but not "feed", "feedback" or "gebührend", and the suspension
# ("Aussetzung"), but not "Voraussetzung".
FEE_EN = r"(?P<fee>\bfees?\b)"
FEE_DE = r"(?P<gebühr>gebühr(?!end))"
SUSPENSION_DE = r"(?P<aussetzung>(?<!vor)aussetz)"
# ANNEX_II.G.VALUATION_AUDIT: each referenced asset in either word order and any inflection, and the
# valuation as a noun or a verb, but not "evaluation".
REFERENCED_ASSET_EN = r"(?P<referenced_asset>referenced assets?|assets? referenced)"
REFERENCED_ASSET_DE = r"(?P<referenzierter_vermögenswert>referenziert\w*\s+vermögenswert)"
VALUATION_EN = r"(?P<valuation>(?<!\be)valuation|\bvalu(?:ed|ing)\b)"
VALUATION_DE = r"(?P<bewertung>bewert)"
# COMMON.MANAGEMENT_STATEMENT: the Title of MiCAR the white paper complies with, as the templates write it
# ("erfüllt Titel II") or as Art. 6 Abs. 6, Art. 19 Abs. 5 and Art. 51 Abs. 5 do ("diesem Titel", "des
# vorliegenden Titels"), but not the white paper's own title ("mit dem Titel").
TITLE_DE = r"(?P<titel_ii_bis_iv>titels?\s+(?:ii|iii|iv)\b|(?:diese[mrs]?|vorliegenden)\s+titels?\b)"
