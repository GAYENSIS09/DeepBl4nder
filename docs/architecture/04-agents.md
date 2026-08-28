# 04 — Agents : runs, transitions, collaboration

> Consolidation de : Roadmap A §23/§29-30, C §6-7/§24-34.

## Agents

```
DirectorAgent ──► BlenderAgent ──► QAAgent
```

- **DirectorAgent** : comprend le brief, structure l'intention, crée `SceneSpec`/`ShotSpec`,
  sélectionne les skills, planifie la production.
- **BlenderAgent** : transforme les specs en actions Blender, génère/fait générer le Python,
  utilise les tools, interagit avec le `BlenderPlugin`, interprète les résultats du worker.
- **QAAgent** : QA technique, visuel, continuité, sémantique ; diagnostic ; produit un
  `RevisionSpec`.

Ne pas multiplier prématurément les agents : les capacités spécialisées viennent par les skills.

## Agent Run vs Production Run

```
Agent Run (NOOA)                Production Run (DeepBl4nder)
Agent → Context → Memory         Project → Production Step → Artifact
  → Method → LLM → Code/Tool       → Worker → Render/Process → QA
  → Validation → Result            → Revision → Artifact version
  → Events / Trace
```

Les deux sont **corrélés**, jamais fusionnés.

## Identité de corrélation

Chaque opération importante est reliée par : `project_id`, `sequence_id`, `shot_id`,
`production_run_id`, `step_id`, `agent_run_id`, `event_id`, `artifact_id`,
`artifact_version`, `worker_id`, `model`, `skill_versions`, `cost`, `timestamps`.

## Lifecycles

**Agent Run** : CREATED → CONTEXT BUILT → MEMORY RECALLED → METHOD STARTED → LLM/CODE/TOOL
→ STATE UPDATED → EVENTS/TRACE → OUTPUT VALIDATED → COMPLETED. Erreur : ERROR → EVENT →
CONTEXT UPDATE → RETRY / REPAIR / ESCALATE.

**Production Run** : CREATED → PLANNED → RUNNING → ARTIFACTS CREATED → QA → PASS → COMPLETED
/ FAIL → REVISION → RUNNING / BLOCKED → HUMAN.

## Transitions principales

- **Agent → Agent** : caller, callee, input/output types, contexte, mémoire pertinente,
  objets partagés vivants, trace parent, erreurs.
- **Agent → Skill** : discover → load documentation → reference/example → apply → result.
  Le skill enrichit le contexte ; ce n'est pas un agent.
- **Agent → Tool/Plugin** : typed call → policy/permissions → tool → plugin → système
  externe → typed result → event/trace.
- **Agent → CodeAct** : raisonnement → Python généré → validation NOOA → politique
  DeepBl4nder → sandbox → exécution → stdout/stderr/result → event → état. Une erreur
  devient une information exploitable par la boucle de réparation.
- **Artifact → QA** : checks techniques, visuels, sémantiques, continuité → `QAReport`.
- **QA → Revision** : FAIL → classification → étape affectée → `RevisionSpec` → agent
  responsable → nouvelle exécution. (Ex. problème caméra → CameraAgent → Layout → Pre-render,
  et non toute la production.)
- **Human → Production** : APPROVE → continue ; REJECT → RevisionSpec ; MODIFY → nouveau
  input. L'humain intervient là où son jugement est important.

## Collaboration

- **Séquentielle** : `plan = await director.plan(brief); scene = await blender.build(plan); report = await qa.check(scene)`.
- **Parallèle** : `asyncio.gather(cinematography.plan(shot), lighting.plan(shot), animation.plan(shot))`.
- **Hiérarchique** : DirectorAgent supervise Story/Cinematography/Blender/Audio/QA.
- **Révision** : QAAgent → RevisionSpec → agent responsable → nouvel artifact.

La collaboration utilise les mécanismes Python/NOOA (`asyncio`, appels imbriqués, stratégies)
avant tout workflow engine propriétaire.

## Human-in-the-loop (configurable)

Brief → Story → Storyboard → **[APPROVAL]** → Previs → **[APPROVAL]** → Production → Preview
→ **[APPROVAL]** → Final.

