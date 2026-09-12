import type { Metadata } from "next";
import { AuthProvider } from "@/components/auth-provider";
import "@fontsource-variable/manrope";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "AulaData | Gestión de aulas", template: "%s | AulaData" },
  description: "Gestión de espacios académicos, disponibilidad y capacidad de aulas.",
  icons: { icon: "/icon.svg" },
};
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="es"><body><AuthProvider>{children}</AuthProvider></body></html>;
}
