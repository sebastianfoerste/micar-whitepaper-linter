// Python runs off the UI thread. Only static code/packages are fetched.
let pyodide, markupReady = false;
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
      // pypdf serves the PDF loader only. lxml is loaded on the first XHTML check.
      await pyodide.runPythonAsync("import micropip\nawait micropip.install(wheel_url, deps=False)");
      const response = await fetch(new URL("lint.py", import.meta.url));
      if (!response.ok) throw new Error("The browser bridge could not be loaded.");
      await pyodide.runPythonAsync(await response.text());
      self.postMessage({ type: "ready" });
    } else if (data.type === "lint") {
      if (data.format === "xhtml" && !markupReady) {
        // lxml is several megabytes, so JSON-only sessions never fetch it.
        progress("Loading the XHTML parser…");
        await pyodide.loadPackage("lxml");
        // loadPackage reports a failed download without throwing; stay unready so the next check retries it.
        if (!("lxml" in pyodide.loadedPackages)) {
          progress("Ready. Checks run locally in your browser.");
          self.postMessage({ type: "error", id: data.id, text: "The XHTML parser could not load. Check your connection and run the checks again. Your draft is still here." });
          return;
        }
        markupReady = true;
        progress("Ready. Checks run locally in your browser.");
      }
      const draft = { draft_text: data.text, draft_format: data.format ?? "json", draft_regime: data.regime ?? "", draft_name: data.name ?? "" };
      for (const [key, value] of Object.entries(draft)) pyodide.globals.set(key, value);
      try {
        const result = JSON.parse(await pyodide.runPythonAsync("lint_draft(draft_text, draft_format, draft_regime, draft_name)"));
        // A loader refusal is a message for the user, e.g. an XHTML draft without a stated regime.
        if (result.error) self.postMessage({ type: "error", id: data.id, text: result.error });
        else self.postMessage({ type: "result", id: data.id, ...result });
      } finally {
        for (const key of Object.keys(draft)) pyodide.globals.delete(key);
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
