import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import {
  approveEnrollmentRequest,
  createEnrollmentKey,
  listDeviceGroups,
  listDeviceTypes,
  listEnrollmentKeys,
  listEnrollmentRequests,
  rejectEnrollmentRequest,
  revokeEnrollmentKey,
  type DeviceEnrollmentRequest,
  type EnrollmentApiKeyWithSecret,
} from "@/api/fleet";
import { ApiError } from "@/api/http";
import { getOrganization } from "@/api/organizations";
import { useAuth } from "@/auth/AuthContext";
import { FleetNav } from "@/components/fleet/FleetNav";
import { OneTimeSecretDialog } from "@/components/fleet/OneTimeSecretDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { canManageFleet } from "@/lib/permissions";

function buildConfigCommand(domain: string, apiKey: string): string {
  return [
    "meteorcli config \\",
    `  --domain ${domain} \\`,
    `  --api-key ${apiKey}`,
  ].join("\n");
}

export function ApiKeysPage() {
  const { organizationId = "" } = useParams();
  const { token } = useAuth();
  const queryClient = useQueryClient();

  const [keyName, setKeyName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [createdKey, setCreatedKey] = useState<EnrollmentApiKeyWithSecret | null>(null);

  const [approveId, setApproveId] = useState<string | null>(null);
  const [approveName, setApproveName] = useState("");
  const [approveTypeId, setApproveTypeId] = useState("");
  const [approveGroupId, setApproveGroupId] = useState("");

  const orgQuery = useQuery({
    queryKey: ["organization", organizationId, token],
    queryFn: () => getOrganization(token!, organizationId),
    enabled: Boolean(token && organizationId),
  });
  const keysQuery = useQuery({
    queryKey: ["enrollment-keys", organizationId, token],
    queryFn: () => listEnrollmentKeys(token!, organizationId),
    enabled: Boolean(token && organizationId),
  });
  const requestsQuery = useQuery({
    queryKey: ["enrollment-requests", organizationId, token],
    queryFn: () => listEnrollmentRequests(token!, organizationId),
    enabled: Boolean(token && organizationId),
  });
  const typesQuery = useQuery({
    queryKey: ["device-types", organizationId, token],
    queryFn: () => listDeviceTypes(token!, organizationId),
    enabled: Boolean(token && organizationId),
  });
  const groupsQuery = useQuery({
    queryKey: ["device-groups", organizationId, token],
    queryFn: () => listDeviceGroups(token!, organizationId),
    enabled: Boolean(token && organizationId),
  });

  const canManage = canManageFleet(orgQuery.data?.current_user_role);

  const pendingRequests = useMemo(
    () => (requestsQuery.data ?? []).filter((entry) => entry.status === "pending"),
    [requestsQuery.data],
  );

  const createMutation = useMutation({
    mutationFn: () =>
      createEnrollmentKey(token!, organizationId, {
        name: keyName,
      }),
    onSuccess: async (created) => {
      setCreatedKey(created);
      setKeyName("");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["enrollment-keys", organizationId] });
    },
    onError: (err: unknown) => {
      setError(err instanceof ApiError ? err.message : "Could not create the API key.");
    },
  });

  function onCreateKey(event: FormEvent) {
    event.preventDefault();
    createMutation.mutate();
  }

  async function onRevoke(keyId: string) {
    if (!window.confirm("Revoke this API key?")) {
      return;
    }
    setError(null);
    try {
      await revokeEnrollmentKey(token!, organizationId, keyId);
      await queryClient.invalidateQueries({ queryKey: ["enrollment-keys", organizationId] });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not revoke the API key.");
    }
  }

  async function onApprove(event: FormEvent) {
    event.preventDefault();
    if (!approveId) {
      return;
    }
    setError(null);
    try {
      await approveEnrollmentRequest(token!, organizationId, approveId, {
        name: approveName || undefined,
        device_type_id: approveTypeId || undefined,
        device_group_id: approveGroupId || undefined,
      });
      setApproveId(null);
      setApproveName("");
      setApproveTypeId("");
      setApproveGroupId("");
      await queryClient.invalidateQueries({
        queryKey: ["enrollment-requests", organizationId],
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve the request.");
    }
  }

  async function onReject(request: DeviceEnrollmentRequest) {
    const reason = window.prompt("Optional rejection reason:", "") ?? undefined;
    setError(null);
    try {
      await rejectEnrollmentRequest(token!, organizationId, request.id, {
        reason: reason || undefined,
      });
      await queryClient.invalidateQueries({
        queryKey: ["enrollment-requests", organizationId],
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject the request.");
    }
  }

  const domain = window.location.hostname.replace(/^www\./, "");

  return (
    <section className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Fleet</h1>
        <p className="mt-2 text-muted-foreground">{orgQuery.data?.name}</p>
      </div>
      <FleetNav organizationId={organizationId} />

      {error && <p className="text-sm text-red-700">{error}</p>}

      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Pending enrollment requests</h2>
        <div className="overflow-hidden rounded-lg border border-border bg-white/80 shadow-sm">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-border bg-secondary/60 text-xs uppercase tracking-wide text-muted-foreground">
              <tr>
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Hostname</th>
                <th className="px-4 py-3 font-semibold">Machine ID</th>
                <th className="px-4 py-3 font-semibold">Architecture</th>
                {canManage && <th className="px-4 py-3 font-semibold">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {pendingRequests.map((entry) => (
                <tr key={entry.id} className="border-b border-border/70">
                  <td className="px-4 py-3 font-medium">
                    {entry.requested_name ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{entry.hostname ?? "—"}</td>
                  <td className="px-4 py-3 font-mono text-xs">{entry.machine_id ?? "—"}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {entry.architecture ?? "—"}
                  </td>
                  {canManage && (
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() => {
                            setApproveId(entry.id);
                            setApproveName(entry.requested_name ?? "");
                            setApproveTypeId(entry.device_type_id ?? "");
                            setApproveGroupId(entry.device_group_id ?? "");
                          }}
                        >
                          Approve
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => onReject(entry)}>
                          Reject
                        </Button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {pendingRequests.length === 0 && (
                <tr>
                  <td className="px-4 py-6 text-center text-muted-foreground" colSpan={5}>
                    No pending enrollment requests.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {canManage && approveId && (
        <form
          className="grid gap-3 rounded-lg border border-border bg-white/80 p-5 shadow-sm md:grid-cols-3"
          onSubmit={onApprove}
        >
          <div className="md:col-span-3">
            <p className="text-sm font-medium">Approve device</p>
            <p className="text-xs text-muted-foreground">
              Optionally set the name, type, and group assigned when the device claims its
              credential.
            </p>
          </div>
          <div>
            <Label htmlFor="approve-name">Name</Label>
            <Input
              id="approve-name"
              value={approveName}
              onChange={(event) => setApproveName(event.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="approve-type">Device type</Label>
            <select
              id="approve-type"
              className="flex h-10 w-full rounded-md border border-input bg-white px-3 text-sm"
              value={approveTypeId}
              onChange={(event) => setApproveTypeId(event.target.value)}
            >
              <option value="">None</option>
              {(typesQuery.data ?? []).map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <Label htmlFor="approve-group">Device group</Label>
            <select
              id="approve-group"
              className="flex h-10 w-full rounded-md border border-input bg-white px-3 text-sm"
              value={approveGroupId}
              onChange={(event) => setApproveGroupId(event.target.value)}
            >
              <option value="">None</option>
              {(groupsQuery.data ?? []).map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </div>
          <div className="md:col-span-3 flex gap-2">
            <Button type="submit">Confirm approval</Button>
            <Button type="button" variant="secondary" onClick={() => setApproveId(null)}>
              Cancel
            </Button>
          </div>
        </form>
      )}

      {canManage && (
        <form
          className="grid gap-3 rounded-lg border border-border bg-white/80 p-5 shadow-sm md:grid-cols-2"
          onSubmit={onCreateKey}
        >
          <div className="md:col-span-2">
            <p className="text-sm font-medium">API keys</p>
            <p className="text-xs text-muted-foreground">
              Devices use a key with <code>meteorcli config</code> and{" "}
              <code>meteorcli request</code> to ask to join this organization.
            </p>
          </div>
          <div>
            <Label htmlFor="key-name">Name</Label>
            <Input
              id="key-name"
              value={keyName}
              onChange={(event) => setKeyName(event.target.value)}
              required
            />
          </div>
          <div className="flex items-end">
            <Button type="submit" disabled={createMutation.isPending}>
              Create API key
            </Button>
          </div>
        </form>
      )}

      <div className="overflow-hidden rounded-lg border border-border bg-white/80 shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-border bg-secondary/60 text-xs uppercase tracking-wide text-muted-foreground">
            <tr>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">Prefix</th>
              <th className="px-4 py-3 font-semibold">Status</th>
              {canManage && <th className="px-4 py-3 font-semibold">Actions</th>}
            </tr>
          </thead>
          <tbody>
            {(keysQuery.data ?? []).map((entry) => (
              <tr key={entry.id} className="border-b border-border/70">
                <td className="px-4 py-3 font-medium">{entry.name}</td>
                <td className="px-4 py-3 font-mono text-xs">{entry.key_prefix}…</td>
                <td className="px-4 py-3">{entry.revoked_at ? "Revoked" : "Active"}</td>
                {canManage && (
                  <td className="px-4 py-3">
                    {!entry.revoked_at && (
                      <Button variant="ghost" size="sm" onClick={() => onRevoke(entry.id)}>
                        Revoke
                      </Button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {(keysQuery.data ?? []).length === 0 && (
              <tr>
                <td className="px-4 py-6 text-center text-muted-foreground" colSpan={4}>
                  No API keys yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {createdKey && (
        <OneTimeSecretDialog
          title="API key created"
          description="Copy this key now and configure meteorcli with it. For security it will not be shown again."
          secret={createdKey.api_key}
          command={buildConfigCommand(domain, createdKey.api_key)}
          onClose={() => setCreatedKey(null)}
        />
      )}
    </section>
  );
}
