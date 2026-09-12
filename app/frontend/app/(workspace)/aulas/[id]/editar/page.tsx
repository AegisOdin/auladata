"use client";
import { use } from "react";
import { ClassroomLoader } from "@/components/classroom-loader";
import { ClassroomForm } from "@/components/classroom-form";
export default function EditClassroomPage({ params }: { params: Promise<{ id: string }> }) { const { id } = use(params); return <ClassroomLoader key={id} id={id}>{classroom => <ClassroomForm classroom={classroom} />}</ClassroomLoader>; }
