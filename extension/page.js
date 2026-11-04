// Rolewise Fill page helper. Runs in the page's own JS world (manifest "world": "MAIN") because React-based dropdowns
// (react-select on Greenhouse) only accept a choice through their component, which the isolated content script
// can't reach. content.js sends {reqId, id, wanted} as a JSON string; this replies with {reqId, ok, chosen}.
(() => {
  if (window.__rolewisePage) return;
  window.__rolewisePage = true;

  const low = s => String(s || "").replace(/\s+/g, " ").trim().toLowerCase();

  function findSelect(input) {
    const key = Object.keys(input).find(k => k.startsWith("__reactFiber$"));
    let f = key && input[key], inst = null, load = null;
    for (let d = 0; f && d < 120; d++, f = f.return) {
      if (!inst && f.stateNode && typeof f.stateNode.selectOption === "function") inst = f.stateNode;
      if (!load && f.memoizedProps && typeof f.memoizedProps.loadOptions === "function") load = f.memoizedProps.loadOptions;
      if (inst && load) break;
    }
    return { inst, load };
  }

  const flat = opts => (opts || []).flatMap(o => (o && o.options ? o.options : [o]));
  // Prefix match first; substring match only for longer terms (so "MDI" can't hit an unrelated school name).
  const match = (opts, w) => opts.find(o => low(o.label).startsWith(low(w)))
    || (low(w).length >= 6 ? opts.find(o => low(o.label).includes(low(w))) : undefined);

  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // Paginated async selects return {options, hasMore}; classic ones call back with an array.
  const runLoad = (load, q) => new Promise(res => {
    const done = v => res(Array.isArray(v) ? v : (v && v.options) || []);
    const r = load(q, done, { page: 1 });
    if (r && r.then) r.then(done);
    setTimeout(() => res([]), 4000);
  });
  const hasValue = inst => {
    const v = inst.props.value ?? (inst.state && inst.state.selectValue);
    return Array.isArray(v) ? v.length > 0 : !!v;
  };

  async function choose(id, wanted) {
    const input = document.getElementById(id);
    if (!input) return { ok: false };
    const { inst, load } = findSelect(input);
    if (!inst) return { ok: false };
    for (const w of wanted) {
      let hit = match(flat(inst.props.options), w);
      if (!hit && load) hit = match(flat(await runLoad(load, w)), w);
      if (!hit && typeof inst.props.onInputChange === "function") {
        // Search-as-you-type fields (e.g. Location (City)) fetch options when the text changes.
        inst.props.onInputChange(w, { action: "input-change", prevInputValue: "" });
        await sleep(2500);
        hit = match(flat(inst.props.options), w);
      }
      if (hit) {
        inst.selectOption(hit);
        await sleep(500);
        if (hasValue(inst)) return { ok: true, chosen: String(hit.label) };
      }
    }
    return { ok: false };
  }

  document.addEventListener("rolewise-select", async e => {
    const { reqId, id, wanted } = JSON.parse(e.detail);
    let res = { ok: false };
    try { res = await choose(id, wanted); } catch (err) { res = { ok: false, error: String(err) }; }
    document.dispatchEvent(new CustomEvent("rolewise-selected", { detail: JSON.stringify({ reqId, ...res }) }));
  });
})();
