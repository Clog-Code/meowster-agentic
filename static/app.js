// Minimal AG-UI client: POSTs a RunAgentInput to /agent, reads the SSE
// stream by hand (fetch + ReadableStream, since EventSource doesn't
// support POST bodies), and renders text/tool/state events.
//
// This is a backend-dev test harness only. The real frontend integration
// is the Flutter app, which should follow the same event contract.

const messagesEl = document.getElementById("messages");
const todosEl = document.getElementById("todos");
const threadId = crypto.randomUUID();
const history = [];

function addMessage(role, text, imageUrl) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  if (imageUrl) {
    const img = document.createElement("img");
    img.src = imageUrl;
    img.className = "msg-image";
    div.appendChild(img);
  }
  if (text) {
    const span = document.createElement("span");
    span.textContent = text;
    div.appendChild(span);
  }
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function renderTodos(todos) {
  todosEl.innerHTML = "";
  for (const todo of todos) {
    const li = document.createElement("li");
    li.textContent = `${todo.status === "completed" ? "✅" : "▫️"} ${todo.content}`;
    if (todo.status === "completed") li.classList.add("completed");
    todosEl.appendChild(li);
  }
}

async function consumeAgentStream(response) {
  if (!response.ok || !response.body) {
    addMessage("error", `Request failed: ${response.status}`);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let currentAssistantDiv = null;
  let assistantText = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const events = buffer.split("\n\n");
    buffer = events.pop() ?? ""; // last chunk may be incomplete

    for (const raw of events) {
      const line = raw.trim();
      if (!line.startsWith("data:")) continue;
      const jsonStr = line.slice("data:".length).trim();
      if (!jsonStr) continue;

      let evt;
      try {
        evt = JSON.parse(jsonStr);
      } catch {
        continue;
      }

      switch (evt.type) {
        case "TEXT_MESSAGE_START":
          assistantText = "";
          currentAssistantDiv = addMessage("assistant", "");
          break;
        case "TEXT_MESSAGE_CONTENT":
          assistantText += evt.delta ?? "";
          if (currentAssistantDiv) {
            const span = currentAssistantDiv.querySelector("span") || currentAssistantDiv;
            span.textContent = assistantText;
          }
          break;
        case "TEXT_MESSAGE_END":
          if (assistantText) {
            history.push({ id: crypto.randomUUID(), role: "assistant", content: assistantText });
          }
          currentAssistantDiv = null;
          break;
        case "TOOL_CALL_START":
          addMessage("tool", `🔧 calling ${evt.toolCallName}…`);
          break;
        case "TOOL_CALL_RESULT":
          addMessage("tool", `↩ result: ${(evt.content ?? "").slice(0, 300)}`);
          break;
        case "STATE_SNAPSHOT":
          if (evt.snapshot?.todos) renderTodos(evt.snapshot.todos);
          break;
        case "RUN_ERROR":
          addMessage("error", `⚠ ${evt.message}`);
          break;
        default:
          break; // RUN_STARTED, RUN_FINISHED, STEP_*, TOOL_CALL_ARGS/END — no UI needed
      }
    }
  }
}

