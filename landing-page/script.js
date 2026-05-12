/**
 * Sift landing page — minimal JS for copy-to-clipboard.
 */

document.addEventListener("DOMContentLoaded", () => {
  const copyBtn = document.querySelector("[data-copy]");
  if (!copyBtn) return;

  const cmdEl = document.querySelector(".cmd");
  const label = copyBtn.querySelector(".copy-label");

  copyBtn.addEventListener("click", async () => {
    const text = cmdEl?.textContent?.trim();
    if (!text) return;

    try {
      await navigator.clipboard.writeText(text);
      if (label) {
        const original = label.textContent;
        label.textContent = "✓ copiado";
        setTimeout(() => {
          label.textContent = original;
        }, 2000);
      }
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      if (label) {
        const original = label.textContent;
        label.textContent = "✓ copiado";
        setTimeout(() => {
          label.textContent = original;
        }, 2000);
      }
    }
  });
});
