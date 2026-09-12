import { stateLabels, type ClassroomState } from "@/types";
export function StatusBadge({ state }: { state: ClassroomState }) { return <span className={`status-badge status-${state.toLowerCase()}`}><i />{stateLabels[state]}</span>; }
