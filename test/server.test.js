import test from "node:test";
import assert from "node:assert/strict";
import request from "supertest";
import { createApp } from "../src/server.js";

const app = createApp();

test("GET /api/health returns ok", async () => {
  const res = await request(app).get("/api/health");
  assert.equal(res.status, 200);
  assert.equal(res.body.status, "ok");
});

test("POST /api/chat returns a reply", async () => {
  const res = await request(app)
    .post("/api/chat")
    .send({ message: "reverse abc" });
  assert.equal(res.status, 200);
  assert.equal(res.body.reply, "Reversed: cba");
});

test("POST /api/chat rejects empty message", async () => {
  const res = await request(app).post("/api/chat").send({ message: "" });
  assert.equal(res.status, 400);
  assert.ok(res.body.error);
});

test("GET / serves the web UI", async () => {
  const res = await request(app).get("/");
  assert.equal(res.status, 200);
  assert.match(res.text, /AI Demo/);
});
