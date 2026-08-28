"use client";

import { Suspense, useState, useCallback } from "react";

import { ProductionStream } from "@/components/ProductionStream";
import dynamic from "next/dynamic";

// @ts-nocheck -- ScenePreview utilise Three.js dynamiquement
const ScenePreview = dynamic(() => import("@/components/ScenePreview").then((m) => m.ScenePreview) as any, { ssr: false });
import PatchEditor, { PatchParam } from "@/components/PatchEditor";

const DEFAULT_PARAMS: PatchParam[] = [
  { id: "cam_fov", label: "Champ de vision", type: "range", value: 50, min: 10, max: 120, section: "camera" },
  { id: "cam_distance", label: "Distance", type: "range", value: 5, min: 1, max: 20, section: "camera" },
  { id: "cam_height", label: "Hauteur", type: "range", value: 2, min: 0, max: 10, section: "camera" },
  { id: "light_intensity", label: "Intensite", type: "range", value: 1.0, min: 0, max: 3, step: 0.1, section: "lighting" },
  { id: "light_color", label: "Couleur", type: "color", value: "#ffffff", section: "lighting" },
  { id: "light_angle", label: "Angle", type: "range", value: 45, min: 0, max: 180, section: "lighting" },
  { id: "char_scale", label: "Echelle", type: "range", value: 1.0, min: 0.1, max: 3, step: 0.1, section: "character" },
  { id: "char_rotation", label: "Rotation Y", type: "range", value: 0, min: 0, max: 360, section: "character" },
  { id: "env_fog", label: "Brouillard", type: "range", value: 0, min: 0, max: 1, step: 0.05, section: "environment" },
  { id: "env_ground_color", label: "Sol", type: "color", value: "#444444", section: "environment" },
  { id: "render_samples", label: "Samples", type: "number", value: 128, min: 1, max: 4096, section: "render" },
  { id: "render_resolution", label: "Resolution", type: "select", value: "1920x1080", options: [
    { label: "720p", value: "1280x720" },
    { label: "1080p", value: "1920x1080" },
    { label: "4K", value: "3840x2160" },
  ], section: "render" },
];

export default function RealtimePage() {
  const [params, setParams] = useState<PatchParam[]>(DEFAULT_PARAMS);

  const handleParamChange = useCallback((id: string, value: string | number) => {
    setParams((prev) => prev.map((p) => (p.id === id ? { ...p, value } : p)));
  }, []);

  const getParam = (id: string) => params.find((p) => p.id === id)?.value;

  const sceneProps = {
    cameraPosition: [0, getParam("cam_height") as number, getParam("cam_distance") as number] as [number, number, number],
    fov: getParam("cam_fov") as number,
    characterRotationY: getParam("char_rotation") as number,
    characterScale: getParam("char_scale") as number,
    ambientIntensity: getParam("light_intensity") as number,
    groundColor: getParam("env_ground_color") as string,
  };

  return (
    <Suspense fallback={<div className="p-10 text-muted">Chargement…</div>}>
      <div className="flex h-[calc(100vh-4rem)]">
        <div className="flex-1 flex flex-col">
          <div className="flex-1 bg-gray-900 rounded-lg m-2 overflow-hidden">
            {/* @ts-ignore -- ScenePreview props dynamiques */}
            <ScenePreview {...sceneProps} />
          </div>
          <div className="h-64 mx-2 mb-2">
            <ProductionStream />
          </div>
        </div>

        <div className="w-80 p-2 overflow-y-auto">
          <PatchEditor params={params} onChange={handleParamChange} />
        </div>
      </div>
    </Suspense>
  );
}
