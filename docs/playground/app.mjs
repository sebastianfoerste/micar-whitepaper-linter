import { MAX_BYTES, REGIMES, formatDraft, parseDraft, reportIsCurrent, sectionSelection, selectFindings } from "./model.mjs";

const $ = id => document.getElementById(id);
const input = $("input");
let worker, timer, ready = false, busy = false, samples;
let report = null, reportText = "", checkedText = "", pendingText = "", requestId = 0;
let filter = "open", modified = false;

function showError(id, message = "") {
  $(id).textContent = message;
  $(id).hidden = !message;
}

function syncDraft() {
  const size = new TextEncoder().encode(input.value).length;
  $("size").textContent = `${(size / 1024).toFixed(1)} KB`;
  try {
    const draft = parseDraft(input.value);
    $("regime").textContent = REGIMES[draft.type.toLowerCase()];
  } catch { $("regime").textContent = "Draft structure needs attention"; }
  const current = reportIsCurrent(report, checkedText, input.value);
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

function replaceDraft(text) {
  if (input.value && modified && !window.confirm("Replace this edited draft? Save a copy first if you need to keep it.")) return;
  input.value = text;
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
    if (!input.value) replaceDraft(JSON.stringify(samples.incomplete, null, 2));
    $("load-example").disabled = false;
    showError("sample-error");
  } catch {
    samples = null;
    $("load-example").disabled = false;
    showError("sample-error", "Examples could not load. Press Load to retry, or import or paste a JSON draft.");
  }
}

$("load-example").onclick = async () => {
  if (!samples) await loadSamples();
  if (samples) replaceDraft(JSON.stringify(samples[$("example").value], null, 2));
};
$("import").onclick = () => $("file").click();
$("file").onchange = async event => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  const before = input.value;
  try {
    if (file.size > MAX_BYTES) throw new Error("The file exceeds the 1 MB playground limit. Use the CLI for larger files.");
    // file.text() would silently swap invalid bytes (e.g. a Windows-1252 export) for U+FFFD.
    let text;
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer()); }
    catch { throw new Error("The file is not valid UTF-8. Save it as UTF-8 JSON and import it again."); }
    parseDraft(text);
    if (input.value !== before) throw new Error("The draft changed while the file was opening. Import the file again when you are ready.");
    replaceDraft(text);
  } catch (error) { showError("input-error", error.message || "The file could not be read. Try a UTF-8 JSON file."); }
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
        checkedText = pendingText;
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
  try { parseDraft(input.value); }
  catch (error) {
    showError("input-error", error.message);
    input.setAttribute("aria-invalid", "true");
    input.focus();
    return;
  }
  input.removeAttribute("aria-invalid");
  busy = true;
  pendingText = input.value;
  requestId += 1;
  syncDraft();
  timer = setTimeout(() => runtimeFailed("The check timed out. Retry the engine and run the checks again."), 30000);
  worker.postMessage({ type: "lint", id: requestId, text: pendingText });
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
  if (!reportIsCurrent(report, checkedText, input.value)) return;
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
    details.open = index === 0;
    const summary = node("summary");
    summary.append(node("span", `badge ${finding.status}`, finding.status === "missing" ? "Missing" : finding.status === "review" ? "Review" : "Pass"));
    const heading = node("div");
    heading.append(node("span", "finding-label", finding.label), node("span", "finding-id", finding.rule_id));
    summary.append(heading);
    const body = node("div", "finding-body");
    body.append(node("p", "citation", finding.citation));
    const issues = node("ul");
    for (const issue of finding.issues) issues.append(node("li", "", issue));
    if (!finding.issues.length) issues.append(node("li", "", "Automated check matched. Verify the disclosure in substance."));
    body.append(issues, node("p", "finding-meta", `${finding.severity} severity · ${finding.word_count} words · ${finding.section}`));
    // iXBRL is a file-format check; adding a JSON section cannot satisfy it.
    if (finding.rule_id !== "COMMON.IXBRL_TAGGING") {
      const source = node("button", "text-button source-button", `Inspect section: ${finding.section} ↗`);
      source.disabled = !reportIsCurrent(report, checkedText, input.value);
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
$("download-draft").onclick = () => download(input.value, "whitepaper-draft.json", "application/json");
$("export-json").onclick = () => {
  if (!busy && reportIsCurrent(report, checkedText, input.value)) download(JSON.stringify(report, null, 2), "micar-review.json", "application/json");
};
$("export-text").onclick = () => {
  if (!busy && reportIsCurrent(report, checkedText, input.value)) download(reportText, "micar-review.txt", "text/plain;charset=utf-8");
};
window.addEventListener("beforeunload", event => {
  if (modified) { event.preventDefault(); event.returnValue = ""; }
});

loadSamples();
startRuntime();
