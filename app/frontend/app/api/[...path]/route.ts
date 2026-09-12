import { proxyBackend } from "@/lib/proxy";

export const dynamic = "force-dynamic";
type Context = { params: Promise<{ path: string[] }> };
async function handler(request: Request, context: Context) {
  const { path } = await context.params;
  if (path[0] !== "v1" || path.some(segment => segment === "." || segment === "..")) {
    return Response.json({ detail: "Ruta no disponible." }, { status: 404 });
  }
  return proxyBackend(request, `/api/${path.map(encodeURIComponent).join("/")}`);
}
export { handler as GET, handler as POST, handler as PUT, handler as PATCH, handler as DELETE };
