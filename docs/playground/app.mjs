import { FORMATS, MAX_BYTES, MAX_XHTML_BYTES, REGIMES, displayCitation, draftFormat, formatDraft, parseDraft, reportIsCurrent,
  ruleDocHref, sectionSelection, selectFindings, validateDraft } from "./model.mjs";

const $ = id => document.getElementById(id);
const input = $("input");
let worker, timer, ready = false, busy = false, samples, markupReady = false;
let report = null, reportText = "", checkedKey = "", checkedFormat = "json", pendingKey = "", pendingFormat = "json", requestId = 0;
let filter = "open", modified = false, expanded = false, draftName = "";

// An XHTML draft is checked under the regime the user chose, so the choice is part of what was checked.
const chosenRegime = () => draftFormat(input.value) === "xhtml" ? $("regime-select").value : "";
const draftKey = () => `${chosenRegime()}\n${input.value}`;
const isCurrent = () => reportIsCurrent(report, checkedKey, draftKey());

function showError(id, message = "") {
  $(id).textContent = message;
  $(id).hidden = !message;
}

function syncDraft() {
  const size = new TextEncoder().encode(input.value).length;
  $("size").textContent = `${(size / 1024).toFixed(1)} KB`;
  const format = draftFormat(input.value);
  $("format-badge").textContent = FORMATS[format];
  $("regime-row").hidden = format !== "xhtml";
  $("format").disabled = format !== "json";
  try {
    const draft = validateDraft(input.value);
    $("regime").textContent = REGIMES[draft.regime ?? chosenRegime()] ?? "Choose the regime of this file";
  } catch { $("regime").textContent = "Draft structure needs attention"; }
  const current = isCurrent();
  $("stale").hidden = !report || current;
  $("export-json").disabled = !current || busy;
  $("export-text").disabled = !current || busy;
  $("lint").disabled = !ready || busy;
  $("lint").firstChild.textContent = busy ? "Checking… " : "Run checks ";
  $("result-state").textContent = busy ? "Checking draft" : report ? (current ? "Checks complete" : "Draft changed") : "Awaiting checks";
  document.querySelector(".results-panel").setAttribute("aria-busy", String(busy));
  document.querySelectorAll(".source-button").forEach(button => { button.disabled = !current; });
}

input.addEventListener("input", () => {
  modified = true;
  showError("input-error");
  showError("run-error");
  input.removeAttribute("aria-invalid");
  syncDraft();
});

function replaceDraft(text, name = "", regime = "") {
  if (input.value && modified && !window.confirm("Replace this edited draft? Save a copy first if you need to keep it.")) return;
  input.value = text;
  draftName = name;
  $("regime-select").value = regime;
  modified = false;
  showError("input-error");
  showError("sample-error");
  showError("run-error");
  input.removeAttribute("aria-invalid");
  syncDraft();
}

async function loadSamples() {
  try {
    const response = await fetch("samples.json");
    if (!response.ok) throw new Error();
    samples = await response.json();
    for (const key of ["incomplete", "other", "art", "emt"]) parseDraft(JSON.stringify(samples[key]));
    const markup = await fetch("sample-numbered.xhtml");
    if (!markup.ok) throw new Error();
    samples.numbered = await markup.text();
    if (!input.value) replaceDraft(JSON.stringify(samples.incomplete, null, 2));
    $("load-example").disabled = false;
    showError("sample-error");
  } catch {
    samples = null;
    $("load-example").disabled = false;
    showError("sample-error", "Examples could not load. Press Load to retry, or import or paste a draft.");
  }
}

$("load-example").onclick = async () => {
  if (!samples) await loadSamples();
  if (!samples) return;
  const sample = samples[$("example").value];
  if (typeof sample === "string") replaceDraft(sample, "synthetic-numbered-draft.xhtml", "other");
  else replaceDraft(JSON.stringify(sample, null, 2));
};
$("regime-select").onchange = () => { showError("input-error"); syncDraft(); };
$("import").onclick = () => $("file").click();
$("file").onchange = async event => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  const before = input.value;
  try {
    const markup = /\.(xhtml|html?)$/i.test(file.name);
    if (file.size > (markup ? MAX_XHTML_BYTES : MAX_BYTES)) {
      throw new Error(`The file exceeds the ${markup ? `${MAX_XHTML_BYTES / 1024 / 1024} MB XHTML` : "1 MB JSON"} playground limit. Use the CLI for larger files.`);
    }
    // file.text() would silently swap invalid bytes (e.g. a Windows-1252 export) for U+FFFD.
    let text;
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()); }
    catch { throw new Error("The file is not valid UTF-8. Save it as UTF-8 and import it again."); }
    if (validateDraft(text).format !== (markup ? "xhtml" : "json")) throw new Error("The file content does not match its extension.");
    if (input.value !== before) throw new Error("The draft changed while the file was opening. Import the file again when you are ready.");
    replaceDraft(text, file.name);
  } catch (error) { showError("input-error", error.message || "The file could not be read. Try a UTF-8 JSON or XHTML file."); }
};

