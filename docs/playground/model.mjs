// Pure input and report helpers shared with the browser regression tests.
export const MAX_BYTES = 1024 * 1024;
export const REGIMES = {
  other: "Annex I · Other crypto-assets",
  art: "Annex II · Asset-referenced tokens",
  emt: "Annex III · E-money tokens",
};

export function parseDraft(text) {
  if (new TextEncoder().encode(text).length > MAX_BYTES) {
    throw new Error("This playground accepts JSON drafts up to 1 MB. Use the CLI for larger files.");
  }
  let draft;
  try { draft = JSON.parse(text); }
  catch { throw new Error("The draft is not valid JSON. Check quotation marks, commas and brackets."); }
  if (!draft || typeof draft !== "object" || Array.isArray(draft)) {
    throw new Error("The draft must be a JSON object. Load an example to see the structure.");
  }
  if (typeof draft.type !== "string" || !Object.hasOwn(REGIMES, draft.type.toLowerCase())) {
    throw new Error('Set "type" to "other", "art" or "emt" to select the checks explicitly.');
  }
  if (!draft.sections || typeof draft.sections !== "object" || Array.isArray(draft.sections)) {
    throw new Error('Add a "sections" object containing section names and their text.');
  }
  for (const [key, value] of Object.entries(draft.sections)) {
    if (typeof value !== "string") {
      throw new Error(`Section "${key}" must contain text. Use an empty string for a missing disclosure.`);
    }
  }
  return draft;
}

export function selectFindings(findings, filter = "open", search = "") {
  const query = search.trim().toLowerCase();
  const statusOrder = { missing: 0, review: 1, pass: 2 };
  return findings.filter(f => {
    const matches = filter === "all" || (filter === "open" ? f.status !== "pass" : f.status === filter);
    return matches && [f.rule_id, f.label, f.citation, f.section, f.severity, ...f.issues]
      .join(" ").toLowerCase().includes(query);
  }).sort((a, b) => {
    const aBlocker = a.status !== "pass" && a.severity === "BLOCKER";
    const bBlocker = b.status !== "pass" && b.severity === "BLOCKER";
    return Number(bBlocker) - Number(aBlocker) || statusOrder[a.status] - statusOrder[b.status];
  });
}

export function reportIsCurrent(report, checkedText, currentText) {
  return Boolean(report) && checkedText === currentText;
}

// The scanners below walk the draft's own characters. Round-tripping through
// JSON.parse/JSON.stringify would round integers above 2^53, move integer-like
// keys to the front and drop duplicate keys, none of which Python's json does.
// Callers validate with parseDraft first, so the text is well-formed JSON.
const WHITESPACE = " \t\n\r";

function skipWhitespace(text, i) {
  while (i < text.length && WHITESPACE.includes(text[i])) i += 1;
  return i;
}

function stringEnd(text, i) {
  for (i += 1; text[i] !== '"'; i += 1) if (text[i] === "\\") i += 1;
  return i + 1;
}

function valueEnd(text, i) {
  if (text[i] === '"') return stringEnd(text, i);
  if (text[i] === "{" || text[i] === "[") {
    for (let depth = 0; ; i += 1) {
      if (text[i] === '"') i = stringEnd(text, i) - 1;
      else if (text[i] === "{" || text[i] === "[") depth += 1;
      else if ((text[i] === "}" || text[i] === "]") && --depth === 0) return i + 1;
    }
  }
  while (i < text.length && !(WHITESPACE + ",}]").includes(text[i])) i += 1;
  return i;
}

function objectMembers(text, i) {
  const members = [];
  for (i = skipWhitespace(text, i + 1); text[i] === '"';) {
    const keyEnd = stringEnd(text, i);
    const valueStart = skipWhitespace(text, skipWhitespace(text, keyEnd) + 1);
    const end = valueEnd(text, valueStart);
    members.push({ key: JSON.parse(text.slice(i, keyEnd)), start: i, valueStart, end });
    i = skipWhitespace(text, end);
    if (text[i] === ",") i = skipWhitespace(text, i + 1);
  }
  return members;
}

export function formatDraft(text) {
  parseDraft(text);
  let out = "", depth = 0;
  const newline = () => "\n" + "  ".repeat(depth);
  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (char === '"') {
      const end = stringEnd(text, i);
      out += text.slice(i, end);
      i = end - 1;
    } else if (char === "{" || char === "[") {
      const next = skipWhitespace(text, i + 1);
      if (text[next] === (char === "{" ? "}" : "]")) { out += char + text[next]; i = next; }
      else { depth += 1; out += char + newline(); }
    } else if (char === "}" || char === "]") { depth -= 1; out += newline() + char; }
    else if (char === ",") out += "," + newline();
    else if (char === ":") out += ": ";
    else if (!WHITESPACE.includes(char)) out += char;
  }
  return out;
}

export function sectionSelection(text, section) {
  const draft = parseDraft(text);
  if (!Object.hasOwn(draft.sections, section)) return null;
  // JSON.parse and Python's json both keep the last duplicate key, so select the last match.
  const sections = objectMembers(text, skipWhitespace(text, 0)).findLast(member => member.key === "sections");
  const member = objectMembers(text, sections.valueStart).findLast(item => item.key === section);
  return { start: member.start, end: member.end };
}
