"use client";
import { useEffect, useRef, useState } from "react";
import { Archive, X } from "lucide-react";
import { api, errorMessage } from "@/lib/api";
import type { Classroom } from "@/types";

export function DeleteDialog({ classroom, onClose, onDeleted }: { classroom: Classroom; onClose: () => void; onDeleted: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => { const element = dialog.current; element?.showModal(); return () => element?.close(); }, []);
  async function remove() {
    setPending(true); setError("");
    try { await api.remove(classroom.id); onDeleted(); }
    catch (error) { setError(errorMessage(error)); setPending(false); }
  }
  return <dialog ref={dialog} className="confirm-dialog" aria-labelledby="delete-title" onCancel={event => { event.preventDefault(); if (!pending) onClose(); }}>
    <button className="dialog-close icon-button" aria-label="Cerrar confirmación" disabled={pending} onClick={onClose}><X size={20} /></button><div className="dialog-icon"><Archive size={25} /></div><h2 id="delete-title">¿Deseas dar de baja esta aula?</h2><p><strong>{classroom.clave} · {classroom.nombre}</strong> dejará de aparecer en el directorio. Su registro se conservará en la base de datos.</p>
    {error && <div className="alert" role="alert">{error}</div>}
    <div className="form-actions"><button className="btn btn-secondary" disabled={pending} onClick={onClose}>Cancelar</button><button className="btn btn-danger" disabled={pending} onClick={() => void remove()}>{pending ? "Dando de baja…" : "Dar de baja"}</button></div>
  </dialog>;
}