$("format").onclick = () => {
  try {
    const formatted = formatDraft(input.value);
    if (formatted !== input.value) {
      input.value = formatted;
      modified = true;
    }
    showError("input-error");
    input.removeAttribute("aria-invalid");
    syncDraft();
  } catch (error) { showError("input-error", error.message); }
};

function runtimeFailed(message) {
  clearTimeout(timer);
  worker?.terminate();
  ready = false;
  busy = false;
  $("status").textContent = message;
  $("status-dot").className = "status-dot error";
  $("retry").hidden = false;
  syncDraft();
}

function startRuntime() {
  worker?.terminate();
  clearTimeout(timer);
  ready = false;
  busy = false;
  markupReady = false;
  $("retry").hidden = true;
  $("status-dot").className = "status-dot";
  $("status").textContent = "Loading Python runtime…";
  syncDraft();
  try {
    const instance = new Worker(new URL("runtime.mjs", import.meta.url), { type: "module" });
    worker = instance;
    timer = setTimeout(() => runtimeFailed("Loading timed out. Check your connection and retry; your draft is still here."), 90000);
    instance.onerror = event => {
      event.preventDefault();
      if (worker === instance) runtimeFailed("The rule engine stopped. Retry to reload it; your draft is still here.");
    };
    instance.onmessage = ({ data }) => {
      if (worker !== instance) return;
      if (data.type === "progress") $("status").textContent = data.text;
      if (data.type === "ready") {
        clearTimeout(timer);
        ready = true;
        $("status").textContent = "Ready. Checks run locally in your browser.";
        $("status-dot").className = "status-dot ready";
        syncDraft();
      }
      if (data.type === "error") {
        if (data.id === undefined) runtimeFailed(data.text);
        else if (data.id === requestId) {
          clearTimeout(timer);
          busy = false;
          showError("run-error", data.text);
          syncDraft();
        }
      }
      if (data.type === "result" && data.id === requestId) {
        clearTimeout(timer);
        busy = false;
        report = data.report;
        reportText = data.text;
        checkedKey = pendingKey;
        checkedFormat = pendingFormat;
        markupReady ||= pendingFormat === "xhtml";
        renderReport();
        syncDraft();
      }
    };
    const wheelName = document.querySelector("script[data-wheel]").dataset.wheel;
    instance.postMessage({ type: "init", wheelUrl: new URL(wheelName, location.href).href });
  } catch { runtimeFailed("This browser could not start the rule engine. Enable web workers and retry, or use the CLI."); }
}

function runChecks() {
  if (!ready || busy) return;
  showError("input-error");
  showError("run-error");
  let draft;
  try { draft = validateDraft(input.value); }
  catch (error) {
    showError("input-error", error.message);
    input.setAttribute("aria-invalid", "true");
    input.focus();
    return;
  }
  input.removeAttribute("aria-invalid");
  if (draft.format === "xhtml" && !chosenRegime()) {
    showError("input-error", "Choose the regime of this XHTML file. It is not inferred from the text.");
    $("regime-select").focus();
    return;
  }
  busy = true;
  pendingKey = draftKey();
  pendingFormat = draft.format;
  requestId += 1;
  syncDraft();
  // The first XHTML check also downloads the XML parser; an 8 MB XHTML draft can take tens of seconds on a slow device.
  timer = setTimeout(() => runtimeFailed("The check timed out. Retry the engine and run the checks again."),
    draft.format === "xhtml" ? (markupReady ? 60000 : 120000) : 30000);
  worker.postMessage({ type: "lint", id: requestId, text: input.value, format: draft.format, regime: chosenRegime(), name: draftName });
}
$("lint").onclick = runChecks;
$("retry").onclick = startRuntime;
input.addEventListener("keydown", event => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault(); runChecks(); }
});

function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function renderReport() {
  $("empty").hidden = true;
  $("results").hidden = false;
  $("report-title").textContent = report.title;
  $("report-regime").textContent = `${REGIMES[report.whitepaper_type]} · ${report.summary.total} checks`;
  for (const key of ["blockers", "missing", "review", "pass"]) $("count-" + key).textContent = report.summary[key];
  $("review-boundary").textContent = report.summary.blockers
    ? "Open blockers require attention. Substantive lawyer review is required before any filing decision."
    : "No open blockers detected. Substantive lawyer review is still required.";
  $("warnings").replaceChildren(...report.warnings.map(warning => node("p", "", warning)));
  $("warnings").hidden = !report.warnings.length;
  renderFindings();
}

