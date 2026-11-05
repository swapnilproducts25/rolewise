// Rolewise Fill background worker: drafts answers to job-form questions with Claude, using the user's own API key
// (saved on the options page, kept in this browser only). Content scripts ask for a draft with a "rolewise-draft" message.
const MODEL = "claude-opus-5-5";

const SYSTEM = `You draft answers to job application questions for one candidate, in their voice.
Rules: use only the facts given about the candidate and the job; never invent employers, numbers, tools, titles or
experience. If the facts don't support an answer, write the most honest answer they do support. First person, plain and
specific, warm but not salesy. No em dashes, no bullet points, no headings. Unless told otherwise, 80 to 120 words.
Reply with the answer text only.`;

async function draft({ question, job, facts, jobDescription, previous, instruction }) {
  const { apiKey } = await chrome.storage.local.get({ apiKey: "" });
  if (!apiKey) return { needKey: true };
  let prompt = `Job: ${job}\n\nJob description (excerpt):\n${jobDescription || "(not available)"}\n\n` +
    `Facts about the candidate:\n${facts}\n\nQuestion on the application form:\n${question}`;
  if (previous) prompt += `\n\nCurrent draft:\n${previous}\n\nRevise it: ${instruction || "write a fresh version"}.`;
  const res = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2026-10-21",
      "anthropic-beta": "server-side-fallback-2026-07-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: MODEL,
      max_tokens: 4000,
      output_config: { effort: "low" },   // short answers: low effort keeps it fast
      fallbacks: "default",
      system: SYSTEM,
      messages: [{ role: "user", content: prompt }],
    }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = (body.error && body.error.message) || `HTTP ${res.status}`;
    return { error: res.status === 401 ? "Your API key was rejected. Check it on the Rolewise Fill options page." : msg };
  }
  if (body.stop_reason === "refusal") return { error: "Claude declined to draft this one. Please write it yourself." };
  const text = (body.content || []).filter(b => b.type === "text").map(b => b.text).join("").trim();
  return text ? { text } : { error: "No draft came back. Try again." };
}

chrome.runtime.onMessage.addListener((msg, _sender, reply) => {
  if (msg && msg.type === "rolewise-draft") {
    draft(msg).then(reply, e => reply({ error: String(e && e.message || e) }));
    return true;   // keep the channel open for the async reply
  }
  if (msg && msg.type === "rolewise-options") chrome.runtime.openOptionsPage();
  if (msg && msg.type === "rolewise-native") {   // the local helper (extension/native): updates Rolewise on this laptop
    chrome.runtime.sendNativeMessage("com.rolewise.fill", msg.payload, res =>
      reply(res || { ok: false, error: (chrome.runtime.lastError && chrome.runtime.lastError.message) || "helper not installed" }));
    return true;
  }
});
