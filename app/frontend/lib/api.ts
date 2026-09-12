import type { Classroom, ClassroomInput, ClassroomList, Health, User } from "@/types";

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); this.name = "ApiError"; }
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Content-Type": "application/json", "X-Requested-With": "AulaData", ...init.headers },
    });
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    throw new ApiError(0, "No se pudo conectar. Revisa tu conexión e intenta de nuevo.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    let message = "No se pudo completar la solicitud. Intenta de nuevo.";
    if (response.status === 401) message = "Tu sesión terminó. Inicia sesión de nuevo.";
    if (response.status === 403) message = "No tienes permiso para realizar esta acción.";
    if (response.status === 404) message = "El aula no existe o fue dada de baja.";
    if (response.status === 409) message = "Esta clave ya está registrada. Usa una clave diferente.";
    if (response.status === 422) message = "Revisa los campos: los textos son obligatorios y la capacidad debe ser un entero mayor que cero.";
    if (response.status >= 500) message = "El servicio no está disponible. Intenta de nuevo en unos momentos.";
    if (typeof body.detail === "string" && response.status === 400) message = body.detail;
    if (response.status === 401 && !path.includes("/auth/")) window.dispatchEvent(new Event("auladata:unauthorized"));
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

const base = "/api/v1";
export const api = {
  me: () => request<User>(`${base}/auth/me`),
  login: (email: string, password: string) => request<User>(`${base}/auth/login`, { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<void>(`${base}/auth/logout`, { method: "POST" }),
  health: () => request<Health>("/health"),
  list: (query: string, signal?: AbortSignal) => request<ClassroomList>(`${base}/classrooms?${query}`, { signal }),
  classroom: (id: string) => request<Classroom>(`${base}/classrooms/${encodeURIComponent(id)}`),
  create: (data: ClassroomInput) => request<Classroom>(`${base}/classrooms`, { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: ClassroomInput) => request<Classroom>(`${base}/classrooms/${encodeURIComponent(id)}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: number) => request<void>(`${base}/classrooms/${id}`, { method: "DELETE" }),
};
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : "Ocurrió un error. Intenta de nuevo.";
export const formatDate = (value: string) => new Intl.DateTimeFormat("es-MX", { day: "2-digit", month: "short", year: "numeric" }).format(new Date(value));
