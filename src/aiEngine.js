const KNOWLEDGE = [
  {
    match: /^reverse\s+(.+)/i,
    reply: (m) => `Reversed: ${[...m[1].trim()].reverse().join("")}`,
  },
  {
    match: /^count\s+(?:words\s+)?(?:in\s+)?(.+)/i,
    reply: (m) => {
      const words = m[1].trim().split(/\s+/).filter(Boolean);
      return `That phrase has ${words.length} word${words.length === 1 ? "" : "s"}.`;
    },
  },
  {
    match: /\b(who|what)\s+are\s+you\b/i,
    reply: () =>
      "I'm a deterministic, offline demo model. No external API keys or network calls required — perfect for verifying a fresh dev environment.",
  },
  {
    match: /\b(hello|hi|hey|你好|您好)\b/i,
    reply: () =>
      "Hello! I'm a small demo assistant running entirely on your local dev environment. Ask me to echo, reverse, or count something.",
  },
];

/**
 * Produce a deterministic assistant reply for a user message.
 * Kept fully offline so the environment needs no secrets or egress.
 *
 * @param {string} message raw user input
 * @returns {{ reply: string, tokens: number }}
 */
export function generateReply(message) {
  if (typeof message !== "string" || message.trim() === "") {
    throw new Error("message must be a non-empty string");
  }

  const trimmed = message.trim();
  const tokens = trimmed.split(/\s+/).filter(Boolean).length;

  for (const entry of KNOWLEDGE) {
    const m = trimmed.match(entry.match);
    if (m) {
      return { reply: entry.reply(m), tokens };
    }
  }

  return {
    reply: `You said: "${trimmed}". I'm a demo model, so I'll just reflect that back with ${tokens} token${tokens === 1 ? "" : "s"} counted.`,
    tokens,
  };
}
