"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ArrowLeft, Building2, Check, Info, Save } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { api, errorMessage } from "@/lib/api";
import { stateLabels, typeLabels, type Classroom, type ClassroomInput } from "@/types";

const empty: ClassroomInput = { clave: "", nombre: "", edificio: "", capacidad: 30, tipo: "TEORICA", estado: "ACTIVA" };
export function ClassroomForm({ classroom }: { classroom?: Classroom }) {
  const { user } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<ClassroomInput>(classroom ? { clave: classroom.clave, nombre: classroom.nombre, edificio: classroom.edificio, capacidad: classroom.capacidad, tipo: classroom.tipo, estado: classroom.estado } : empty);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const editing = Boolean(classroom);
  const back = classroom ? `/aulas/${classroom.id}` : "/aulas";
  if (user?.role !== "ADMIN") return <div className="empty-page"><h1>Acceso de consulta</h1><p>Solo un administrador puede registrar o editar aulas.</p><Link className="btn btn-secondary" href="/aulas">Volver a las aulas</Link></div>;
  function update<K extends keyof ClassroomInput>(key: K, value: ClassroomInput[K]) { setData(current => ({ ...current, [key]: value })); }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError("");
    if (![data.clave, data.nombre, data.edificio].every(value => value.trim()) || !Number.isInteger(data.capacidad) || data.capacidad <= 0) { setError("Completa los campos y usa una capacidad entera mayor que cero."); return; }
    setPending(true);
    const input = { ...data, clave: data.clave.trim().toUpperCase(), nombre: data.nombre.trim(), edificio: data.edificio.trim() };
    try { const result = classroom ? await api.update(String(classroom.id), input) : await api.create(input); router.push(`/aulas/${result.id}?saved=${editing ? "updated" : "created"}`); }
    catch (error) { setError(errorMessage(error)); setPending(false); }
  }
  return <>
    <Link className="back-link" href={back}><ArrowLeft size={16} />{editing ? "Volver al detalle" : "Volver a las aulas"}</Link><div className="page-heading"><div><h1>{editing ? "Editar aula" : "Registrar nueva aula"}</h1><p>{editing ? "Actualiza los datos de este espacio académico." : "Agrega un espacio al directorio del campus."}</p></div></div>
    <div className="form-layout"><form className="form-card" onSubmit={submit}><div className="form-card-heading"><Building2 size={21} /><div><h2>Información del aula</h2><p>Todos los campos son obligatorios.</p></div></div><fieldset disabled={pending} className="form-fields"><legend className="sr-only">Datos del aula</legend>
      <div className="field"><label htmlFor="clave">Clave del aula</label><input id="clave" name="clave" required maxLength={20} value={data.clave} onChange={event => update("clave", event.target.value)} placeholder="Ej. ISC-A04" /><small>Identificador único, hasta 20 caracteres.</small></div>
      <div className="field"><label htmlFor="nombre">Nombre</label><input id="nombre" name="nombre" required maxLength={100} value={data.nombre} onChange={event => update("nombre", event.target.value)} placeholder="Ej. Laboratorio de Redes" /></div>
      <div className="form-grid"><div className="field"><label htmlFor="edificio">Edificio</label><input id="edificio" name="edificio" required maxLength={50} value={data.edificio} onChange={event => update("edificio", event.target.value)} placeholder="Ej. Edificio K" /></div><div className="field"><label htmlFor="capacidad">Capacidad</label><div className="input-suffix"><input id="capacidad" name="capacidad" type="number" required min={1} step={1} value={Number.isNaN(data.capacidad) ? "" : data.capacidad} onChange={event => update("capacidad", event.target.valueAsNumber)} /><span>personas</span></div></div></div>
      <div className="form-grid"><div className="field"><label htmlFor="tipo">Tipo de aula</label><select id="tipo" value={data.tipo} onChange={event => update("tipo", event.target.value as ClassroomInput["tipo"])}>{Object.entries(typeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div><div className="field"><label htmlFor="estado">Estado</label><select id="estado" value={data.estado} onChange={event => update("estado", event.target.value as ClassroomInput["estado"])}>{Object.entries(stateLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></div></div>
    </fieldset>{error && <div className="alert form-error" role="alert">{error}</div>}<div className="form-actions form-card-actions"><Link className="btn btn-secondary" href={back}>Cancelar</Link><button className="btn btn-primary" disabled={pending}><Save size={17} />{pending ? "Guardando…" : editing ? "Guardar cambios" : "Registrar aula"}</button></div></form>
    <aside className="form-help"><div className="help-icon"><Info size={22} /></div><h3>Un directorio al día</h3><p>La información precisa ayuda a aprovechar mejor cada espacio del campus.</p><ul><li><Check size={16} />Usa una clave fácil de identificar.</li><li><Check size={16} />Registra la capacidad real del aula.</li><li><Check size={16} />Mantén actualizado su estado.</li></ul><div className="help-divider" /><strong>Acerca del estado</strong><p><b>Activa:</b> disponible para su uso.<br /><b>Mantenimiento:</b> en reparación.<br /><b>Inactiva:</b> fuera de servicio.</p></aside></div>
  </>;
}
