# 05 — Skills

> Consolidation de : Roadmap A §14, B §6, C §9-10. Mécanisme NOOA (`TextSkill`, `skill_registry`) + contenu métier DeepBl4nder.

## Définition

Un skill est une unité de connaissance / procédure. Il **enrichit le contexte** ; ce n'est pas
un agent. Un agent peut exploiter plusieurs skills.

Structure type :

```text
skills/<skill-name>/
├── SKILL.md          # frontmatter (name, description) + instructions/règles
├── references/       # documentation ciblée
├── examples/         # exemples commentés
├── scripts/          # scripts réutilisables (facultatifs)
└── templates/        # gabarits (facultatifs)
```

NOOA fournit `TextSkill(path=..., id=...)` qui lit le `SKILL.md` (frontmatter YAML lenient,
style Claude Code) avec `run_script(name, ...)` et `read_file(path)` protégé.

## Catalogue

Catalogue complet embarqué (26 skills) : blender-python, storytelling, dialogue,
storyboard, cinematography, composition, feasibility, modeling, assets, uv,
texturing, shading, rigging, animation, camera, lighting, simulation, rendering,
compositing, sound-design, music, voice, translation, subtitles, continuity, qa.

## Progressive disclosure

Tous les skills ne sont pas injectés dans chaque contexte :

```text
Agent → skill discovery → skill description → documentation pertinente
  → reference/example → action
```

Exemple : CameraAgent → skill cinematography → reference lens/composition → instructions
spécifiques au plan. Cela réduit le contexte inutile.

## Distinction finale

```
Skill  = ce que l'agent sait faire / sait comment faire
Tool   = action disponible
Plugin = connexion à un système externe
```
