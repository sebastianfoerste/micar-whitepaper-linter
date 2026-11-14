import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import test from "node:test";
import { MAX_BYTES, MAX_XHTML_BYTES, checksLabel, displayCitation, draftFormat, findingScope, inspectableSection, validateDraft, formatDraft, parseDraft, reportIsCurrent, ruleDocHref, sectionSelection, selectFindings } from "../../docs/playground/model.mjs";

const valid = { type: "art", sections: { summary: "A synthetic draft." } };
const parse = data => parseDraft(JSON.stringify(data));

test("validates the explicit regime and string sections, allowing missing disclosures", () => {
  assert.deepEqual(parse(valid), valid);
  assert.equal(parse({ type: "ART", sections: {} }).type, "ART");
  assert.equal(parse({ type: "other", sections: { summary: "" } }).sections.summary, "");
});

test("rejects malformed JSON, arrays, invalid regimes and ambiguous section values", () => {
  assert.throws(() => parseDraft("{"), /valid JSON/);
  for (const data of [null, [], 3, "draft"]) assert.throws(() => parse(data), /JSON object/);
  for (const type of [undefined, "", "bitcoin", "toString", "__proto__", 1]) {
    assert.throws(() => parse({ ...valid, type }), /Set "type"/);
  }
  for (const sections of [undefined, null, [], "summary"]) assert.throws(() => parse({ ...valid, sections }), /sections/);
  for (const value of [null, [], {}, 42, true]) {
    assert.throws(() => parse({ ...valid, sections: { summary: value } }), /must contain text/);
  }
});

test("applies the size limit to UTF-8 bytes rather than character count", () => {
  assert.throws(() => parseDraft(" ".repeat(MAX_BYTES + 1)), /up to 1 MB/);
  assert.throws(() => parse({ ...valid, sections: { summary: "€".repeat(MAX_BYTES / 2) } }), /up to 1 MB/);
});

const findings = [
  { rule_id: "A", status: "pass", severity: "BLOCKER", label: "Summary", citation: "Article 6", section: "summary", issues: [] },
  { rule_id: "B", status: "missing", severity: "MAJOR", label: "Language", citation: "Article 19", section: "language", issues: ["Missing text"] },
  { rule_id: "C", status: "review", severity: "BLOCKER", label: "Deposit floor", citation: "Article 36", section: "reserve", issues: ["Human review required"] },
  { rule_id: "D", status: "missing", severity: "BLOCKER", label: "Risks", citation: "Article 6", section: "risks", issues: [] },
];

test("prioritises open blockers without mistaking passed blocker rules for open items", () => {
  assert.deepEqual(selectFindings(findings).map(f => f.rule_id), ["D", "C", "B"]);
  assert.deepEqual(selectFindings(findings, "pass").map(f => f.rule_id), ["A"]);
  assert.deepEqual(selectFindings(findings, "all").map(f => f.rule_id), ["D", "C", "B", "A"]);
  assert.deepEqual(findings.map(f => f.rule_id), ["A", "B", "C", "D"]);
});

test("combines search with status and searches citations, issues and section keys", () => {
  assert.deepEqual(selectFindings(findings, "open", "ARTICLE 36").map(f => f.rule_id), ["C"]);
  assert.deepEqual(selectFindings(findings, "review", " human ").map(f => f.rule_id), ["C"]);
  assert.deepEqual(selectFindings(findings, "missing", "reserve"), []);
  assert.deepEqual(selectFindings(findings, "open", "<script>"), []);
});

test("edits made during or after a run invalidate exports until the exact text is restored", () => {
  assert.equal(reportIsCurrent(null, "draft", "draft"), false);
  assert.equal(reportIsCurrent({}, "draft", "changed"), false);
  assert.equal(reportIsCurrent({}, "draft", "draft"), true);
});

const member = (text, { start, end }) => JSON.parse(`{${text.slice(start, end)}}`);

test("section navigation selects the real section, including escaped keys and metadata collisions", () => {
  const draft = { metadata: { sections: { summary: "Fake" } }, type: "art", summary: "Another decoy", sections: { summary: "Real", 'a"b': "Escaped" } };
  for (const text of [JSON.stringify(draft), JSON.stringify(draft, null, 2), JSON.stringify(draft, null, "\t")]) {
    for (const section of ["summary", 'a"b']) {
      assert.deepEqual(member(text, sectionSelection(text, section)), { [section]: draft.sections[section] });
    }
    assert.equal(sectionSelection(text, "absent"), null);
  }
});

