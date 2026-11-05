const key = document.getElementById("key"), status = document.getElementById("status");
chrome.storage.local.get({ apiKey: "" }, d => { if (d.apiKey) status.textContent = "A key is saved. Paste a new one to replace it."; });
document.getElementById("save").onclick = () => {
  const v = key.value.trim();
  if (!v.startsWith("sk-ant-")) { status.textContent = "That doesn't look like an Anthropic API key (it starts with sk-ant-)."; return; }
  chrome.storage.local.set({ apiKey: v }, () => { key.value = ""; status.textContent = "Saved. ✨ Draft now works in job forms."; });
};
document.getElementById("clear").onclick = () =>
  chrome.storage.local.remove("apiKey", () => { status.textContent = "Key removed."; });
