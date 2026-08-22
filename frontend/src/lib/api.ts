'use client';

import { API_URL } from '@/lib/config';
import { getToken } from '@/lib/auth';

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  created_at: string;
}

export interface MembershipOut {
  organization_id: string;
  role: string;
}

export interface MeOut {
  user: UserOut;
  memberships: MembershipOut[];
}

export interface OrgOut {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  role: string;
}

export interface WorkspaceOut {
  id: string;
  organization_id: string;
  name: string;
  created_at: string;
}

export interface ProjectOut {
  id: string;
  workspace_id: string;
  organization_id: string;
  name: string;
  description: string;
  created_by: string;
  created_at: string;
}

export interface ProductionOut {
  id: string;
  project_id: string;
  organization_id: string;
  name: string;
  brief: string;
  status: string;
  current_step: string;
  progress: number;
  cost: number;
  version: number;
  error: string;
  created_by: string;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ShotOut {
  id: string;
  index: number;
  start: number;
  end: number;
  camera_summary: string;
  action: string;
  status: string;
}

export interface SceneOut {
  id: string;
  name: string;
  order_index: number;
  status: string;
  shots: ShotOut[];
}

export interface SequenceOut {
  id: string;
  name: string;
  order_index: number;
  scenes: SceneOut[];
}

export interface TimelineOut {
  production_id: string;
  sequences: SequenceOut[];
}

export interface PatchRequest {
  target: string;
  old_value: any | null;
  new_value: any;
  rationale: string;
}

export interface PatchResponse {
  patch_id: string;
  status: string;
  message: string;
}

export interface ArtifactRecordOut {
  id: string;
  type: string;
  name: string;
  version: number;
  path: string;
  sha256: string;
  status: string;
  cost: number;
  parent_ids: string[];
  created_at: string;
}

export interface ArtifactRecordsOut {
  records: ArtifactRecordOut[];
}

export interface MemberOut {
  user_id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface OrgDetailOut {
  id: string;
  name: string;
  owner_id: string;
  created_at: string;
  role: string;
  members: MemberOut[];
}

export interface ArtifactOut {
  name: string;
  type: string;
  path: string;
  size: number;
  cost: number;
}

export interface WorkerRunOut {
  production_id: string;
  since: number;
}

export interface RoutingProviderOut {
  id: string;
  model: string;
  base_url: string;
  successes: number;
  failures: number;
  cooldown_until: number;
  cooldown_remaining_s: number;
  last_error: string | null;
}

export interface WorkerOut {
  status: string;
  queue_depth: number;
  running: WorkerRunOut[];
  processed: number;
  failed: number;
  last_heartbeat: number;
  rotation: string;
  routing: RoutingProviderOut[];
}

export interface UsageQuotas {
  productions: number | null;
  cost: number | null;
}

export interface UsageOut {
  productions: number;
  runs: number;
  total_cost: number;
  quotas: UsageQuotas;
}

export interface ProductionTreeItem {
  production: ProductionOut;
  project: ProjectOut;
  workspace: WorkspaceOut;
  org: OrgOut;
}

class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init?.body !== undefined && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError('Impossible de joindre le serveur DeepBlender.', 0);
  }

  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === 'string') return body.detail;
    if (Array.isArray(body.detail)) {
      return body.detail
        .map((item) => {
          if (item && typeof item === 'object') {
            const msg = (item as { msg?: string }).msg;
            if (typeof msg === 'string') return msg;
          }
          return String(item);
        })
        .join(' ; ');
    }
  } catch {
    // Corps illisible : fallback ci-dessous.
  }
  return `Erreur HTTP ${response.status}`;
}

function encodePath(path: string): string {
  return path
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');
}

async function requestBlob(path: string): Promise<{ blob: Blob; filename: string }> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { headers });
  } catch {
    throw new ApiError('Impossible de joindre le serveur DeepBlender.', 0);
  }
  if (!response.ok) {
    throw new ApiError(await errorMessage(response), response.status);
  }
  const blob = await response.blob();
  let filename = 'artifact';
  const match = response.headers.get('content-disposition')?.match(/filename="?([^";]+)"?/);
  if (match) filename = match[1];
  return { blob, filename };
}

