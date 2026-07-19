// 依存ゼロのローカル検証用: app/ を静的配信しつつ /api/state を in-memory KV で GET/PUT。
// 実行: node tools/mock_sync_server.mjs  (http://localhost:8123)
import http from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..", "app");
let stateStore = null; // in-memory "KV"

const TYPES = {
  ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
  ".json": "application/json", ".png": "image/png", ".webmanifest": "application/manifest+json",
};

async function readBody(req) {
  const chunks = [];
  for await (const c of req) chunks.push(c);
  return Buffer.concat(chunks).toString("utf-8");
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");
  if (url.pathname === "/api/state") {
    if (req.method === "GET") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(stateStore ?? JSON.stringify({ pages: {}, activityDates: [] }));
      return;
    }
    if (req.method === "PUT") {
      stateStore = await readBody(req);
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
      return;
    }
  }
  // static
  let p = normalize(url.pathname === "/" ? "/index.html" : url.pathname);
  try {
    const data = await readFile(join(ROOT, p));
    res.writeHead(200, { "content-type": TYPES[extname(p)] ?? "application/octet-stream" });
    res.end(data);
  } catch {
    res.writeHead(404); res.end("not found");
  }
});

server.listen(8123, () => console.log("mock sync server on http://localhost:8123"));
