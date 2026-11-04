// Rolewise Fill: fills an application form from a Rolewise kit. It never clicks Submit.
(() => {
  if (window.__rolewiseFill) return;
  window.__rolewiseFill = true;

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const norm = s => (s || "").replace(/\s+/g, " ").trim();
  const low = s => norm(s).toLowerCase();

  // Label pattern -> answer key. Order matters: specific before general.
  const RULES = [
    [/preferred (first )?name/, null],
    [/first\s*name|given name/, "first_name"],
    [/last\s*name|surname|family name/, "last_name"],
    [/email me|future (job )?openings|job alerts|keep me (updated|informed)/, "future_emails"],
    [/e-?mail/, "email"],
    [/phone|mobile/, "phone"],
    [/linkedin/, "linkedin"],
    [/github/, null],
    [/website|portfolio|personal site/, "website"],
    [/iran|cuba|north korea|sanction/, "export_sanctioned"],
    [/additional citizenship/, "export_additional"],
    [/citizenship.*first|first.*citizenship/, "export_first"],
    [/gender|ethnic|race|sexual orientation|transgender|disabilit|veteran|neurodiver|household earner|pronoun/, "diversity"],
    [/sponsor/, "sponsorship"],
    [/authori[sz]ed to work|right to work|eligible to work|legally (able|permitted) to work|work permit/, "authorised"],
    [/relocat/, "relocate"],
    [/remote location|work remotely|remote work/, null],
    [/hybrid|in-?office|on-?site|office location|days per week/, "hybrid"],
    [/previously (worked|been employed)|former employee|worked (for|at) .{0,40}before|ever worked|ever been employed|employed by/, "previously_worked"],
    [/how did you (hear|find|learn)|where did you (hear|find)|source/, "heard"],
    [/whatsapp|sms|text messages/, null],
    [/country (where|in which) you (currently )?reside|country of residence|country you live/, "residence_country"],
    [/^school\b|university|institution/, "school"],
    [/^degree\b/, "degree"],
    [/discipline|field of study|major/, "discipline"],
    [/location \(city\)|^city\b/, "city"],
    [/current (or (most recent|previous) )?(company|employer)|(most recent|previous) (company|employer)|current organi[sz]ation/, "current_company"],
    [/current (or previous )?(job )?title|current (role|position)/, "current_title"],
    [/salary|compensation|pay expectation|expected (pay|package)/, "salary"],
    [/notice period/, "notice"],
    [/start date|when can you start|earliest (start|availability)|availability/, "start_date"],
    [/current location|where are you (currently )?(based|located)|^location\b|city of residence|^city\b/, "location"],
    [/full name|^name\b|your name/, "full_name"],
  ];
  const CONSENT = /consent|agree|acknowledg|privacy|data (protection|transfer|retention|processing)|point of data|terms|retain my data|gdpr/;

  function labelFor(el) {
    let t = "";
    if (el.labels && el.labels.length) t = el.labels[0].innerText;
    if (!t && el.getAttribute("aria-labelledby")) {
      t = el.getAttribute("aria-labelledby").split(" ").map(id => document.getElementById(id)?.innerText || "").join(" ");
    }
    if (!t) t = el.getAttribute("aria-label") || "";
    if (!t) {
      const box = el.closest("fieldset, .field, .application-question, .select__container, [class*=field], [class*=question], li, .form-group");
      const l = box && box.querySelector("label, legend, .application-label, [class*=label]");
      t = l ? l.innerText : "";
    }
    if (!t) t = el.placeholder || el.name || el.id || "";
    return norm(t.replace(/\*/g, ""));
  }

  // kits/rules.json (written by build_kits.py) overrides the built-in RULES, so new questions need no reload.
  let activeRules = RULES;
  async function loadRules() {
    try {
      const raw = await (await fetch(chrome.runtime.getURL("kits/rules.json"))).json();
      activeRules = raw.map(([pattern, key]) => [new RegExp(pattern), key]);
    } catch (e) { activeRules = RULES; }
  }

  function lookup(label, kit) {
    const L = low(label);
    for (const q of kit.questions || []) {
      if ((q.match || []).every(k => L.includes(String(k).toLowerCase()))) return q.value;
    }
    for (const [re, key] of activeRules) {
      if (re.test(L)) return key ? kit.answers[key] : IGNORE;
    }
    return undefined;
  }
  const IGNORE = Symbol("ignore"); // a rule maps this label to "leave it alone" (e.g. phone country picker)

  function setNative(el, value) {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  const asList = v => (Array.isArray(v) ? v : [v]).filter(x => x !== undefined && x !== null).map(String);
  const pick = (texts, wanted) => {
    for (const w of asList(wanted)) {
      const hit = texts.find(t => low(t.text).startsWith(low(w)));
      if (hit) return hit;
    }
    return null;
  };

  // React dropdowns are chosen through page.js (page world): send the input id + wanted options, await the reply.
  let reqSeq = 0;
  function fillReactSelect(input, wanted) {
    if (!input.id) return Promise.resolve(false);
    const reqId = ++reqSeq;
    return new Promise(resolve => {
      const onReply = e => {
        const r = JSON.parse(e.detail);
        if (r.reqId !== reqId) return;
        document.removeEventListener("rolewise-selected", onReply);
        resolve(r.ok);
      };
      document.addEventListener("rolewise-selected", onReply);
      document.dispatchEvent(new CustomEvent("rolewise-select",
        { detail: JSON.stringify({ reqId, id: input.id, wanted: asList(wanted) }) }));
      setTimeout(() => { document.removeEventListener("rolewise-selected", onReply); resolve(false); }, 30000);
    });
  }

  async function attachFiles(kit, report) {
    // Upload widgets (Homerun, Workable) can render after the text fields: wait up to 8s for them.
    for (let i = 0; i < 16 && !document.querySelector("input[type=file]"); i++) await sleep(500);
    const inputs = [...document.querySelectorAll("input[type=file]")];
    for (const input of inputs) {
      const L = low(labelFor(input) + " " + input.id + " " + input.name);
      const kind = /cover/.test(L) ? "cover_letter" : /resume|cv\b|curriculum/.test(L) ? "cv" : null;
      if (!kind || !kit.files[kind] || (input.files && input.files.length)) continue;
      const path = kit.files[kind];
      const name = path.split("/").pop();
      // Some widgets upload on change and then clear the input: look for the file name nearby to avoid duplicates.
      const box = input.closest("fieldset, [class*=question], [class*=field], [class*=upload], li") || input.parentElement;
      if (report.filled.some(f => f.endsWith(name)) || (box && box.innerText.includes(name))) continue;
      const blob = await (await fetch(chrome.runtime.getURL(path))).blob();
      const type = name.endsWith(".pdf") ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
      const dt = new DataTransfer();
      dt.items.add(new File([blob], name, { type }));
      input.files = dt.files;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      report.filled.push(`${kind === "cv" ? "CV" : "Cover letter"}: ${name}`);
    }
  }

  async function fill(kit) {
    const report = { filled: [], missing: [] };
    await attachFiles(kit, report);
    await sleep(3000); // let the form re-render after uploads before typing

    const seen = new Set();
    const controls = [...document.querySelectorAll("input, textarea, select")]
      .filter(el => !["hidden", "file", "submit", "button", "search"].includes(el.type) && !el.disabled
        && !(el.id || "").startsWith("g-recaptcha") && el.offsetParent !== null);

    for (const el of controls) {
      const label = labelFor(el);
      if (el.type === "radio") {
        if (seen.has(el.name)) continue;
        seen.add(el.name);
        const group = [...document.querySelectorAll(`input[type=radio][name="${CSS.escape(el.name)}"]`)];
        if (group.some(r => r.checked)) continue;
        const qLabel = labelFor(el.closest("fieldset") || el);
        const v = lookup(qLabel, kit);
        if (v === IGNORE) continue;
        const hit = v && pick(group.map(r => ({ el: r, text: labelFor(r) })), v);
        if (hit) { hit.el.click(); report.filled.push(qLabel); } else report.missing.push(qLabel);
        continue;
      }
      if (el.type === "checkbox") {
        const L = low(label);
        // "Which countries will you work in?" checkbox lists: tick the job's country.
        const groupQ = low(labelFor(el.closest("fieldset") || el.parentElement?.parentElement || el));
        if (/countr(y|ies).{0,60}(work|anticipate|located|based)/.test(groupQ) && kit.answers.job_country) {
          if (!el.checked && asList(kit.answers.job_country).some(c => L === low(c))) { el.click(); report.filled.push(`☑ ${label}`); }
          continue;
        }
        if (!el.checked && CONSENT.test(L)) { el.click(); report.filled.push(`☑ ${label.slice(0, 60)}`); continue; }
        const v = lookup(label, kit);
        if (v === IGNORE) continue;
        if (!el.checked && v && asList(v).some(x => L.startsWith(low(x)))) { el.click(); report.filled.push(label); }
        continue;
      }
      if (el.tagName === "SELECT") {
        if (el.value) continue;
        const v = lookup(label, kit);
        if (v === IGNORE) continue;
        const hit = v && pick([...el.options].map(o => ({ el: o, text: o.text })), v);
        if (hit) { el.value = hit.el.value; el.dispatchEvent(new Event("change", { bubbles: true })); report.filled.push(label); }
        else if (el.required) report.missing.push(label);
        continue;
      }
      if (el.getAttribute("role") === "combobox") {
        if (!label || /^\+?\d|country code/i.test(label) && !/reside/i.test(label)) continue; // phone-country picker sets itself
        const box = el.closest(".select__container, .select-shell, [class*=select]");
        if (box && box.querySelector("[class*=single-value], [class*=singleValue]")) continue;
        const v = lookup(label, kit);
        if (v === IGNORE) continue;
        let wanted = v;
        if (/location/.test(low(label)) && !/city/.test(low(label)) && kit.answers.location_choice) wanted = asList(v).concat(kit.answers.location_choice);
        if (wanted !== undefined && await fillReactSelect(el, wanted)) report.filled.push(label);
        else report.missing.push(label);
        continue;
      }
      if (el.value) continue;
      const v = lookup(label, kit);
      if (v === IGNORE) continue;
      if (v !== undefined && !Array.isArray(v)) { setNative(el, String(v)); report.filled.push(label); }
      else if (Array.isArray(v) && v.length) { setNative(el, String(v[0])); report.filled.push(label); }
      else if (el.required || el.getAttribute("aria-required") === "true") report.missing.push(label);
    }
    await attachFiles(kit, report);   // second pass: upload boxes that appeared while the form was being filled
    if (kit.files.cv && document.querySelector("input[type=file]") && !report.filled.some(f => f.startsWith("CV"))) report.missing.push("CV upload (attach it yourself)");
    report.filled = [...new Set(report.filled)];
    report.missing = [...new Set(report.missing)].filter(m => m && !report.filled.includes(m));
    // Highlight what still needs the user.
    document.querySelectorAll("[data-rolewise-missing]").forEach(e => { e.style.outline = ""; e.removeAttribute("data-rolewise-missing"); });
    controls.filter(el => report.missing.includes(labelFor(el)) || report.missing.includes(labelFor(el.closest("fieldset") || el)))
      .forEach(el => { el.style.outline = "3px solid #e0a800"; el.setAttribute("data-rolewise-missing", "1"); });
    return report;
  }

  async function loadIndex() {
    return (await fetch(chrome.runtime.getURL("kits/index.json"))).json();
  }
  const token = u => (u || "").toLowerCase().replace(/[?#].*$/, "").replace(/\/+$/, "");
  function matchKit(index) {
    const here = location.href.toLowerCase();
    const jid = (here.match(/(?:jobs\/|token=|gh_jid=)(\d{5,})/) || [])[1];
    return index.find(k => k.urls.some(u => {
      const t = token(u);
      const kid = (u.toLowerCase().match(/(?:jobs\/|token=|gh_jid=|view\/)(\d{5,})/) || [])[1];
      return (jid && kid && jid === kid) || (t && here.startsWith(t));
    }));
  }

  // ---------- UI ----------
  // Only on real application forms, never on confirmation/thank-you pages.
  const DONE_TEXT = /thank you for (applying|your application)|application (has been|was) (received|submitted)|and\.\.\.sent|we('| ha)ve received your application/i;
  function isApplicationPage() {
    if (/confirmation|thank-?you|submitted/i.test(location.pathname + location.search)) return false;
    if (DONE_TEXT.test((document.body && document.body.innerText || "").slice(0, 4000))) return false;
    return !!document.querySelector("input[type=file], #first_name, input[name*=email i], input[autocomplete=email], input[type=email]");
  }
  function markSubmitted() {
    let id = null;
    try { id = sessionStorage.getItem("rolewise:lastKit"); } catch (e) {}
    if (!id || !DONE_TEXT.test((document.body && document.body.innerText || "").slice(0, 4000))) return;
    try { sessionStorage.removeItem("rolewise:lastKit"); } catch (e) {}
    chrome.storage.local.get({ submitted: [] }, d => {
      if (!d.submitted.includes(id)) chrome.storage.local.set({ submitted: d.submitted.concat(id) });
    });
  }
  const submittedIds = () => new Promise(r => chrome.storage.local.get({ submitted: [] }, d => r(d.submitted)));
  const filledKey = () => "rolewise:filled:" + location.href.split("#")[0];
  const alreadyFilled = () => { try { return sessionStorage.getItem(filledKey()) === "1"; } catch (e) { return false; } };

  // Compact tab on the right edge (vertically centred, away from Submit buttons); click to expand / collapse.
  const ui = document.createElement("div");
  ui.style.cssText = "position:fixed;right:0;top:38%;z-index:2147483647;display:flex;align-items:flex-start;font:14px/1.4 -apple-system,Segoe UI,Arial,sans-serif";
  ui.innerHTML = `
    <div id="jf-panel" style="display:none;width:300px;max-height:60vh;overflow:auto;background:#fff;color:#14223b;border:1px solid #dde3ec;border-radius:12px 0 0 12px;padding:12px;box-shadow:0 8px 24px rgba(0,0,0,.2)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><b>Rolewise</b><button id="jf-min" title="Collapse" style="border:0;background:none;font-size:18px;cursor:pointer;color:#5b6880">–</button></div>
      <div id="jf-body"></div>
      <button id="jf-btn" style="margin-top:10px;width:100%;background:#1d3461;color:#fff;border:0;border-radius:8px;padding:9px;font-weight:700;cursor:pointer">Fill with Rolewise</button>
    </div>
    <button id="jf-tab" title="Rolewise" style="writing-mode:vertical-rl;transform:rotate(180deg);background:#1d3461;color:#fff;border:0;border-radius:0 8px 8px 0;padding:12px 7px;font-weight:700;font-size:12px;letter-spacing:.06em;cursor:pointer;box-shadow:0 4px 14px rgba(0,0,0,.2)">ROLEWISE</button>`;
  const panel = ui.querySelector("#jf-panel"), body = ui.querySelector("#jf-body"), btn = ui.querySelector("#jf-btn");
  const open = v => { panel.style.display = v ? "block" : "none"; };
  ui.querySelector("#jf-tab").onclick = async () => {
    const opening = panel.style.display === "none";
    open(opening);
    if (opening && !body.innerHTML) body.innerHTML = "Click Fill to complete this form." + await showQueue();
  };
  ui.querySelector("#jf-min").onclick = () => open(false);
  const show = html => { open(true); body.innerHTML = html; };
  // The Ready queue: every job Rolewise has prepared, one click each, so a whole batch is done in one sitting.
  async function showQueue(currentId) {
    try {
      const index = await loadIndex(), done = await submittedIds();
      const ready = index.filter(k => k.status === "ready" && k.id !== currentId && k.urls.length && !done.includes(k.id))
        .sort((a, b) => (b.fit || 0) - (a.fit || 0));
      if (!ready.length) return "";
      return `<div style="margin-top:12px;border-top:1px solid #dde3ec;padding-top:8px"><b>Next in your queue (${ready.length})</b>` +
        ready.slice(0, 5).map(k => `<div style="margin-top:6px"><a href="${k.urls[0]}#rolewise-fill" style="color:#1d3461;font-weight:600;text-decoration:none">→ ${k.label}</a>${k.fit ? ` <span style="color:#5b6880;font-size:12px">fit ${k.fit}</span>` : ""}</div>`).join("") +
        `</div>`;
    } catch (e) { return ""; }
  }
  const refreshState = () => {
    if (alreadyFilled()) { btn.textContent = "Refill"; body.innerHTML ||= "Already filled on this page. Review and submit, or refill."; }
    else { btn.textContent = "Fill with Rolewise"; }
  };

  // React sites (Greenhouse) re-render the whole document while hydrating and drop foreign nodes, so attach after
  // the page settles, re-attach if it disappears, and remove it once the page stops being an application form.
  if (window.top === window) {
    let autoDone = false;
    const sync = () => {
      const want = isApplicationPage();
      if (want && !ui.isConnected) { document.body.appendChild(ui); refreshState(); }
      if (!want && ui.isConnected) ui.remove();
      // A confirmation page after Rolewise filled a form here: drop that job from the Ready queue.
      if (!want) markSubmitted();
      // Opened from the briefing's "Open & fill" button (#rolewise-fill): fill once, automatically.
      if (want && !autoDone && /(rolewise|jobify)-fill/.test(location.hash) && !alreadyFilled()) { autoDone = true; btn.click(); }
    };
    setTimeout(sync, 2500);
    setInterval(sync, 2000);
  }

  async function run(kitId) {
    show("Filling…");
    btn.disabled = true;
    await loadRules();
    const kit = await (await fetch(chrome.runtime.getURL(`kits/${kitId}.json`))).json();
    const r = await fill(kit);
    try { sessionStorage.setItem(filledKey(), "1"); sessionStorage.setItem("rolewise:lastKit", kitId); } catch (e) {}
    btn.disabled = false;
    refreshState();
    show(`<b>${kit.company} · ${kit.title}</b>
      <div style="margin:6px 0;color:#1f7a4d">Filled ${r.filled.length}</div>
      <div style="font-size:12px;color:#5b6880">${r.filled.map(x => "✓ " + x.slice(0, 70)).join("<br>")}</div>
      ${r.missing.length ? `<div style="margin-top:8px;color:#9a5b00"><b>Needs you (${r.missing.length}, outlined in yellow)</b><br>${r.missing.map(x => "• " + x.slice(0, 80)).join("<br>")}</div>` : ""}
      <div style="margin-top:10px;font-weight:600">Review, click the form's Submit, and type any code the site emails you.</div>
      ${await showQueue(kit.id)}`);
  }

  btn.onclick = async () => {
    if (alreadyFilled() && !confirm("Rolewise already filled this form. Fill it again?")) return;
    try {
      const index = await loadIndex();
      const kit = matchKit(index);
      if (kit) return run(kit.id);
      show(`<b>Which job is this?</b><br><select id="jf-pick" style="width:100%;margin-top:6px">${index.map(k => `<option value="${k.id}">${k.label}</option>`).join("")}</select>
        <button id="jf-go" style="margin-top:8px;width:100%;background:#fff;color:#1d3461;border:1px solid #1d3461;border-radius:8px;padding:8px">Fill this job</button>`);
      body.querySelector("#jf-go").onclick = () => run(body.querySelector("#jf-pick").value);
    } catch (e) {
      show(`Couldn't load kits: ${e.message}. Run <code>scripts/build_kits.py</code>.`);
    }
  };
})();