export const api = {
  async register(payload: { email: string; password: string; full_name?: string }): Promise<TokenResponse> {
    return request<TokenResponse>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async login(payload: { email: string; password: string }): Promise<TokenResponse> {
    return request<TokenResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async me(): Promise<MeOut> {
    return request<MeOut>('/api/me');
  },

  async listOrganizations(): Promise<OrgOut[]> {
    return request<OrgOut[]>('/api/organizations');
  },

  async createOrganization(name: string): Promise<OrgOut> {
    return request<OrgOut>('/api/organizations', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  async getOrganization(organizationId: string): Promise<OrgDetailOut> {
    return request<OrgDetailOut>(`/api/organizations/${encodeURIComponent(organizationId)}`);
  },

  async listMembers(organizationId: string): Promise<MemberOut[]> {
    return request<MemberOut[]>(`/api/organizations/${encodeURIComponent(organizationId)}/members`);
  },

  async addMember(organizationId: string, payload: { email: string; role?: string }): Promise<MemberOut> {
    return request<MemberOut>(`/api/organizations/${encodeURIComponent(organizationId)}/members`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async listWorkspaces(organizationId: string): Promise<WorkspaceOut[]> {
    return request<WorkspaceOut[]>(`/api/organizations/${encodeURIComponent(organizationId)}/workspaces`);
  },

  async createWorkspace(organizationId: string, name: string): Promise<WorkspaceOut> {
    return request<WorkspaceOut>(`/api/organizations/${encodeURIComponent(organizationId)}/workspaces`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  async listProjects(workspaceId: string): Promise<ProjectOut[]> {
    return request<ProjectOut[]>(`/api/workspaces/${encodeURIComponent(workspaceId)}/projects`);
  },

  async createProject(workspaceId: string, payload: { name: string; description?: string }): Promise<ProjectOut> {
    return request<ProjectOut>(`/api/workspaces/${encodeURIComponent(workspaceId)}/projects`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getProject(projectId: string): Promise<ProjectOut> {
    return request<ProjectOut>(`/api/projects/${encodeURIComponent(projectId)}`);
  },

  async deleteProject(projectId: string): Promise<void> {
    return request<void>(`/api/projects/${encodeURIComponent(projectId)}`, { method: 'DELETE' });
  },

  async listProductions(projectId: string): Promise<ProductionOut[]> {
    return request<ProductionOut[]>(`/api/projects/${encodeURIComponent(projectId)}/productions`);
  },

  async createProduction(projectId: string, payload: { name: string; brief: string }): Promise<ProductionOut> {
    return request<ProductionOut>(`/api/projects/${encodeURIComponent(projectId)}/productions`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getProduction(productionId: string): Promise<ProductionOut> {
    return request<ProductionOut>(`/api/productions/${encodeURIComponent(productionId)}`);
  },

  async runProduction(productionId: string): Promise<ProductionOut> {
    return request<ProductionOut>(`/api/productions/${encodeURIComponent(productionId)}/run`, { method: 'POST' });
  },

  async cancelProduction(productionId: string): Promise<ProductionOut> {
    return request<ProductionOut>(`/api/productions/${encodeURIComponent(productionId)}/cancel`, { method: 'POST' });
  },

  async listArtifacts(productionId: string): Promise<ArtifactOut[]> {
    return request<ArtifactOut[]>(`/api/productions/${encodeURIComponent(productionId)}/artifacts`);
  },

  async requestRevision(
    productionId: string,
    payload: { target_step?: string; comment?: string },
  ): Promise<ProductionOut> {
    return request<ProductionOut>(`/api/productions/${encodeURIComponent(productionId)}/revision`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async downloadArtifact(productionId: string, path: string): Promise<{ blob: Blob; filename: string }> {
    return requestBlob(`/api/productions/${encodeURIComponent(productionId)}/artifacts/${encodePath(path)}`);
  },

  async deleteArtifact(productionId: string, path: string): Promise<void> {
    return request<void>(`/api/productions/${encodeURIComponent(productionId)}/artifacts/${encodePath(path)}`, {
      method: 'DELETE',
    });
  },

  async preview(productionId: string): Promise<{ blob: Blob; filename: string }> {
    return requestBlob(`/api/productions/${encodeURIComponent(productionId)}/preview`);
  },

  async getTimeline(productionId: string): Promise<TimelineOut> {
    return request<TimelineOut>(`/api/productions/${encodeURIComponent(productionId)}/timeline`);
  },

  async createPatch(productionId: string, payload: PatchRequest): Promise<PatchResponse> {
    return request<PatchResponse>(`/api/productions/${encodeURIComponent(productionId)}/patches`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async approveProduction(productionId: string): Promise<ProductionOut> {
    return request<ProductionOut>(`/api/productions/${encodeURIComponent(productionId)}/approve`, { method: 'POST' });
  },

  async listArtifactVersions(
    productionId: string,
    type?: string,
    name?: string
  ): Promise<ArtifactRecordsOut> {
    const params = new URLSearchParams();
    if (type) params.set('type', type);
    if (name) params.set('name', name);
    return request<ArtifactRecordsOut>(`/api/productions/${encodeURIComponent(productionId)}/versions?${params.toString()}`);
  },

  async restoreArtifactVersion(artifactId: string): Promise<PatchResponse> {
    return request<PatchResponse>(`/api/artifacts/${encodeURIComponent(artifactId)}/restore`, { method: 'POST' });
  },

  async getArtifactBlob(productionId: string, path: string): Promise<Blob> {
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(
      `${API_URL}/api/productions/${encodeURIComponent(productionId)}/artifacts/${encodePath(path)}`,
      { headers },
    );
    if (!response.ok) throw new ApiError('Artifact introuvable.', response.status);
    return response.blob();
  },

  async getWorker(): Promise<WorkerOut> {
    return request<WorkerOut>('/api/worker');
  },

  async getUsage(): Promise<UsageOut> {
    return request<UsageOut>('/api/usage');
  },
};
