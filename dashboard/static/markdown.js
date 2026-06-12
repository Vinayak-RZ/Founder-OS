/** Lightweight Markdown render + sanitize for Nawab OS chat and file viewer. */
(function (global) {
  "use strict";

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function inlineFormat(s) {
    let out = escapeHtml(s);
    out = out.replace(/`([^`]+)`/g, "<code>$1</code>");
    out = out.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out = out.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, label, url) => {
      const u = String(url).trim();
      if (/^(https?:|\/api\/|\/static\/)/i.test(u)) {
        return `<a href="${escapeHtml(u)}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`;
      }
      return escapeHtml(label);
    });
    return out;
  }

  function renderMarkdown(text) {
    const src = String(text ?? "");
    if (!src.trim()) return "";

    const lines = src.replace(/\r\n/g, "\n").split("\n");
    const html = [];
    let inCode = false;
    let codeBuf = [];
    let listType = null;

    function flushList() {
      if (listType) {
        html.push(listType === "ol" ? "</ol>" : "</ul>");
        listType = null;
      }
    }

    function flushCode() {
      if (!inCode) return;
      html.push(`<pre class="md-pre"><code>${escapeHtml(codeBuf.join("\n"))}</code></pre>`);
      codeBuf = [];
      inCode = false;
    }

    for (const raw of lines) {
      const line = raw;

      if (line.trim().startsWith("```")) {
        flushList();
        if (inCode) flushCode();
        else inCode = true;
        continue;
      }
      if (inCode) {
        codeBuf.push(line);
        continue;
      }

      if (!line.trim()) {
        flushList();
        html.push("");
        continue;
      }

      const h = line.match(/^(#{1,6})\s+(.+)$/);
      if (h) {
        flushList();
        const level = h[1].length;
        html.push(`<h${level} class="md-h${level}">${inlineFormat(h[2])}</h${level}>`);
        continue;
      }

      const ul = line.match(/^[-*+]\s+(.+)$/);
      if (ul) {
        if (listType !== "ul") {
          flushList();
          listType = "ul";
          html.push("<ul class=\"md-ul\">");
        }
        html.push(`<li>${inlineFormat(ul[1])}</li>`);
        continue;
      }

      const ol = line.match(/^\d+\.\s+(.+)$/);
      if (ol) {
        if (listType !== "ol") {
          flushList();
          listType = "ol";
          html.push("<ol class=\"md-ol\">");
        }
        html.push(`<li>${inlineFormat(ol[1])}</li>`);
        continue;
      }

      flushList();
      html.push(`<p class="md-p">${inlineFormat(line)}</p>`);
    }

    flushList();
    flushCode();
    return html.filter(Boolean).join("\n");
  }

  global.FOSMarkdown = { render: renderMarkdown, escapeHtml };
})(window);
