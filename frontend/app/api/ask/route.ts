// Server-side proxy to the TestLens API, so the browser never needs the API address
// and API_URL can be set at runtime (container env) rather than at build time.

const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function POST(request: Request): Promise<Response> {
  try {
    const upstream = await fetch(`${API_URL}/api/ask`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: await request.text(),
      cache: "no-store",
    });
    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return Response.json({ detail: "TestLens API is unreachable" }, { status: 502 });
  }
}
