# DeepBlender

---

## Contexte et vision

L'idée centrale est d'utiliser une architecture multi-agents grace a [NVIDIA NeMo Labs OO-Agents](https://github.com/NVIDIA-NeMo/labs-OO-Agents), pour piloter Blender de façon structurée. Avant de parler d'agents, il faut comprendre comment un film ou une animation est réellement produit:

1. Intention & Briefing
2. Scénario et structure narrative
3. Storyboard
4. Prévisualisation (Prévis / Animatic) + bande-son de référence
5. Étude de faisabilité technique
6. Préparation des assets (Modélisation)
7. UV Mapping / Texturing / Shading
8. Rigging et Weight Painting
9. Mise en scène (Layout) dans Blender
10. Animation, Caméra et Lumière (ajout des simulations si besoin)
11. Rendu préliminaire (tests de qualité)
12. Itérations et corrections (retour aux étapes 9 ou 10)
13. Rendu final (Render Farm ou local)
14. Compositing
15. Mixage audio final, sous-titres et langues
16. Contrôle qualité et export (codec, couleurs, etc.)

Cette approche permettrait de passer d'une demande vague comme "fais une scène de suspense dans une ruelle" à une scène Blender exploitable, puis à une version animée ou filmée.

## Objectifs et non-objectifs

### Objectifs

- Transformer une intention textuelle en scène Blender, storyboard, séquence courte ou étude visuelle.
- Découper la production en compétences précises reliées à des agents et sous-agents bien définis.
- Fournir un runtime d'orchestration réutilisable, avec une architecture modulaire et extensible.
- Garantir la traçabilité (provenance, versions), l'observabilité et le contrôle des coûts.
- Garder l'humain dans la boucle à chaque étape où la décision a de la valeur.

### Non-objectifs

- Générer des longs métrages autonomes dès le départ (le MVP vise des séquences de 5 à 10 secondes).
- Remplacer l'expertise d'un studio: DeepBlender est une production assistée, pas un remplacement.
- Écrire tout le code d'un coup: ce document décrit la cible, l'implémentation suit un chemin incrémental.

### Qualité et métriques de succès

L'architecture ne peut pas être jugée sans cibles mesurables. Ces objectifs sont revus à chaque palier d'implémentation:

- **Latence**: du brief au premier rendu d'essai, cible < 5 min sur scène de démo; < 10 min pour une séquence de 10 s.
- **Coût**: cible < 1 € par scène de démo (LLM + rendu), mesuré via la provenance des coûts.
- **Qualité**: taux de passage QA automatique au premier coup ≥ 60 % à maturité, mesuré sur un golden set de scènes de référence.
- **Évolutivité**: 3 workers parallèles sur une machine, 1 worker par scène, rendu GPU; le système tolère l'ajout d'un worker sans redémarrage.
- **Fiabilité**: une production interrompue (crash du Runtime Controller) reprend par rejeu des événements non consommés; aucune perte de données acceptée.
- **Observabilité**: état et coût visibles en temps réel; alerte sur dépassement de budget en moins de 30 s.
- **Sécurité**: aucun code généré ne s'exécute en dehors du périmètre autorisé; aucune opération non autorisée n'est exécutée silencieusement.

## Compétences à couvrir

- narration et structure dramatique;
- écriture de dialogues;
- découpage en plans;
- composition visuelle;
- création et gestion d'assets;
- rigging et pose;
- animation de personnages et d'objets;
- caméra et cadrage;
- éclairage et ambiance;
- sound design;
- musique et mixage;
- voix, accents et diction;
- traduction et sous-titres;
- étude de faisabilité et prévisualisation;
- continuité et contrôle qualité.

## Cas d'usage

- Générer une scène Blender à partir d'un brief textuel.
- Créer un storyboard simple avant animation.
- Produire une animatique pour prévisualiser un épisode ou un court métrage.
- Préparer une séquence stylisée type anime, cartoon ou semi-réaliste.
- Étudier rapidement plusieurs variantes de décor, d'éclairage ou de caméra avant production.
- Évaluer si une idée est réalisable techniquement dans un délai et avec des ressources données.
- Aider un créateur à itérer plus vite sur le décor, la caméra et le mouvement.
- Ajouter une piste audio, des effets sonores et une musique d'ambiance adaptés à la scène.
- Gérer plusieurs langues pour les dialogues, les sous-titres et l'interface.