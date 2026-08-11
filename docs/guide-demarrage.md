# Guide de démarrage et d'arrêt (DeepBlender SaaS)

L'application SaaS comporte **deux processus** à lancer :

| Processus | Technologie | Port par défaut | Rôle |
|---|---|---|---|
| **API** | FastAPI + uvicorn | `8000` | Auth, RBAC, orgs/workspaces/projets/productions, runs pipeline, SSE, révisions, artefacts, worker, usage |
| **Frontend** | Next.js 14 | `3000` | Interface web (dashboard, pipeline, temps réel, coûts) |

Le frontend appelle l'API en absolu (`NEXT_PUBLIC_API_URL`), le backend autorise
le CORS depuis `http://localhost:3000`.

---

## 1. Prérequis

- **Python 3.12+** avec le paquet installé : `pip install -e .`
- **Node.js 18+** avec les dépendances du frontend :
  ```bash
  cd frontend
  npm install
  ```
- (optionnel, pour des runs réels) des clés LLM dans `.env` : voir
  [`.env.example`](../.env.example). Sans clé, le pipeline échoue au step
  `director` — c'est le comportement attendu en local.

---

## 2. Démarrer l'API

Depuis la racine du projet :

```bash
python -m deepblender.api.app --host 127.0.0.1 --port 8000
```

Options :

| Option | Valeur par défaut | Description |
|---|---|---|
| `--host` | `0.0.0.0` (env `DEEPBENDER_HOST`) | Adresse d'écoute |
| `--port` | `8000` (env `DEEPBENDER_PORT`) | Port d'écoute |
| `--db` | `deepblender.db` (env `DEEPBLENDER_DB`) | Base SQLAlchemy : **chemin de fichier** (`deepblender.db`) ou **URL** (`sqlite:///deepblender.db`, `postgresql://…`) |

Variables d'environnement utiles (à définir dans `.env` ou le shell) :

| Variable | Rôle |
|---|---|
| `DEEPBLENDER_DB` | Base de données (équivalent de `--db`) |
| `DEEPBLENDER_DATA_DIR` | Dossier des workdirs de runs (défaut `data`) |
| `DEEPBLENDER_SECRET_KEY` | Clé de signature des jetons — **définissez-la** : sinon clé aléatoire à chaque boot et les sessions expirent au redémarrage |
| `DEEPBLENDER_BUDGET` | Budget max par production (USD, défaut `1.0`) |
| `DEEPBLENDER_QUOTA_PRODUCTIONS` | Quota de productions (laissé vide = illimité) |
| `DEEPBLENDER_QUOTA_COST` | Quota de coût cumulé en USD (laissé vide = illimité) |
| `DEEPBLENDER_CORS_ORIGINS` | Origines CORS séparées par des virgules (défaut `http://localhost:3000`) |

### LLM multi-fournisseurs (robuste au rate limiting)

Par défaut, le routeur utilise **tous** les fournisseurs dont la clé dédiée est
définie dans `.env` (`GEMINI_API_KEY`, `GROQ_API_KEY`, `NVIDIA_API_KEY`,
`OPENROUTER_API_KEY`, `CLOUDFLARE_API_KEY`). Les appels sont répartis en
`adaptive` (pondérés par la santé de chaque fournisseur) ou `random` et basculent
automatiquement vers un autre fournisseur en cas
d'erreur (429 / quota / panne), avec mise en cooldown du fournisseur fautif.

| Variable | Défaut | Rôle |
|---|---|---|
| `LLM_PROVIDERS` | *(tous les fournisseurs avec clé)* | Pool **strict** et ordonné : `gemini,groq,nvidia` |
| `LLM_PROVIDER` | `gemini` | Fournisseur préféré, mis en tête du pool |
| `LLM_ROTATION` | `adaptive` | `adaptive` (pondéré par la santé historique) \| `random` (tirage uniforme) |
| `LLM_COOLDOWN_SECONDS` | `30` | Cooldown de base après échec (×5 rate limit, ×10 erreurs auth/modèle) |
| `LLM_MODEL` / `<FOURNISSEUR>_MODEL` | *(défaut du fournisseur)* | Modèle actif par fournisseur |

