import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "playwright";

const root = fileURLToPath(new URL("..", import.meta.url));
const outputDir = join(root, "tmp", "verification");
const url = process.env.VOXEL_UX_URL || "http://127.0.0.1:4173/";

const viewports = [
  { name: "desktop", width: 1440, height: 900 },
  { name: "mobile", width: 390, height: 844 },
];

await mkdir(outputDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const errors = [];

try {
  for (const viewport of viewports) {
    const page = await browser.newPage({ viewport });
    page.on("console", (message) => {
      if (message.type() === "error") errors.push(`${viewport.name}: ${message.text()}`);
    });
    page.on("pageerror", (error) => errors.push(`${viewport.name}: ${error.message}`));

    await page.goto(url, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForSelector("#c", { timeout: 15000 });
    await page.waitForFunction(() => document.querySelector("#hud-agents")?.textContent === "15", null, {
      timeout: 15000,
    });
    await page.locator("[data-command='execute']").click();
    await page.waitForFunction(() => document.querySelector("#hud-event")?.textContent?.includes("SIMULATED"), null, {
      timeout: 15000,
    });

    const canvasStats = await page.evaluate(() => {
      const canvas = document.querySelector("#c");
      const gl = canvas.getContext("webgl2") || canvas.getContext("webgl");
      if (!gl) return { width: canvas.width, height: canvas.height, nonBlank: 0, samples: 0 };
      const width = canvas.width;
      const height = canvas.height;
      const pixels = new Uint8Array(width * height * 4);
      gl.readPixels(0, 0, width, height, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      let nonBlank = 0;
      let samples = 0;
      for (let i = 0; i < pixels.length; i += 64) {
        const r = pixels[i];
        const g = pixels[i + 1];
        const b = pixels[i + 2];
        const a = pixels[i + 3];
        samples += 1;
        if (a > 0 && r + g + b > 50) nonBlank += 1;
      }
      return { width, height, nonBlank, samples };
    });

    if (canvasStats.width <= 0 || canvasStats.height <= 0) {
      throw new Error(`${viewport.name}: canvas has invalid size ${canvasStats.width}x${canvasStats.height}`);
    }
    if (canvasStats.nonBlank < Math.max(100, Math.floor(canvasStats.samples * 0.01))) {
      throw new Error(`${viewport.name}: canvas appears blank (${JSON.stringify(canvasStats)})`);
    }

    const agents = await page.locator("#hud-agents").innerText();
    const voxels = Number.parseInt(await page.locator("#hud-voxels").innerText(), 10);
    if (agents !== "15") throw new Error(`${viewport.name}: expected 15 agents, found ${agents}`);
    if (voxels < 21) throw new Error(`${viewport.name}: execute command did not add visible voxel`);

    const screenshotPath = join(outputDir, `${viewport.name}.png`);
    await page.screenshot({ path: screenshotPath, fullPage: true });
    await page.close();

    console.log(
      `${viewport.name} verified: ${canvasStats.width}x${canvasStats.height}, ${canvasStats.nonBlank}/${canvasStats.samples} nonblank samples, screenshot ${screenshotPath}`,
    );
  }

  if (errors.length > 0) {
    throw new Error(`browser console errors:\n${errors.join("\n")}`);
  }
} finally {
  await browser.close();
}
