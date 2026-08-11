'use client';

import { api, type OrgOut, type ProductionOut, type ProductionTreeItem, type ProjectOut, type WorkspaceOut } from '@/lib/api';

export interface ProductionTree {
  productions: ProductionTreeItem[];
  orgs: OrgOut[];
  workspaces: WorkspaceOut[];
  projects: ProjectOut[];
}

/**
 * Parcourt l'ensemble du graphe utilisateur (organisations → workspaces →
 * projets → productions) et le renvoie aplati.
 */
export async function fetchProductionTree(): Promise<ProductionTree> {
  const orgs = await api.listOrganizations();
  const workspaces: WorkspaceOut[] = [];
  const projects: ProjectOut[] = [];
  const productions: ProductionTreeItem[] = [];

  for (const org of orgs) {
    const orgWorkspaces = await api.listWorkspaces(org.id);
    for (const workspace of orgWorkspaces) {
      const orgProjects = await api.listProjects(workspace.id);
      for (const project of orgProjects) {
        const projectProductions = await api.listProductions(project.id);
        for (const production of projectProductions) {
          productions.push({ production, project, workspace, org });
        }
      }
      projects.push(...orgProjects);
    }
    workspaces.push(...orgWorkspaces);
  }

  return { productions, orgs, workspaces, projects };
}

export function sortProductions(items: ProductionTreeItem[]): ProductionTreeItem[] {
  return [...items].sort((a, b) => b.production.updated_at.localeCompare(a.production.updated_at));
}

/**
 * Garantit l'existence d'une organisation, d'un workspace et d'un projet,
 * en les créant si nécessaire. Renvoie l'identifiant du projet cible.
 */
export async function ensureProject(preferredName?: string): Promise<ProjectOut> {
  const orgs = await api.listOrganizations();
  const org: OrgOut =
    orgs.length > 0
      ? orgs[0]
      : await api.createOrganization(`Studio ${(await api.me()).user.full_name.trim().split(' ')[0] || 'DeepBlender'}`);

  const workspaces = await api.listWorkspaces(org.id);
  const workspace: WorkspaceOut =
    workspaces.length > 0 ? workspaces[0] : await api.createWorkspace(org.id, 'Production principale');

  const projects = await api.listProjects(workspace.id);
  const project: ProjectOut =
    projects.length > 0
      ? projects[0]
      : await api.createProject(workspace.id, {
          name: preferredName || 'Projet principal',
          description: 'Créé automatiquement par DeepBlender.',
        });

  return project;
}

export function productionStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    draft: 'Brouillon',
    queued: 'En file',
    running: 'En cours',
    waiting_approval: 'Approbation requise',
    revising: 'En révision',
    completed: 'Terminée',
    failed: 'Échouée',
    cancelled: 'Annulée',
    blocked: 'Bloquée',
  };
  return labels[status] ?? status;
}

export type { ProductionTreeItem, ProductionOut };
