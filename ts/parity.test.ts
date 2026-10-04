import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import {
  ClaimSchema,
  ParityObjectSchema,
  ResearchRequestSchema,
} from "./parity.js";

const fixtureRoot = fileURLToPath(
  new URL("../fixtures/parity/", import.meta.url),
);

async function fixture(path: string): Promise<unknown> {
  return JSON.parse(await readFile(`${fixtureRoot}${path}`, "utf8")) as unknown;
}

test("valid shared fixtures satisfy their parity schemas", async () => {
  const names = ["request.json", "plan.json", "evidence.json", "claim.json", "tool-events.json"];
  for (const name of names) {
    const value = await fixture(`valid/${name}`);
    const result = Array.isArray(value)
      ? value.map((item) => ParityObjectSchema.parse(item))
      : ParityObjectSchema.parse(value);
    assert.ok(result);
  }
});

test("unknown versions and fields are rejected", async () => {
  for (const name of ["unknown-version.json", "unknown-field.json"]) {
    const result = ParityObjectSchema.safeParse(await fixture(`invalid/${name}`));
    assert.equal(result.success, false, name);
  }
});

test("invalid claim types are rejected", async () => {
  const result = ClaimSchema.safeParse(await fixture("invalid/invalid-claim-type.json"));
  assert.equal(result.success, false);
});

test("research request has the supported schema version", async () => {
  const value = await fixture("valid/request.json");
  assert.equal(ResearchRequestSchema.parse(value).schema_version, 1);
});
