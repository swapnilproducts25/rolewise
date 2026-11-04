// Toolbar menu: the Ready queue (kits built by scripts/build_kits.py), best fit first.
const list = document.getElementById("list");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

fetch(chrome.runtime.getURL("kits/index.json"))
  .then(r => r.json())
  .then(index => {
    const byFit = (a, b) => (b.fit || 0) - (a.fit || 0);
    const ready = index.filter(k => k.status === "ready" && k.urls.length).sort(byFit);
    const coming = index.filter(k => k.status === "preparing").sort(byFit);
    let html = ready.length
      ? `<h2>Ready to submit (${ready.length})</h2>` + ready.map(k =>
          `<a class="job" data-url="${esc(k.urls[0])}">${esc(k.label)}${k.fit ? ` <span class="fit">fit ${k.fit}</span>` : ""}</a>`).join("")
      : `<p class="muted">Nothing ready right now. New jobs appear here after you tap Prepare in your briefing.</p>`;
    if (coming.length)
      html += `<h2>Being prepared (${coming.length})</h2>` + coming.map(k => `<div class="soon">${esc(k.label)}</div>`).join("");
    list.innerHTML = html;
    list.querySelectorAll("a.job").forEach(a => a.onclick = () => chrome.tabs.create({ url: a.dataset.url + "#rolewise-fill" }));
  })
  .catch(() => {
    list.innerHTML = `<p class="muted">No jobs yet. Rolewise builds them on your laptop's daily run
      (or run <code>scripts/build_kits.py</code>).</p>`;
  });
