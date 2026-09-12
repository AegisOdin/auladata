export type Role = "ADMIN" | "VIEWER";
export type ClassroomType = "LABORATORIO" | "TEORICA" | "MIXTA";
export type ClassroomState = "ACTIVA" | "MANTENIMIENTO" | "INACTIVA";
export interface User { id: number; name: string; email: string; role: Role; is_active: boolean }
export interface Classroom {
  id: number;
  clave: string;
  nombre: string;
  edificio: string;
  capacidad: number;
  tipo: ClassroomType;
  estado: ClassroomState;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}
export type ClassroomInput = Pick<Classroom, "clave" | "nombre" | "edificio" | "capacidad" | "tipo" | "estado">;
export interface ClassroomList { items: Classroom[]; total: number; page: number; page_size: number }
export interface Health { status: string; service: string; environment: "DEV" | "QA" | "PROD"; version: string; commit: string }
export const typeLabels: Record<ClassroomType, string> = { LABORATORIO: "Laboratorio", TEORICA: "Teórica", MIXTA: "Mixta" };
export const stateLabels: Record<ClassroomState, string> = { ACTIVA: "Activa", MANTENIMIENTO: "Mantenimiento", INACTIVA: "Inactiva" };
