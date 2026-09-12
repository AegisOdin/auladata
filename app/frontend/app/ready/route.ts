import { proxyBackend } from "@/lib/proxy";
export const dynamic = "force-dynamic";
export const GET = (request: Request) => proxyBackend(request, "/ready");