La santé du routeur est visible sur le tableau de bord (carte « Worker intégré »
→ « Fournisseurs LLM ») et via `GET /api/worker` (champs `rotation` et `routing`).

Exemple avec base et données dédiées :

```bash
$env:DEEPBLENDER_DB="sqlite:///C:/data/deepblender.db"
$env:DEEPBLENDER_DATA_DIR="C:/data/runs"
$env:DEEPBLENDER_SECRET_KEY="une-cle-longue-et-secrete-32-octets-min"
python -m deepblender.api.app --host 127.0.0.1 --port 8000
```

**Vérifier que l'API tourne :**

- Documentation interactive : <http://localhost:8000/docs>
- La route `GET /api/me` répond `401 Unauthorized` (normal sans jeton) :
  ```powershell
  Invoke-WebRequest -Uri http://localhost:8000/api/me | Out-Null   # erreur 401 attendue
  ```

---

## 3. Arrêter l'API

- **Dans le terminal qui l'a lancée** : `Ctrl+C`.
- **Sinon** (processus lancé en arrière-plan), libérer le port 8000 :
  ```powershell
  Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force
  }
  ```

---

## 4. Démarrer le frontend

Depuis `frontend/` :

```bash
npm run dev        # développement (rechargement à chaud) — http://localhost:3000
```

En production (après un build) :

```bash
npm run build
npm start
```

Connexion à l'API : par défaut `http://localhost:8000`. Pour pointer ailleurs :

```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
npm run dev
```

**Vérifier :** ouvrir <http://localhost:3000> → redirigé vers `/login` ; s'enregistrer puis créer une production.

---

## 5. Arrêter le frontend

- **Dans le terminal qui l'a lancée** : `Ctrl+C`.
- **Sinon**, libérer le port 3000 :
  ```powershell
  Get-NetTCPConnection -LocalPort 3000 -State Listen | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force
  }
  ```

---

## 6. Dépannage

| Symptôme | Cause / solution |
|---|---|
| `npm run build` échoue avec `EBUSY` / `EINVAL` sur `.next` | Le dossier `.next` a été pollué (OneDrive). Purger puis relancer : `Remove-Item .next -Recurse -Force` dans `frontend/` |
| L'API répond « impossible de joindre le serveur » dans l'UI | L'API n'est pas lancée, ou `NEXT_PUBLIC_API_URL` pointe ailleurs que le port réel |
| `Could not parse SQLAlchemy URL` | (normalement corrigé) `--db` accepte désormais un simple chemin de fichier ; en cas de doute utiliser `sqlite:///…` |
| Connexion impossible après redémarrage de l'API | `DEEPBLENDER_SECRET_KEY` non définie → clé aléatoire à chaque boot. La définir pour garder les sessions |
| Un run échoue immédiatement au step `director` | Aucune clé LLM configurée dans `.env` — comportement attendu hors production |
| Le run échoue avec `model … is no longer available` (LiteLLM) | Le modèle a été retiré chez le fournisseur. Définir un modèle actuel : `GEMINI_LLM_MODEL=gemini/gemini-3.6-flash`, ou utiliser plusieurs fournisseurs dans `.env` (le routeur bascule automatiquement). Relancer l'API |
| Le run échoue avec `Model has been deprecated: …` (ex. Cloudflare `@cf/meta/llama-3.1-8b-instruct`) | Le modèle a été déprécié par le fournisseur. Mettre à jour `<FOURNISSEUR>_MODEL` dans `.env` vers un modèle du catalogue actuel (ex. `CLOUDFLARE_MODEL=cloudflare/@cf/google/gemma-4-26b-a4b-it`), puis relancer l'API |
| La preview affiche « Aucun rendu disponible » | Sans Blender + clés LLM, aucun frame n'est rendu — l'endpoint `GET /api/productions/{id}/preview` renvoie 404 tant qu'il n'y a pas d'image/vidéo |

---

## 7. Commandes rapides (PowerShell)

```powershell
# API (dev)
python -m deepblender.api.app --host 127.0.0.1 --port 8000

# Frontend (dev)
Set-Location frontend; npm run dev; Set-Location ..

# Vérification API
Invoke-WebRequest -Uri http://localhost:8000/docs

# Arrêt API + frontend
Get-NetTCPConnection -LocalPort 8000,3000 -State Listen | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
```
