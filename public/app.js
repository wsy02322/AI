const messagesEl = document.getElementById("messages");
const form = document.getElementById("composer");
const input = document.getElementById("input");
const sendBtn = document.getElementById("send");

function addMessage(text, who) {
  const wrap = document.createElement("div");
  wrap.className = `message message--${who}`;
  const bubble = document.createElement("div");
  bubble.className = "message__bubble";
  bubble.textContent = text;
  wrap.appendChild(bubble);
  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

async function sendMessage(message) {
  addMessage(message, "user");
  const pending = addMessage("…", "bot");
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    const data = await res.json();
    pending.textContent = data.reply;
  } catch (err) {
    pending.textContent = `Error: ${err.message}`;
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (!message) return;
  input.value = "";
  sendBtn.disabled = true;
  await sendMessage(message);
  sendBtn.disabled = false;
  input.focus();
});
