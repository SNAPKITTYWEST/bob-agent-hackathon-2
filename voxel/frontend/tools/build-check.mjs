import { existsSync, statSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { createInitialWorld, listAgents, listVoxels } from "../src/world-model.js";

const root = fileURLToPath(new URL("..", import.meta.url));

const requiredFiles = [
  "index.html",
  "src/app.js",
  "src/styles.css",
  "src/world-model.js",
  "src/quantum-mapping.js",
  "src/agent-roster.js",
  "assets/characters/snapkitty-orange-operative.png",
  "assets/characters/snapkitty-blue-operative.png",
  "assets/characters/snapkitty-wireframe-operative.jpg",
];

for (const file of requiredFiles) {
  const absolute = join(root, file);
  if (!existsSync(absolute)) {
    throw new Error(`Missing frontend build file: ${file}`);
  }
  if (statSync(absolute).size === 0) {
    throw new Error(`Frontend build file is empty: ${file}`);
  }
}

const html = await readFile(join(root, "index.html"), "utf8");
for (const reference of ["./src/styles.css", "./src/app.js", "three@0.160.0"]) {
  if (!html.includes(reference)) {
    throw new Error(`index.html does not reference ${reference}`);
  }
}

const world = createInitialWorld({ agentCount: 15 });
const agents = listAgents(world);
const voxels = listVoxels(world);

if (agents.length !== 15) {
  throw new Error(`Expected 15 digital twin agents, found ${agents.length}`);
}

if (voxels.length < 20) {
  throw new Error(`Expected Bell-state voxels plus 15 agent markers, found ${voxels.length}`);
}

if (world.metadata.backendTruth.includes("visualization") === false) {
  throw new Error("World metadata must state the browser layer is visualization.");
}

console.log(`frontend build audit passed: ${agents.length} agents, ${voxels.length} voxels`);