// Long section texts wrap, so a line count misses the target. Lay out a hidden
// copy of the textarea's text up to the offset and read where it ends.
function wrappedOffset(textarea, index) {
  const style = getComputedStyle(textarea);
  const mirror = node("div");
  for (const property of ["fontFamily", "fontSize", "fontStyle", "fontWeight", "lineHeight", "letterSpacing", "wordSpacing", "tabSize",
    "paddingTop", "paddingRight", "paddingBottom", "paddingLeft"]) mirror.style[property] = style[property];
  Object.assign(mirror.style, { position: "absolute", top: "0", left: "0", visibility: "hidden", boxSizing: "border-box",
    width: `${textarea.clientWidth}px`, whiteSpace: "pre-wrap", overflowWrap: "break-word" });
  const marker = node("span", "", "​");
  mirror.append(textarea.value.slice(0, index), marker);
  document.body.append(mirror);
  const offset = marker.offsetTop;
  mirror.remove();
  return offset;
}

// Selects the section in the draft as written; only a worker result may mark text as checked.
function locateSection(section) {
  if (!isCurrent()) return;
  const selection = sectionSelection(input.value, section);
  if (!selection) {
    showError("input-error", `Section "${section}" is absent. Add it inside the sections object.`);
    input.focus();
    return;
  }
  input.focus();
  input.setSelectionRange(selection.start, selection.end);
  input.scrollTop = Math.max(0, wrappedOffset(input, selection.start) - input.clientHeight / 3);
  input.scrollIntoView({ block: "center", behavior: "instant" });
  showError("input-error");
}

function renderFindings() {
  if (!report) return;
  const findings = selectFindings(report.findings, filter, $("search").value);
  const container = $("findings");
  container.replaceChildren();
  $("visible-count").textContent = `${findings.length} of ${report.summary.total} findings · open blockers first`;
  if (!findings.length) container.append(node("p", "no-findings", "No findings match this view. Try another filter or search."));
  findings.forEach((finding, index) => {
    const details = node("details", "finding");
    details.open = expanded || index === 0;
    const summary = node("summary");
    summary.append(node("span", `badge ${finding.status}`, finding.status === "missing" ? "Missing" : finding.status === "review" ? "Review" : "Pass"));
    const heading = node("div");
    // The citation sits in the collapsed row so the legal basis can be scanned without opening each finding.
    heading.append(node("span", "finding-label", finding.label), node("span", "finding-citation", displayCitation(finding.citation)),
      node("span", "finding-id", finding.rule_id));
    summary.append(heading);
    const body = node("div", "finding-body");
    const issues = node("ul");
    for (const issue of finding.issues) issues.append(node("li", "", issue));
    if (!finding.issues.length) issues.append(node("li", "", "Automated check matched. Verify the disclosure in substance."));
    body.append(issues, node("p", "finding-meta", `${finding.severity} severity · ${finding.word_count} words · ${finding.section}`));
    // A new tab keeps the draft in this one; rule pages are static and load nothing else.
    const rulePage = node("a", "rule-link", `How ${finding.rule_id} is checked `);
    const arrow = node("span", "", "↗");
    arrow.setAttribute("aria-hidden", "true");
    rulePage.append(arrow, node("span", "sr-only", " (opens in a new tab)"));
    rulePage.href = ruleDocHref(finding.rule_id, location.href);
    rulePage.target = "_blank";
    rulePage.rel = "noopener";
    body.append(rulePage);
    // iXBRL is a file-format check; adding a JSON section cannot satisfy it.
    // Section navigation reads JSON keys; an XHTML draft has none to select.
    if (finding.rule_id !== "COMMON.IXBRL_TAGGING" && checkedFormat === "json") {
      const source = node("button", "text-button source-button", `Inspect section: ${finding.section} ↗`);
      source.disabled = !isCurrent();
      source.onclick = () => locateSection(finding.section);
      body.append(source);
    }
    details.append(summary, body);
    container.append(details);
  });
}

document.querySelectorAll("[data-filter]").forEach(button => {
  button.onclick = () => {
    filter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
    renderFindings();
  };
});
$("search").oninput = renderFindings;
$("toggle-all").onclick = () => {
  expanded = !expanded;
  $("toggle-all").textContent = expanded ? "Collapse all" : "Expand all";
  $("toggle-all").setAttribute("aria-pressed", String(expanded));
  renderFindings();
};

function download(text, filename, type) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const link = node("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
$("download-draft").onclick = () => draftFormat(input.value) === "xhtml"
  ? download(input.value, "whitepaper-draft.xhtml", "application/xhtml+xml")
  : download(input.value, "whitepaper-draft.json", "application/json");
$("export-json").onclick = () => {
  if (!busy && isCurrent()) download(JSON.stringify(report, null, 2), "micar-review.json", "application/json");
};
$("export-text").onclick = () => {
  if (!busy && isCurrent()) download(reportText, "micar-review.txt", "text/plain;charset=utf-8");
};
window.addEventListener("beforeunload", event => {
  if (modified) { event.preventDefault(); event.returnValue = ""; }
});

loadSamples();
startRuntime();
