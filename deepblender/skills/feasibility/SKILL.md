---
name: feasibility
description: Étudier la faisabilité technique d'une idée : durée, complexité, ressources, budget, risques.
---

# Faisabilité

Évaluer si une intention est réalisable avec un délai et des ressources donnés. Cette étape évite de commencer un projet qui ne pourra pas être terminé.

## Facteurs d'évaluation

### 1. Durée du plan

| Durée | Complexité | Risque |
|-------|-----------|--------|
| 1-3 s | Faible | Très faisable |
| 3-10 s | Moyen | Faisable avec soin |
| 10-30 s | Élevé | Nécessite une planification |
| 30-60 s | Très élevé | Risqué sans experience |
| > 60 s | Extrem | Déconseillé sans équipe |

- **Règle** : pour un premier plan, commencer par 5-8 s.
- **Budget temps** : 1 s de rendu = 1-10 minutes de calcul (selon complexité).

### 2. Nombre de plans

```
Total = nb_plans × durée_moyenne × facteur_complexité

Exemple : 5 plans × 8 s × 1.5 = 60 s de vidéo finale
```

- **Facteur complexité** : 1.0 (simple), 1.5 (moyen), 2.0 (complexe).
- **Rendu** : multiplier par le temps de rendu par frame × frames par plan.

### 3. Assets requis

| Type | Difficulté | Temps estimé |
|------|-----------|--------------|
| Primitives simples | Faible | 5-15 min |
| Props détaillés | Moyen | 30-60 min |
| Personnages | Élevé | 2-8 h |
| Environnements | Élevé | 1-4 h |
| Animations complexes | Très élevé | 4-16 h |
| Simulations | Variable | 1-8 h |

### 4. Budget GPU

```python
# Estimation par frame (Cycles)
samples = 256
resolution = 1920 * 1080  # 2M pixels
complexity = 1.5  # matériaux simples
time_per_frame = (samples / 1000) * (resolution / 1e6) * complexity * 60  # secondes

# Pour 250 frames (10 s à 25 fps)
total_time = time_per_frame * 250 / 3600  # heures
```

### 5. Coût LLM

```python
# Estimation par étape
director_cost = 0.005  # $ par plan
blender_cost = 0.010   # $ par plan
qa_cost = 0.003        # $ par plan
render_cost = 0.0      # GPU local
audio_cost = 0.005     # $ par plan
compositing_cost = 0.003  # $ par plan
localization_cost = 0.008  # $ par langue

total_per_plan = sum([director_cost, blender_cost, qa_cost, 
                      render_cost, audio_cost, compositing_cost])
# ≈ $0.026 par plan
```

## Matrice de décision

### Faisable ✅
- 1-5 plans de 5-10 s
- Assets simples à moyens
- Pas de simulation
- Rendu Eevee ou Cycles basse résolution
- Budget GPU < 2 h

### Risqué ⚠️
- 5-10 plans de 10-20 s
- Personnages avec rig
- Simulations simples (cloth, particles)
- Rendu Cycles moyen
- Budget GPU 2-8 h

### Non faisable ❌
- > 10 plans de > 20 s
- Personnages avec animation faciale
- Simulations fluides/soft body
- Rendu Cycles haute résolution
- Budget GPU > 8 h

## Simplifications

| Problème | Solution |
|----------|----------|
| Trop de plans | Réduire à 3-5 plans essentiels |
| Personnage complexe | Utiliser des formes abstraites |
| Animation fluide | Réduire à des mouvements simples |
| Rendu lent | Passer à Eevee, réduire résolution |
| Simulation | Remplacer par une animation clé |
| Environnement | Simplifier, utiliser un fond uni |

## Rapport de faisabilité

```python
feasibility_report = {
    "verdict": "faisable" | "risque" | "non_faisable",
    "duration": "8 s",
    "shots": 4,
    "complexity": "moyen",
    "estimated_render_time": "45 min",
    "estimated_cost": "$0.10",
    "risques": ["animation de caméra complexe", "matériaux verre"],
    "simplifications": ["réduire le nombre de plans", "remplacer le verre par un matériau simple"],
    "recommendation": "Commencer par un test de 3 s"
}
```

## Erreurs courantes

1. **Sous-estimer le rendu** : un plan de 10 s à 512 samples peut prendre 1 h.
2. **Trop d'assets** : chaque asset = temps de modélisation + texturing + materials.
3. **Ignorer le budget LLM** : les appels API coûtent, surtout avec des prompts longs.
4. **Pas de plan B** : toujours prévoir une version simplifiée.
5. **Commencer complexe** : toujours commencer simple, enrichir après.

## Règles

- Décomposer en étapes du pipeline (préproduction → export).
- Estimer : durée, complexité, assets requis, besoin GPU, coût LLM/render.
- Identifier les risques (assets manquants, simulations coûteuses, rig complexe).
- Proposer des simplifications si le brief dépasse les contraintes.
- Sortir un `FeasibilityReport` typé : verdict, estimation, contraintes, alternatives.
- Réviser le plan (durée, complexité, périmètre) si les contraintes sont dépassées.
- Toujours prévoir une version simplifiée.
