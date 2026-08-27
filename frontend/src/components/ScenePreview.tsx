// @ts-nocheck - This component requires @react-three/fiber, @react-three/drei, and three
// to be installed. TypeScript errors are expected when these packages are not present.
'use client';

import { useEffect, useState } from 'react';

interface ScenePreviewProps {
  sceneUrl?: string;
  characters?: Array<{ name: string; position: [number, number, number] }>;
  camera?: {
    position: [number, number, number];
    target: [number, number, number];
    focalLength?: number;
  };
  environment?: {
    lightingMood?: string;
    rain?: boolean;
  };
  isPlaying?: boolean;
}

export function ScenePreview({
  characters = [],
  environment,
  isPlaying = false,
}: ScenePreviewProps) {
  const [hasThree, setHasThree] = useState<boolean | null>(null);

  useEffect(() => {
    // @ts-ignore - dynamic import, types will be available when packages are installed
    import('@react-three/fiber')
      .then(() => setHasThree(true))
      .catch(() => setHasThree(false));
  }, []);

  if (hasThree === null) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg bg-off-black text-muted">
        <p>Chargement de la preview 3D...</p>
      </div>
    );
  }

  if (!hasThree) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-lg bg-off-black text-muted gap-3 p-6">
        <div className="text-4xl">🎬</div>
        <p className="text-lg font-display text-off-white">Preview 3D</p>
        <p className="text-center text-xs max-w-sm">
          Installez les dépendances Three.js pour activer la prévisualisation 3D interactive.
        </p>
        <code className="rounded bg-off-black border border-border px-3 py-1.5 text-xs text-acid">
          npm install three @react-three/fiber @react-three/drei @types/three
        </code>
        {characters.length > 0 && (
          <div className="mt-2 text-center">
            <p className="text-xs text-muted">
              {characters.length} personnage{characters.length !== 1 ? 's' : ''} dans la scène
            </p>
            <ul className="mt-1 text-xs text-muted">
              {characters.map((c, i) => (
                <li key={i}>{c.name}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  return <_ThreeScene characters={characters} environment={environment} isPlaying={isPlaying} />;
}

function _ThreeScene(props: { characters: ScenePreviewProps['characters']; environment: ScenePreviewProps['environment']; isPlaying: boolean }) {
  const [SceneModule, setSceneModule] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      // @ts-ignore - dynamic import
      import('@react-three/fiber'),
      // @ts-ignore - dynamic import
      import('@react-three/drei'),
    ]).then(([fiber, drei]) => {
      setSceneModule({ Canvas: fiber.Canvas, OrbitControls: drei.OrbitControls });
    });
  }, []);

  if (!SceneModule) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg bg-off-black text-muted">
        <p>Chargement du moteur 3D...</p>
      </div>
    );
  }

  return <_RenderScene {...props} Canvas={SceneModule.Canvas} OrbitControls={SceneModule.OrbitControls} />;
}

function _RenderScene({
  characters = [],
  environment,
  isPlaying,
  Canvas,
  OrbitControls,
}: {
  characters: ScenePreviewProps['characters'];
  environment: ScenePreviewProps['environment'];
  isPlaying: boolean;
  Canvas: any;
  OrbitControls: any;
}) {
  return (
    <div className="relative h-full w-full rounded-lg overflow-hidden bg-off-black">
      <Canvas shadows gl={{ antialias: true }} camera={{ position: [0, 5, 10], fov: 50 }}>
        <ambientLight intensity={environment?.lightingMood === 'dark' ? 0.1 : 0.3} />
        <directionalLight position={[5, 8, 5]} intensity={2.0} castShadow />
        <pointLight position={[-5, 3, -5]} intensity={0.5} color="#4a9eff" />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
          <planeGeometry args={[40, 40]} />
          <meshStandardMaterial color="#1a1a2e" roughness={0.8} metalness={0.2} />
        </mesh>

        {characters?.map((char, i) => (
          <group key={char.name || i} position={char.position}>
            <mesh position={[0, 0.85, 0]} castShadow>
              <capsuleGeometry args={[0.3, 1.0, 8, 16]} />
              <meshStandardMaterial color={`hsl(${i * 60}, 60%, 50%)`} roughness={0.6} />
            </mesh>
            <mesh position={[0, 1.7, 0]} castShadow>
              <sphereGeometry args={[0.2, 16, 16]} />
              <meshStandardMaterial color="#e0c8a0" roughness={0.7} />
            </mesh>
          </group>
        ))}

        <OrbitControls enablePan enableZoom enableRotate autoRotate={isPlaying} autoRotateSpeed={0.5} />
      </Canvas>

      <div className="absolute bottom-2 left-2 rounded bg-black/60 px-2 py-1 text-xs text-muted">
        {characters?.length ?? 0} personnage{(characters?.length ?? 0) !== 1 ? 's' : ''} · Cliquez pour orbiter
      </div>
    </div>
  );
}
