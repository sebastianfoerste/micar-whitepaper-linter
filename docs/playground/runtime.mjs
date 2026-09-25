// Python runs off the UI thread. Only static code/packages are fetched.
let pyodide;
const progress = text => self.postMessage({ type: "progress", text });

self.onmessage = async ({ data }) => {
  try {
    if (data.type === "init") {
      progress("Loading Python runtime…");
      const { loadPyodide } = await import("https://cdn.jsdelivr.net/pyodide/v0.28.2/full/pyodide.mjs");
      pyodide = await loadPyodide();
      progress("Loading the rule engine…");
      await pyodide.loadPackage("micropip");
      pyodide.globals.set("wheel_url", data.wheelUrl);
      // lxml and pypdf serve the PDF/XHTML loaders only; the JSON path never imports them.
      await pyodide.runPythonAsync("import micropip\nawait micropip.install(wheel_url, deps=False)");
      const response = await fetch(new URL("lint.py", import.meta.url));
      if (!response.ok) throw new Error("The browser bridge could not be loaded.");
      await pyodide.runPythonAsync(await response.text());
      self.postMessage({ type: "ready" });
    } else if (data.type === "lint") {
      pyodide.globals.set("draft_text", data.text);
      try {
        const result = await pyodide.runPythonAsync("lint_draft(draft_text)");
        self.postMessage({ type: "result", id: data.id, ...JSON.parse(result) });
      } finally {
        pyodide.globals.delete("draft_text");
      }
    }
  } catch {
    // Avoid exposing Python tracebacks containing draft text.
    self.postMessage({
      type: "error", id: data.id,
      text: data.type === "init"
        ? "The rule engine could not load. Check your connection and retry. Your draft is still here."
        : "The check could not finish. Check the draft structure and try again. Your draft is still here.",
    });
  }
};
