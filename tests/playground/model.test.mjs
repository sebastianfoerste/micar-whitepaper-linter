import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { MAX_BYTES, formatDraft, parseDraft, reportIsCurrent, sectionSelection, selectFindings } from "../../docs/playground/model.mjs";

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
