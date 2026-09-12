import { Building2 } from "lucide-react";
export function Brand({ inverse = false }: { inverse?: boolean }) {
  return <div className={`brand ${inverse ? "brand-inverse" : ""}`}><span className="brand-mark"><Building2 size={25} strokeWidth={1.8} /></span><span>Aula<span className="brand-data">Data</span></span></div>;
}
