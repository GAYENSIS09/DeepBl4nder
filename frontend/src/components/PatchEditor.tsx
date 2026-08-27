"use client";

import { useState, useCallback } from "react";

interface PatchParam {
  id: string;
  label: string;
  type: "text" | "number" | "select" | "color" | "range";
  value: string | number;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
  section?: string;
}

interface PatchEditorProps {
  params: PatchParam[];
  onChange: (id: string, value: string | number) => void;
  onApply?: () => void;
}

const PARAM_SECTIONS: Record<string, string> = {
  camera: "Camera",
  lighting: "Eclairage",
  character: "Personnage",
  environment: "Environnement",
  render: "Rendu",
};

export default function PatchEditor({ params, onChange, onApply }: PatchEditorProps) {
  const [expandedSection, setExpandedSection] = useState<string | null>("camera");
  const [draggedParam, setDraggedParam] = useState<string | null>(null);

  const sections = Array.from(new Set(params.map((p) => p.section || "camera")));

  const handleDragStart = useCallback((id: string) => {
    setDraggedParam(id);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const handleDrop = useCallback(
    (targetId: string) => {
      if (draggedParam && draggedParam !== targetId) {
        onChange(draggedParam, params.find((p) => p.id === targetId)?.value ?? "");
      }
      setDraggedParam(null);
    },
    [draggedParam, params, onChange]
  );

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-semibold text-gray-800">Editeur de Parametres</h3>
        {onApply && (
          <button
            onClick={onApply}
            className="px-3 py-1 text-xs font-medium text-white bg-blue-600 rounded hover:bg-blue-700"
          >
            Appliquer
          </button>
        )}
      </div>

      <div className="divide-y divide-gray-100">
        {sections.map((section) => {
          const sectionParams = params.filter((p) => (p.section || "camera") === section);
          const isExpanded = expandedSection === section;

          return (
            <div key={section}>
              <button
                onClick={() => setExpandedSection(isExpanded ? null : section)}
                className="w-full flex items-center justify-between px-4 py-2 text-xs font-medium text-gray-600 hover:bg-gray-50"
              >
                <span>{PARAM_SECTIONS[section] || section}</span>
                <svg
                  className={`w-4 h-4 transition-transform ${isExpanded ? "rotate-180" : ""}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {isExpanded && (
                <div className="px-4 py-3 space-y-3 bg-gray-50">
                  {sectionParams.map((param) => (
                    <div
                      key={param.id}
                      draggable
                      onDragStart={() => handleDragStart(param.id)}
                      onDragOver={handleDragOver}
                      onDrop={() => handleDrop(param.id)}
                      className={`flex flex-col gap-1 p-2 rounded cursor-move transition-colors ${
                        draggedParam === param.id ? "bg-blue-50 border border-blue-200" : "hover:bg-white"
                      }`}
                    >
                      <label className="text-xs font-medium text-gray-700">{param.label}</label>

                      {param.type === "text" && (
                        <input
                          type="text"
                          value={param.value as string}
                          onChange={(e) => onChange(param.id, e.target.value)}
                          className="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        />
                      )}

                      {param.type === "number" && (
                        <input
                          type="number"
                          value={param.value as number}
                          min={param.min}
                          max={param.max}
                          step={param.step}
                          onChange={(e) => onChange(param.id, parseFloat(e.target.value))}
                          className="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        />
                      )}

                      {param.type === "range" && (
                        <div className="flex items-center gap-2">
                          <input
                            type="range"
                            value={param.value as number}
                            min={param.min ?? 0}
                            max={param.max ?? 100}
                            step={param.step ?? 1}
                            onChange={(e) => onChange(param.id, parseFloat(e.target.value))}
                            className="flex-1"
                          />
                          <span className="text-xs text-gray-500 w-12 text-right">{String(param.value)}</span>
                        </div>
                      )}

                      {param.type === "select" && (
                        <select
                          value={param.value as string}
                          onChange={(e) => onChange(param.id, e.target.value)}
                          className="px-2 py-1 text-sm border border-gray-300 rounded focus:ring-1 focus:ring-blue-500"
                        >
                          {param.options?.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      )}

                      {param.type === "color" && (
                        <div className="flex items-center gap-2">
                          <input
                            type="color"
                            value={param.value as string}
                            onChange={(e) => onChange(param.id, e.target.value)}
                            className="w-8 h-8 border border-gray-300 rounded cursor-pointer"
                          />
                          <span className="text-xs text-gray-500">{param.value as string}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export type { PatchParam, PatchEditorProps };
