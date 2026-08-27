# DeepBl4nder — Référence Complète du Frontend

> **Version** : 0.2.0 — **Stack** : Next.js 14 · React 18 · TypeScript 5 · Tailwind CSS 3 · SWR 2 · Vitest 2

---

## Table des matières

1. [Architecture globale](#1-architecture-globale)
2. [Configuration du projet](#2-configuration-du-projet)
3. [Feuilles de style globales](#3-feuilles-de-style-globales)
4. [Mise en page racine (Root Layout)](#4-mise-en-page-racine-root-layout)
5. [Authentification — pages login / register](#5-authentification--pages-login--register)
6. [Mise en page applicative `(app)`](#6-mise-en-page-applicative-app)
7. [Tableau de bord — Dashboard](#7-tableau-de-bord--dashboard)
8. [Page Pipeline](#8-page-pipeline)
9. [Page Temps réel (Realtime)](#9-page-temps-réel-realtime)
10. [Page Coûts (Costs)](#10-page-coûts-costs)
11. [Page Bibliothèque (Library)](#11-page-bibliothèque-library)
12. [Page Membres (Members)](#12-page-membres-members)
13. [Page Paramètres (Settings)](#13-page-paramètres-settings)
14. [Composants UI — `ui.tsx`](#14-composants-ui--uitsx)
15. [Composant Sidebar](#15-composant-sidebar)
16. [Composant RequireAuth](#16-composant-requireauth)
17. [Composant PipelineForm](#17-composant-pipelineform)
18. [Composant ProductionStream](#18-composant-productionstream)
19. [Composants ArtifactViewers](#19-composants-artifactviewers)
20. [Composant PatchEditor](#20-composant-patcheditor)
21. [Composant ScenePreview](#21-composant-scenepreview)
22. [Hook useProductionStream](#22-hook-useproductionstream)
23. [Hook useProductionTree](#23-hook-useproductiontree)
24. [Librairie API — `lib/api.ts`](#24-librairie-api--apits)
25. [Librairie Auth — `lib/auth.ts`](#25-librairie-auth--authts)
26. [Contexte Auth — `lib/auth-context.tsx`](#26-contexte-auth--auth-contexttsx)
27. [Configuration — `lib/config.ts`](#27-configuration--configts)
28. [Formatage — `lib/format.ts`](#28-formatage--formatts)
29. [Notifications — `lib/notifications.tsx`](#29-notifications--notifications tsx)
30. [Productions — `lib/productions.ts`](#30-productions--productionsts)
31. [SSE — `lib/sse.ts`](#31-sse--ssets)
32. [Carte d'依赖ances et flux de données](#32-carte-des-dépendances-et-flux-de-données)

---

## 1. Architecture globale

```
frontend/
├── package.json
├── next.config.js
├── tailwind.config.js
├── tsconfig.json
├── vitest.config.ts
└── src/
    ├── app/
    │   ├── globals.css
    │   ├── layout.tsx              # Root layout (AuthProvider + NotificationsProvider)
    │   ├── login/page.tsx          # Page de connexion
    │   ├── register/page.tsx       # Page d'inscription
    │   └── (app)/                  # Route group protégée par RequireAuth
    │       ├── layout.tsx          # Sidebar + RequireAuth
    │       ├── page.tsx            # Dashboard
    │       ├── pipeline/page.tsx   # Formulaire de lancement
    │       ├── realtime/page.tsx   # Vue temps réel (3D + SSE)
    │       ├── costs/page.tsx      # Suivi des coûts
    │       ├── library/page.tsx    # Bibliothèque d'assets
    │       ├── members/page.tsx    # Gestion des membres
    │       └── settings/page.tsx   # Paramètres
    ├── components/
    │   ├── ui.tsx                  # Composants UI de base
    │   ├── Sidebar.tsx             # Navigation latérale
    │   ├── RequireAuth.tsx         # Garde d'authentification
    │   ├── PipelineForm.tsx        # Formulaire de production
    │   ├── ProductionStream.tsx    # Flux SSE + timeline + artefacts
    │   ├── ArtifactViewers.tsx     # Visualiseurs JSON/code/média
    │   ├── PatchEditor.tsx         # Éditeur de paramètres de scène
    │   └── ScenePreview.tsx        # Prévisualisation 3D (Three.js)
    ├── hooks/
    │   ├── useProductionStream.ts  # Hook SSE temps réel
    │   └── useProductionTree.ts    # Hook SWR arbre de productions
    └── lib/
        ├── api.ts                  # Client API REST
        ├── auth.ts                 # Token localStorage
        ├── auth-context.tsx        # React context auth
        ├── config.ts               # URL de l'API
        ├── format.ts               # Fonctions de formatage
        ├── notifications.tsx       # Système de toasts
        ├── productions.ts          # Arbre + helpers productions
        └── sse.ts                  # Client SSE bas-niveau
```

**Principes architecturaux :**

- **Routage App Router** : les dossiers sous `src/app/` definissent les routes. Le route group `(app)` protège toutes les pages derrière `RequireAuth`.
- **Composants serveur vs client** : seuls les fichiers marqués `'use client'` s'exécutent côté client. Le layout racine est un Server Component.
- **State management** : pas de Redux/Zustand — le state est porté par des React Contexts (`AuthProvider`, `NotificationsProvider`) et des hooks SWR.
- **Communication API** : toutes les requêtes passent par `lib/api.ts` qui ajoute automatiquement le token Bearer. Les flux temps réel utilisent SSE via `lib/sse.ts`.

---

## 2. Configuration du projet

### 2.1 `package.json`

| Champ | Valeur |
|-------|--------|
| **Nom** | `DeepBl4nder-frontend` |
| **Version** | `0.2.0` |
| **Privé** | `true` |

**Scripts :**

| Script | Commande | Description |
|--------|----------|-------------|
| `dev` | `next dev -p 3000` | Serveur de développement sur le port 3000 |
| `build` | `next build` | Build de production |
| `start` | `next start` | Démarrage du serveur de production |
| `lint` | `next lint` | Vérification du lint (ESLint intégré Next.js) |
| `test` | `vitest run` | Exécution unique des tests |
| `test:watch` | `vitest` | Mode watch des tests |

**Dépendances principales :**

| Package | Version | Rôle |
|---------|---------|------|
| `next` | 14.2.0 | Framework React SSR/SSG |
| `react` | ^18.2.0 | Bibliothèque UI |
| `react-dom` | ^18.2.0 | Rendu DOM |
| `swr` | ^2.2.0 | Fetching & caching de données (stale-while-revalidate) |

**Dépendances de développement :**

| Package | Rôle |
|---------|------|
| `typescript` ^5.3 | Typage statique |
| `tailwindcss` ^3.4 | CSS utility-first |
| `@tailwindcss/typography` | Plugin prose pour le texte |
| `autoprefixer` / `postcss` | Post-traitement CSS |
| `vitest` ^2.1 | Framework de tests |
| `@testing-library/react` ^16.1 | Tests de composants |
| `@testing-library/jest-dom` ^6.6 | Matchers DOM |
| `@testing-library/user-event` ^14.5 | Simulation d'événements utilisateur |
| `jsdom` ^25.0 | Environnement DOM pour les tests |

### 2.2 `next.config.js`

**Paramètres :**

- `poweredBy: false` — supprime l'en-tête `X-Powered-By: Next.js` (sécurité).
- **En-têtes de sécurité** appliqués à toutes les routes (`/(.*)`) :
  - `X-Frame-Options: DENY` — empêche le clickjacking
  - `X-Content-Type-Options: nosniff` — empêche le sniffing MIME
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: camera=(), microphone=(), geolocation=()`
  - `X-XSS-Protection: 1; mode=block`
- **Rewrites** : toutes les requêtes `/api/:path*` sont proxyées vers `${NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/:path*`. Cela évite les problèmes de CORS en développement.

### 2.3 `tailwind.config.js`

**Palette de couleurs personnalisée :**

| Nom | Valeur | Usage |
|-----|--------|-------|
| `black` | `#0A0A0A` | Fond principal |
| `off-black` | `#111111` | Fond sidebar/cartes |
| `white` | `#FFFFFF` | Texte display |
| `off-white` | `#F5F5F0` | Texte corps |
| `acid` | `#AAFF00` | Accent principal (vert acide) |
| `acid-dim` | `#88CC00` | Accent foncé (hover) |
| `muted` | `#888880` | Texte secondaire |
| `border` | `#222222` | Bordures |

**Polices** (via CSS variables, chargées dans le layout) :

| Variable | Police | Usage |
|----------|--------|-------|
| `--font-display` | Space Grotesk | Titres, badges |
| `--font-body` | Inter | Texte corps |
| `--font-mono` | JetBrains Mono | Code, statistiques |

**Animations :**

| Nom | Description |
|-----|-------------|
| `fade-up` | Apparition vers le haut (0.7s) |
| `fade-in` | Apparition en fondu (0.5s) |

**Tailles de texte étendues :** `8xl` (6rem), `9xl` (8rem), `10xl` (10rem) — pour les titres hero.

**Plugins :** `@tailwindcss/typography` pour les classes `prose`.

### 2.4 `tsconfig.json`

| Option | Valeur | Rôle |
|--------|--------|------|
| `target` | ES2017 | Output JS |
| `lib` | dom, dom.iterable, esnext | APIs disponibles |
| `strict` | true | Typage strict |
| `module` | esnext | Module system |
| `moduleResolution` | bundler | Résolution Next.js |
| `jsx` | preserve | JSX géré par SWC |
| `incremental` | true | Compilation incrémentale |
| `paths.@/*` | `./src/*` | Alias d'import |

### 2.5 `vitest.config.ts`

| Option | Valeur |
|--------|--------|
| `environment` | `jsdom` |
| `globals` | `true` (describe, it, expect sans import) |
| `setupFiles` | `./src/__tests__/setup.ts` |
| `include` | `src/**/*.test.{ts,tsx}` |
| `resolve.alias.@` | `src/` |

---

## 3. Feuilles de style globales

**Fichier :** `src/app/globals.css`

### Variables CSS

```css
--bg: #0a0a0a;
--bg-card: #0f0f0f;
--bg-sidebar: #111111;
--bg-accent: #aaff00;
--bg-accent-dim: #88cc00;
--text-body: #f5f5f0;
--text-muted: #888880;
--text-display: #ffffff;
--border: #222222;
```

### Polices chargées

```css
--font-display: 'Space Grotesk', 'Segoe UI', system-ui, sans-serif;
--font-body: 'Inter', 'Segoe UI', system-ui, sans-serif;
--font-mono: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
```

### Styles de base

- `color-scheme: dark` — thème sombre forcé
- `body` : fond `--bg`, couleur `--text-body`, smoothing antialiased
- `::selection` : fond acid, texte noir
- Scrollbar customisée (6px, thumb `#333`)
- `focus-visible` : outline acid (2px, offset 2px)
- Transitions fluides sur `background-color`, `border-color`, `color`, `box-shadow` (durée 0ms par défaut)

### Keyframes

| Animation | Description |
|-----------|-------------|
| `slideInRight` | Toast entrant depuis la droite |
| `slideOutRight` | Toast sortant vers la droite |
| `.toast-enter` | Classe d'entrée toast (0.3s) |
| `.toast-exit` | Classe de sortie toast (0.3s) |

### Utilitaires personnalisés

| Classe | Description |
|--------|-------------|
| `.card-bg` | Fond `--bg-card` |
| `.card-glass` | Effet glassmorphism (blur 12px) |
| `.text-gradient-acid` | Texte dégradé acid (clip) |
| `.glow-acid` | Ombre lumineuse acid au survol |

---

## 4. Mise en page racine (Root Layout)

**Fichier :** `src/app/layout.tsx`

### Composant

```typescript
export default function RootLayout({ children }: { children: React.ReactNode }): JSX.Element
```

**Rôle :** Point d'entrée HTML. Charge les polices Google, fournit les contextes globaux.

### Polices chargées

| Fonction | Police | Variable CSS |
|----------|--------|--------------|
| `Space_Grotesk()` | Space Grotesk | `--font-display` |
| `Inter()` | Inter | `--font-body` |
| `JetBrains_Mono()` | JetBrains Mono | `--font-mono` |

Toutes avec `subsets: ['latin']`, `display: 'swap'`.

### Métadonnées

```typescript
export const metadata: Metadata = {
  title: 'DeepBl4nder — AI Audiovisual Production',
  description: 'Plateforme SaaS de production audiovisuelle assistée par agents IA...',
  icons: { icon: '/favicon.svg' },
};
```

### Arbre rendu

```
<html lang="fr" className="variables-polices">
  <body className="bg-black text-off-white font-body antialiased">
    <AuthProvider>
      <NotificationsProvider>
        {children}
      </NotificationsProvider>
    </AuthProvider>
  </body>
</html>
```

### Connexion avec le reste

- Fournit `AuthProvider` → utilisé par `RequireAuth`, `Sidebar`, `LoginPage`, `RegisterPage`, `ProductionStream`
- Fournit `NotificationsProvider` → utilisé partout via `useNotifications()`
- Toutes les pages enfants héritent de ces deux contextes

---

## 5. Authentification — pages login / register

### 5.1 Page Login

**Fichier :** `src/app/login/page.tsx`

**Directive :** `'use client'`

#### Composant

```typescript
export default function LoginPage(): JSX.Element
```

#### State

| Variable | Type | Initial | Rôle |
|----------|------|---------|------|
| `email` | `string` | `''` | Champ email |
| `password` | `string` | `''` | Champ mot de passe |
| `busy` | `boolean` | `false` | Indicateur de chargement |
| `error` | `string \| null` | `null` | Message d'erreur |

#### Hooks utilisés

- `useRouter()` — redirection après connexion
- `useAuth()` — déstructure `login`
- `useNotifications()` — déstructure `notify`

#### Fonction handleSubmit

```typescript
const handleSubmit = async (event: FormEvent) => Promise<void>
```

1. Appelle `login(email.trim(), password)`
2. Notifie succès : `'Connexion réussie.'`
3. Redirige vers `/` via `router.replace('/')`
4. En cas d'erreur : affiche le message dans `error`

#### Rendu

Formulaire centré (max-w-md) avec :
- Champ `email` (type email, autocomplete)
- Champ `password` (type password, autocomplete)
- `<FormError>` pour les erreurs
- `<Button>` submit désactivé si `busy` ou champs vides
- Lien vers `/register`

### 5.2 Page Register

**Fichier :** `src/app/register/page.tsx`

**Directive :** `'use client'`

#### Composant

```typescript
export default function RegisterPage(): JSX.Element
```

#### State

| Variable | Type | Initial | Rôle |
|----------|------|---------|------|
| `fullName` | `string` | `''` | Nom complet |
| `email` | `string` | `''` | Email |
| `password` | `string` | `''` | Mot de passe (min 8 car.) |
| `busy` | `boolean` | `false` | Chargement |
| `error` | `string \| null` | `null` | Erreur |

#### Fonction handleSubmit

```typescript
const handleSubmit = async (event: FormEvent) => Promise<void>
```

1. Appelle `register(email.trim(), password, fullName.trim())`
2. Notifie succès : `'Compte créé. Bienvenue sur DeepBl4nder.'`
3. Redirige vers `/`
4. Bouton désactivé si `busy`, email vide ou `password.length < 8`

#### Rendu

Formulaire avec :
- Champ `fullName` (autocomplete name)
- Champ `email` (type email, requis)
- Champ `password` (type password, minLength=8, hint : "8 caractères minimum")
- `<Button>` submit
- Lien vers `/login`

---

## 6. Mise en page applicative `(app)`

**Fichier :** `src/app/(app)/layout.tsx`

**Directive :** `'use client'`

#### Composant

```typescript
export default function AppLayout({ children }: { children: ReactNode }): JSX.Element
```

#### Structure rendue

```tsx
<RequireAuth>
  <div className="min-h-screen">
    <Sidebar />
    <main className="min-h-screen lg:ml-[200px]">{children}</main>
  </div>
</RequireAuth>
```

- `RequireAuth` redirige vers `/login` si pas de token
- `Sidebar` affichée en fixe à gauche (200px)
- `main` décalé de 200px sur desktop (`lg:ml-[200px]`)

---

## 7. Tableau de bord — Dashboard

**Fichier :** `src/app/(app)/page.tsx`

**Directive :** `'use client'`

### Composant principal

```typescript
export default function DashboardPage(): JSX.Element
```

#### State (via hooks)

| Source | Variables | Rôle |
|--------|-----------|------|
| `useProductionTree()` | `productions`, `error`, `isLoading`, `mutate` | Arbre des productions (SWR, polling 4s) |
| `useWorker()` | `worker`, `workerError` | Statut du worker (polling 5s) |
| `useNotifications()` | `notify` | Toasts |

#### Valeurs dérivées

- `active` : productions avec status `running` ou `queued`
- `totalCost` : somme des `cost` de toutes les productions

#### handleDeleteProject

```typescript
const handleDeleteProject = useCallback(async (item: ProductionTreeItem) => Promise<void>, [mutate, notify])
```

1. `confirm()` avec nom du projet et avertissement
2. Appelle `api.deleteProject(item.project.id)`
3. Notifie succès/erreur
4. Appelle `mutate()` pour recharger les données

#### Constantes

```typescript
const STATUS_TONE: Record<string, 'acid' | 'green' | 'amber' | 'red' | 'blue' | 'muted'>
```

Mapping status → couleur de badge :
| Status | Tone |
|--------|------|
| `draft` | `muted` |
| `queued` | `blue` |
| `running` | `acid` |
| `waiting_approval` | `amber` |
| `revising` | `blue` |
| `completed` | `green` |
| `failed` | `red` |
| `cancelled` | `muted` |
| `blocked` | `amber` |

#### Fonction helper

```typescript
function rotationLabel(rotation: string): string
```

Traduit les modes de rotation LLM : `vote` → "Vote (majorité)", `adaptive` → "Adaptatif (pondéré)", `random` → "Aléatoire".

### Composant ProductionCard

```typescript
function ProductionCard({ item, onDeleteProject }: {
  item: ProductionTreeItem;
  onDeleteProject: (item: ProductionTreeItem) => void;
}): JSX.Element
```

**State local :** `deleteBusy`, `stopBusy`

**Actions :**
- Clic sur la carte → navigue vers `/realtime`
- Bouton "Arrêter" → `api.cancelProduction(production.id)`
- Bouton "Supprimer" → déclenche `onDeleteProject(item)` (supprime le projet entier)

**Affichage :** Nom, badge status, version, path (org/workspace/projet), temps mis à jour, durée, étape courante, barre de progression, coût, pourcentage.

### Composant WorkerCard

```typescript
function WorkerCard({ worker, error }: { worker: WorkerOut | null; error: string | null }): JSX.Element
```

**Affiche :**
- Statut du worker (En ligne / En attente / Erreur) avec point clignotant
- File d'attente, runs en cours, runs traités, échecs
- Liste des runs en cours (ID + timestamp)
- Liste des fournisseurs LLM avec cooldown, succès, échecs, rotation, dernière erreur

### Hook useWorker

```typescript
function useWorker(): { worker: WorkerOut | null; workerError: string | null }
```

- Charge `api.getWorker()` au montage
- Polling toutes les 5 secondes
- Cleanup via flag `active` + `clearInterval`

---

## 8. Page Pipeline

**Fichier :** `src/app/(app)/pipeline/page.tsx`

```typescript
import { PipelineForm } from '@/components/PipelineForm';
export default function PipelinePage() { return <PipelineForm />; }
```

Page wrapper simple qui délegue tout à `PipelineForm`.

---

## 9. Page Temps réel (Realtime)

**Fichier :** `src/app/(app)/realtime/page.tsx`

#### Composant

```typescript
export default function RealtimePage(): JSX.Element
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `params` | `PatchParam[]` | Paramètres 3D de la scène (initiaux : caméra, éclairage, personnage, environnement, rendu) |

#### Constante DEFAULT_PARAMS

12 paramètres répartis en 5 sections :

| ID | Label | Type | Section | Défaut |
|----|-------|------|---------|--------|
| `cam_fov` | Champ de vision | range (10–120) | camera | 50 |
| `cam_distance` | Distance | range (1–20) | camera | 5 |
| `cam_height` | Hauteur | range (0–10) | camera | 2 |
| `light_intensity` | Intensité | range (0–3, step 0.1) | lighting | 1.0 |
| `light_color` | Couleur | color | lighting | #ffffff |
| `light_angle` | Angle | range (0–180) | lighting | 45 |
| `char_scale` | Échelle | range (0.1–3, step 0.1) | character | 1.0 |
| `char_rotation` | Rotation Y | range (0–360) | character | 0 |
| `env_fog` | Brouillard | range (0–1, step 0.05) | environment | 0 |
| `env_ground_color` | Sol | color | environment | #444444 |
| `render_samples` | Samples | number (1–4096) | render | 128 |
| `render_resolution` | Resolution | select | render | 1920x1080 |

#### handleParamChange

```typescript
const handleParamChange = useCallback((id: string, value: string | number) => void, [])
```

Met à jour un paramètre par ID dans le tableau `params`.

#### getParam

```typescript
const getParam = (id: string) => params.find(p => p.id === id)?.value
```

#### Rendu

Layout split en deux colonnes :
1. **Gauche** : `ScenePreview` (prévisualisation 3D, dynamic import sans SSR) + `ProductionStream` (flux SSE, 264px haut)
2. **Droite** : `PatchEditor` (éditeur de paramètres, 320px large)

Wrap dans `<Suspense>` avec fallback "Chargement…".

---

## 10. Page Coûts (Costs)

**Fichier :** `src/app/(app)/costs/page.tsx`

**Directive :** `'use client'`

#### Composant principal

```typescript
export default function CostsPage(): JSX.Element
```

#### State (via hooks)

| Source | Variables |
|--------|-----------|
| `useProductionTree(5000)` | `productions`, `error`, `isLoading` |
| `useUsage()` | `usage` (UsageOut \| null) |

#### Valeurs dérivées

- `total` : somme des coûts
- `maxCost` : coût maximum (minimum 0.0001 pour éviter division par zéro)

#### Affichage

1. **En-tête** : titre + sous-titre
2. **Erreur API** : si `error`
3. **UsagePanel** : consommation et quotas
4. **Statistiques** : nombre de productions, coût total, coût moyen
5. **Barres de coûts** : pour chaque production, une barre proportionnelle au coût

### Sous-composant useUsage

```typescript
function useUsage(): { usage: UsageOut | null }
```

- Charge `api.getUsage()` au montage
- Polling toutes les 5 secondes
- Ignore les erreurs silencieusement

### Sous-composant QuotaBar

```typescript
function QuotaBar({ label, value, quota, format }: {
  label: string;
  value: number;
  quota: number | null;
  format: (v: number) => string;
}): JSX.Element
```

- Si `quota === null` : barre à 100% (aucune limite)
- Sinon : barre proportionnelle, rouge si dépassement

### Sous-composant UsagePanel

```typescript
function UsagePanel({ usage }: { usage: UsageOut | null }): JSX.Element | null
```

Affiche :
- Stats : runs lancés, coût cumulé, productions
- Barres de quota : productions, coût total

---

## 11. Page Bibliothèque (Library)

**Fichier :** `src/app/(app)/library/page.tsx`

**Directive :** `'use client'`

#### Composant principal

```typescript
export default function LibraryPage(): JSX.Element
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `activeTab` | `'assets' \| 'templates' \| 'skills'` | Onglet actif |

#### Interface Asset

```typescript
interface Asset {
  name: string; type: string; path: string;
  size: number; source: string; created_at: string;
}
```

#### Constante ASSET_ICONS

```typescript
const ASSET_ICONS: Record<string, string> = {
  model: '🧊', texture: '🎨', hdri: '🌅', audio: '🎵',
  script: '📄', render: '🎬', unknown: '📦'
};
```

#### Rendu

Onglets avec indicateur acid :
1. **Assets 3D** — Grille de sources (PolyHaven HDRIs 1000+, Quaternius Models 200+, Scripts Blender)
2. **Templates** — Scènes prédéfinies (Cyberpunk Alley, Dark Forest, Studio Interview) avec tags
3. **Skills IA** — 10 skills catégorisés (Narration, Rendu, Assets, Animation, Audio, Post-prod)

**Note :** Données actuellement hardcodées (pas d'API backend pour la bibliothèque).

---

## 12. Page Membres (Members)

**Fichier :** `src/app/(app)/members/page.tsx`

**Directive :** `'use client'`

#### Composant principal

```typescript
export default function MembersPage(): JSX.Element
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `org` | `OrgDetailOut \| null` | Détail de l'organisation |
| `loading` | `boolean` | Chargement |
| `error` | `string \| null` | Erreur |
| `newEmail` | `string` | Email du nouveau membre |
| `newRole` | `string` | Rôle du nouveau membre (défaut: `viewer`) |
| `addBusy` | `boolean` | Chargement ajout |

#### Constantes

```typescript
const ROLE_LABELS: Record<string, string> = {
  owner: 'Propriétaire', admin: 'Administrateur',
  editor: 'Éditeur', viewer: 'Observateur'
};

const ROLE_TONES: Record<string, 'acid' | 'green' | 'blue' | 'muted'> = {
  owner: 'acid', admin: 'green', editor: 'blue', viewer: 'muted'
};
```

#### Fonctions

**loadOrg** — `useCallback(async () => Promise<void>, [])`

1. `api.listOrganizations()` → prend la première
2. `api.getOrganization(orgs[0].id)` → charge le détail avec membres

**handleAddMember** — `async (e: React.FormEvent) => Promise<void>`

1. `api.addMember(org.id, { email, role })`
2. Notifie succès, réinitialise le formulaire
3. Recharge l'organisation

#### Rendu

1. Carte de l'organisation (nom, nombre de membres, rôle de l'utilisateur)
2. Formulaire d'ajout (email + rôle sélecteur + bouton)
3. Liste des membres (nom, email, badge rôle, badge propriétaire)

---

## 13. Page Paramètres (Settings)

**Fichier :** `src/app/(app)/settings/page.tsx`

**Directive :** `'use client'`

#### Composant principal

```typescript
export default function SettingsPage(): JSX.Element
```

#### Interface Settings

```typescript
interface Settings {
  llmProvider: string;      // Défaut: 'gemini'
  llmModel: string;         // Défaut: 'gemini-2.0-flash'
  renderEngine: string;     // Défaut: 'blender'
  renderQuality: string;    // Défaut: 'medium'
  renderResolution: string; // Défaut: '1920x1080'
  defaultFps: number;       // Défaut: 24
  budgetLimit: number;      // Défaut: 1.0
  autoApprove: boolean;     // Défaut: false
  notifications: boolean;   // Défaut: true
  maxRevisions: number;     // Défaut: 1
  targetLanguages: string;  // Défaut: 'fr,en'
}
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `settings` | `Settings` | Paramètres courants |
| `saved` | `boolean` | Indicateur de sauvegarde (2s) |

#### Persistance

- **Chargement** : `localStorage.getItem('deepbl4nder_settings')` au montage (`useEffect`)
- **Sauvegarde** : `localStorage.setItem(...)` dans `handleSave()`
- **Réinitialisation** : `localStorage.removeItem(...)` dans `handleReset()`

#### Panneaux de configuration

1. **Modèle LLM** : Fournisseur (Gemini, Groq, NVIDIA, OpenRouter, Cloudflare, Local), Modèle (Gemini 2.0 Flash/Pro, Llama 3.3 70B, Qwen 3.6 27B, GPT-OSS 120B), Languages cibles
2. **Moteur de rendu** : Moteur (Blender, Unreal Engine 5, Godot 4, AI Video CogVideoX), Qualité (Brouillon/Moyen/Haute/Ultra), Résolution (720p–4K), FPS (12–60)
3. **Budget** : Budget max par production ($0.1–100), Révisions max QA (0–5)
4. **Workflow** : Approbation automatique, Notifications

---

## 14. Composants UI — `ui.tsx`

**Fichier :** `src/components/ui.tsx`

**Directive :** `'use client'`

Bibliothèque de composants UI réutilisables. Tous les styles utilisent Tailwind CSS.

### Button

```typescript
function Button({
  variant = 'primary',  // 'primary' | 'secondary' | 'ghost' | 'danger' | 'outline'
  className = '',
  ...props               // ButtonHTMLAttributes<HTMLButtonElement>
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }): JSX.Element
```

| Variant | Apparence |
|---------|-----------|
| `primary` | Fond acid, texte noir |
| `secondary` | Fond off-black, texte off-white |
| `outline` | Bordure, texte off-white → acid au hover |
| `ghost` | Texte muted → off-white au hover |
| `danger` | Fond rouge sombre, texte rouge clair |

Tous : `rounded-lg`, `px-4 py-2`, `text-sm`, focus ring acid, disabled opacity 50.

### Card / CardHeader / CardBody

```typescript
function Card({ className = '', children }: { className?: string; children: ReactNode }): JSX.Element
function CardHeader({ title, subtitle, actions }: {
  title: ReactNode; subtitle?: ReactNode; actions?: ReactNode;
}): JSX.Element
function CardBody({ className = '', children }: { className?: string; children: ReactNode }): JSX.Element
```

- `Card` : `card-bg border border-border rounded-xl`
- `CardHeader` : flex avec titre, sous-titre et actions, bordure inférieure
- `CardBody` : padding `p-5`

### Badge

```typescript
type BadgeTone = 'acid' | 'green' | 'amber' | 'red' | 'blue' | 'muted';

function Badge({ tone = 'muted', className = '', children }: {
  tone?: BadgeTone; className?: string; children: ReactNode;
}): JSX.Element
```

Badge inline avec fond coloré translucent (`bg-{color}/15 text-{color}`).

### Field / FormError

```typescript
function Field({ label, htmlFor, error, hint, children }: {
  label: ReactNode; htmlFor: string; error?: string | null;
  hint?: ReactNode; children: ReactNode;
}): JSX.Element

function FormError({ id, message }: { id?: string; message?: string | null }): JSX.Element | null
```

- `Field` : conteneur de champ avec label, hint (si pas d'erreur), et `FormError`
- `FormError` : paragraphe rouge avec `role="alert"`

### Input / TextArea / Select

```typescript
function Input({ invalid, className = '', ...props }: InputHTMLAttributes<HTMLInputElement> & { invalid?: boolean }): JSX.Element
function TextArea({ invalid, className = '', ...props }: TextareaHTMLAttributes<HTMLTextAreaElement> & { invalid?: boolean }): JSX.Element
function Select({ invalid, className = '', children, ...props }: SelectHTMLAttributes<HTMLSelectElement> & { invalid?: boolean; children: ReactNode }): JSX.Element
```

Tous : `INPUT_BASE` commun (`w-full rounded-lg border bg-off-black px-3 py-2 text-sm text-off-white`). Si `invalid` : bordure rouge, sinon bordure + focus acid. Supporte `aria-invalid`.

### Spinner

```typescript
function Spinner({ className = '' }: { className?: string }): JSX.Element
```

Cercle animé `animate-spin`, bordure muted + bordure top acid, `role="status"`.

### Skeleton

```typescript
function Skeleton({ className = '' }: { className?: string }): JSX.Element
```

Rectangle animé `animate-pulse` en `bg-off-black`.

### EmptyState

```typescript
function EmptyState({ title, description, actions }: {
  title: ReactNode; description?: ReactNode; actions?: ReactNode;
}): JSX.Element
```

Centre flex avec bordure pointillée, titre, description, actions.

### ProgressBar

```typescript
function ProgressBar({ value, className = '' }: { value: number; className?: string }): JSX.Element
```

Barre de progression. `value` entre 0 et 1 (converti en pourcentage). Rôle `progressbar` ARIA.

### Stat

```typescript
function Stat({ label, value, accent }: {
  label: ReactNode; value: ReactNode; accent?: boolean;
}): JSX.Element
```

Carte stat : label en `text-xs text-muted`, valeur en `font-display text-xl`. Si `accent`, valeur en acid.

### Tabs / TabList / TabTrigger / TabContent

```typescript
function Tabs({ defaultValue, children, className = '' }: {
  defaultValue: string; children: ReactNode; className?: string;
}): JSX.Element

function TabList({ children, className = '' }: { children: ReactNode; className?: string }): JSX.Element

function TabTrigger({ value, children, className = '' }: {
  value: string; children: ReactNode; className?: string;
}): JSX.Element

function TabContent({ value, children, className = '' }: {
  value: string; children: ReactNode; className?: string;
}): JSX.Element
```

Système d'onglets basé sur React Context (`TabsContext`).
- `Tabs` : provider, gère l'état de l'onglet actif
- `TabList` : conteneur flex
- `TabTrigger` : bouton avec aria-selected, bordure bottom acid si actif
- `TabContent` : rend les children uniquement si l'onglet est actif

---

## 15. Composant Sidebar

**Fichier :** `src/components/Sidebar.tsx`

**Directive :** `'use client'`

#### Composant

```typescript
export function Sidebar(): JSX.Element
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `mobileOpen` | `boolean` | Menu mobile ouvert/fermé |

#### Hooks

- `usePathname()` — route active pour le highlight
- `useRouter()` — redirection après déconnexion
- `useAuth()` — user + logout

#### Constante NAV

```typescript
const NAV = [
  { href: '/', label: 'Tableau de bord', icon: '◈' },
  { href: '/pipeline', label: 'Pipeline', icon: '▷' },
  { href: '/realtime', label: 'Temps réel', icon: '⇄' },
  { href: '/library', label: 'Bibliothèque', icon: '☰' },
  { href: '/costs', label: 'Coûts', icon: '¤' },
  { href: '/members', label: 'Membres', icon: '⊕' },
  { href: '/settings', label: 'Paramètres', icon: '⚙' },
];
```

#### Rendu

1. **Bouton hamburger** : visible uniquement mobile (`lg:hidden`), toggle `mobileOpen`
2. **Overlay** : fond noir semi-transparent sur mobile, clic ferme le menu
3. **Aside fixe** : `w-[200px]`, `fixed inset-y-0 left-0`
   - Logo + nom DeepBl4nder
   - Navigation : chaque lien avec icône + label, background acid si actif
   - Footer : email du bouton "Se déconnecter"

#### Connexion

- Utilise `useAuth()` pour l'email et la déconnexion
- Utilise `usePathname()` pour la navigation active
- Ferme le menu mobile après clic sur un lien

---

## 16. Composant RequireAuth

**Fichier :** `src/components/RequireAuth.tsx`

**Directive :** `'use client'`

#### Composant

```typescript
export function RequireAuth({ children }: { children: ReactNode }): JSX.Element
```

#### Comportement

1. Lit `token` et `ready` depuis `useAuth()`
2. Si `ready && !token` → redirige vers `/login` via `useEffect`
3. Si pas prêt ou pas de token → affiche un spinner centré ("Chargement…")
4. Sinon → rend `children`

#### Connexion

Utilisé par `(app)/layout.tsx` pour protéger toutes les pages de l'application.

---

## 17. Composant PipelineForm

**Fichier :** `src/components/PipelineForm.tsx`

**Directive :** `'use client'`

#### Composant

```typescript
export function PipelineForm(): JSX.Element
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `name` | `string` | Nom de la production |
| `brief` | `string` | Brief créatif |
| `busy` | `boolean` | Chargement |
| `error` | `string \| null` | Erreur |

#### Fonction handleSubmit

```typescript
const handleSubmit = async (event: FormEvent) => Promise<void>
```

1. `ensureProject()` — crée auto org/workspace/projet si nécessaire
2. `api.createProduction(project.id, { name, brief })`
3. `api.runProduction(production.id)`
4. Notifie succès
5. Redirige vers `/realtime?production={id}`

#### Validation

`canSubmit = brief.trim().length > 0 && !busy`

#### Rendu

Grille 5 colonnes (formulaire sur 3) :
- Champ nom (optionnel, max 120 car.)
- Champ brief (TextArea, 8 lignes, requis, avec hint)
- Bouton "Créer et lancer" avec spinner
- Message de chargement "Envoi du brief au pipeline…"

---

## 18. Composant ProductionStream

**Fichier :** `src/components/ProductionStream.tsx` (931 lignes)

**Directive :** `'use client'`

### Composant principal

```typescript
export function ProductionStream({ initialProductionId }: {
  initialProductionId?: string;
}): JSX.Element
```

C'est le composant le plus complexe du frontend. Il gère :
- La sélection de production
- Le flux SSE temps réel
- L'affichage des événements de pipeline
- La timeline et les patches
- Les artefacts (listing, visualisation, téléchargement, suppression)
- Les demandes de révision
- L'approbation
- Le preview

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `productionId` | `string \| null` | ID de la production sélectionnée |
| `runBusy` | `boolean` | Chargement relance run |
| `now` | `number` | Horloge pour le heartbeat |
| `revisionStep` | `string` | Étape cible de révision |
| `revisionComment` | `string` | Commentaire de révision |
| `revisionBusy` | `boolean` | Chargement révision |
| `revisionError` | `string \| null` | Erreur révision |
| `artifacts` | `ArtifactOut[]` | Liste des artefacts |
| `artifactsLoading` | `boolean` | Chargement artefacts |
| `previewUrl` | `{ url: string; isVideo: boolean } \| null` | URL blob du preview |
| `previewBusy` | `boolean` | Chargement preview |
| `viewingArtifact` | `ArtifactOut \| null` | Artefact en cours de visualisation |
| `deleteBusy` | `string \| null` | Chemin de l'artifact en suppression |
| `timeline` | `TimelineOut \| null` | Timeline de la production |
| `timelineLoading` | `boolean` | Chargement timeline |
| `patchTargets` | `Record<string, ...>` | État des patches par shot |
| `patchBusy` | `string \| null` | Shot en cours de patch |

#### Hooks utilisés

- `useSearchParams()` — lecture du paramètre `?production=`
- `useAuth()` — token pour le SSE
- `useNotifications()` — toasts
- `useProductionTree(5000)` — polling productions (5s)
- `useProductionStream(productionId, token)` — flux SSE

#### Fonctions principales

| Fonction | Description |
|----------|-------------|
| `refreshArtifacts()` | Recharge `api.listArtifacts(productionId)` |
| `refreshTimeline()` | Recharge `api.getTimeline(productionId)` |
| `handleApproval()` | `api.approveProduction(productionId)` |
| `handlePatch(shotId, target, newValue, rationale)` | `api.createPatch(productionId, ...)` |
| `handleRevision()` | `api.requestRevision(productionId, { target_step, comment })` |
| `handleDownload(artifact)` | `api.downloadArtifact(...)` →.createObjectURL → `<a>` click |
| `handleDeleteArtifact(artifact)` | `api.deleteArtifact(...)` + refresh |
| `handlePreview()` | `api.preview(productionId)` → blob URL |
| `handleRun()` | `api.runProduction(productionId)` |
| `handleCancel()` | `api.cancelProduction(productionId)` |

#### Constantes internes

**EVENT_META** : mapping type d'événement → { label, tone } :
`run_started`, `run_completed`, `run_blocked`, `run_failed`, `step_started`, `step_completed`, `step_resumed`, `step_failed`, `approval_requested`, `approval_granted`, `approval_rejected`, `revision_requested`, `cost_recorded`, `budget_alert`, `llm_call`

**STEP_ICONS** : `director` → 🎬, `blender` → 🧊, `qa` → 🔍, `audio` → 🎵, `compositing` → 🎨, `localization` → 🌍

**Extensions de fichiers** : `IMAGE_EXTS`, `VIDEO_EXTS`, `AUDIO_EXTS`, `TEXT_EXTS` — pour déterminer le type de visualiseur.

#### Helpers

```typescript
function artifactViewType(artifact: ArtifactOut): 'image' | 'video' | 'audio' | 'text' | null
function eventSummary(event: SSEEvent): string
function eventTime(event: SSEEvent): string
function statusBadge(status: SSEStatus, heartbeatText: string): ReactNode
```

### Sous-composant TimelineView

```typescript
function TimelineView({ timeline, patchTargets, onPatchTargetChange, onSubmitPatch, patchBusy }: TimelineViewProps): JSX.Element
```

Affiche la hiérarchie Séquence → Scène → Plan avec :
- Badge status par plan (planned/pending/running/completed/failed/blocked)
- Résumé caméra, action, durée
- Formulaire de patch inline (`PatchForm`)

### Sous-composant PatchForm

```typescript
function PatchForm({ shotId, shotIndex, patchTargets, onPatchTargetChange, onSubmitPatch, patchBusy }: PatchFormProps): JSX.Element
```

- Sélecteur de cible (camera_summary, action, camera_angle, camera_movement, duration, transition, visual_notes)
- Input "Nouvelle valeur"
- Input "Raison (optionnel)"
- Bouton "Patch"

### Sous-composant ArtifactViewer

```typescript
function ArtifactViewer({ artifact, productionId, onClose }: {
  artifact: ArtifactOut; productionId: string; onClose: () => void;
}): JSX.Element
```

Modal plein écran qui :
1. Charge le blob via `api.getArtifactBlob()`
2. Détermine le type (JSON/code/image/video/audio)
3. Affiche le visualiseur approprié (`JsonViewer`, `CodeViewer`, `VideoPlayer`, `AudioPlayer`, `ImagePlayer`)
4. Pour le JSON : propose "Copier" et affiche `JsonViewer`
5. Pour le code : détection du langage par extension

### Rendu principal

1. **En-tête** : titre + sélecteur de production + boutons Reconnecter/Arrêter/Relancer
2. **Carte production** : nom, status, version, coût, badge SSE, bouton approbation si `waiting_approval`
3. **Carte événements** : liste scrollable des événements SSE avec badges colorés et résumés
4. **Carte révision** : formulaire avec étape cible (sélecteur) et commentaire
5. **Carte Timeline & Artefacts** : onglets Timeline / Artefacts
   - Timeline : `TimelineView`
   - Artefacts : preview, liste avec visualiser/télécharger/supprimer
6. **Modal** : `ArtifactViewer` si `viewingArtifact`

---

## 19. Composants ArtifactViewers

**Fichier :** `src/components/ArtifactViewers.tsx`

**Directive :** `'use client'`

Quatre visualiseurs sans dépendance externe.

### JsonViewer

```typescript
function JsonViewer({ data, filename }: { data: JsonValue; filename: string }): JSX.Element
```

**State :** `expanded: Set<string>` (chemins dépliés), `copied: boolean`

**Features :**
- Arbre repliable avec nœuds conteneurs
- Coloration : clés en sky-300, strings emerald-300, nombres amber-300, booléens violet-300
- Compteurs de nœuds et d'éléments
- Boutons "Tout déplier" / "Tout replier" / "Copier"
- Expansion initiale : nœuds depth ≤ 2
- Border-left récursive pour l'indentation visuelle

**Helpers internes :**

```typescript
function collectContainerPaths(value: JsonValue, prefix?, depth?, acc?): Array<{ path: string; depth: number }>
function PrimitiveValue({ value }: { value: Exclude<JsonValue, object> }): JSX.Element
function CountBadge({ count, unit }: { count: number; unit: string }): JSX.Element
function TreeNode({ name, value, path, depth, expanded, toggle }: TreeNodeProps): JSX.Element
```

### CodeViewer

```typescript
function CodeViewer({ content }: { content: string }): JSX.Element
```

Affiche du code avec numéros de ligne dans un tableau `<table>`. Chaque ligne dans un `<tr>` hoverable. Gestion des lignes vides (espace insécable).

### VideoPlayer

```typescript
function VideoPlayer({ url, filename }: { url: string; filename: string }): JSX.Element
```

Lecteur vidéo HTML5 `<video>` avec contrôles, `playsInline`, `preload="metadata"`, bordure + ombre acid, caption.

### AudioPlayer

```typescript
function AudioPlayer({ url, filename }: { url: string; filename: string }): JSX.Element
```

Lecteur audio dans une carte stylée avec :
- Icône 🎵 avec fond acid
- Nom du fichier
- Barre de visualisation décorative (16 barres statiques)
- Élément `<audio>` natif avec contrôles

### ImagePlayer

```typescript
function ImagePlayer({ url, filename }: { url: string; filename: string }): JSX.Element
```

Figure avec `<img>`, `max-h-[62vh]`, bordure, ombre, caption avec icône 🖼.

---

## 20. Composant PatchEditor

**Fichier :** `src/components/PatchEditor.tsx`

**Directive :** `'use client'`

### Interfaces exportées

```typescript
interface PatchParam {
  id: string;
  label: string;
  type: 'text' | 'number' | 'select' | 'color' | 'range';
  value: string | number;
  options?: { label: string; value: string }[];
  min?: number; max?: number; step?: number;
  section?: string;
}

interface PatchEditorProps {
  params: PatchParam[];
  onChange: (id: string, value: string | number) => void;
  onApply?: () => void;
}
```

### Composant

```typescript
export default function PatchEditor({ params, onChange, onApply }: PatchEditorProps): JSX.Element
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `expandedSection` | `string \| null` | Section dépliée (défaut: `'camera'`) |
| `draggedParam` | `string \| null` | Paramètre en cours de drag |

#### Constante PARAM_SECTIONS

```typescript
const PARAM_SECTIONS: Record<string, string> = {
  camera: 'Camera', lighting: 'Éclairage', character: 'Personnage',
  environment: 'Environnement', render: 'Rendu'
};
```

#### Drag & Drop

Les paramètres sont `draggable`. Le drag-and-drop échange les valeurs entre paramètres.

- `handleDragStart(id)` — enregistre l'ID source
- `handleDragOver(e)` — `preventDefault()` pour autoriser le drop
- `handleDrop(targetId)` — échange les valeurs source ↔ cible

#### Rendu

- **En-tête** : titre "Éditeur de Paramètres" + bouton "Appliquer" (si `onApply`)
- **Sections** : chaque section est repliable (accordéon), une seule ouverte à la fois
- **Champs** : rendu selon `param.type` :
  - `text` : `<input type="text">`
  - `number` : `<input type="number">` avec min/max/step
  - `range` : `<input type="range">` + affichage de la valeur
  - `select` : `<select>` avec options
  - `color` : `<input type="color">` + affichage hex

**Note visuelle :** Ce composant utilise un thème clair (fond blanc, texte gris) différent du reste de l'app. C'est le seul composant avec ce style.

---

## 21. Composant ScenePreview

**Fichier :** `src/components/ScenePreview.tsx`

**Directive :** `'use client'`, `@ts-nocheck`

### Interfaces

```typescript
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
```

### Composant principal

```typescript
export function ScenePreview({ characters, environment, isPlaying }: ScenePreviewProps): JSX.Element
```

**State :** `hasThree: boolean | null` — détecte si `@react-three/fiber` est installé.

**Logique :**
1. Tente `import('@react-three/fiber')` dynamiquement
2. Si échec → affiche un placeholder avec instructions d'installation
3. Si succès → rend `_ThreeScene`

### Sous-composant _ThreeScene

Charge dynamiquement `@react-three/fiber` (Canvas) et `@react-three/drei` (OrbitControls).

### Sous-composant _RenderScene

```typescript
function _RenderScene({ characters, environment, isPlaying, Canvas, OrbitControls }): JSX.Element
```

Rendu 3D :
- **Lumières** : ambient (0.1–0.3 selon lightingMood), directional (intensity 2, shadows), point bleu
- **Sol** : planeGeometry 40x40, couleur dark blue, roughness 0.8
- **Personnages** : capsule (corps) + sphère (tête), couleurs HSL uniques
- **Contrôles** : OrbitControls avec pan, zoom, rotation, auto-rotate si `isPlaying`
- **Overlay** : compteur de personnages + "Cliquez pour orbiter"

### Dépendances optionnelles

Ce composant nécessite `three`, `@react-three/fiber`, `@react-three/drei`, `@types/three`. S'ils ne sont pas installés, un fallback informatif est affiché.

---

## 22. Hook useProductionStream

**Fichier :** `src/hooks/useProductionStream.ts`

### Interface de retour

```typescript
export interface ProductionStreamState {
  events: SSEEvent[];
  status: SSEStatus;
  lastHeartbeatAt: number | null;
  reconnect: () => void;
}
```

### Hook

```typescript
export function useProductionStream(
  productionId: string | null,
  token: string | null,
): ProductionStreamState
```

#### Comportement

1. Si `productionId` ou `token` est null → reset (events vide, status idle)
2. Sinon : appelle `connectSSE()` avec :
   - URL : `${API_URL}/api/productions/${productionId}/events`
   - Token Bearer
   - `onEvent` : ajoute l'événement en tête du tableau (max 300)
   - `onStatus` : met à jour le statut
   - `onHeartbeat` : enregistre le timestamp
3. Cleanup : `handle.close()` au démontage

#### reconnect

Incrémente un nonce pour forcer la recréation de l'effet SSE.

#### Connexion

Utilisé par `ProductionStream` pour recevoir les événements temps réel de la pipeline.

---

## 23. Hook useProductionTree

**Fichier :** `src/hooks/useProductionTree.ts`

### Hook

```typescript
export function useProductionTree(refreshInterval = 4000): {
  tree: ProductionTree | undefined;
  productions: ProductionTreeItem[];
  error: any;
  isLoading: boolean;
  mutate: () => void;
}
```

#### Comportement

1. Utilise `useSWR` avec clé `'production-tree'` et fetcher `fetchProductionTree`
2. `refreshInterval` : 4000ms par défaut (polling)
3. Trie les productions par `updated_at` décroissant

#### Connexion

Utilisé par : Dashboard, CostsPage, ProductionStream. Centralise la récupération de l'arbre complet org → workspace → project → production.

---

## 24. Librairie API — `lib/api.ts`

**Fichier :** `src/lib/api.ts`

### Interfaces exportées

| Interface | Champs principaux |
|-----------|-------------------|
| `TokenResponse` | `access_token`, `token_type` |
| `UserOut` | `id`, `email`, `full_name`, `created_at` |
| `MembershipOut` | `organization_id`, `role` |
| `MeOut` | `user: UserOut`, `memberships: MembershipOut[]` |
| `OrgOut` | `id`, `name`, `owner_id`, `created_at`, `role` |
| `WorkspaceOut` | `id`, `organization_id`, `name`, `created_at` |
| `ProjectOut` | `id`, `workspace_id`, `organization_id`, `name`, `description`, `created_by`, `created_at` |
| `ProductionOut` | `id`, `project_id`, `organization_id`, `name`, `brief`, `status`, `current_step`, `progress`, `cost`, `version`, `error`, `created_by`, timestamps |
| `ShotOut` | `id`, `index`, `start`, `end`, `camera_summary`, `action`, `status` |
| `SceneOut` | `id`, `name`, `order_index`, `status`, `shots: ShotOut[]` |
| `SequenceOut` | `id`, `name`, `order_index`, `scenes: SceneOut[]` |
| `TimelineOut` | `production_id`, `sequences: SequenceOut[]` |
| `PatchRequest` | `target`, `old_value`, `new_value`, `rationale` |
| `PatchResponse` | `patch_id`, `status`, `message` |
| `ArtifactRecordOut` | `id`, `type`, `name`, `version`, `path`, `sha256`, `status`, `cost`, `parent_ids`, `created_at` |
| `ArtifactRecordsOut` | `records: ArtifactRecordOut[]` |
| `MemberOut` | `user_id`, `email`, `full_name`, `role` |
| `OrgDetailOut` | `id`, `name`, `owner_id`, `created_at`, `role`, `members: MemberOut[]` |
| `ArtifactOut` | `name`, `type`, `path`, `size`, `cost` |
| `WorkerRunOut` | `production_id`, `since` |
| `RoutingProviderOut` | `id`, `model`, `base_url`, `successes`, `failures`, `cooldown_*`, `last_error` |
| `WorkerOut` | `status`, `queue_depth`, `running`, `processed`, `failed`, `last_heartbeat`, `rotation`, `routing` |
| `UsageQuotas` | `productions`, `cost` |
| `UsageOut` | `productions`, `runs`, `total_cost`, `quotas` |
| `ProductionTreeItem` | `production`, `project`, `workspace`, `org` |

### Classe ApiError

```typescript
class ApiError extends Error {
  status: number;
  constructor(message: string, status: number);
}
```

### Fonction request\<T\>

```typescript
async function request<T>(path: string, init?: RequestInit): Promise<T>
```

- Ajoute `Authorization: Bearer {token}` si disponible
- Ajoute `Content-Type: application/json` par défaut pour les bodies
- Gère les erreurs réseau (→ `ApiError` status 0)
- Parse le body d'erreur (`detail` string ou array)
- Supporte 204 No Content

### Fonction requestBlob

```typescript
async function requestBlob(path: string): Promise<{ blob: Blob; filename: string }>
```

Pour les téléchargements binaires. Parse le `Content-Disposition` pour le filename.

### Objet api (méthodes statiques)

| Méthode | HTTP | Endpoint | Retour |
|---------|------|----------|--------|
| `register(payload)` | POST | `/api/auth/register` | `TokenResponse` |
| `login(payload)` | POST | `/api/auth/login` | `TokenResponse` |
| `me()` | GET | `/api/me` | `MeOut` |
| `listOrganizations()` | GET | `/api/organizations` | `OrgOut[]` |
| `createOrganization(name)` | POST | `/api/organizations` | `OrgOut` |
| `getOrganization(id)` | GET | `/api/organizations/:id` | `OrgDetailOut` |
| `listMembers(orgId)` | GET | `/api/organizations/:id/members` | `MemberOut[]` |
| `addMember(orgId, payload)` | POST | `/api/organizations/:id/members` | `MemberOut` |
| `listWorkspaces(orgId)` | GET | `/api/organizations/:id/workspaces` | `WorkspaceOut[]` |
| `createWorkspace(orgId, name)` | POST | `/api/organizations/:id/workspaces` | `WorkspaceOut` |
| `listProjects(wsId)` | GET | `/api/workspaces/:id/projects` | `ProjectOut[]` |
| `createProject(wsId, payload)` | POST | `/api/workspaces/:id/projects` | `ProjectOut` |
| `getProject(id)` | GET | `/api/projects/:id` | `ProjectOut` |
| `deleteProject(id)` | DELETE | `/api/projects/:id` | `void` |
| `listProductions(projId)` | GET | `/api/projects/:id/productions` | `ProductionOut[]` |
| `createProduction(projId, payload)` | POST | `/api/projects/:id/productions` | `ProductionOut` |
| `getProduction(id)` | GET | `/api/productions/:id` | `ProductionOut` |
| `runProduction(id)` | POST | `/api/productions/:id/run` | `ProductionOut` |
| `cancelProduction(id)` | POST | `/api/productions/:id/cancel` | `ProductionOut` |
| `listArtifacts(prodId)` | GET | `/api/productions/:id/artifacts` | `ArtifactOut[]` |
| `requestRevision(prodId, payload)` | POST | `/api/productions/:id/revision` | `ProductionOut` |
| `downloadArtifact(prodId, path)` | GET | `/api/productions/:id/artifacts/:path` | `{ blob, filename }` |
| `deleteArtifact(prodId, path)` | DELETE | `/api/productions/:id/artifacts/:path` | `void` |
| `preview(prodId)` | GET | `/api/productions/:id/preview` | `{ blob, filename }` |
| `getTimeline(prodId)` | GET | `/api/productions/:id/timeline` | `TimelineOut` |
| `createPatch(prodId, payload)` | POST | `/api/productions/:id/patches` | `PatchResponse` |
| `approveProduction(id)` | POST | `/api/productions/:id/approve` | `ProductionOut` |
| `listArtifactVersions(prodId, type?, name?)` | GET | `/api/productions/:id/versions` | `ArtifactRecordsOut` |
| `restoreArtifactVersion(artifactId)` | POST | `/api/artifacts/:id/restore` | `PatchResponse` |
| `getArtifactBlob(prodId, path)` | GET | `/api/productions/:id/artifacts/:path` | `Blob` |
| `getWorker()` | GET | `/api/worker` | `WorkerOut` |
| `getUsage()` | GET | `/api/usage` | `UsageOut` |

---

## 25. Librairie Auth — `lib/auth.ts`

**Fichier :** `src/lib/auth.ts`

### Constantes

```typescript
const TOKEN_KEY = 'DeepBl4nder_token';
const EMAIL_KEY = 'DeepBl4nder_email';
```

### Fonctions

| Fonction | Signature | Rôle |
|----------|-----------|------|
| `getToken()` | `(): string \| null` | Lit le token JWT depuis localStorage |
| `getEmail()` | `(): string \| null` | Lit l'email depuis localStorage |
| `saveAuth(token, email)` | `(token: string, email: string) => void` | Sauvegarde token + email |
| `clearAuth()` | `(): void` | Supprime token + email |

Toutes les fonctions vérifient `typeof window === 'undefined'` pour la compatibilité SSR.

---

## 26. Contexte Auth — `lib/auth-context.tsx`

**Fichier :** `src/lib/auth-context.tsx`

**Directive :** `'use client'`

### Interface

```typescript
interface AuthContextValue {
  token: string | null;
  user: UserOut | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}
```

### AuthProvider

```typescript
function AuthProvider({ children }: { children: ReactNode }): JSX.Element
```

#### State

| Variable | Type | Initial | Rôle |
|----------|------|---------|------|
| `token` | `string \| null` | `null` | JWT courant |
| `user` | `UserOut \| null` | `null` | Profil utilisateur |
| `ready` | `boolean` | `false` | Session restaurée |

#### Cycle de vie

1. **Montage** : lit `getToken()` depuis localStorage
   - Si token présent → `api.me()` pour restaurer l'utilisateur
   - Si pas de token → `ready = true`
   - Si `api.me()` échoue → `clearAuth()`
2. **login(email, password)** :
   - `api.login()` → `saveAuth()` → `api.me()` → met à jour `token` + `user`
3. **register(email, password, fullName?)** :
   - `api.register()` → `saveAuth()` → `api.me()` → met à jour `token` + `user`
4. **logout()** : `clearAuth()` → reset `token` et `user`
5. **refreshUser()** : `api.me()` → met à jour `user`

Le contexte est mémoïsé via `useMemo`.

### Hook useAuth

```typescript
function useAuth(): AuthContextValue
```

Lève une erreur si utilisé en dehors de `AuthProvider`.

---

## 27. Configuration — `lib/config.ts`

**Fichier :** `src/lib/config.ts`

```typescript
export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

Constante unique. Utilisée par `api.ts`, `sse.ts`, et `useProductionStream.ts`.

---

## 28. Formatage — `lib/format.ts`

**Fichier :** `src/lib/format.ts`

### Fonctions

| Fonction | Signature | Description |
|----------|-----------|-------------|
| `fmtDateTime(iso)` | `(iso: string \| null \| undefined) => string` | Date complète : `jj/mm/aaaa hh:mm` (fr-FR) |
| `fmtTime(iso)` | `(iso: string \| null \| undefined) => string` | Heure seule : `hh:mm` (fr-FR) |
| `fmtCost(cost)` | `(cost: number) => string` | Coût : `$0.0004` (4 décimales) |
| `fmtSize(bytes)` | `(bytes: number) => string` | Taille : `o`, `Ko`, `Mo` |
| `fmtDuration(start, end)` | `(startedAt: string \| null, finishedAt: string \| null) => string` | Durée : `X s`, `X min Y s`, `X h Y min` |
| `fmtPercent(progress)` | `(progress: number) => string` | Pourcentage : `42 %` (progress 0→1) |

Toutes les fonctions gèrent les valeurs null/undefined/NaN en retournant `'—'`.

---

## 29. Notifications — `lib/notifications.tsx`

**Fichier :** `src/lib/notifications.tsx`

**Directive :** `'use client'`

### Types

```typescript
type ToastKind = 'success' | 'error' | 'info';

interface ToastItem {
  id: number;
  kind: ToastKind;
  message: string;
}
```

### Constantes

| Constante | success | error | info |
|-----------|---------|-------|------|
| `DURATION` | 6000ms | 8000ms | 4000ms |
| `STYLE.border` | `border-acid/60` | `border-red-500/70` | `border-muted/60` |
| `STYLE.dot` | `bg-acid` | `bg-red-500` | `bg-muted` |

### NotificationsProvider

```typescript
function NotificationsProvider({ children }: { children: ReactNode }): JSX.Element
```

#### State

| Variable | Type | Rôle |
|----------|------|------|
| `toasts` | `ToastItem[]` | Liste des toasts actifs |
| `nextId` | `useRef(1)` | Compteur d'IDs |

#### Fonction notify

```typescript
const notify = useCallback((kind: ToastKind, message: string) => void, [dismiss])
```

1. Incrémente `nextId`
2. Ajoute le toast à la liste
3. Planifie la suppression automatique via `setTimeout`

#### Dismiss

Supprime un toast par ID. Toujours tous les toasts si `Escape` est pressé.

#### Rendu

Toasts en position fixe (`top-4 right-4 z-50`), `w-80`, chaque toast :
- Fond `card-bg`, bordure colorée
- Point colored + message
- Bouton ✕ pour fermer
- `role="alert"` pour les erreurs, `role="status"` pour les autres
- `aria-live="polite"` sur le conteneur

### Hook useNotifications

```typescript
function useNotifications(): NotificationsContextValue
```

Lève une erreur si utilisé en dehors de `NotificationsProvider`.

---

## 30. Productions — `lib/productions.ts`

**Fichier :** `src/lib/productions.ts`

**Directive :** `'use client'`

### Interface

```typescript
interface ProductionTree {
  productions: ProductionTreeItem[];
  orgs: OrgOut[];
  workspaces: WorkspaceOut[];
  projects: ProjectOut[];
}
```

### Fonction fetchProductionTree

```typescript
async function fetchProductionTree(): Promise<ProductionTree>
```

Parcourt le graphe complet :
1. `api.listOrganizations()` → pour chaque org
2. `api.listWorkspaces(org.id)` → pour chaque workspace
3. `api.listProjects(workspace.id)` → pour chaque project
4. `api.listProductions(project.id)` → pour chaque production

Construit le tableau `productions: ProductionTreeItem[]` avec chaque production associée à son project, workspace et org.

**Note :** 4 appels API imbriqués en séquentiel. Potentiellement lent pour les grandes organisations.

### Fonction sortProductions

```typescript
function sortProductions(items: ProductionTreeItem[]): ProductionTreeItem[]
```

Trie par `updated_at` décroissant (plus récent en premier).

### Fonction ensureProject

```typescript
async function ensureProject(preferredName?: string): Promise<ProjectOut>
```

Crée l'arbre complet si nécessaire :
1. Prend la première org ou crée "Studio {prénom}"
2. Prend le premier workspace ou crée "Production principale"
3. Prend le premier projet ou crée "Projet principal"

Utilisé par `PipelineForm` pour garantir une cible de création.

### Fonction productionStatusLabel

```typescript
function productionStatusLabel(status: string): string
```

Traduit les statuts techniques en labels français :
| Status | Label |
|--------|-------|
| `draft` | Brouillon |
| `queued` | En file |
| `running` | En cours |
| `waiting_approval` | Approbation requise |
| `revising` | En révision |
| `completed` | Terminée |
| `failed` | Échouée |
| `cancelled` | Annulée |
| `blocked` | Bloquée |

### Ré-exports

```typescript
export type { ProductionTreeItem, ProductionOut };
```

---

## 31. SSE — `lib/sse.ts`

**Fichier :** `src/lib/sse.ts`

**Directive :** `'use client'`

### Interfaces

```typescript
interface SSEEvent {
  seq: number;
  [key: string]: unknown;
}

type SSEStatus =
  | { state: 'idle' }
  | { state: 'connecting'; attempt: number }
  | { state: 'connected' }
  | { state: 'reconnecting'; attempt: number; delayMs: number }
  | { state: 'error'; message: string };

interface SSEHandle {
  close: () => void;
}

interface ConnectSSEOptions {
  url: string;
  token: string;
  after?: number;
  onEvent: (event: SSEEvent) => void;
  onStatus: (status: SSEStatus) => void;
  onHeartbeat?: () => void;
  signal?: AbortSignal;
  baseBackoffMs?: number;  // Défaut: 500
  maxBackoffMs?: number;   // Défaut: 30000
}
```

### Fonction connectSSE

```typescript
function connectSSE(options: ConnectSSEOptions): SSEHandle
```

#### Algorithme

1. **Boucle principale `run()`** : tourne tant que `!closed`
2. **Connexion** : `fetch(url, { headers: { Authorization, Accept: text/event-stream } })`
3. **Gestion des erreurs HTTP** :
   - 401/403 → erreur fatale (pas de reconnexion)
   - 404 → erreur fatale
   - Autre → reconnexion
4. **Lecture du stream** : `response.body.getReader()` + `TextDecoder`
5. **Parsing SSE** : sépare par `\n\n`, parse chaque bloc :
   - `event: ping` ou `event: heartbeat` → appelle `onHeartbeat()`
   - `data:` → JSON.parse → déduplique par `seq` → `onEvent()`
6. **Reconnexion** : backoff exponentiel `min(maxBackoff, baseBackoff * 2^(attempt-1))`
7. **Reprise** : ajoute `?after=<lastSeq>` à l'URL (équivalent Last-Event-ID)

#### close()

1. Met `closed = true`
2. Annule le timer de retry
3. Abort le contrôleur en cours
4. Émet status `idle`

#### Garanties

- Pas de `EventSource` natif (ne supporte pas les headers Authorization)
- Déduplication par `seq` (rejette les événements déjà vus)
- Backoff borné (max 30 secondes)
- Arrêt propre (abort + timer)
- Supporte un `AbortSignal` externe

---

## 32. Carte des dépendances et flux de données

### Flux d'initialisation

```
RootLayout
├── AuthProvider (restaure token depuis localStorage → api.me())
│   └── NotificationsProvider (fournit notify())
│       └── <LoginPage> / <RegisterPage>  (hors route group (app))
│       └── (app)/layout
│           ├── RequireAuth (redirige si pas token)
│           │   └── Sidebar (useAuth → user, logout)
│           │   └── <children> = pages protégées
```

### Flux de données — Arbre des productions

```
useProductionTree (SWR, polling 4s)
├── fetchProductionTree()
│   ├── api.listOrganizations()
│   ├── api.listWorkspaces(org.id)      × N orgs
│   ├── api.listProjects(workspace.id)  × N workspaces
│   └── api.listProductions(project.id) × N projects
└── sortProductions() (par updated_at DESC)
    → Dashboard, CostsPage, ProductionStream
```

### Flux SSE — Temps réel

```
ProductionStream
├── useSearchParams() → production ID
├── useProductionStream(productionId, token)
│   └── connectSSE()
│       └── fetch(API_URL/api/productions/:id/events)
│           └── ReadableStream → JSON.parse → events[]
├── api.listArtifacts(productionId)     (polling via events.length)
├── api.getTimeline(productionId)       (polling via events.length)
└── api.getWorker()                     (Dashboard only, 5s)
```

### Flux d'authentification

```
LoginPage
├── useAuth().login(email, password)
│   └── api.login() → TokenResponse
│   └── saveAuth(token, email) → localStorage
│   └── api.me() → setUser()
├── notify('success')
└── router.replace('/')

RegisterPage
├── useAuth().register(email, password, fullName)
│   └── api.register() → TokenResponse
│   └── saveAuth(token, email) → localStorage
│   └── api.me() → setUser()
└── router.replace('/')

Sidebar
├── useAuth().logout()
│   └── clearAuth() → localStorage.removeItem()
│   └── setToken(null), setUser(null)
└── router.replace('/login')
```

### Flux de création de production

```
PipelineForm
├── ensureProject()
│   ├── api.listOrganizations()  → ou createOrganization()
│   ├── api.listWorkspaces()     → ou createWorkspace()
│   └── api.listProjects()       → ou createProject()
├── api.createProduction(projectId, { name, brief })
├── api.runProduction(production.id)
└── router.push('/realtime?production=ID')
```

### Dépendances inter-fichiers

| Fichier | Dépend de |
|---------|-----------|
| `app/layout.tsx` | `lib/auth-context`, `lib/notifications` |
| `app/login/page.tsx` | `lib/auth-context`, `lib/notifications`, `components/ui` |
| `app/register/page.tsx` | `lib/auth-context`, `lib/notifications`, `components/ui` |
| `(app)/layout.tsx` | `components/RequireAuth`, `components/Sidebar` |
| `(app)/page.tsx` | `lib/api`, `components/ui`, `hooks/useProductionTree`, `lib/notifications`, `lib/productions`, `lib/format` |
| `(app)/pipeline/page.tsx` | `components/PipelineForm` |
| `(app)/realtime/page.tsx` | `components/ProductionStream`, `components/ScenePreview`, `components/PatchEditor` |
| `(app)/costs/page.tsx` | `lib/api`, `components/ui`, `hooks/useProductionTree`, `lib/productions`, `lib/format` |
| `(app)/library/page.tsx` | `components/ui`, `lib/notifications` |
| `(app)/members/page.tsx` | `lib/api`, `lib/notifications`, `components/ui` |
| `(app)/settings/page.tsx` | `components/ui`, `lib/notifications` |
| `components/Sidebar.tsx` | `lib/auth-context` |
| `components/RequireAuth.tsx` | `lib/auth-context` |
| `components/PipelineForm.tsx` | `lib/api`, `lib/productions`, `lib/notifications`, `components/ui` |
| `components/ProductionStream.tsx` | `lib/api`, `lib/auth-context`, `lib/notifications`, `hooks/useProductionStream`, `hooks/useProductionTree`, `lib/sse`, `components/ui`, `components/ArtifactViewers`, `lib/format` |
| `components/ArtifactViewers.tsx` | `components/ui` |
| `components/PatchEditor.tsx` | (aucune dépendance interne) |
| `components/ScenePreview.tsx` | (dépendances dynamiques: three, r3f, drei) |
| `hooks/useProductionStream.ts` | `lib/config`, `lib/sse` |
| `hooks/useProductionTree.ts` | `lib/productions` (via SWR) |
| `lib/api.ts` | `lib/config`, `lib/auth` |
| `lib/auth-context.tsx` | `lib/api`, `lib/auth` |
| `lib/auth.ts` | (aucune) |
| `lib/config.ts` | (aucune) |
| `lib/format.ts` | (aucune) |
| `lib/notifications.tsx` | (aucune) |
| `lib/productions.ts` | `lib/api` |
| `lib/sse.ts` | (aucune) |

---

*Document généré automatiquement à partir de l'analyse du code source frontend.*
