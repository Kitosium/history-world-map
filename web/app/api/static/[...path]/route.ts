import { existsSync, promises as fs } from "node:fs";
import path from "node:path";
import type { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const ROOTS = new Set(["data"]);

const CONTENT_TYPES: Record<string, string> = {
  ".json": "application/json; charset=utf-8",
  ".geojson": "application/geo+json; charset=utf-8",
  ".pdf": "application/pdf",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".md": "text/markdown; charset=utf-8"
};

interface RouteContext {
  params: Promise<{ path?: string[] }>;
}

function repositoryRoot() {
  const cwd = process.cwd();
  if (existsSync(path.join(cwd, "data"))) return cwd;
  const parent = path.resolve(cwd, "..");
  if (existsSync(path.join(parent, "data"))) return parent;
  return cwd;
}

export async function GET(_request: NextRequest, context: RouteContext) {
  const { path: segments = [] } = await context.params;
  if (!segments.length || !ROOTS.has(segments[0])) {
    return new Response("Not found", { status: 404 });
  }

  const base = repositoryRoot();
  const resolved = path.resolve(base, ...segments);
  const allowed = [...ROOTS].map((root) => path.resolve(base, root) + path.sep);
  if (!allowed.some((prefix) => resolved.startsWith(prefix))) {
    return new Response("Not found", { status: 404 });
  }

  try {
    const stat = await fs.stat(resolved);
    if (!stat.isFile()) {
      return new Response("Not found", { status: 404 });
    }
    const body = await fs.readFile(resolved);
    const extension = path.extname(resolved).toLowerCase();
    return new Response(body, {
      headers: {
        "Content-Type": CONTENT_TYPES[extension] || "application/octet-stream",
        "Content-Length": String(stat.size),
        "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400"
      }
    });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