async function runAgent(userMessageContent) {
  history.push({ id: crypto.randomUUID(), role: "user", content: userMessageContent });

  const body = {
    threadId,
    runId: crypto.randomUUID(),
    state: {},
    messages: history.map((m) => ({ id: m.id, role: m.role, content: m.content })),
    tools: [],
    context: [],
    forwardedProps: {},
  };

  const response = await fetch("/agent", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  await consumeAgentStream(response);
}

// ── File attachment ──────────────────────────────────────────────────────────

const fileInput = document.getElementById("file-input");
const previewContainer = document.getElementById("attachment-preview");
const previewImg = document.getElementById("preview-img");
const removeBtn = document.getElementById("remove-attachment");

let pendingImageUrl = null;  // for preview / display
let pendingImagePath = null; // absolute disk path for visual_search

fileInput.addEventListener("change", async () => {
  const file = fileInput.files[0];
  if (!file) return;

  // Show local preview immediately
  previewImg.src = URL.createObjectURL(file);
  previewContainer.classList.remove("hidden");
  pendingImageUrl = null;

  const form = new FormData();
  form.append("file", file);
  try {
    const res = await fetch("/upload", { method: "POST", body: form });
    if (res.ok) {
      const data = await res.json();
      pendingImageUrl = data.url;
      pendingImagePath = data.path;
    } else {
      addMessage("error", `Upload failed: ${res.status}`);
      clearAttachment();
    }
  } catch (err) {
    addMessage("error", `Upload error: ${err.message}`);
    clearAttachment();
  }
  fileInput.value = "";
});

function clearAttachment() {
  pendingImageUrl = null;
  pendingImagePath = null;
  previewImg.src = "";
  previewContainer.classList.add("hidden");
}

removeBtn.addEventListener("click", clearAttachment);

// ── Send chat ─────────────────────────────────────────────────────────────────

document.getElementById("send-chat").addEventListener("click", () => {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text && !pendingImageUrl) return;

  const imageUrl = pendingImageUrl;
  const imagePath = pendingImagePath;
  // Pass the disk path so the agent can call visual_search(image_path=...)
  // directly — no localhost URL needed.
  const agentContent = imagePath
    ? `${text}\n[image attached — use visual_search with image_path: ${imagePath}]`
    : text;

  addMessage("user", text || "(image)", imageUrl);
  input.value = "";
  clearAttachment();
  runAgent(agentContent);
});

document.getElementById("chat-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("send-chat").click();
});
const SCENARIOS = {
  health: {
    pet_id: "buddy-01",
    species: "dog",
    emotion: "distress",
    emotion_confidence: 0.87,
    health_flags: ["limping", "whining"],
    notes: "Detected via audio distress classifier + posture anomaly",
  },
  supply: {
    pet_id: "buddy-01",
    species: "dog",
    food_level: "empty",
    water_level: "ok",
    notes: "Empty bowl detected via vision model",
  },
  info: {
    pet_id: "buddy-01",
    species: "dog",
    emotion: "playful",
    emotion_confidence: 0.92,
    food_level: "full",
    water_level: "ok",
  },
};

document.getElementById("send-perception").addEventListener("click", async () => {
  const scenario = document.getElementById("scenario").value;
  const payload = { ...SCENARIOS[scenario], thread_id: threadId, timestamp: new Date().toISOString() };

  addMessage("user", `[perception-event: ${scenario}]\n${JSON.stringify(payload, null, 2)}`);

  const response = await fetch("/perception", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  await consumeAgentStream(response);
});

// ── Google OAuth ──────────────────────────────────────────────────────────────

const authBadge = document.getElementById("auth-badge");
const authBtn = document.getElementById("auth-btn");

const OAUTH_URL = `/auth/google?thread_id=${threadId}`;

async function checkAuth() {
  try {
    const res = await fetch(`/auth/me?thread_id=${threadId}`);
    if (!res.ok) return;
    const data = await res.json();
    const hasGoogle = data.providers?.some((p) => p.provider === "google");
    if (hasGoogle) {
      authBadge.textContent = "✅ Calendar connected";
      authBadge.className = "auth-badge connected";
      authBtn.textContent = "Reconnect";
    }
  } catch {
    // server not running etc — silently degrade
  }
}

authBtn.addEventListener("click", () => {
  const popup = window.open(OAUTH_URL, "google-oauth", "width=600,height=700,popup=1");
  if (!popup || popup.closed) {
    window.location.href = OAUTH_URL;
  }
});

// Listen for postMessage from the OAuth popup so the badge updates
// immediately instead of waiting for the next poll interval.
window.addEventListener("message", (event) => {
  if (event.data?.type === "oauth-connected") {
    checkAuth();
  }
});

// Poll auth status every 3 s as a fallback (e.g. if popup was blocked
// and user navigated in the same tab, then came back).
checkAuth();
setInterval(checkAuth, 3000);
