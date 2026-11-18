// Rolewise Fill: fills an application form from a Rolewise kit. It never clicks Submit.
(() => {
  if (window.__rolewiseFill) return;
  window.__rolewiseFill = true;

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // Kits (answers, CV files) are read through the background worker, never exposed to the page.
  const kitFile = (path, as = "json") => new Promise((resolve, reject) =>
    chrome.runtime.sendMessage({ type: "rolewise-file", path, as }, res =>
      res && res.ok ? resolve(res.data) : reject(new Error((res && res.error) || "kit not found"))));
  const dataUrlToBlob = async url => (await fetch(url)).blob();
  // Multi-step sites (LinkedIn Easy Apply, Workday): the user opens each step; Rolewise fills only the step on
  // screen when asked, never on page load, and never clicks Next, Review or Submit.
  const LINKEDIN = location.hostname.endsWith("linkedin.com");
  // Workday has its own mode (wdStart below): Rolewise fills every page and clicks Save and Continue up to Review.
  const WORKDAY = /myworkday(jobs)?\.com$/.test(location.hostname);
  const STEP_MODE = LINKEDIN;
  const linkedinModal = () => [...document.querySelectorAll(
    ".jobs-easy-apply-modal, .jobs-easy-apply-content, [data-test-modal-id='easy-apply-modal'], div[role=dialog]")]
    .find(d => d.offsetParent !== null && d.querySelector("input, select, textarea")
      && /easy apply|apply to|contact info|resume|additional questions|review your application|work authori/i.test(d.innerText || ""));
  let ROOT = document;   // where fill() looks: the Easy Apply dialog on LinkedIn, the whole page elsewhere
  // Every match of a selector, including inside open shadow roots: SmartRecruiters' apply page (spl-* components)
  // keeps every field in shadow DOM, where a plain querySelectorAll finds nothing.
  function deepAll(root, sel) {
    const out = [...root.querySelectorAll(sel)];
    const walk = r => r.querySelectorAll("*").forEach(n => { if (n.shadowRoot) { out.push(...n.shadowRoot.querySelectorAll(sel)); walk(n.shadowRoot); } });
    walk(root);
    return out;
  }
  const FORM_SIGNS = "input[type=file], #first_name, input[name*=email i], input[autocomplete=email], input[type=email]";
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
    [/authori[sz]ed to work|right to work|eligible to work|legally (able|permitted) to work|work permit/, "authorised"],
    [/(require|need|will you).{0,60}sponsor|visa sponsorship/, "sponsorship"],
    [/how many years|years of (work |relevant |professional )?experience|years' experience/, "years"],
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
  const DIAL = [["+353", ["Ireland"]], ["+971", ["United Arab Emirates", "UAE"]], ["+44", ["United Kingdom", "UK"]],
    ["+91", ["India"]], ["+49", ["Germany"]], ["+31", ["Netherlands"]], ["+34", ["Spain"]], ["+351", ["Portugal"]],
    ["+33", ["France"]], ["+966", ["Saudi Arabia"]], ["+1", ["United States", "Canada"]]];
  const CONSENT =/consent|agree|acknowledg|privacy|data (protection|transfer|retention|processing)|point of data|terms|retain my data|gdpr/;

  const questionBox = el => el.closest(".application-question") || el.closest("[class*=question], .field, .form-group")
    || el.closest("li");
  function questionLabel(el) {
    const fs = el.closest("fieldset");
    if (fs) return labelFor(fs);
    const box = questionBox(el);
    const l = box && box.querySelector(".application-label, legend, [class*=label]:not(:has(input))");
    return l ? norm(labelText(l).replace(/[*✱]/g, "")) : labelFor(el);
  }

  // A label's own words only: forms like Lever wrap the whole control in the <label>, so its text would otherwise
  // include every dropdown option ("What is your location? Afghanistan Albania …") and picker messages.
  function labelText(l) {
    if (!l) return "";
    const c = l.cloneNode(true);
    c.querySelectorAll("select, option, input, textarea, button, ul, [role=listbox], [role=option], [class*=dropdown], " +
      "[class*=result], [class*=error], [class*=loading], [aria-live], .visually-hidden, [class*=filename], .application-field, [class*=upload]").forEach(n => n.remove());
    return c.textContent;
  }

  function labelFor(el) {
    let t = "";
    if (el.labels && el.labels.length) t = labelText(el.labels[0]);
    if (!t && el.getAttribute("aria-labelledby")) {
      t = el.getAttribute("aria-labelledby").split(" ").map(id => document.getElementById(id)?.innerText || "").join(" ");
    }
    if (!t) t = el.getAttribute("aria-label") || "";
    const host = el.getRootNode && el.getRootNode().host;   // a field inside a web component: its label lives there
    if (!t && host) t = host.getAttribute("label") || labelText(el.getRootNode().querySelector("label")) || "";
    if (!t) {
      const box = el.closest(".application-question")
        || el.closest("fieldset, .field, .select__container, [class*=field], [class*=question], li, .form-group");
      const l = box && box.querySelector("label, legend, .application-label, [class*=label]");
      t = l ? labelText(l) : "";
    }
    if (!t) t = el.placeholder || el.name || el.id || "";
    return norm(t.replace(/[*✱]/g, ""));
  }

  // kits/rules.json (written by build_kits.py) overrides the built-in RULES, so new questions need no reload.
  let activeRules = RULES;
  async function loadRules() {
    try {
      const raw = await kitFile("kits/rules.json");
      activeRules = raw.map(([pattern, key]) => [new RegExp(pattern), key]);
    } catch (e) { activeRules = RULES; }
  }

  function lookup(label, kit) {
    const L = low(label);
    for (const q of kit.questions || []) {
      if ((q.match || []).every(k => L.includes(String(k).toLowerCase()))) { if (q.review && String(q.value).length > 30) drafted.add(norm(label)); return q.value; }
    }
    for (const [re, key] of activeRules) {
      if (!re.test(L)) continue;
      if (key === "years") {   // "How many years of experience do you have with SQL?" -> the matching topic, if any
        const map = kit.answers.years || {};
        // Longest topic first, whole words only ("ai" must not match "email" or "maintain")
        const hasWords = t => new RegExp(`(^|[^a-z0-9])${t.toLowerCase().replace(/[.*+?^${}()|[\]\\/]/g, "\\$&")}($|[^a-z0-9])`).test(L);
        const topic = Object.keys(map).sort((a, b) => b.length - a.length).find(hasWords);
        return topic ? String(map[topic]) : (/work experience\b|in total|overall|professional experience/.test(L) && map.total ? String(map.total) : undefined);
      }
      return key ? kit.answers[key] : IGNORE;
    }
    return undefined;
  }
  const drafted = new Set();   // labels answered with a drafted (not standard) answer in this fill
  const IGNORE = Symbol("ignore"); // a rule maps this label to "leave it alone" (e.g. phone country picker)

  function setNative(el, value) {
    const proto = el.tagName === "TEXTAREA" ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value").set.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
    el.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    el.dispatchEvent(new Event("blur", { bubbles: true }));
  }

  const asList = v => (Array.isArray(v) ? v : [v]).filter(x => x !== undefined && x !== null).map(String);

  // "*band:N*" picks the range option that contains N ("90 000 EUR - 100 000 EUR", "less than 40k", "more than 220 000");
  // "*any*" picks the first real option (only used as the last fallback for low-stakes questions).
  const nums = t => (String(t).replace(/(\d)[\s,.'](?=\d{3}\b)/g, "$1").match(/\d+(?:\.\d+)?\s*k?/gi) || [])
    .map(x => parseFloat(x) * (/k/i.test(x) ? 1000 : 1));
  function bandPick(items, text, n) {
    const ranged = items.map(it => {
      const t = low(text(it)), v = nums(t);
      if (!v.length) return null;
      if (/less than|under|below|up to/.test(t)) return { it, lo: 0, hi: v[0] };
      if (/more than|over|above|\+|or more/.test(t)) return { it, lo: v[0], hi: Infinity };
      return { it, lo: v[0], hi: v[1] ?? v[0] };
    }).filter(Boolean);
    const top = Math.max(...ranged.map(r => (r.hi === Infinity ? r.lo : r.hi)));
    if (!ranged.length || n > top * 3 || n < top / 20) return null;   // wrong scale (monthly vs yearly)
    // A floor of 90,000 picks "90 000 - 100 000", and with bands like "85,001 - 90,000 / 90,001 - 95,000" the one
    // starting just above it (a floor means "or above").
    const hit = ranged.find(r => n >= r.lo && n < r.hi) || ranged.find(r => r.lo > n && r.lo <= n * 1.02)
      || ranged.find(r => n >= r.lo && n <= r.hi) || ranged.find(r => r.hi === Infinity && n >= r.lo);
    return hit ? hit.it : null;
  }
  const PLACEHOLDER = /^(select|choose|please|--|—|$)/i;
  // One wanted value against the options: exact, then prefix, then all of its words ("Asian (Indian)" finds
  // "Asian - Indian"), then substring. A one-word value that fits several options ("Asian" → "Asian - Chinese" and
  // "Asian - Indian") is ambiguous: it is skipped, so a more specific value wins or the question is flagged.
  const wordsOf = s => low(s).match(/[a-z0-9]+/g) || [];
  function matchOne(texts, w) {
    const W = low(w), ws = wordsOf(w);
    const exact = texts.find(t => low(t.text) === W);
    if (exact) return exact;
    for (const test of [t => low(t.text).startsWith(W),
                        t => ws.length > 1 && ws.every(x => wordsOf(t.text).includes(x)),
                        t => W.length >= 6 && low(t.text).includes(W)]) {
      const hits = texts.filter(test);
      if (hits.length === 1 || (hits.length > 1 && ws.length > 1)) return hits[0];
      if (hits.length > 1) return null;
    }
    return null;
  }
  const pick = (texts, wanted) => {
    for (const w of asList(wanted)) {
      const band = /^\*band:(\d+)\*$/.exec(w);
      const hit = band ? bandPick(texts, t => t.text, +band[1])
        : w === "*any*" ? texts.find(t => !PLACEHOLDER.test(t.text.trim()))
        : matchOne(texts, w);
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

  // Type-to-search dropdowns that aren't React-select (Ashby: "Current Location", "How did you get to know us?"):
  // open the list and click a wanted option; if none shows, type each wanted value and click the first match.
  async function fillTypeahead(el, wanted) {
    const options = () => {
      const lb = el.getAttribute("aria-controls") && document.getElementById(el.getAttribute("aria-controls"));
      return [...(lb || document).querySelectorAll("[role=option]")].filter(o => o.offsetParent !== null)
        .map(o => ({ el: o, text: norm(o.innerText) }));
    };
    const type = v => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, v);
      el.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
    };
    const choose = async want => {
      for (let i = 0; i < 10; i++) {
        await sleep(300);
        const hit = pick(options(), want);
        if (hit) {
          ["mousedown", "mouseup", "click"].forEach(t => hit.el.dispatchEvent(new MouseEvent(t, { bubbles: true })));
          await sleep(300);
          return true;
        }
      }
      return false;
    };
    el.focus(); el.click();
    if (await choose(wanted)) return true;
    for (const w of asList(wanted).filter(w => !w.startsWith("*"))) {
      type(w);
      if (await choose([w])) return true;
    }
    type("");
    return false;
  }

  // The nearest visible words around a field, through web-component hosts ("Resume *" over SmartRecruiters' drop zone;
  // its other drop zone, "or Apply With Indeed", only imports a CV to pre-fill the form and is left alone).
  function nearText(el) {
    let n = el;
    for (let k = 0; k < 8 && n; k++) {
      n = (n.getRootNode() && n.getRootNode().host) || n.parentElement;
      for (let up = n, j = 0; up && j < 4; j++, up = up.parentElement) {
        const t = norm(up.innerText || "");
        if (t) return t.slice(0, 60);
      }
    }
    return "";
  }

  const hostTags = el => { const t = []; for (let n = el; n && n.getRootNode && n.getRootNode().host; n = n.getRootNode().host) {
    for (let up = n.getRootNode().host; up; up = up.parentElement) t.push(up.tagName.toLowerCase()); } return t; };
  async function putFile(input, kit, kind) {
    const path = kit.files[kind], name = path.split("/").pop();
    const blob = await dataUrlToBlob(await kitFile(path, "dataurl"));
    const type = name.endsWith(".pdf") ? "application/pdf" : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    const dt = new DataTransfer();
    dt.items.add(new File([blob], name, { type }));
    input.files = dt.files;
    input.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
    input.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    return name;
  }
  // SmartRecruiters asks for Experience and Education as separate entries ("Add" per job). Its own "apply with resume"
  // box reads the CV and fills them, with name and contact details: so the CV goes there first, once per form.
  async function smartRecruitersPrefill(kit, report) {
    if (location.hostname !== "jobs.smartrecruiters.com" || !kit.files.cv) return;
    const zone = deepAll(document, "input[type=file]").find(i => hostTags(i).includes("oc-apply-with-resume"));
    const key = `rolewise:srPrefill:${kit.id}:${location.pathname}`;
    try { if (!zone || sessionStorage.getItem(key)) return; sessionStorage.setItem(key, "1"); } catch (e) { if (!zone) return; }
    show("Reading your CV into the form (experience and education)…");
    await putFile(zone, kit, "cv");
    const filledIn = () => /\S/.test(((document.querySelector("oc-experience") || {}).innerText || "").replace(/Experience|\*|Add/g, ""));
    for (let i = 0; i < 40 && !filledIn(); i++) await sleep(500);   // up to 20 s for the CV to be read
    await sleep(1500);
    report.filled.push(filledIn() ? "Experience and education (read from your CV: check the dates)" : "CV sent to the form's autocomplete");
  }

  async function attachFiles(kit, report) {
    await smartRecruitersPrefill(kit, report);
    // Upload widgets (Homerun, Workable) can render after the text fields: wait up to 8s for them.
    for (let i = 0; i < (STEP_MODE ? 2 : 16) && !deepAll(ROOT, "input[type=file]").length; i++) await sleep(500);
    const inputs = deepAll(ROOT, "input[type=file]");
    for (const input of inputs) {
      const L = low(labelFor(input) + " " + input.id + " " + input.name + " " + nearText(input));
      const kind = /cover/.test(L) ? "cover_letter" : /resume|cv\b|curriculum/.test(L) ? "cv" : null;
      if (!kind || !kit.files[kind] || (input.files && input.files.length)) continue;
      const path = kit.files[kind];
      const name = path.split("/").pop();
      // Some widgets upload on change and then clear the input: look for the file name nearby to avoid duplicates.
      const box = input.closest("fieldset, [class*=question], [class*=field], [class*=upload], li") || input.parentElement;
      if (report.filled.some(f => f.endsWith(name))) continue;
      if (box && box.innerText.includes(name)) { report.filled.push(`${kind === "cv" ? "CV" : "Cover letter"}: ${name}`); continue; }
      const blob = await dataUrlToBlob(await kitFile(path, "dataurl"));
      const type = name.endsWith(".pdf") ? "application/pdf"
        : "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
      const dt = new DataTransfer();
      dt.items.add(new File([blob], name, { type }));
      input.files = dt.files;
      input.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
      input.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
      report.filled.push(`${kind === "cv" ? "CV" : "Cover letter"}: ${name}`);
    }
  }

  async function fill(kit, second = false) {
    drafted.clear();
    const report = { filled: [], missing: [] };
    if (!second) await attachFiles(kit, report);
    await sleep(second ? 0 : STEP_MODE ? 800 : 3000); // let the form re-render after uploads before typing

    const seen = new Set();
    const answered = new Set();
    const controls = deepAll(ROOT, "input, textarea, select")
      .filter(el => !["hidden", "file", "submit", "button", "search"].includes(el.type) && !el.disabled
        && !(el.id || "").startsWith("g-recaptcha") && el.offsetParent !== null
        && !(WORKDAY && (el.placeholder === "Search" || /dateSection/.test(el.id))));

    for (const el of controls) {
      const label = labelFor(el);
      if (el.type === "radio") {
        if (seen.has(el.name)) continue;
        seen.add(el.name);
        const group = [...document.querySelectorAll(`input[type=radio][name="${CSS.escape(el.name)}"]`)];
        if (group.some(r => r.checked)) continue;
        const qLabel = questionLabel(el);
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
        // Checkbox questions ("How did you hear about us?"): answer the question once, by its fieldset label.
        const fs = el.closest("fieldset") || el.closest(".application-question");
        if (fs && fs.querySelectorAll("input[type=checkbox]").length > 1) {
          if (!seen.has(fs)) {
            seen.add(fs);
            const boxes = [...fs.querySelectorAll("input[type=checkbox]")];
            const q = questionLabel(el);
            const gv = lookup(q, kit);
            if (gv !== undefined && gv !== IGNORE && !boxes.some(b => b.checked)) {
              const hit = pick(boxes.map(b => ({ el: b, text: labelFor(b) })), gv);
              if (hit) { hit.el.click(); report.filled.push(q); answered.add(fs); }
            } else if (boxes.some(b => b.checked)) answered.add(fs);
          }
          continue;   // never treat an option ("Yes", "He/him") as a question of its own
        }
        // A lone tick box under a question ("Previously employed by us?" with just "No"): answer by the question.
        const q1 = questionLabel(el);
        const byQ = lookup(label, kit) === undefined && q1 && q1 !== label;
        const v = byQ ? lookup(q1, kit) : lookup(label, kit);
        if (v === IGNORE) continue;
        if (!el.checked && v && asList(v).some(x => L.startsWith(low(x)))) { el.click(); report.filled.push(byQ ? q1 : label); }
        continue;
      }
      if (el.tagName === "SELECT") {
        if (el.value) continue;
        const v = lookup(label, kit);
        if (v === IGNORE) continue;
        const hit = v && pick([...el.options].map(o => ({ el: o, text: o.text })), v);
        if (hit) { el.value = hit.el.value; el.dispatchEvent(new Event("change", { bubbles: true, composed: true })); report.filled.push(label); }
        else if (el.required) report.missing.push(label);
        continue;
      }
      // Phone with its own country picker (Greenhouse): pick the country from the number's dial code, then type the
      // number without it.
      const phoneBox = el.closest(".phone-input, [class*=phone-input]");
      if (phoneBox && el.getAttribute("role") === "combobox") {
        const box = el.closest(".select__container, .select-shell, [class*=select]");
        if (box && box.querySelector("[class*=single-value], [class*=singleValue]")) continue;
        const dial = DIAL.find(([code]) => String(kit.answers.phone || "").replace(/\s/g, "").startsWith(code));
        if (dial && await fillReactSelect(el, dial[1])) report.filled.push("Phone country");
        else report.missing.push(label);
        continue;
      }
      if (phoneBox && el.type === "tel") {
        if (el.value && !/^\+?\d{1,4}\s*$/.test(el.value.trim())) continue;
        const raw = String(kit.answers.phone || "");
        const dial = DIAL.find(([code]) => raw.replace(/\s/g, "").startsWith(code));
        setNative(el, dial ? raw.replace(/\s/g, "").slice(dial[0].length).replace(/^(\d{2})(\d{3})(\d+)$/, "$1 $2 $3") : raw);
        report.filled.push("Phone");
        continue;
      }
      if (el.getAttribute("role") === "combobox") {
        if (!label || /^\+?\d|country code/i.test(label) && !/reside/i.test(label)) continue; // phone-country picker sets itself
        const box = el.closest(".select__container, .select-shell, [class*=select]");
        if (el.value || box && box.querySelector("[class*=single-value], [class*=singleValue]")) continue;
        const v = lookup(label, kit);
        if (v === IGNORE) continue;
        if (!el.id || !box) {   // type-to-search list; a location one wants a place name, not the long location answer
          const place = /location|based|where .{0,20}(live|reside)/.test(low(label));
          const want = place ? asList(kit.answers.city).concat(asList(kit.answers.residence_country)) : v;
          if (want !== undefined && asList(want).length && await fillTypeahead(el, want)) report.filled.push(label);
          else report.missing.push(label);
          continue;
        }
        let wanted = v;
        if (/location/.test(low(label)) && !/city/.test(low(label)) && kit.answers.location_choice) wanted = asList(v).concat(kit.answers.location_choice);
        if (wanted !== undefined && await fillReactSelect(el, wanted)) report.filled.push(label);
        else report.missing.push(label);
        continue;
      }
      if (el.value) continue;
      const v = lookup(label, kit);
      if (v === IGNORE) continue;
      const picker = el.parentElement && el.parentElement.querySelector("input[name=selectedLocation]");
      if (picker && kit.answers.city) {
        const tries = asList(kit.answers.residence_country).sort((a, b) => b.length - a.length).concat(asList(kit.answers.city));
        let opt = null;
        for (const place of tries) {
          el.focus();
          Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, place);
          el.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
          el.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true, key: place.slice(-1) }));
          el.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true, key: place.slice(-1) }));
          for (let i = 0; i < 10 && !opt; i++) {
            await sleep(400);
            opt = [...el.parentElement.querySelectorAll("[class*=dropdown-location], [class*=dropdown] [class*=result], [class*=dropdown] li, [role=option]")]
              .find(o => o.offsetParent !== null && low(o.innerText).includes(low(place)));
          }
          if (opt) break;
        }
        if (opt) { opt.click(); report.filled.push(label); } else report.missing.push(label);
        continue;
      }
      if (v !== undefined && !Array.isArray(v)) { setNative(el, String(v)); report.filled.push(label); }
      else if (Array.isArray(v) && v.length) { setNative(el, String(v[0])); report.filled.push(label); }
      else if (el.required || el.getAttribute("aria-required") === "true") report.missing.push(label);
    }
    if (!second) await attachFiles(kit, report);   // upload boxes that appeared while the form was being filled
    if (!second && kit.files.cv && deepAll(ROOT, "input[type=file]").length && !report.filled.some(f => f.startsWith("CV"))) report.missing.push("CV upload (attach it yourself)");
    report.missing.push(...unanswered(controls));
    report.drafted = [...drafted].filter(l => report.filled.includes(l));
    controls.filter(el => report.drafted.includes(labelFor(el)) || report.drafted.includes(questionLabel(el)))
      .forEach(el => { el.style.outline = "3px solid #3b6fd8"; });
    report.filled = [...new Set(report.filled)];
    report.missing = [...new Set(report.missing)].filter(m => m && !report.filled.includes(m));
    // Highlight what still needs the user.
    document.querySelectorAll("[data-rolewise-missing]").forEach(e => { e.style.outline = ""; e.removeAttribute("data-rolewise-missing"); });
    controls.filter(el => report.missing.includes(labelFor(el)) || report.missing.includes(questionLabel(el)))
      .forEach(el => { el.style.outline = "3px solid #e0a800"; el.setAttribute("data-rolewise-missing", "1"); });
    return report;
  }

  // After filling: every visible required question still empty (required attribute, aria-required, or a * in its
  // label) is reported, so the panel never says "all done" while the form would refuse to submit.
  function unanswered(controls) {
    const starred = el => {
      const box = el.closest("fieldset, .field, .application-question, [class*=field], [class*=question], li, .form-group");
      const t = (el.labels && el.labels[0] ? el.labels[0].innerText : "") || (box ? (box.querySelector("label, legend") || {}).innerText || "" : "");
      return /\*/.test(t);
    };
    const needed = el => el.required || el.getAttribute("aria-required") === "true" || starred(el)
      || !!(el.getRootNode().host && el.getRootNode().host.hasAttribute("required"));
    const out = [], radios = new Set();
    for (const el of controls) {
      if (!el.isConnected || el.offsetParent === null || el.disabled) continue;
      if (el.type === "radio") {
        if (radios.has(el.name)) continue; radios.add(el.name);
        const group = [...document.querySelectorAll(`input[type=radio][name="${CSS.escape(el.name)}"]`)];
        if (!group.some(r => r.checked) && needed(el)) out.push(questionLabel(el));
      } else if (el.getAttribute("role") === "combobox") {
        const box = el.closest(".select__container, .select-shell, [class*=select]");
        const has = box && box.querySelector("[class*=single-value], [class*=singleValue], [class*=multi-value], [class*=multiValue]");
        if (!has && !el.value && needed(el)) out.push(labelFor(el));
      } else if (el.type !== "checkbox" && !el.value && needed(el)) out.push(labelFor(el));
    }
    return out.filter(Boolean);
  }

  async function loadIndex() {
    return kitFile("kits/index.json");
  }
  const token = u => (u || "").toLowerCase().replace(/[?#].*$/, "").replace(/\/+$/, "");
  // Workday URLs change on the way (…/apply, /en-US/…/apply/applyManually): match on the requisition id ("_REF089460W").
  const wdReq = u => ((u || "").match(/\/job\/[^?#]*_([A-Za-z0-9-]{4,})(?:\/|$|\?|#)/) || [])[1];
  function matchKit(index) {
    const here = location.href.toLowerCase();
    if (WORKDAY && wdReq(location.href)) {
      const hit = index.find(k => k.urls.some(u => /myworkday/.test(u) && wdReq(u) === wdReq(location.href)));
      if (hit) return hit;
    }
    const jid = (here.match(/(?:jobs\/|token=|gh_jid=|currentjobid=|view\/)(\d{5,})/) || [])[1];
    return index.find(k => k.urls.some(u => {
      const t = token(u);
      const kid = (u.toLowerCase().match(/(?:jobs\/|token=|gh_jid=|view\/)(\d{5,})/) || [])[1];
      return (jid && kid && jid === kid) || (t && here.startsWith(t));
    }));
  }

  // ---------- UI ----------
  // Only on real application forms, never on confirmation/thank-you pages.
  const DONE_TEXT = /thank you for (applying|your application)|application (has been|was) (successfully )?(received|submitted|sent)|successfully (submitted|applied)|your application was sent|and\.\.\.sent|we('| ha)ve received your application|application submitted|you('ve| have) (successfully )?applied/i;
  function isApplicationPage() {
    if (LINKEDIN) return !!linkedinModal();
    if (WORKDAY) return /\/apply\b/.test(location.pathname) && !DONE_TEXT.test((document.body && document.body.innerText || "").slice(0, 4000));
    if (/confirmation|thank-?you|submitted/i.test(location.pathname + location.search)) return false;
    if (DONE_TEXT.test((document.body && document.body.innerText || "").slice(0, 4000))) return false;
    return deepAll(document, FORM_SIGNS).length > 0;
  }
  function markSubmitted() {
    let id = null;
    try { id = sessionStorage.getItem("rolewise:lastKit"); } catch (e) {}
    if (!id) return;
    // Done when the page says so, or when you clicked the form's Submit button and the form then went away
    // (a validation error keeps the form on screen, so that never counts).
    let clicked = 0;
    try { clicked = +sessionStorage.getItem("rolewise:submitClicked") || 0; } catch (e) {}
    const text = document.body && document.body.innerText || "";
    const formShown = deepAll(document, FORM_SIGNS)
      .some(e => e.offsetParent !== null);
    const said = DONE_TEXT.test(text.slice(0, 4000)) || (!LINKEDIN && !formShown && DONE_TEXT.test(text));
    const gone = !LINKEDIN && !WORKDAY && !formShown && Date.now() - clicked < 10 * 60000;
    if (!said && !gone) return;
    try { sessionStorage.removeItem("rolewise:submitClicked"); } catch (e) {}
    try { sessionStorage.removeItem("rolewise:lastKit"); } catch (e) {}
    chrome.storage.local.get({ submitted: [] }, d => {
      if (!d.submitted.includes(id)) chrome.storage.local.set({ submitted: d.submitted.concat(id) });
    });
    chrome.runtime.sendMessage({ type: "rolewise-native", payload: { action: "applied", id } }, res =>
      toast(res && res.ok ? "Application submitted ✓ Marked applied in your tracker."
        : "Application submitted ✓ It leaves your queue now; the tracker marks it applied on the next run."));
  }
  // A short confirmation on the site's thank-you page, so you know it was recorded.
  function toast(msg) {
    const t = document.createElement("div");
    t.style.cssText = "position:fixed;right:16px;top:16px;z-index:2147483647;max-width:320px;background:#1f7a4d;color:#fff;" +
      "font:14px/1.4 -apple-system,Segoe UI,Arial,sans-serif;padding:12px 14px;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.2)";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 10000);
  }
  const submittedIds = () => new Promise(r => chrome.storage.local.get({ submitted: [] }, d => r(d.submitted)));
  const filledKey = () => "rolewise:filled:" + location.href.split("#")[0];
  const alreadyFilled = () => { if (STEP_MODE) return false; try { return sessionStorage.getItem(filledKey()) === "1"; } catch (e) { return false; } };

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
    if (opening && !body.innerHTML) body.innerHTML = "Click Fill to complete this form.";
  };
  ui.querySelector("#jf-min").onclick = () => open(false);
  const show = html => { open(true); body.innerHTML = html; };
  // One fill at a time: while filling, the button is visibly disabled and clicks are ignored.
  let busy = false;
  const setBusy = v => {
    busy = v; btn.disabled = v;
    btn.style.opacity = v ? "0.5" : "1"; btn.style.cursor = v ? "not-allowed" : "pointer";
    if (v) btn.textContent = "Filling…"; else refreshState();
  };
  const tab = ui.querySelector("#jf-tab");
  const setTab = (text, colour) => { tab.textContent = text; tab.style.background = colour || "#1d3461"; };
  const refreshState = () => {
    if (busy) return;
    btn.textContent = STEP_MODE ? "Fill this step" : WORKDAY ? (wdActive() ? "Continue filling" : "Fill all pages") : "Fill with Rolewise";
    btn.style.display = alreadyFilled() ? "none" : "block";   // filled: the job now is to review and submit
    if (alreadyFilled()) body.innerHTML ||= `Filled. Review the form and click its Submit button.${again}`;
  };
  // A quiet link, not a button: refilling is rarely needed (e.g. the page reloaded and lost what was typed).
  const again = `<div style="margin-top:10px;font-size:12px"><a href="#" data-rolewise-again style="color:#5b6880">Fill again</a></div>`;
  body.addEventListener("click", e => {
    if (!e.target.closest("[data-rolewise-again]")) return;
    e.preventDefault(); btn.click();
  });


  // React sites (Greenhouse) re-render the whole document while hydrating and drop foreign nodes, so attach after
  // the page settles, re-attach if it disappears, and remove it once the page stops being an application form.
  let forced = false;   // opened by hand ("Fill this page"): stay on this page whatever it looks like
  chrome.runtime.onMessage.addListener(msg => {
    if (!msg || msg.type !== "rolewise-fill-page" || window.top !== window) return;
    forced = true;
    if (!ui.isConnected) document.body.appendChild(ui);
    refreshState();
    btn.click();
  });
  if (window.top === window) {
    let autoDone = false;
    const sync = () => {
      const want = forced || isApplicationPage();
      if (want && !ui.isConnected) { document.body.appendChild(ui); refreshState(); }
      if (!want && ui.isConnected) ui.remove();
      // A confirmation page after Rolewise filled a form here: drop that job from the Ready queue.
      markSubmitted();
      // Opened from the briefing's "Open & fill" button (#rolewise-fill): fill once, automatically.
      if (want && !STEP_MODE && !autoDone && /(rolewise|jobify)-fill/.test(location.hash) && !alreadyFilled()) { autoDone = true; btn.click(); }
      if (WORKDAY) wdTick();
    };
    // Note when you click the form's own Submit button on a page Rolewise filled.
    document.addEventListener("click", e => {
      const b = e.target.closest && e.target.closest("button, input[type=submit], [role=button]");
      if (!b || ui.contains(b) || !/submit|send application|apply now|^apply$/i.test(norm(b.innerText || b.value || ""))) return;
      try { if (sessionStorage.getItem("rolewise:lastKit")) sessionStorage.setItem("rolewise:submitClicked", String(Date.now())); } catch (err) {}
    }, true);
    setTimeout(sync, 2500);
    setInterval(sync, 2000);
  }

  const today = () => new Date().toISOString().slice(0, 10);
  async function linkedinCapReached(kitId) {
    const d = await new Promise(r => chrome.storage.local.get({ liDay: "", liJobs: [] }, r));
    const jobs = d.liDay === today() ? d.liJobs : [];
    if (jobs.includes(kitId)) return false;
    if (jobs.length >= 15) return true;
    chrome.storage.local.set({ liDay: today(), liJobs: jobs.concat(kitId) });
    return false;
  }
  // Free-text questions: a small "✨ Draft" bar right under the field. Claude writes the answer into the field from the
  // job and the CV facts in the kit (background.js, the user's own API key); Redraft / Shorter / More specific refine it.
  const draftable = label => !/^cv upload|consent|acknowledg|privacy/i.test(label) && label.length > 25;
  const freeText = el => (el.tagName === "TEXTAREA" || (el.type === "text" && !el.closest("[class*=select]") && el.getAttribute("role") !== "combobox"))
    && !el.parentElement.querySelector("input[name=selectedLocation]");
  function draftBar(el, kit, question) {
    // A field inside a web component (SmartRecruiters): the bar goes under the component, in the page itself.
    let anchor = el;
    while (anchor.getRootNode && anchor.getRootNode().host) anchor = anchor.getRootNode().host;
    if (anchor.nextElementSibling && anchor.nextElementSibling.dataset && anchor.nextElementSibling.dataset.rolewiseBar) return;
    const bar = document.createElement("div");
    bar.dataset.rolewiseBar = "1";
    bar.style.cssText = "display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0 10px;font:13px/1.3 -apple-system,Segoe UI,Arial,sans-serif";
    const mk = (text, primary) => {
      const b = document.createElement("button");
      b.type = "button"; b.textContent = text;
      b.style.cssText = primary
        ? "background:#1d3461;color:#fff;border:0;border-radius:7px;padding:6px 12px;font-weight:600;cursor:pointer"
        : "background:#fff;color:#1d3461;border:1px solid #c9d4e8;border-radius:7px;padding:5px 10px;cursor:pointer";
      return b;
    };
    const status = document.createElement("span");
    status.style.color = "#5b6880";
    const draftBtn = mk(el.value ? "✨ Redraft" : "✨ Draft with Rolewise", true);
    const refine = [["Shorter", "make it about half as long"], ["More specific", "make it more specific to this job, with one concrete result"],
                    ["Warmer", "make it a little warmer and more personal, same facts"]].map(([t, how]) => [mk(t), how]);
    let previous = "";
    const ask = async instruction => {
      status.textContent = "Drafting…";
      [draftBtn, ...refine.map(r => r[0])].forEach(b => { b.disabled = true; b.style.opacity = ".5"; });
      const res = await chrome.runtime.sendMessage({ type: "rolewise-draft", question, job: `${kit.title} at ${kit.company}`,
        facts: kit.context || "", jobDescription: kit.jd || "", previous: instruction ? (el.value || previous) : "", instruction });
      [draftBtn, ...refine.map(r => r[0])].forEach(b => { b.disabled = false; b.style.opacity = "1"; });
      if (res && res.needKey) {
        status.innerHTML = 'Add your Anthropic API key once to draft here. <a href="#" style="color:#1d3461">Open settings</a>';
        status.querySelector("a").onclick = e => { e.preventDefault(); chrome.runtime.sendMessage({ type: "rolewise-options" }); };
        return;
      }
      if (!res || res.error) { status.textContent = (res && res.error) || "Couldn't draft. Try again."; return; }
      previous = res.text;
      setNative(el, res.text);
      el.style.outline = "3px solid #3b6fd8";
      draftBtn.textContent = "✨ Redraft";
      refine.forEach(([b]) => { b.hidden = false; });
      status.textContent = "Drafted from your CV. Check it, edit freely.";
    };
    draftBtn.onclick = () => ask("");
    refine.forEach(([b, how]) => { b.hidden = !el.value; b.onclick = () => ask(how); });
    bar.append(draftBtn, ...refine.map(r => r[0]), status);
    anchor.insertAdjacentElement("afterend", bar);
  }
  function addDraftBars(kit, controls, labels) {
    for (const el of controls) {
      if (!el.isConnected || el.offsetParent === null || !freeText(el)) continue;
      const q = labelFor(el);
      // Open questions, drafted answers, and every written answer already in a text box (Redraft, Shorter...).
      const written = el.tagName === "TEXTAREA" && norm(el.value).length > 40;
      if ((labels.includes(q) || written) && draftable(q)) draftBar(el, kit, q);
    }
  }

  async function run(kitId) {
    if (WORKDAY) return wdStart(kitId);
    if (LINKEDIN && await linkedinCapReached(kitId)) {
      show("You've reached today's 15 LinkedIn applications. Rolewise keeps this cap to protect your account; carry on tomorrow.");
      return;
    }
    ROOT = (LINKEDIN && linkedinModal()) || document;
    show(STEP_MODE ? "Filling this step…" : "Filling… this takes about 10 seconds.");
    setBusy(true);
    await loadRules();
    const kit = await kitFile(`kits/${kitId}.json`);
    let r = await fill(kit);
    // A second pass only when something is still open (fields that appear after the first answers or uploads).
    if (!STEP_MODE && r.missing.length) {
      body.innerHTML = `Almost done: checking ${r.missing.length} field${r.missing.length > 1 ? "s" : ""} again…`;
      await sleep(1500);
      const again2 = await fill(kit, true);
      again2.filled = [...new Set(r.filled.concat(again2.filled))];
      again2.missing = [...new Set(r.missing.concat(again2.missing))].filter(m => !again2.filled.includes(m)
        && !(m.startsWith("CV upload") && again2.filled.some(f => f.startsWith("CV"))));
      again2.drafted = [...new Set((r.drafted || []).concat(again2.drafted || []))];
      r = again2;
    }
    try { sessionStorage.setItem(filledKey(), "1"); sessionStorage.setItem("rolewise:lastKit", kitId); } catch (e) {}
    setBusy(false);
    const esc = x => String(x).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
    // "✨ Draft" is offered only for written answers, never for dropdowns or pickers.
    const writable = new Set(deepAll(ROOT, "textarea, input[type=text]").filter(freeText).map(labelFor));
    const draftable2 = x => draftable(x) && writable.has(x);
    // Questions in a few words: up to the first "?" (or sentence end), at most 60 characters.
    const short = x => { const s = norm(x).match(/^.*?\?|^.*?\.(?=\s)|^.*/)[0]; return s.length > 60 ? s.slice(0, 57).trimEnd() + "…" : s; };
    const item = (x, i, kind) => `<li style="margin:3px 0"><a href="#" data-rw-go="${kind}${i}" style="color:inherit;text-decoration:none;border-bottom:1px dotted">${esc(short(x))}</a>` +
      (kind === "m" && draftable2(x) ? ` <span style="color:#3b6fd8;white-space:nowrap">✨ Draft below it</span>` : "") + `</li>`;
    const list = (xs, kind) => `<ul style="margin:4px 0 0;padding-left:18px">${xs.map((x, i) => item(x, i, kind)).join("")}</ul>`;
    const ticks = r.filled.filter(x => x.startsWith("☑")).length;
    const plain = r.filled.filter(x => !x.startsWith("☑"));
    const sec = (colour, title, html) => `<div style="margin-top:10px;padding:8px 10px;border-left:3px solid ${colour};background:#f7f9fc;border-radius:6px">` +
      `<div style="font-weight:700;color:${colour}">${title}</div>${html}</div>`;
    show(`<div style="font-weight:700">${esc(kit.company)}</div><div style="color:#5b6880;font-size:13px">${esc(kit.title)}</div>
      ${r.missing.length ? sec("#9a5b00", `${r.missing.length} for you to answer`, list(r.missing, "m"))
        : sec("#1f7a4d", "Everything is filled", "")}
      ${r.drafted.length ? sec("#3b6fd8", `${r.drafted.length} written for you, check the wording`, list(r.drafted, "d")) : ""}
      <div style="margin-top:10px;font-weight:600">${STEP_MODE ? "Check this step, then click Next. On the next step, click Fill this step again." : "Then review and click the form's Submit button."}</div>
      <details style="margin-top:8px;font-size:12px;color:#5b6880"><summary style="cursor:pointer">${plain.length} answers filled${ticks ? ` · ${ticks} consent box${ticks > 1 ? "es" : ""} ticked` : ""}</summary>
        <ul style="margin:4px 0 0;padding-left:18px">${plain.map(x => `<li>${esc(short(x))}</li>`).join("")}</ul></details>
      ${again}`);
    // Click a question in the summary to jump to it on the form.
    body.querySelectorAll("[data-rw-go]").forEach(a => a.onclick = e => {
      e.preventDefault();
      const [kind, i] = [a.dataset.rwGo[0], +a.dataset.rwGo.slice(1)];
      const want = (kind === "m" ? r.missing : r.drafted)[i];
      const el = deepAll(ROOT, "input, select, textarea").find(c => labelFor(c) === want || questionLabel(c) === want);
      if (el) { el.scrollIntoView({ block: "center", behavior: "smooth" }); try { el.focus({ preventScroll: true }); } catch (err) {} }
    });
    addDraftBars(kit, deepAll(ROOT, "textarea, input[type=text]"), r.missing.concat(r.drafted || []));
    // Get out of the way of the form's own Submit button: collapse to the edge tab, which keeps the status.
    if (r.missing.length) {
      setTab(`${r.missing.length} TO CHECK`, "#9a5b00");
      const first = document.querySelector("[data-rolewise-missing]");
      if (first) first.scrollIntoView({ block: "center", behavior: "smooth" });
    } else setTab("FILLED ✓", "#1f7a4d");
    // Stay on screen until you submit, docked at the top right, clear of the form's Submit button at the bottom.
    ui.style.top = "12px";
    panel.style.maxHeight = "45vh";
  }

  // ---------- Workday ----------
  // Opened from the Rolewise menu (or "Fill all pages"): Rolewise fills each page, clicks Save and Continue, and stops
  // on Review for you to click Submit. It never types a password and never clicks Submit. It stops early on anything
  // it can't answer (highlighted) or on Workday errors; fix those, then click "Continue filling".
  const WD_KEY = "rolewise:wd";
  const ss = { get: k => { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
               set: (k, v) => { try { sessionStorage.setItem(k, v); } catch (e) {} },
               del: k => { try { sessionStorage.removeItem(k); } catch (e) {} } };
  const wdActive = () => !!ss.get(WD_KEY);
  const vis = el => el && el.offsetParent !== null;
  const byText = (sel, re) => [...document.querySelectorAll(sel)].find(b => vis(b) && re.test(norm(b.innerText || b.value || "")));
  const wdStepName = () => {
    const m = ((document.querySelector("main") || document.body).innerText || "").match(/current step \d+ of \d+\s*\n\s*([^\n]+)/i);
    return m ? low(m[1]) : "";
  };
  const wdOptions = () => [...document.querySelectorAll("[role=option]")].filter(vis)
    .map(o => ({ el: o, text: norm(o.innerText) })).filter(o => o.text && !/^select one$/i.test(o.text));
  const KEYCODE = { Enter: 13, Escape: 27, Backspace: 8, Delete: 46 };
  const press = (el, key) => ["keydown", "keyup"].forEach(t => el.dispatchEvent(new KeyboardEvent(t,
    { key, code: key, keyCode: KEYCODE[key], which: KEYCODE[key], bubbles: true })));
  const tap = el => ["mousedown", "mouseup", "click"].forEach(t => el.dispatchEvent(new MouseEvent(t, { bubbles: true })));
  function typeIn(el, v) {   // text into a React-controlled box without blurring it (search boxes, date parts)
    el.focus();
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, v);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // A "Select One" dropdown (button with a listbox): open it and click the wanted option.
  async function wdChoose(btn, wanted, highest = false) {
    btn.scrollIntoView({ block: "center" });
    btn.click();
    await sleep(700);
    const opts = wdOptions();
    const hit = highest ? (opts.find(o => /native|bilingual|expert|mother/i.test(o.text)) || opts[opts.length - 1])
      : pick(opts, wanted);
    if (!hit) { btn.click(); await sleep(300); return false; }
    tap(hit.el);
    await sleep(600);
    return !/^select one$/i.test(norm(btn.innerText));
  }
  // Search lists ("How did you hear", school, field of study): Workday picks the result by itself when the search
  // finds exactly one, even a wrong one, so every pick is checked and a wrong one removed.
  const promptBox = el => { let n = el; for (let i = 0; i < 7 && n; i++, n = n.parentElement) if (n.querySelector("[role=listbox]")) return n; return el.parentElement; };
  const chips = el => [...promptBox(el).querySelectorAll("[role=listbox] [role=option]")]
    .map(o => norm(o.innerText).replace(/,? press delete.*$/i, "")).filter(Boolean);
  async function unchip(el) {
    for (const o of promptBox(el).querySelectorAll("[role=listbox] [role=option]")) { o.focus(); press(o, "Delete"); press(o, "Backspace"); }
    typeIn(el, ""); press(el, "Backspace");
    await sleep(500);
    return !chips(el).length;
  }
  const fits = (got, w) => got.some(c => matchOne([{ text: c }], w));
  async function wdPrompt(el, wanted) {
    if (chips(el).length) return true;
    for (const w of asList(wanted).filter(w => !w.startsWith("*"))) {
      typeIn(el, w); press(el, "Enter");
      await sleep(1800);
      if (chips(el).length) {
        if (fits(chips(el), w)) return true;
        if (!(await unchip(el))) return false;   // a wrong auto-pick that won't go: left for you (flagged)
        continue;
      }
      for (let depth = 0; depth < 2; depth++) {   // some lists have two levels (a category, then the item)
        const hit = pick(wdOptions(), [w]);
        if (!hit) break;
        tap(hit.el.querySelector("[data-automation-id=promptOption], [data-automation-id=checkboxPanel]") || hit.el);
        await sleep(900);
        if (chips(el).length) break;
      }
      if (fits(chips(el), w)) { press(el, "Escape"); return true; }
      if (chips(el).length && !(await unchip(el))) return false;
    }
    typeIn(el, ""); press(el, "Escape");
    return false;
  }
  async function wdDate(prefix, value) {   // "01/2026" (month/year) or 2012 (year only)
    const s = String(value || "");
    if (!s) return true;
    const [m, y] = s.includes("/") ? s.split("/") : ["", s];
    const mEl = document.getElementById(`${prefix}-dateSectionMonth-input`), yEl = document.getElementById(`${prefix}-dateSectionYear-input`);
    for (const [el, v] of [[mEl, m && String(+m)], [yEl, y]]) {
      if (!el || !v) continue;
      typeIn(el, v);
      el.dispatchEvent(new FocusEvent("blur", { bubbles: true }));
      await sleep(150);
    }
    return (!mEl || !m || +mEl.value === +m) && (!yEl || +yEl.value === +y);
  }
  const sectionOf = name => [...document.querySelectorAll("main [role=group]")]
    .find(g => new RegExp(`^${name}`, "i").test(g.getAttribute("aria-labelledby") || ""));
  const entries = idEnd => [...document.querySelectorAll(`[id$="${idEnd}"]`)].map(e => e.id.slice(0, -idEnd.length));
  async function wdAdd(name, idEnd) {   // "Add" / "Add Another" in a section; returns the new entry's id prefix
    const sec = sectionOf(name);
    const b = sec && [...sec.querySelectorAll("button")].find(b => /^add( another)?$/i.test(norm(b.innerText)));
    if (!b) return null;
    const before = new Set(entries(idEnd));
    b.click();
    for (let i = 0; i < 10; i++) {
      await sleep(400);
      const neu = entries(idEnd).find(p => !before.has(p));
      if (neu) return neu;
    }
    return null;
  }
  const byId = id => document.getElementById(id);
  const setIfEmpty = (id, v) => { const el = byId(id); if (el && !el.value && v) setNative(el, v); };

  async function wdExperience(kit, report) {
    const h = kit.history || {};
    // Work history: one entry per role. A page that already has entries (a saved draft) is left as it is.
    let jobs = entries("--jobTitle");
    if (!jobs.some(p => byId(p + "jobTitle").value)) {
      for (const [i, j] of (h.experience || []).entries()) {
        const p = jobs[i] || await wdAdd("Work-Experience", "--jobTitle");
        if (!p) { report.missing.push(`Work experience: ${j.company}`); continue; }
        jobs = entries("--jobTitle");
        setIfEmpty(p + "jobTitle", j.title); setIfEmpty(p + "companyName", j.company);
        setIfEmpty(p + "location", j.location); setIfEmpty(p + "roleDescription", j.description);
        const cur = byId(p + "currentlyWorkHere");
        if (cur && j.current && !cur.checked) cur.click();
        const ok = (await wdDate(p + "startDate", j.from)) && (j.current || await wdDate(p + "endDate", j.to));
        (ok ? report.filled : report.missing).push(`${j.title}, ${j.company}${ok ? "" : ": dates"}`);
      }
    }
    // Education: every degree (answers.yaml education_entries), whatever "highest level" says.
    let eds = entries("--school");
    if (!eds.some(p => chips(byId(p + "school")).length)) {
      for (const [i, e] of (h.education || []).entries()) {
        const p = eds[i] || await wdAdd("Education", "--school");
        if (!p) { report.missing.push("Education"); continue; }
        eds = entries("--school");
        const ok = [await wdPrompt(byId(p + "school"), e.school)];
        if (byId(p + "degree")) ok.push(await wdChoose(byId(p + "degree"), e.degree));
        if (byId(p + "fieldOfStudy")) ok.push(await wdPrompt(byId(p + "fieldOfStudy"), e.field));
        await wdDate(p + "firstYearAttended", e.from);
        await wdDate(p + "lastYearAttended", e.to);
        (ok.every(Boolean) ? report.filled : report.missing).push(`Education: ${asList(e.degree)[0]}`);
      }
    }
    // Languages: from answers.yaml, "highest" = the top level on offer.
    let langs = entries("--language");
    if (sectionOf("Languages") && !langs.some(p => !/select one/i.test(norm(byId(p + "language").innerText)))) {
      for (const [i, l] of (h.languages || []).entries()) {
        const p = langs[i] || await wdAdd("Languages", "--language");
        if (!p) break;
        langs = entries("--language");
        const ok = await wdChoose(byId(p + "language"), [l.language]);
        const fl = byId(p + "native");
        if (fl && !fl.checked) fl.click();
        for (const b of document.querySelectorAll(`button[id^="${p}"][aria-haspopup=listbox]`))
          if (b.id !== p + "language" && /select one/i.test(norm(b.innerText))) await wdChoose(b, [], true);
        (ok ? report.filled : report.missing).push(`Language: ${l.language}`);
      }
    }
    // Certifications stay on the CV: Workday's fixed lists rarely have them, and a near match would be untrue.
    // CV: the PDF. A file left from an earlier try (e.g. the Word version) is removed first.
    const sec = sectionOf("Resume");
    const name = kit.files.cv.split("/").pop();
    if (sec && !(sec.innerText || "").includes(name)) {
      for (const b of [...sec.querySelectorAll("button")].filter(b => /^delete .+\.\w{3,4}$/i.test(b.getAttribute("aria-label") || ""))) { b.click(); await sleep(800); }
      const input = sec.querySelector("input[type=file]");
      if (input) { await putFile(input, kit, "cv"); for (let i = 0; i < 20 && !(sec.innerText || "").includes(name); i++) await sleep(500); }
      ((sec.innerText || "").includes(name) ? report.filled : report.missing).push(`CV upload: ${name}`);
    }
  }

  // Every page: dropdowns, search lists, yes/no radios, text boxes and the standard consent boxes, from the kit.
  const localPhone = kit => {
    const raw = String(kit.answers.phone || "").replace(/\s/g, ""), dial = DIAL.find(([c]) => raw.startsWith(c));
    return dial ? raw.slice(dial[0].length) : raw;
  };
  function wdLookup(label, kit) {   // Workday's own fields first, then the usual answers
    const L = low(label);
    if (/^country$|country\/region/.test(L)) return kit.answers.residence_country;
    if (/country phone code/.test(L)) return kit.answers.residence_country;
    if (/device type/.test(L)) return ["Mobile", "Mobile Phone", "Cell"];
    if (/^emirate|^state\b|province/.test(L)) return asList(kit.answers.city);
    return lookup(label, kit);
  }
  async function wdGeneric(kit, report) {
    const main = document.querySelector("main") || document;
    const ph = byId("phoneNumber--phoneNumber");
    if (ph && !ph.value && kit.answers.phone) { setNative(ph, localPhone(kit)); report.filled.push("Phone"); }
    for (const b of [...main.querySelectorAll("button[aria-haspopup=listbox]")].filter(vis)) {
      if (!/^select one$/i.test(norm(b.innerText)) || /^(education|language|workExperience|certification)-/.test(b.id)) continue;
      const label = labelFor(b).replace(/select one|required/gi, "").trim();
      const v = wdLookup(label, kit);
      if (v === IGNORE) continue;
      if (v === undefined) { report.missing.push(label); continue; }
      (await wdChoose(b, v) ? report.filled : report.missing).push(label);
    }
    for (const el of [...main.querySelectorAll("input[placeholder=Search]")].filter(vis)) {
      if (/^(education|certification|language)-/.test(el.id) || /skill/i.test(labelFor(el)) || chips(el).length) continue;
      const label = labelFor(el);
      const v = wdLookup(label, kit);
      const required = el.getAttribute("aria-required") === "true" || /\*/.test((el.labels && el.labels[0] && el.labels[0].innerText) || "");
      if (v === undefined || v === IGNORE) { if (required) report.missing.push(label); continue; }
      (await wdPrompt(el, v) ? report.filled : report.missing).push(label);
    }
    const saved = ROOT;
    ROOT = main;
    try {
      const r = await fill(kit, true);   // text boxes, radios, consent boxes (no uploads on this pass)
      report.filled.push(...r.filled);
      report.missing.push(...r.missing.filter(m => !/^(month|year|day|search|mm|yyyy|dd)$/i.test(m)));
    } finally { ROOT = saved; }
  }

  async function wdFillPage(kit) {
    const report = { filled: [], missing: [] };
    if (/experience/.test(wdStepName())) await wdExperience(kit, report);
    await wdGeneric(kit, report);
    report.missing = [...new Set(report.missing)].filter(Boolean);
    return report;
  }

  const escH = x => String(x).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  function wdStop(kit, why, list = []) {
    ss.set(WD_KEY, "paused:" + kit.id);
    show(`<div style="font-weight:700">${escH(kit.company)}</div><div style="color:#9a5b00;margin-top:6px;font-weight:600">${escH(why)}</div>` +
      (list.length ? `<ul style="margin:4px 0 0;padding-left:18px">${list.map(x => `<li>${escH(x)}</li>`).join("")}</ul>` : "") +
      `<div style="margin-top:8px">Fix these on the page, then click <b>Continue filling</b>.</div>`);
    setTab(`${list.length || 1} TO CHECK`, "#9a5b00");
    refreshState();
  }
  function wdStart(kitId) {
    ss.set(WD_KEY, kitId);
    ss.set("rolewise:lastKit", kitId);
    ss.del("rolewise:wdTries");
    show("Filling every page of this application. You'll only need to click Submit at the end.");
    setTab("FILLING…", "#1d3461");
    refreshState();
    wdTick();
  }
  let wdBusy = false, wdSaid = "";
  async function wdTick() {
    const state = ss.get(WD_KEY);
    if (!state || state.startsWith("paused:") || wdBusy || busy) return;
    if (!ui.isConnected) document.body.appendChild(ui);
    wdBusy = true;
    try {
      const kit = await kitFile(`kits/${state}.json`);
      const main = (document.querySelector("main") || document.body).innerText || "";
      // Start page: apply manually (Rolewise fills it; Workday's own CV reader often garbles dates).
      const manual = byText("button, a", /^apply manually$/i);
      if (manual && /start your application/i.test(main)) { manual.click(); await sleep(2000); return; }
      // Sign in / create account: Rolewise fills the email; the password is always yours (Chrome can suggest one).
      if ([...document.querySelectorAll("input[type=password]")].some(vis)) {
        const email = [...document.querySelectorAll("input[type=email], input[data-automation-id=email], input[autocomplete=email]")].find(vis);
        if (email && !email.value && kit.answers.email) setNative(email, kit.answers.email);
        const mode = /create account/i.test(main) && !/^sign in$/i.test(norm((byText("button", /^(sign in|create account)$/i) || {}).innerText || "")) ? "create" : "signin";
        if (wdSaid !== mode) {
          wdSaid = mode;
          show(mode === "create"
            ? "<b>Create your account</b><br>Your email is filled. Click the password box and choose Chrome's <i>suggested password</i> (use it for Verify too), tick the box and click Create Account. Rolewise carries on after that; if Workday emails a verification link, open it."
            : "<b>Sign in</b><br>Your email is filled. Let Chrome fill your password and click Sign In. Rolewise carries on after that.");
        }
        return;
      }
      const step = wdStepName();
      if (!step) return;
      if (/review/.test(step)) {
        ss.del(WD_KEY);
        ss.set("rolewise:lastKit", kit.id);
        show(`<div style="font-weight:700">${escH(kit.company)}</div><div style="margin-top:6px;color:#1f7a4d;font-weight:700">Every page is filled ✓</div>` +
          `<div style="margin-top:6px">Read the Review page, then click <b>Submit</b>.</div>`);
        setTab("FILLED ✓", "#1f7a4d");
        refreshState();
        return;
      }
      const tries = JSON.parse(ss.get("rolewise:wdTries") || "{}");
      if ((tries[step] || 0) >= 2) {
        const errs = [...document.querySelectorAll("[data-automation-id=errorMessage], [data-automation-id=errorBanner] li, [role=alert]")]
          .filter(vis).map(e => norm(e.innerText)).filter(Boolean);
        return wdStop(kit, "Workday won't move past this page.", errs.slice(0, 8));
      }
      show(`Filling: ${escH(step.replace(/^./, c => c.toUpperCase()))}…`);
      await sleep(1500);   // let the page finish loading its fields
      const r = await wdFillPage(kit);
      if (r.missing.length) {
        document.querySelectorAll("main button[aria-haspopup=listbox], main input, main textarea").forEach(el => {
          if (r.missing.includes(labelFor(el).replace(/select one|required/gi, "").trim())) el.style.outline = "3px solid #e0a800";
        });
        addDraftBars(kit, [...document.querySelectorAll("main textarea, main input[type=text]")], r.missing);
        return wdStop(kit, `${r.missing.length} for you to answer on this page`, r.missing);
      }
      tries[step] = (tries[step] || 0) + 1;
      ss.set("rolewise:wdTries", JSON.stringify(tries));
      const next = byText("button", /^(save and continue|next|continue)$/i);
      if (!next) return wdStop(kit, "Couldn't find Save and Continue on this page.");
      next.click();   // never Submit: that one is yours
      for (let i = 0; i < 30 && wdStepName() === step; i++) {
        await sleep(500);
        if ([...document.querySelectorAll("[data-automation-id=errorMessage], [data-automation-id=errorBanner]")].some(vis)) break;
      }
    } catch (e) {
      show(`Rolewise stopped: ${escH(e.message)}`);
    } finally { wdBusy = false; }
  }
  // "Continue filling" after a stop.
  if (WORKDAY) btn.addEventListener("click", e => {
    const s = ss.get(WD_KEY);
    if (s && s.startsWith("paused:")) { e.stopImmediatePropagation(); wdStart(s.slice(7)); }
  }, true);
  // Opened from the queue on a posting that has closed: say so and take the job out of the queue (tracker: posting-closed).
  const CLOSED_TEXT = /page you are looking for doesn'?t exist|no longer (accepting applications|available|open)|not currently accepting applications|job (is )?no longer (available|open)|position (has been|is) (filled|closed)|this (job|position|posting) has (expired|closed|been (filled|removed))|job not found|posting (is )?closed/i;
  if (window.top === window && /(rolewise|jobify)-fill/.test(location.hash) && !LINKEDIN) {
    setTimeout(async () => {
      const text = (document.body && document.body.innerText || "").slice(0, 3000);
      if (!CLOSED_TEXT.test(text)) return;
      let kit = null;
      try { kit = matchKit(await loadIndex()); } catch (e) {}
      if (!kit) return;
      ss.del(WD_KEY);
      if (!ui.isConnected) document.body.appendChild(ui);
      show(`<b>${escH(kit.company)}: this posting has closed.</b><div style="margin-top:6px">Rolewise took it out of your queue.</div>`);
      setTab("CLOSED", "#5b6880");
      chrome.runtime.sendMessage({ type: "rolewise-native", payload: { action: "skip", id: kit.id, reason: "posting-closed (seen when opened from the queue)" } }, () => {});
      chrome.storage.local.get({ submitted: [] }, d => { if (!d.submitted.includes(kit.id)) chrome.storage.local.set({ submitted: d.submitted.concat(kit.id) }); });
    }, 7000);
  }
  // Opened from the Rolewise menu: remember the job for this tab, so the fill survives Workday's redirects and sign-in.
  if (WORKDAY && window.top === window && /(rolewise|jobify)-fill/.test(location.hash)) {
    loadIndex().then(index => { const k = matchKit(index); if (k && !ss.get(WD_KEY)) wdStart(k.id); }).catch(() => {});
  }

  let forceAgain = false;
  const esc0 = x => String(x).replace(/[&<>"]/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  body.addEventListener("click", e => {
    if (!e.target.closest("[data-rolewise-force]")) return;
    e.preventDefault(); forceAgain = true; btn.click();
  });
  btn.onclick = async () => {
    if (busy) return;
    if (alreadyFilled() && !confirm("Fill this form again? Anything you typed may be overwritten.")) return;
    try {
      const index = await loadIndex();
      const kit = matchKit(index);
      // Already submitted (tracker or this browser): say so instead of filling the form a second time.
      if (kit && !forceAgain && (!["shortlisted", "preparing", "ready"].includes(kit.status) || (await submittedIds()).includes(kit.id))) {
        show(`<b>You've already applied to this job.</b><div style="margin-top:6px;color:#5b6880">It's marked ${esc0(kit.status === "ready" ? "applied" : kit.status)} in your tracker.</div>` +
          `<div style="margin-top:10px;font-size:12px"><a href="#" data-rolewise-force style="color:#5b6880">Fill anyway</a></div>`);
        setTab("APPLIED ✓", "#1f7a4d");
        return;
      }
      forceAgain = false;
      if (kit) return run(kit.id);
      const page = low(location.hostname + " " + document.title + " " + (document.querySelector("h1") || {}).innerText);
      const company = k => low(k.label.split(" · ")[0]).replace(/\(.*?\)/g, "").trim();
      const ranked = index.filter(k => ["ready", "preparing", "shortlisted"].includes(k.status))
        .map(k => ({ k, hit: company(k).split(/\s+/).some(w => w.length > 2 && page.includes(w)) }))
        .sort((a, b) => b.hit - a.hit || (b.k.fit || 0) - (a.k.fit || 0)).map(x => x.k);
      show(`<b>Which job is this?</b><br><select id="jf-pick" style="width:100%;margin-top:6px">${ranked.map(k => `<option value="${k.id}">${k.label}</option>`).join("")}</select>
        <button id="jf-go" style="margin-top:8px;width:100%;background:#fff;color:#1d3461;border:1px solid #1d3461;border-radius:8px;padding:8px">Fill this job</button>`);
      body.querySelector("#jf-go").onclick = () => run(body.querySelector("#jf-pick").value);
    } catch (e) {
      setBusy(false);
      show(`Couldn't load kits: ${e.message}. Run <code>scripts/build_kits.py</code>.`);
    }
  };
})();
