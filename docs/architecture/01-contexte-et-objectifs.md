# 01 — Contexte et objectifs

> Consolidation de : Roadmap A §1, B §1/§18-19, C §1/§37. Aligne la vision sur les capacités réelles de NOOA.

## Vision

DeepBl4nder transforme une intention créative en production audiovisuelle traçable, itérable
et observable :

> « Fais une scène de suspense dans une ruelle. »

devient une chaîne de production :

```text
Brief → Narration → Storyboard → Prévis/Animatic → Faisabilité → Assets → Lookdev
  → Rigging → Layout → Animation/Caméra/Lumière/Simulation → Pre-render → QA
  → Revision → Final Render → Compositing → Audio → Sous-titres/Langues
  → Final QA → Export
```

**NOOA est le runtime agentique. DeepBl4nder est le monde métier de production.**

## Objectifs ADD (contraintes)

| Exigence | Valeur cible |
|---|---|
| Latence | Brief → premier preview < 5 min ; séquence 10 s < 10 min |
| Coût | scène de démonstration < 1 € (LLM + exécution + rendu) |
| Qualité | premier passage QA ≥ 60 % sur un golden set |
| Évolutivité | 3 workers parallèles, 1 worker/scène, ajout de worker sans redémarrage |
| Fiabilité | crash → restart → reprise sans aucune perte de production |
| Observabilité | état + coût visibles en temps réel, alerte budget < 30 s |
| Sécurité | code généré : validation → politique → sandbox/worker, jamais `exec` direct |

## Portée initiale

Le pipeline couvre les 18 étapes ; la **boucle fondamentale** est le socle démontré en premier :

```text
Brief → DirectorAgent → SceneSpec/ShotSpec → BlenderAgent → skill → code généré
  → validation/politique → Blender Worker → render → QAAgent → PASS / Revision → Artifact
```

Cible courante : 5–10 s, 1 scène, 3–5 agents, 3 workers max.

**Verticale de référence** (démonstration de bout en bout) :
Brief → Story → Storyboard → Shot → Scène Blender → Caméra → Lumière → Animation simple
→ Render → QA → Revision.

Cas d'usage de référence : *« Une ruelle sombre sous la pluie, un personnage marche
lentement vers une porte pendant cinq secondes. »*

## Cas d'usage couverts progressivement

Génération de scènes Blender, storyboard, animatique, prévisualisation, variantes caméra /
décor / éclairage, animation, gestion d'assets, sound design, musique, voix, sous-titres,
traduction (dialogues, sous-titres et interface), compositing, QA, render farm.

## Critère de réussite du premier jalon

> Prendre un brief inédit, produire une séquence Blender de 5–10 s, tracer sa production,
> détecter ses défauts, effectuer une correction et produire une version améliorée.

La boucle fondamentale : `Intent → Plan → Skills → Structured Specs → Code → Worker
→ Render → QA → Revision`. C'est le socle ; le reste est une industrialisation progressive.
