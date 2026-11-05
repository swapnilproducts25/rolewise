// Toolbar menu: the Ready queue (kits built by scripts/build_kits.py), best fit first, plus Pause/Resume and Debrief.
// Skip, Pause/Resume and Debrief go to the local helper (extension/native, set up once with
// scripts/install_native_host.py), which updates the tracker on this laptop at once. Without the helper, the same
// action goes as a "Rolewise action" tap email to yourself, which the next run picks up.
const list = document.getElementById("list");
const esc = s => String(s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const getDone = () => new Promise(r => chrome.storage.local.get({ submitted: [] }, d => r(d.submitted)));
const native = payload => new Promise(r => chrome.runtime.sendMessage({ type: "rolewise-native", payload }, res => r(res || {})));
const status = () => fetch(chrome.runtime.getURL("kits/status.json")).then(r => r.json()).catch(() => ({}));
const split = label => { const [co, ...rest] = String(label).split(" · "); return [co, rest.join(" · ")]; };
// Only jobs that need a different route get a tag; the hover text says how.
const TAGS = {
  "easy-apply": ["Easy Apply", "On LinkedIn: click Easy Apply, then Fill this step on each step"],
  "company-site": ["Company site", "Click Apply on LinkedIn; on the company's form click Fill page"],
  "linkedin": ["LinkedIn", "If LinkedIn shows Easy Apply, use it; otherwise apply on the company site with Fill page"],
};

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
  btn.title = paused ? "Start the daily runs again" : "Stop new jobs and briefings until you resume";
  if (paused) {
    const until = st.paused_until ? ` until ${st.paused_until}` : "";
    list.insertAdjacentHTML("afterbegin", `<div class="paused"><b>Paused${esc(until)}.</b> Replies are still recorded.</div>`);
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
  list.insertAdjacentHTML("beforeend", `<h2>Interviews</h2>` + st.interviews.map(i => {
    const [co, role] = split(i.label);
    return `<div class="iv"><div class="row"><div class="job"><div class="co">${esc(co)}</div><div class="role">${esc(role)}</div></div>` +
      `<button class="act" data-id="${esc(i.id)}" title="Jot rough notes after the call">Debrief</button></div></div>`;
  }).join(""));
  list.querySelectorAll(".iv .act").forEach(b => b.onclick = () => {
    const wrap = b.closest(".iv");
    if (wrap.querySelector(".deb")) return;
    wrap.insertAdjacentHTML("beforeend", `<div class="deb"><textarea rows="5" placeholder="Who you met, what they asked, ` +
      `what went well or badly, next steps"></textarea><button class="save">Save</button> <span class="msg"></span></div>`);
    const box = wrap.querySelector(".deb");
    box.querySelector("textarea").focus();
    box.querySelector(".save").onclick = async () => {
      const notes = box.querySelector("textarea").value.trim();
      if (!notes) return;
      const res = await native({ action: "debrief", id: b.dataset.id, notes });
      if (res.ok) box.innerHTML = `<span class="msg">Saved. The next run turns it into a full debrief.</span>`;
      else tapEmail(st.email, `ANSWER ${b.dataset.id}`, `Debrief notes:\n${notes}\n\n`);
    };
  });
}

async function render() {
  const [index, done, st] = await Promise.all([
    fetch(chrome.runtime.getURL("kits/index.json")).then(r => r.json()), getDone(), status()]);
  const byFit = (a, b) => (b.fit || 0) - (a.fit || 0);
  const ready = index.filter(k => k.status === "ready" && k.urls.length && !done.includes(k.id)).sort(byFit);
  const coming = index.filter(k => k.status === "preparing").length;
  let html = `<h2>Ready to submit · ${ready.length}</h2>`;
  html += ready.length ? ready.map(k => {
    const [co, role] = split(k.label);
    const tag = TAGS[k.mode];
    return `<div class="row"><div class="job" data-url="${esc(k.urls[0])}" title="Open the form; it fills itself">` +
      `<div class="co">${esc(co)}${tag ? `<span class="tag" title="${esc(tag[1])}">${tag[0]}</span>` : ""}</div>` +
      `<div class="role">${esc(role)}</div></div>` +
      (k.fit ? `<span class="fit" title="Fit score">${k.fit}</span>` : "") +
      `<button class="x" data-id="${esc(k.id)}" title="Skip this job">✕</button></div>`;
  }).join("") : `<p class="note">Nothing ready. New jobs arrive with the morning run.</p>`;
  if (coming) html += `<p class="note">${coming} more being prepared</p>`;
  list.innerHTML = html;
  list.querySelectorAll(".job[data-url]").forEach(a => a.onclick = () => chrome.tabs.create({ url: a.dataset.url + "#rolewise-fill" }));
  list.querySelectorAll("button.x").forEach(b => b.onclick = async () => {
    const id = b.dataset.id;
    b.closest(".row").style.opacity = ".4";
    const res = await native({ action: "skip", id });
    if (!res.ok && st.email) tapEmail(st.email, `SKIP ${id}`, "Add a reason below if you like.\n\n");
    const d = await getDone();
    chrome.storage.local.set({ submitted: d.concat(id) }, render);
  });
  renderInterviews(st);
  await renderPause(st);
}

document.getElementById("fillpage").onclick = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;
  const res = await new Promise(r => chrome.runtime.sendMessage({ type: "rolewise-fill-tab", tabId: tab.id }, r));
  if (res && res.ok) window.close();
  else list.insertAdjacentHTML("afterbegin", `<p class="note">Open an application form first, then click Fill page.</p>`);
};

render().catch(() => {
  list.innerHTML = `<p class="note">No jobs yet. They appear after the laptop's daily run.</p>`;
});
