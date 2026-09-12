"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Archive, ArrowDownUp, ArrowRight, Building2, ChevronLeft, ChevronRight, DoorOpen, Eye, FlaskConical, Pencil, Plus, RotateCw, Search, SlidersHorizontal } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { StatusBadge } from "@/components/status-badge";
import { DeleteDialog } from "@/components/delete-dialog";
import { api, errorMessage, formatDate } from "@/lib/api";
import { stateLabels, typeLabels, type Classroom, type ClassroomList } from "@/types";

export default function ClassroomsPage() {
  const { user } = useAuth();
  const admin = user?.role === "ADMIN";
  const [search, setSearch] = useState("");
  const [estado, setEstado] = useState("");
  const [tipo, setTipo] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<ClassroomList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  const [deleting, setDeleting] = useState<Classroom | null>(null);
  const [notice, setNotice] = useState("");
  const fetchList = useCallback(async (signal: AbortSignal) => {
    setLoading(true); setError("");
    const query = new URLSearchParams({ page: String(page), page_size: "10" });
    if (search.trim()) query.set("search", search.trim());
    if (estado) query.set("estado", estado);
    if (tipo) query.set("tipo", tipo);
    try { const result = await api.list(query.toString(), signal); setData(result); }
    catch (error) { if (!signal.aborted) setError(errorMessage(error)); }
    finally { if (!signal.aborted) setLoading(false); }
  }, [search, estado, tipo, page]);
  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => void fetchList(controller.signal), 250);
    return () => { clearTimeout(timeout); controller.abort(); };
  }, [fetchList, refresh]);
  const filtered = Boolean(search || estado || tipo);
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / 10));
  function clearFilters() { setSearch(""); setEstado(""); setTipo(""); setPage(1); }
  return <>
    <div className="page-heading"><div><div className="section-kicker"><span className="small-rule" />Directorio del campus</div><h1>Gestión de aulas</h1><p>Un solo lugar para consultar y organizar tus espacios académicos.</p></div>{admin && <Link className="btn btn-primary" href="/aulas/nueva"><Plus size={18} />Nueva aula</Link>}</div>
    <section className="directory-intro" aria-label="Información del directorio"><div className="directory-icon"><Building2 size={29} strokeWidth={1.5} /></div><div><h2>Espacios que hacen posible aprender</h2><p>Consulta la capacidad, el tipo y el estado de cada aula del campus.</p></div><span className="intro-tag"><DoorOpen size={15} />Directorio de aulas</span></section>
    {notice && <div className="notice" role="status">{notice}<button type="button" onClick={() => setNotice("")} aria-label="Cerrar notificación">×</button></div>}
    <section className="directory-card" aria-labelledby="directory-title">
      <div className="directory-header"><div className="directory-title"><h2 id="directory-title">Aulas registradas</h2>{data && <span className="count-badge">{data.total}</span>}</div><button className="text-button" onClick={() => setRefresh(value => value + 1)} disabled={loading}><RotateCw size={15} />Actualizar</button></div>
      <div className="filter-bar"><div className="search-input"><Search size={18} /><label className="sr-only" htmlFor="search">Buscar aulas</label><input id="search" type="search" maxLength={100} placeholder="Buscar por clave, nombre o edificio…" value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} /></div><div className="filter-controls"><SlidersHorizontal size={17} className="filter-icon" /><label className="sr-only" htmlFor="estado">Estado</label><select id="estado" value={estado} onChange={event => { setEstado(event.target.value); setPage(1); }}><option value="">Todos los estados</option>{Object.entries(stateLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><label className="sr-only" htmlFor="tipo">Tipo de aula</label><select id="tipo" value={tipo} onChange={event => { setTipo(event.target.value); setPage(1); }}><option value="">Todos los tipos</option>{Object.entries(typeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div></div>
      {error ? <div className="table-feedback"><p className="alert" role="alert">{error}</p><button className="btn btn-secondary" onClick={() => setRefresh(value => value + 1)}>Reintentar</button></div> : <>
        <div className={`table-scroll ${loading ? "table-is-loading" : ""}`} aria-busy={loading}>
          <table><thead><tr><th scope="col"><span>Clave<ArrowDownUp size={12} /></span></th><th scope="col">Nombre del aula</th><th scope="col">Edificio</th><th scope="col" className="capacity-cell">Capacidad</th><th scope="col">Tipo</th><th scope="col">Estado</th><th scope="col">Actualización</th><th scope="col" className="actions-cell">Acciones</th></tr></thead><tbody>
          {data?.items.map(classroom => <tr key={classroom.id}><td><Link className="classroom-code" href={`/aulas/${classroom.id}`}>{classroom.clave}</Link></td><td><Link className="classroom-name" href={`/aulas/${classroom.id}`}>{classroom.nombre}</Link></td><td className="building-cell">{classroom.edificio}</td><td className="capacity-cell"><span>{classroom.capacidad}</span><small> lugares</small></td><td><span className="type-cell">{classroom.tipo === "LABORATORIO" ? <FlaskConical size={14} /> : <DoorOpen size={14} />}{typeLabels[classroom.tipo]}</span></td><td><StatusBadge state={classroom.estado} /></td><td className="date-cell">{formatDate(classroom.updated_at)}</td><td><div className="table-actions"><Link className="icon-button" href={`/aulas/${classroom.id}`} title="Ver aula" aria-label={`Ver ${classroom.clave}`}><Eye size={16} /></Link>{admin && <><Link className="icon-button" href={`/aulas/${classroom.id}/editar`} title="Editar aula" aria-label={`Editar ${classroom.clave}`}><Pencil size={15} /></Link><button className="icon-button archive-button" title="Dar de baja" aria-label={`Dar de baja ${classroom.clave}`} onClick={() => setDeleting(classroom)}><Archive size={15} /></button></>}</div></td></tr>)}
          </tbody></table>
          {!data && loading && <div className="table-feedback" role="status"><span className="spinner" />Cargando aulas…</div>}
          {data?.items.length === 0 && <div className="table-feedback"><DoorOpen size={33} /><h3>{filtered ? "No encontramos aulas con estos filtros" : "Tu directorio está listo para comenzar"}</h3><p>{filtered ? "Prueba con otra búsqueda o consulta todos los espacios." : "Agrega la primera aula para organizar los espacios del campus."}</p>{filtered ? <button className="btn btn-secondary" onClick={clearFilters}>Limpiar filtros</button> : admin && <Link className="btn btn-primary" href="/aulas/nueva"><Plus size={17} />Nueva aula</Link>}</div>}
        </div>
        <div className="table-footer"><span role="status">{data ? data.total ? `Mostrando ${(page - 1) * 10 + 1}–${Math.min(page * 10, data.total)} de ${data.total} aulas${filtered ? " encontradas" : ""}` : "0 aulas encontradas" : "Consultando directorio…"}</span><div className="pagination"><button className="icon-button" aria-label="Página anterior" disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}><ChevronLeft size={17} /></button><span>Página {page} de {pages}</span><button className="icon-button" aria-label="Página siguiente" disabled={page >= pages || loading} onClick={() => setPage(page + 1)}><ChevronRight size={17} /></button></div></div>
      </>}
    </section><p className="directory-hint"><span className="hint-dot" />Los espacios dados de baja se conservan y no aparecen en este directorio.{admin && <Link href="/aulas/nueva">Registrar un espacio<ArrowRight size={14} /></Link>}</p>
    {deleting && <DeleteDialog classroom={deleting} onClose={() => setDeleting(null)} onDeleted={() => { setNotice(`${deleting.clave} se dio de baja correctamente.`); setDeleting(null); if (data?.items.length === 1 && page > 1) setPage(page - 1); else setRefresh(value => value + 1); }} />}
  </>;
}
