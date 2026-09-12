"use client";
import { use, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Archive, ArrowLeft, Building2, CalendarDays, DoorOpen, Pencil, Users } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { ClassroomLoader } from "@/components/classroom-loader";
import { DeleteDialog } from "@/components/delete-dialog";
import { StatusBadge } from "@/components/status-badge";
import { formatDate } from "@/lib/api";
import { typeLabels, type Classroom } from "@/types";

function Detail({ classroom }: { classroom: Classroom }) {
  const { user } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [deleting, setDeleting] = useState(false);
  const saved = searchParams.get("saved");
  return <><Link className="back-link" href="/aulas"><ArrowLeft size={16} />Volver a las aulas</Link><div className="page-heading"><div><div className="detail-code">{classroom.clave}</div><h1>{classroom.nombre}</h1><p>Información y estado del espacio académico.</p></div>{user?.role === "ADMIN" && <Link className="btn btn-primary" href={`/aulas/${classroom.id}/editar`}><Pencil size={17} />Editar aula</Link>}</div>
    {saved && <div className="notice" role="status">{saved === "created" ? "El aula se registró correctamente." : "Los cambios se guardaron correctamente."}</div>}
    <section className="detail-card"><div className="detail-card-header"><span className="detail-icon"><DoorOpen size={30} /></span><div><h2>Información del aula</h2><span>Clave {classroom.clave}</span></div><StatusBadge state={classroom.estado} /></div><dl className="detail-grid"><div><dt><Building2 size={17} />Edificio</dt><dd>{classroom.edificio}</dd></div><div><dt><Users size={17} />Capacidad</dt><dd>{classroom.capacidad}<small> personas</small></dd></div><div><dt><DoorOpen size={17} />Tipo de aula</dt><dd>{typeLabels[classroom.tipo]}</dd></div><div><dt><CalendarDays size={17} />Fecha de registro</dt><dd>{formatDate(classroom.created_at)}</dd></div></dl><div className="detail-updated">Última actualización: {formatDate(classroom.updated_at)}</div></section>
    {user?.role === "ADMIN" && <section className="archive-section"><div><h3>Dar de baja este espacio</h3><p>El aula dejará de aparecer en el directorio. Su historial se conservará.</p></div><button className="btn btn-danger-outline" onClick={() => setDeleting(true)}><Archive size={16} />Dar de baja</button></section>}
    {deleting && <DeleteDialog classroom={classroom} onClose={() => setDeleting(false)} onDeleted={() => router.push("/aulas")} />}
  </>;
}
export default function ClassroomDetailPage({ params }: { params: Promise<{ id: string }> }) { const { id } = use(params); return <ClassroomLoader key={id} id={id}>{classroom => <Detail classroom={classroom} />}</ClassroomLoader>; }
