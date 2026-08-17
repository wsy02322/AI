import express from "express";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { generateReply } from "./aiEngine.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

export function createApp() {
  const app = express();
  app.use(express.json());

  app.get("/api/health", (_req, res) => {
    res.json({ status: "ok", uptime: process.uptime() });
  });

  app.post("/api/chat", (req, res) => {
    const { message } = req.body ?? {};
    try {
      const { reply, tokens } = generateReply(message);
      res.json({ reply, tokens });
    } catch (err) {
      res.status(400).json({ error: err.message });
    }
  });

  app.use(express.static(join(__dirname, "..", "public")));

  return app;
}

const isMain = process.argv[1] === fileURLToPath(import.meta.url);
if (isMain) {
  const port = Number(process.env.PORT) || 3000;
  const app = createApp();
  app.listen(port, () => {
    console.log(`AI demo server listening on http://localhost:${port}`);
  });
}
