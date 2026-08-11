---
name: simulation
description: Ajouter des simulations physiques : fluides, tissus, cheveux, particules, contraintes.
---

# Simulation

Utiliser les simulations Blender quand la physique compte. Les simulations ajoutent du réalisme mais sont coûteuses en temps.

## Types de simulations

| Type | Usage | Coût | Cache requis |
|------|-------|------|--------------|
| **Cloth** | Tissus, vêtements, drapeaux | Moyen | Oui |
| **Fluid** | Eau, fumée, gaz | Élevé | Oui |
| **Soft Body** | Objets mous, gelée | Moyen | Oui |
| **Particles** | Cheveux, poils, pluie, poussière | Variable | Oui |
| **Rigid Body** | Objets solides qui tombent/collident | Faible | Non |
| **Smoke** | Fumée, flammes | Élevé | Oui |

## Rigid Body (le plus simple)

```python
import bpy

# Créer un objet qui tombe
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 5))
cube = bpy.context.active_object
cube.name = "falling_cube"

# Ajouter Rigid Body
bpy.ops.rigidbody.object_add(type='ACTIVE')
cube.rigid_body.mass = 1.0  # kg
cube.rigid_body.friction = 0.5
cube.rigid_body.restitution = 0.3  # rebond

# Créer un sol
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "floor"
bpy.ops.rigidbody.object_add(type='PASSIVE')
```

## Cloth (tissu)

```python
import bpy

# Créer un plane (le tissu)
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 3))
cloth = bpy.context.active_object
cloth.name = "cloth"

# Subdivision pour la souplesse
bpy.ops.object.modifier_add(type='SUBSURF')
cloth.modifiers["Subdivision"].levels = 4

# Ajouter Cloth
bpy.ops.object.modifier_add(type='CLOTH')
cloth_mod = cloth.modifiers["Cloth"]

# Paramètres
cloth_mod.settings.mass = 0.3
cloth_mod.settings.tension_stiffness = 15
cloth_mod.settings.compression_stiffness = 15
cloth_mod.settings.shear_stiffness = 5
cloth_mod.settings.bending_stiffness = 0.5

# Collision avec un objet
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 2))
sphere = bpy.context.active_object
sphere.name = "collision_sphere"
bpy.ops.rigidbody.object_add(type='PASSIVE')
```

## Fluid (fluide)

```python
import bpy

# Domain (le conteneur de simulation)
bpy.ops.mesh.primitive_cube_add(size=3, location=(0, 0, 1.5))
domain = bpy.context.active_object
domain.name = "fluid_domain"

bpy.ops.object.modifier_add(type='FLUID')
domain.modifiers["Fluid"].settings.type = 'DOMAIN'
domain.modifiers["Fluid"].settings.domain_type = 'LIQUID'
domain.modifiers["Fluid"].settings.resolution = 64
domain.modifiers["Fluid"].settings.cache_type = 'MODULAR'

# Objet liquide (la source)
bpy.ops.mesh.primitive_cube_add(size=0.5, location=(0, 0, 2.5))
fluid_source = bpy.context.active_object
fluid_source.name = "fluid_source"

bpy.ops.object.modifier_add(type='FLUID')
fluid_source.modifiers["Fluid"].settings.type = 'FLOW'
fluid_source.modifiers["Fluid"].settings.flow_type = 'LIQUID'
fluid_source.modifiers["Fluid"].settings.flow_behavior = 'INFLOW'
```

## Particles (cheveux/pluie)

```python
import bpy

# Créer un émetteur
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 5))
emitter = bpy.context.active_object
emitter.name = "rain_emitter"

# Ajouter un système de particules
bpy.ops.object.particle_system_add()
ps = emitter.particle_systems[0]
settings = ps.settings

# Paramètres pluie
settings.count = 10000
settings.frame_start = 1
settings.frame_end = 250
settings.lifetime = 50
settings.emission_from = 'FACE'

# Physics
settings.physics_type = 'NEWTON'
settings.particle_size = 0.01
settings.mass = 0.001

# Render
settings.render_type = 'OBJECT'
settings.particle_size = 0.02
```

## Cache des simulations

```python
# Pour toutes les simulations (cloth, fluid, etc.)
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = 250

# Le cache est automatiquement créé dans //cache/
# OU manuellement :
bpy.ops.ptcache.bake_all(bake=True)
```

### Règles de cache
1. **Toujours cacher avant le render** : les simulations ne sont pas déterministes sans cache.
2. **Seed fixe** : `settings.seed = 42` pour la reproductibilité.
3. **Tester à basse résolution** : `resolution = 32` pour les tests, `128-256` pour le final.
4. **Vérifier la stabilité** : pas de blow-up, pas d'artefacts.

## Déterminisme

```python
# Fixer les seeds pour la reproductibilité
# Particles
settings.seed = 42

# Cloth (pas de seed direct, mais le cache le fige)
# Fluid
domain.modifiers["Fluid"].settings.seed = 42

# Rigid Body (pas de seed, mais déterministe par défaut)
```

## Budget

| Simulation | Résolution test | Résolution final | Temps estimé |
|------------|----------------|------------------|--------------|
| Rigid Body | 10 objets | 50 objets | 1-5 min |
| Cloth | 64x64 | 256x256 | 5-30 min |
| Particles | 1000 | 10000 | 2-10 min |
| Fluid | 32 | 128-256 | 30 min - 4 h |

## Erreurs courantes

1. **Pas de cache** : simulation différente à chaque frame = non déterministe.
2. **Résolution trop haute** : temps de simulation excessive.
3. **Pas de collision** : objets qui se traversent.
4. **Seed variable** : même paramètres mais résultat différent.
5. **Oublier le frame range** : simulation qui dépasse la durée du plan.
6. **Trop de particules** : lent, mémoire insuffisante.

## Règles

- Ne simuler que si nécessaire (fluide, tissu, cheveux, soft body) ; sinon animer à la main.
- Cache la simulation : la précalculer et la figer avant le render final.
- Seed fixe et paramètres déterministes pour la reproductibilité.
- Budget : réduire la résolution de simulation pour les tests, augmenter au final.
- Vérifier la stabilité (pas de blow-up) avant de lancer le render.
- Livrer un `SimulationCache` versionné rattaché à l'`AnimatedScene`.