test("section navigation works on the draft as written and follows JSON's last-duplicate rule", () => {
  const text = '{ "type":"art","sections" : { "2":"b" , "1":"a", "summary":"old", "summary" :"new" },"supply":12345678901234567890 }';
  assert.deepEqual(member(text, sectionSelection(text, "summary")), { summary: "new" });
  assert.deepEqual(member(text, sectionSelection(text, "1")), { 1: "a" });
  const shadowed = '{"type":"art","sections":{"summary":"ignored"},"sections":{"summary":"used"}}';
  assert.deepEqual(member(shadowed, sectionSelection(shadowed, "summary")), { summary: "used" });
});

test("LEI findings point to no section, wherever the LEI is", () => {
  // As the engine reports them for a draft whose only LEI is in "offeror" and that has no "issuer" section:
  // both LEI rules are anchored to "issuer" with 0 words.
  const text = JSON.stringify({ type: "other", sections: { offeror: "Synthetic Offeror GmbH. LEI: 9999SYNTH0000ZZQ0166." } });
  const lei = ["COMMON.LEI_CHECK_DIGITS", "COMMON.LEI_CONSISTENCY"].map(rule_id => ({ rule_id, status: "pass", section: "issuer", word_count: 0 }));
  assert.equal(sectionSelection(text, "issuer"), null);
  for (const finding of lei) {
    assert.equal(inspectableSection(finding, "json"), null);
    assert.equal(findingScope(finding), "every section");
  }
  // Other rules keep their section; the format gate and XHTML drafts have none to select.
  const summary = { rule_id: "COMMON.SUMMARY", status: "review", section: "summary", word_count: 12 };
  assert.equal(inspectableSection(summary, "json"), "summary");
  assert.equal(findingScope(summary), "summary");
  assert.equal(inspectableSection(summary, "xhtml"), null);
  assert.equal(inspectableSection({ rule_id: "COMMON.IXBRL_TAGGING", status: "missing", section: "ixbrl_tagging", word_count: 0 }, "json"), null);
});

test("formatting changes whitespace only", () => {
  const samples = JSON.parse(readFileSync(new URL("../../docs/playground/samples.json", import.meta.url), "utf8"));
  for (const sample of Object.values(samples)) {
    const pretty = JSON.stringify(sample, null, 2);
    assert.equal(formatDraft(JSON.stringify(sample)), pretty);
    assert.equal(formatDraft(pretty), pretty);
  }
  const raw = '{"type":"art","sections":{"2":"b","1":"a","s":"caf\\u00e9 [x], {y}: \\"z\\""},"supply":12345678901234567890,"big":1e400,"price":1.0,"list":[],"meta":{}}';
  assert.equal(formatDraft(raw), [
    "{",
    '  "type": "art",',
    '  "sections": {',
    '    "2": "b",',
    '    "1": "a",',
    '    "s": "caf\\u00e9 [x], {y}: \\"z\\""',
    "  },",
    '  "supply": 12345678901234567890,',
    '  "big": 1e400,',
    '  "price": 1.0,',
    '  "list": [],',
    '  "meta": {}',
    "}",
  ].join("\n"));
  assert.throws(() => formatDraft("{"), /valid JSON/);
});

const repoFile = path => readFileSync(new URL(`../../${path}`, import.meta.url), "utf8");

test("a draft that opens with markup is XHTML and states no regime of its own", () => {
  const xhtml = repoFile("docs/playground/sample-numbered.xhtml");
  assert.equal(draftFormat(xhtml), "xhtml");
  assert.equal(draftFormat(`\n  ${xhtml}`), "xhtml");
  assert.deepEqual(validateDraft(xhtml), { format: "xhtml", regime: null });
  assert.equal(draftFormat(JSON.stringify(valid)), "json");
  assert.deepEqual(validateDraft(JSON.stringify({ ...valid, type: "ART" })), { format: "json", regime: "art" });
  assert.throws(() => validateDraft("not a draft"), /valid JSON/);
  assert.deepEqual(validateDraft(`<html>${" ".repeat(6 * 1024 * 1024)}</html>`), { format: "xhtml", regime: null });
  assert.throws(() => validateDraft(`<html>${" ".repeat(MAX_XHTML_BYTES)}</html>`), /up to 8 MB/);
});

