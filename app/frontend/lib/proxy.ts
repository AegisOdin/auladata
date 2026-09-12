/** Proxy fijo hacia FastAPI; el navegador solo usa su propio origen. */
export async function proxyBackend(request: Request, path: string) {
  const upstream = process.env.API_INTERNAL_URL;
  if (!upstream) return Response.json({ detail: "El servicio no está configurado." }, { status: 503 });
  const headers = new Headers();
  for (const name of ["content-type", "cookie", "origin", "x-requested-with"]) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  try {
    const url = new URL(path, upstream);
    url.search = new URL(request.url).search;
    const response = await fetch(url, {
      method: request.method,
      headers,
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
      signal: AbortSignal.timeout(15000),
    });
    const outgoing = new Headers({ "Cache-Control": "no-store" });
    const contentType = response.headers.get("content-type");
    if (contentType) outgoing.set("content-type", contentType);
    for (const cookie of response.headers.getSetCookie()) outgoing.append("set-cookie", cookie);
    return new Response(response.body, { status: response.status, headers: outgoing });
  } catch {
    return Response.json({ detail: "El servicio no está disponible." }, { status: 502 });
  }
}
