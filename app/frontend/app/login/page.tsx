"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Brand } from "@/components/brand";
import { Environment } from "@/components/environment";
import { ApiError, errorMessage } from "@/lib/api";

export default function LoginPage() {
  const { user, login, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  useEffect(() => { if (user && !loading) router.replace("/aulas"); }, [user, loading, router]);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try { await login(email.trim(), password); router.replace("/aulas"); }
    catch (error) { setError(error instanceof ApiError && error.status === 401 ? "El correo o la contraseña no son correctos." : errorMessage(error)); }
    finally { setSubmitting(false); }
  }
  return <main className="login-page">
    <section className="login-story"><Brand inverse /><div className="login-story-body"><div className="login-intro">Un campus mejor organizado</div><h1>Cada espacio.<br />En su lugar.</h1><p>La información de tus aulas, siempre a mano. Consulta, organiza y mantén al día los espacios donde comienza el aprendizaje.</p>
      <div className="campus-plan" aria-hidden="true"><svg viewBox="0 0 450 235" fill="none"><path d="M34 36H411V198H34V36Z M34 118H411 M153 36V118 M282 36V118 M153 152V198 M282 152V198 M34 152H411" stroke="currentColor" strokeWidth="1.5" /><path d="M65 56h20v17H65z M101 56h20v17h-20z M65 86h20v17H65z M101 86h20v17h-20z M188 55h64v48h-64z M314 56h20v17h-20z M350 56h20v17h-20z M314 86h20v17h-20z M350 86h20v17h-20z M60 170h65 M179 170h70 M309 170h65" stroke="currentColor" strokeWidth="1.5" /><path d="M153 118h34m95 0h33m-162 34h34m95 0h33" stroke="#183471" strokeWidth="4" /><circle cx="224" cy="135" r="7" fill="#9bc5ff" /><circle cx="224" cy="135" r="14" stroke="#9bc5ff" strokeOpacity=".35" /></svg><div className="plan-caption"><span className="plan-dot" />Conecta la información con tus espacios</div></div>
    </div><span className="login-story-footer">AulaData / Infraestructura de Servicios</span></section>
    <section className="login-panel"><div className="login-mobile-brand"><Brand /></div><div className="login-form-wrapper"><div className="login-icon"><LockKeyhole size={25} /></div><h2>Bienvenido a AulaData</h2><p className="login-subtitle">Inicia sesión para acceder a tu espacio de trabajo.</p>
      <form onSubmit={submit} className="login-form">
        <label htmlFor="email">Correo electrónico</label><div className="input-with-icon"><Mail size={18} /><input id="email" name="email" type="email" autoComplete="username" disabled={loading || submitting} required maxLength={254} value={email} onChange={event => setEmail(event.target.value)} placeholder="nombre@institucion.edu" /></div>
        <label htmlFor="password">Contraseña</label><div className="input-with-icon"><LockKeyhole size={18} /><input id="password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" disabled={loading || submitting} required maxLength={128} value={password} onChange={event => setPassword(event.target.value)} placeholder="Ingresa tu contraseña" /><button className="icon-button password-toggle" type="button" aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
        {error && <div className="alert" role="alert">{error}</div>}
        <button className="btn btn-primary login-submit" disabled={submitting || loading}>{submitting ? "Iniciando sesión…" : "Iniciar sesión"}<ArrowRight size={18} /></button>
      </form><p className="login-help">¿Necesitas acceso? Solicita una cuenta al administrador de tu institución.</p>
    </div><div className="login-meta"><Environment /></div></section>
  </main>;
}
