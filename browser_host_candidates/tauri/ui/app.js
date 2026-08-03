const invoke = window.__TAURI__.core.invoke;

const address = document.querySelector("#address");
const preview = document.querySelector("#preview");
const attach = document.querySelector("#attach");
const status = document.querySelector("#status");

function setStatus(message) {
  status.value = message;
  status.textContent = message;
}

async function refresh() {
  try {
    const state = await invoke("candidate_get_state");
    address.value = state.url || address.value;
    setStatus(
      `${state.phase}; generation ${state.documentGeneration}; ` +
      `credential in JavaScript: no; production authority: no`
    );
  } catch (error) {
    setStatus(`state unavailable: ${String(error)}`);
  }
}

async function command(name, args = {}) {
  try {
    const result = await invoke(name, args);
    await refresh();
    return result;
  } catch (error) {
    setStatus(`${name} denied: ${String(error)}`);
    throw error;
  }
}

document.querySelector("#navigate").addEventListener("click", () => {
  command("candidate_navigate", { url: address.value }).catch(() => {});
});
document.querySelector("#back").addEventListener("click", () => {
  command("candidate_back").catch(() => {});
});
document.querySelector("#forward").addEventListener("click", () => {
  command("candidate_forward").catch(() => {});
});
document.querySelector("#reload").addEventListener("click", () => {
  command("candidate_reload").catch(() => {});
});
document.querySelector("#cancel").addEventListener("click", () => {
  command("candidate_cancel").then(() => {
    preview.textContent = "Capture cancelled.";
    attach.disabled = true;
  }).catch(() => {});
});

async function capture(mode) {
  const started = await command("candidate_begin_capture", { mode });
  preview.textContent = `Capture ${started.captureRequestId} requested. Waiting for renderer.`;
  attach.disabled = true;
  window.setTimeout(async () => {
    try {
      const envelope = await invoke("candidate_get_preview");
      preview.textContent = envelope.content;
      attach.disabled = false;
      setStatus(`Preview ready from ${envelope.sourceOrigin}; attachment remains explicit.`);
    } catch (error) {
      setStatus(`preview unavailable: ${String(error)}`);
    }
  }, 350);
}

document.querySelector("#capture-selection").addEventListener("click", () => {
  capture("selected_text").catch(() => {});
});
document.querySelector("#capture-page").addEventListener("click", () => {
  capture("visible_page_text").catch(() => {});
});
attach.addEventListener("click", async () => {
  try {
    const receipt = await command("candidate_attach");
    preview.textContent = "Attachment receipt accepted; captured content cleared from host state.";
    attach.disabled = true;
    setStatus(`Synthetic attachment ${receipt.receiptId || "accepted"}; persisted: false.`);
  } catch (_error) {
    attach.disabled = false;
  }
});

refresh();