test("findings show the engine's English citation, and both forms are searchable", () => {
  // The JSON report carries the canonical citation and, in citation_en, the English EU form the CLI prints.
  const finding = {
    rule_id: "S", status: "review", severity: "BLOCKER", label: "Summary", section: "summary", issues: [],
    citation: "Art. 6 Abs. 7, Art. 19 Abs. 6, Art. 51 Abs. 6 MiCAR",
    citation_en: "Art. 6(7), Art. 19(6), Art. 51(6) MiCAR",
  };
  assert.equal(displayCitation(finding), "Art. 6(7), Art. 19(6), Art. 51(6) MiCAR");
  assert.deepEqual(selectFindings([finding], "open", "art. 19(6)").map(f => f.rule_id), ["S"]);
  assert.deepEqual(selectFindings([finding], "open", "19 Abs. 6").map(f => f.rule_id), ["S"]);
  // Display only: the finding, which the exports write, keeps both strings unchanged.
  assert.equal(finding.citation, "Art. 6 Abs. 7, Art. 19 Abs. 6, Art. 51 Abs. 6 MiCAR");
});

test("a finding without an English citation shows the canonical one", () => {
  assert.equal(displayCitation({ citation: "Art. 6 Abs. 7 MiCAR" }), "Art. 6 Abs. 7 MiCAR");
  assert.equal(displayCitation({ citation: "Art. 6 Abs. 7 MiCAR", citation_en: null }), "Art. 6 Abs. 7 MiCAR");
});

const decode = text => text.replaceAll("&quot;", '"').replaceAll("&#x27;", "'").replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&");

test("display citations never alter a pinpoint", () => {
  // Each rule page states the English citation and the canonical form, both from the rule (citations.to_english,
  // which also fills citation_en in the JSON report). "UAbs. 1" becomes "first subparagraph", so its digit is
  // spelled out, as tests/test_citations.py allows.
  const pages = readdirSync(new URL("../../docs/rules/", import.meta.url)).filter(name => name !== "index.html");
  assert.ok(pages.length >= 42);
  for (const name of pages) {
    const page = repoFile(`docs/rules/${name}`);
    const english = decode(page.match(/<dt>Citation<\/dt><dd>([^<]+)<\/dd>/)[1]);
    const canonical = decode(page.match(/<dt>Canonical form<\/dt><dd lang="de">([^<]+)<\/dd>/)[1]);
    const shown = displayCitation({ citation: canonical, citation_en: english });
    assert.equal(shown, english, name);
    assert.deepEqual(shown.match(/\d+/g), canonical.replace(/UAbs\. \d/g, "").match(/\d+/g), name);
  }
});

test("the evidence note states the committed study figures", () => {
  const study = "studies/2026-07-title-ii-annex-i-whitepaper-study";
  const findings = JSON.parse(repoFile(`${study}/findings-pseudonymous.json`));
  const review = JSON.parse(repoFile(`${study}/human-review-summary.json`));
  const page = repoFile("docs/playground/index.html");
  const stated = id => Number(page.match(new RegExp(`id="basis-${id}">(\\d+)<`))[1]);
  assert.equal(stated("documents"), findings.summary.documents_reviewed);
  assert.equal(stated("controls"), findings.summary.rules_checked_per_document);
  assert.equal(stated("cells"), review.rows_total);
  assert.equal(stated("reviewed"), review.rows_completed);
  assert.equal(Object.keys(JSON.parse(repoFile("docs/playground/samples.json"))).length, 4);
});

test("links a finding to its rule page beside the playground", () => {
  const page = "https://example.test/micar-whitepaper-linter/playground/";
  assert.equal(ruleDocHref("ANNEX_II.G.DEPOSIT_FLOOR_REVIEW", page),
    "https://example.test/micar-whitepaper-linter/rules/ANNEX_II.G.DEPOSIT_FLOOR_REVIEW.html");
  assert.equal(ruleDocHref("COMMON.SUMMARY", page + "index.html"),
    "https://example.test/micar-whitepaper-linter/rules/COMMON.SUMMARY.html");
  assert.equal(ruleDocHref("A/B?#", page), "https://example.test/micar-whitepaper-linter/rules/A%2FB%3F%23.html");
});

test("counts the field-level checks that did not run apart from the findings", () => {
  // A JSON draft has no field numbers: those rules have no finding and are named under not_run only.
  assert.equal(checksLabel({ summary: { total: 21 }, not_run: ["ANNEX_II.A.P1", "ITS.CODE_LISTS"] }),
    "21 checks · 2 field-level checks not run");
  assert.equal(checksLabel({ summary: { total: 99 }, not_run: [] }), "99 checks");
  assert.equal(checksLabel({ summary: { total: 1 } }), "1 check");
  assert.equal(checksLabel({ summary: { total: 5 }, not_run: ["ITS.CODE_LISTS"] }), "5 checks · 1 field-level check not run");
});
