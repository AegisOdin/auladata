"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowUpRight, BookOpen, ChevronRight, DoorOpen, LogOut, Menu, ShieldCheck, X } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Brand } from "@/components/brand";
import { Environment } from "@/components/environment";
import { errorMessage } from "@/lib/api";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, error, logout, refresh } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const [leaving, setLeaving] = useState(false);
  useEffect(() => { if (!loading && !user && !error) router.replace("/login"); }, [loading, user, error, router]);
  if (loading) return <div className="page-loading" role="status"><Brand /><span className="spinner" />Validando tu sesión…</div>;
  if (error) return <div className="page-loading"><Brand /><p role="alert">{error}</p><button className="btn btn-primary" onClick={() => void refresh()}>Reintentar conexión</button></div>;
  if (!user) return null;
  const initials = user.name.split(" ").map(name => name[0]).slice(0, 2).join("");
  const pageLabel = pathname === "/aulas" ? "Directorio de aulas" : pathname === "/aulas/nueva" ? "Nueva aula" : pathname.endsWith("/editar") ? "Editar aula" : "Detalle de aula";
  async function signOut() {
    setLeaving(true);
    try { await logout(); router.replace("/login"); }
    catch (error) { setLogoutError(errorMessage(error)); }
    finally { setLeaving(false); }
  }
  return <div className="application">
    <a className="skip-link" href="#content">Saltar al contenido</a>
    {open && <button className="sidebar-overlay" aria-label="Cerrar menú" onClick={() => setOpen(false)} />}
    <aside className={`sidebar ${open ? "sidebar-open" : ""}`}>
      <Link href="/aulas" aria-label="AulaData, inicio" className="sidebar-brand"><Brand /></Link>
      <button className="mobile-close icon-button" aria-label="Cerrar menú" onClick={() => setOpen(false)}><X size={22} /></button>
      <div className="workspace-name"><span className="workspace-symbol"><BookOpen size={18} /></span><div><strong>Espacios académicos</strong><small>Administración del campus</small></div></div>
      <div className="nav-label">Espacio de trabajo</div>
      <nav aria-label="Navegación principal"><Link className="nav-item active" href="/aulas" onClick={() => setOpen(false)} aria-current="page"><DoorOpen size={20} />Gestión de aulas<ChevronRight size={16} className="nav-chevron" /></Link></nav>
      <div className="sidebar-bottom">
        <div className="role-note"><ShieldCheck size={20} /><div><strong>{user.role === "ADMIN" ? "Acceso de administrador" : "Acceso de consulta"}</strong><p>{user.role === "ADMIN" ? "Administra y mantén al día los espacios del campus." : "Consulta la información de los espacios del campus."}</p></div></div>
        <div className="sidebar-system"><span className="system-label">AulaData / Infraestructura de Servicios</span><Environment compact /></div>
      </div>
    </aside>
    <div className="main-column">
      <header className="topbar">
        <div className="breadcrumb"><button className="mobile-menu icon-button" aria-label="Abrir menú" onClick={() => setOpen(true)}><Menu size={21} /></button><span>Espacios</span><ChevronRight size={14} /><strong>{pageLabel}</strong></div>
        <div className="account"><div className="account-text"><strong>{user.name}</strong><small>{user.role === "ADMIN" ? "Administrador" : "Consulta"}</small></div><span className="avatar">{initials}</span><button className="icon-button logout" title="Cerrar sesión" aria-label="Cerrar sesión" disabled={leaving} onClick={() => void signOut()}><LogOut size={18} /></button></div>
      </header>
      <main id="content" className="main-content">{logoutError && <div className="alert" role="alert">{logoutError}</div>}{children}</main>
      <footer className="main-footer"><span>AulaData · Gestión de espacios académicos</span><div className="mobile-environment"><Environment /></div><Link href="/aulas">Directorio del campus<ArrowUpRight size={13} /></Link></footer>
    </div>
  </div>;
}
