"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Health } from "@/types";

export function Environment({ compact = false }: { compact?: boolean }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    const update = () => api.health().then(data => { if (live) { setHealth(data); setFailed(false); } }).catch(() => { if (live) setFailed(true); });
    void update();
    const interval = setInterval(() => void update(), 60000);
    return () => { live = false; clearInterval(interval); };
  }, []);
  if (!health) return <span className="environment-loading">{failed ? "Servicio sin conexión" : "Consultando ambiente…"}</span>;
  return <div className={`environment ${compact ? "environment-compact" : ""}`}>
    <span className={`env-pill env-${health.environment.toLowerCase()}`}><i />{health.environment}</span>
    <span>{health.version}</span><span className="commit" title={health.commit}>Commit {health.commit.slice(0, 7)}</span>
    {failed && <span role="status">Sin conexión</span>}
  </div>;
}
