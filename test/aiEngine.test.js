import test from "node:test";
import assert from "node:assert/strict";
import { generateReply } from "../src/aiEngine.js";

test("reverses text", () => {
  const { reply } = generateReply("reverse hello");
  assert.equal(reply, "Reversed: olleh");
});

test("counts words", () => {
  const { reply } = generateReply("count words in one two three");
  assert.match(reply, /3 words/);
});

test("greets", () => {
  const { reply } = generateReply("hello there");
  assert.match(reply, /Hello/);
});

test("reflects unknown input and counts tokens", () => {
  const { reply, tokens } = generateReply("banana split sundae");
  assert.equal(tokens, 3);
  assert.match(reply, /banana split sundae/);
});

test("rejects empty input", () => {
  assert.throws(() => generateReply("   "), /non-empty string/);
});
