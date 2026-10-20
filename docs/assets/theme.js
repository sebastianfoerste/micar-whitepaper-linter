// Page-session theme switch. The button keeps its label ("Dark theme") and reports aria-pressed.
// The choice lives on <html data-theme> only:
// nothing is written to browser storage or cookies, so a reload follows the system setting.
for (const button of document.querySelectorAll("[data-theme-toggle]")) {
  const root = document.documentElement;
  const isDark = () => (root.dataset.theme ?? (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
  const sync = () => {
    button.setAttribute("aria-pressed", String(isDark()));
  };
  button.addEventListener("click", () => { root.dataset.theme = isDark() ? "light" : "dark"; sync(); });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", sync);
  sync();
}
