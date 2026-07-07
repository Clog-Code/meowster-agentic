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

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.textContent = text;
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
          if (currentAssistantDiv) currentAssistantDiv.textContent = assistantText;
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

document.getElementById("send-chat").addEventListener("click", () => {
  const input = document.getElementById("chat-input");
  const text = input.value.trim();
  if (!text) return;
  addMessage("user", text);
  input.value = "";
  runAgent(text);
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
