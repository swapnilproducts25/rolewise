// Toolbar menu: the Ready queue (kits built by scripts/build_kits.py), best fit first, plus Pause/Resume and Debrief.
// Skip, Pause/Resume and Debrief go to the local helper (extension/native, set up once with
// scripts/install_native_host.py), which updates the tracker on this laptop at once. Without the helper, the same
// action goes as a "Rolewise action" tap email to yourself, which the next run picks up.
const list = document.getElementById("list");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const getDone = () => new Promise(r => chrome.storage.local.get({ submitted: [] }, d => r(d.submitted)));
const native = payload => new Promise(r => chrome.runtime.sendMessage({ type: "rolewise-native", payload }, res => r(res || {})));
const status = () => fetch(chrome.runtime.getURL("kits/status.json")).then(r => r.json()).catch(() => ({}));

const tapEmail = (to, subject, body) => {
  const q = new URLSearchParams({ view: "cm", to, su: `Rolewise action: ${subject}`,
    body: `${subject}\n\n${body}(From Rolewise Fill. Hit send; the next Rolewise run picks it up.)\n` });
  chrome.tabs.create({ url: `https://mail.google.com/mail/?${q}` });
};

async function renderPause(st) {
  let asked = await new Promise(r => chrome.storage.local.get({ pauseAsked: "" }, d => r(d.pauseAsked)));
  if (asked && st.paused === (asked === "PAUSE")) { asked = ""; chrome.storage.local.remove("pauseAsked"); }  // caught up
  const btn = document.getElementById("pause");
  if (!st.email) return;
  const paused = asked ? asked === "PAUSE" : st.paused;
  btn.hidden = false;
  btn.textContent = paused ? "Resume" : "Pause";
  btn.title = paused ? "Start Rolewise's daily runs again" : "Stop daily searching, preparing and briefings until you resume";
  if (paused) {
    const until = st.paused_until ? ` until ${st.paused_until}` : "";
    list.insertAdjacentHTML("afterbegin", `<div class="paused"><b>Rolewise is paused${esc(until)}.</b> No new jobs, preparing ` +
      `or briefings. It still records replies to your applications.</div>`);
  }
  btn.onclick = async () => {
    const verb = paused ? "RESUME" : "PAUSE";
    const res = await native({ action: verb.toLowerCase() });
    if (!res.ok) tapEmail(st.email, verb, verb === "PAUSE" ? 'Add "until YYYY-MM-DD" on the first line if you like.\n\n' : "");
    chrome.storage.local.set({ pauseAsked: verb }, render);
  };
}

function renderInterviews(st) {
  if (!(st.interviews || []).length) return;
  list.insertAdjacentHTML("beforeend", `<h2>Interviews</h2>` + st.interviews.map(i =>
    `<div class="row iv"><div class="soon"><b>${esc(i.label)}</b></div>` +
    `<button class="debrief" data-id="${esc(i.id)}">Debrief</button></div>`).join(""));
  list.querySelectorAll("button.debrief").forEach(b => b.onclick = () => {
    const row = b.closest(".row");
    if (row.querySelector(".deb")) return;
    row.insertAdjacentHTML("beforeend", `<div class="deb"><textarea rows="6" placeholder="Rough notes: who you met, what ` +
      `they asked, what went well or badly, next steps"></textarea><button class="save">Save debrief</button> <span class="msg"></span></div>`);
    const box = row.querySelector(".deb");
    box.querySelector(".save").onclick = async () => {
      const notes = box.querySelector("textarea").value.trim();
      if (!notes) return;
      const res = await native({ action: "debrief", id: b.dataset.id, notes });
      if (res.ok) box.innerHTML = `<span class="msg">Saved. Rolewise writes the full debrief and lessons on its next run.</span>`;
      else tapEmail(st.email, `ANSWER ${b.dataset.id}`, `Debrief notes:\n${notes}\n\n`);
    };
  });
}

async function render() {
  const [index, done, st] = await Promise.all([
    fetch(chrome.runtime.getURL("kits/index.json")).then(r => r.json()), getDone(), status()]);
  const byFit = (a, b) => (b.fit || 0) - (a.fit || 0);
  const ready = index.filter(k => k.status === "ready" && k.urls.length && !done.includes(k.id)).sort(byFit);
  const coming = index.filter(k => k.status === "preparing").sort(byFit);
  let html = ready.length
    ? `<h2>Ready to submit (${ready.length})</h2>` + ready.map(k =>
        `<div class="row"><a class="job" data-url="${esc(k.urls[0])}">${esc(k.label)}${k.fit ? ` <span class="fit">fit ${k.fit}</span>` : ""}` +
        (k.mode === "easy-apply" ? `<span class="tag">LinkedIn Easy Apply: click Easy Apply, then Fill this step</span>`
          : k.mode === "company-site" ? `<span class="tag">Applies on the company's site: use the PDFs in its folder</span>`
          : k.mode === "linkedin" ? `<span class="tag">On LinkedIn: if it shows Easy Apply, click it, then Fill this step</span>` : "") + `</a>` +
        `<button class="done" data-id="${esc(k.id)}" title="Not applying: remove it from the queue">Skip</button></div>`).join("")
    : `<p class="muted">Nothing ready right now. New jobs appear here as Rolewise prepares them.</p>`;
  if (coming.length)
    html += `<h2>Being prepared (${coming.length})</h2>` + coming.map(k => `<div class="soon">${esc(k.label)}</div>`).join("");
  list.innerHTML = html;
  list.querySelectorAll("a.job").forEach(a => a.onclick = () => chrome.tabs.create({ url: a.dataset.url + "#rolewise-fill" }));
  list.querySelectorAll("button.done").forEach(b => b.onclick = async () => {
    const id = b.dataset.id;
    b.disabled = true;
    const res = await native({ action: "skip", id });
    if (!res.ok && st.email) tapEmail(st.email, `SKIP ${id}`, "Add a reason below if you like.\n\n");
    const d = await getDone();
    chrome.storage.local.set({ submitted: d.concat(id) }, render);
  });
  renderInterviews(st);
  await renderPause(st);
}

render().catch(() => {
  list.innerHTML = `<p class="muted">No jobs yet. Rolewise builds them on your laptop's daily run
    (or run <code>scripts/build_kits.py</code>).</p>`;
});
