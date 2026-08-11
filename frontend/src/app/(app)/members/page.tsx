'use client';

import { useCallback, useEffect, useState } from 'react';

import { api, type MemberOut, type OrgDetailOut } from '@/lib/api';
import { useNotifications } from '@/lib/notifications';
import { Badge, Button, Card, CardBody, CardHeader, EmptyState, Field, Input, Select, Skeleton } from '@/components/ui';

const ROLE_LABELS: Record<string, string> = {
  owner: 'Propriétaire',
  admin: 'Administrateur',
  editor: 'Éditeur',
  viewer: 'Observateur',
};

const ROLE_TONES: Record<string, 'acid' | 'green' | 'blue' | 'muted'> = {
  owner: 'acid',
  admin: 'green',
  editor: 'blue',
  viewer: 'muted',
};

export default function MembersPage() {
  const { notify } = useNotifications();
  const [org, setOrg] = useState<OrgDetailOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [newEmail, setNewEmail] = useState('');
  const [newRole, setNewRole] = useState('viewer');
  const [addBusy, setAddBusy] = useState(false);

  const loadOrg = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const orgs = await api.listOrganizations();
      if (orgs.length === 0) {
        setError('Aucune organisation trouvée.');
        return;
      }
      const detail = await api.getOrganization(orgs[0].id);
      setOrg(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger l\'organisation.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadOrg();
  }, [loadOrg]);

  const handleAddMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!org || !newEmail.trim()) return;
    setAddBusy(true);
    try {
      await api.addMember(org.id, { email: newEmail.trim(), role: newRole });
      notify('success', `Membre « ${newEmail.trim()} » ajouté.`);
      setNewEmail('');
      setNewRole('viewer');
      void loadOrg();
    } catch (err) {
      notify('error', err instanceof Error ? err.message : 'Ajout impossible.');
    } finally {
      setAddBusy(false);
    }
  };

  return (
    <div className="animate-fade-up p-4 sm:p-6 md:p-10">
      <header className="mb-6 sm:mb-8">
        <h1 className="font-display text-2xl sm:text-3xl font-bold tracking-tight text-off-white">Membres</h1>
        <p className="mt-1 text-sm sm:text-base text-muted">Gérez les membres de votre organisation et leurs droits d&apos;accès.</p>
      </header>

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : error ? (
        <Card className="border-red-500/40">
          <CardHeader title="Erreur" subtitle={error} />
        </Card>
      ) : !org ? null : (
        <>
          <Card className="mb-6">
            <CardHeader
              title={org.name}
              subtitle={`Organisation · ${org.members.length} membre${org.members.length !== 1 ? 's' : ''} · Vous êtes ${ROLE_LABELS[org.role] ?? org.role}`}
            />
          </Card>

          <Card className="mb-6">
            <CardHeader title="Ajouter un membre" subtitle="Invitez un collaborateur par email." />
            <CardBody>
              <form onSubmit={(e) => void handleAddMember(e)} className="flex flex-col sm:flex-row items-stretch sm:items-end gap-3">
                <div className="flex-1">
                  <Field label="Email" htmlFor="member-email">
                    <Input
                      id="member-email"
                      type="email"
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      placeholder="collaborateur@example.com"
                      required
                    />
                  </Field>
                </div>
                <Field label="Rôle" htmlFor="member-role">
                  <Select
                    id="member-role"
                    value={newRole}
                    onChange={(e) => setNewRole(e.target.value)}
                  >
                    <option value="viewer">Observateur</option>
                    <option value="editor">Éditeur</option>
                    <option value="admin">Administrateur</option>
                  </Select>
                </Field>
                <Button type="submit" disabled={addBusy || !newEmail.trim()} className="sm:mb-0.5">
                  {addBusy ? 'Ajout…' : 'Ajouter'}
                </Button>
              </form>
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Membres" subtitle={`${org.members.length} personne${org.members.length !== 1 ? 's' : ''} dans cette organisation.`} />
            <CardBody className="p-0">
              {org.members.length === 0 ? (
                <div className="p-5">
                  <EmptyState title="Aucun membre" description="Ajoutez un collaborateur ci-dessus." />
                </div>
              ) : (
                <ul className="divide-y divide-border">
                  {org.members.map((member) => (
                    <li key={member.user_id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium text-off-white">
                          {member.full_name || member.email}
                        </p>
                        <p className="truncate text-xs text-muted">{member.email}</p>
                      </div>
                      <Badge tone={ROLE_TONES[member.role] ?? 'muted'}>
                        {ROLE_LABELS[member.role] ?? member.role}
                      </Badge>
                      {member.user_id === org.owner_id ? (
                        <Badge tone="acid">Propriétaire</Badge>
                      ) : null}
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>
        </>
      )}
    </div>
  );
}
