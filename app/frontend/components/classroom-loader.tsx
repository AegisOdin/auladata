"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, errorMessage } from "@/lib/api";
import type { Classroom } from "@/types";

export function ClassroomLoader({ id, children }: { id: string; children: (classroom: Classroom) => React.ReactNode }) {
  const [classroom, setClassroom] = useState<Classroom | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let live = true;
    api.classroom(id).then(value => { if (live) setClassroom(value); }).catch(error => { if (live) setError(errorMessage(error)); });
    return () => { live = false; };
  }, [id]);
  if (error) return <div className="empty-page"><h1>No se pudo consultar el aula</h1><p role="alert">{error}</p><Link className="btn btn-secondary" href="/aulas">Volver a las aulas</Link></div>;
  if (!classroom) return <div className="table-feedback" role="status"><span className="spinner" />Cargando aula…</div>;
  return children(classroom);
}
