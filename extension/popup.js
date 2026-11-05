// Toolbar menu: the Ready queue (kits built by scripts/build_kits.py), best fit first.
// Jobs submitted through Rolewise Fill are hidden automatically (confirmation page); Skip hides one and emails the
// usual "Rolewise action: SKIP" tap to yourself so the tracker learns it on the next run.
const list = document.getElementById("list");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const getDone = () => new Promise(r => chrome.storage.local.get({ submitted: [] }, d => r(d.submitted)));

// Pause / Resume: a tap email to yourself ("Rolewise action: PAUSE" / "RESUME"), the same channel as the briefing's
// buttons, so it controls the cloud run and the laptop run alike. status.json shows the state as of the last kit build.
const tapEmail = (to, verb, note) => {
  const q = new URLSearchParams({ view: "cm", to, su: `Rolewise action: ${verb}`,
    body: `${verb}

(From Rolewise Fill. ${note} Then hit send.)
` });
  chrome.tabs.create({ url: `https://mail.google.com/mail/?${q}` });
};
async function renderPause() {
  const st = await fetch(chrome.runtime.getURL("kits/status.json")).then(r => r.json()).catch(() => null);
  let asked = await new Promise(r => chrome.storage.local.get({ pauseAsked: "" }, d => r(d.pauseAsked)));
  if (st && asked && st.paused === (asked === "PAUSE")) { asked = ""; chrome.storage.local.remove("pauseAsked"); }  // run caught up
  const btn = document.getElementById("pause");
  if (!st || !st.email) return;
  const paused = asked ? asked === "PAUSE" : st.paused;
  btn.hidden = false;
  btn.textContent = paused ? "Resume" : "Pause";
  btn.title = paused ? "Start Rolewise's daily runs again" : "Stop daily searching, preparing and briefings until you resume";
  if (paused) {
    const until = st.paused_until ? ` until ${st.paused_until}` : "";
    document.getElementById("list").insertAdjacentHTML("afterbegin",
      `<div class="paused"><b>Rolewise is paused${esc(until)}.</b> No new jobs, preparing or briefings. It still records replies to your applications. ${asked ? "Your request takes effect at the next run." : ""}</div>`);
  } else if (asked === "RESUME") {
    document.getElementById("list").insertAdjacentHTML("afterbegin", `<div class="paused">Resume requested: Rolewise restarts at its next run.</div>`);
  }
  btn.onclick = () => {
    const verb = paused ? "RESUME" : "PAUSE";
    tapEmail(st.email, verb, verb === "PAUSE" ? 'Add "until YYYY-MM-DD" on the first line if you like.' : "");
    chrome.storage.local.set({ pauseAsked: verb }, () => { list.innerHTML = ""; render().then(renderPause); });
  };
}

async function render() {
  const [index, done] = await Promise.all([
    fetch(chrome.runtime.getURL("kits/index.json")).then(r => r.json()), getDone()]);
  const byFit = (a, b) => (b.fit || 0) - (a.fit || 0);
  const ready = index.filter(k => k.status === "ready" && k.urls.length && !done.includes(k.id)).sort(byFit);
  const coming = index.filter(k => k.status === "preparing").sort(byFit);
  let html = ready.length
    ? `<h2>Ready to submit (${ready.length})</h2>` + ready.map(k =>
        `<div class="row"><a class="job" data-url="${esc(k.urls[0])}">${esc(k.label)}${k.fit ? ` <span class="fit">fit ${k.fit}</span>` : ""}` +
        (k.mode === "easy-apply" ? `<span class="tag">LinkedIn Easy Apply: click Easy Apply, then Fill this step</span>`
          : k.mode === "company-site" ? `<span class="tag">Applies on the company's site: use the PDFs in its folder</span>`
          : k.mode === "linkedin" ? `<span class="tag">On LinkedIn: if it shows Easy Apply, click it, then Fill this step</span>` : "") + `</a>` +
        `<button class="done" data-id="${esc(k.id)}" title="Not applying: hide it and tell Rolewise">Skip</button></div>`).join("")
    : `<p class="muted">Nothing ready right now. New jobs appear here after you tap Prepare in your briefing.</p>`;
  if (coming.length)
    html += `<h2>Being prepared (${coming.length})</h2>` + coming.map(k => `<div class="soon">${esc(k.label)}</div>`).join("");
  list.innerHTML = html;
  list.querySelectorAll("a.job").forEach(a => a.onclick = () => chrome.tabs.create({ url: a.dataset.url + "#rolewise-fill" }));
  list.querySelectorAll("button.done").forEach(b => b.onclick = async () => {
    const id = b.dataset.id;
    const kit = await fetch(chrome.runtime.getURL(`kits/${id}.json`)).then(r => r.json()).catch(() => ({}));
    const me = (kit.answers || {}).email;
    if (me) {   // a pre-written tap email in Gmail: hit Send and the next run marks it skipped
      const q = new URLSearchParams({ view: "cm", to: me, su: `Rolewise action: SKIP ${id}`,
        body: `SKIP ${id}

(From Rolewise Fill. Add a reason below if you like, then hit send.)
` });
      chrome.tabs.create({ url: `https://mail.google.com/mail/?${q}` });
    }
    const d = await getDone();
    chrome.storage.local.set({ submitted: d.concat(id) }, render);
  });
}

render().then(renderPause).catch(() => {
  list.innerHTML = `<p class="muted">No jobs yet. Rolewise builds them on your laptop's daily run
    (or run <code>scripts/build_kits.py</code>).</p>`;
});
