import { createServer } from "node:http";
import { createReadStream, existsSync, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const port = Number.parseInt(process.env.PORT || "4173", 10);

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
};

const server = createServer((request, response) => {
  const requestUrl = new URL(request.url || "/", `http://localhost:${port}`);
  const relativePath = requestUrl.pathname === "/" ? "index.html" : decodeURIComponent(requestUrl.pathname.slice(1));
  const absolutePath = normalize(join(root, relativePath));

  if (!absolutePath.startsWith(root) || !existsSync(absolutePath) || !statSync(absolutePath).isFile()) {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("not found");
    return;
  }

  response.writeHead(200, {
    "content-type": mimeTypes[extname(absolutePath).toLowerCase()] || "application/octet-stream",
    "cache-control": "no-store",
  });
  createReadStream(absolutePath).pipe(response);
});

server.listen(port, "127.0.0.1", () => {
  console.log(`SnapKitty Quantum Voxel UX: http://127.0.0.1:${port}/`);
});
