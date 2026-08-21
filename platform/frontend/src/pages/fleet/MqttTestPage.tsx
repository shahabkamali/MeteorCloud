import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import {
  listDevices,
  listenMqttEvents,
  publishMqttTest,
  type MqttTestEvent,
} from "@/api/fleet";
import { ApiError } from "@/api/http";
import { getOrganization } from "@/api/organizations";
import { useAuth } from "@/auth/AuthContext";
import { FleetNav } from "@/components/fleet/FleetNav";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { canManageFleet } from "@/lib/permissions";
import { formatDateTime } from "@/lib/utils";

function eventsTopic(deviceId: string): string {
  return `devices/${deviceId}/events`;
}

function meteorcliCommand(): string {
  return "meteorcli mqtt-test";
}

export function MqttTestPage() {
  const { organizationId = "" } = useParams();
  const { token } = useAuth();
  const [deviceId, setDeviceId] = useState("");
  const [listening, setListening] = useState(false);
  const [events, setEvents] = useState<MqttTestEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const stopRef = useRef<(() => void) | null>(null);

  const orgQuery = useQuery({
    queryKey: ["organization", organizationId, token],
    queryFn: () => getOrganization(token!, organizationId),
    enabled: Boolean(token && organizationId),
  });
  const devicesQuery = useQuery({
    queryKey: ["devices", organizationId, "mqtt-test", token],
    queryFn: () => listDevices(token!, organizationId, { page: 1, page_size: 100, sort: "name", order: "asc" }),
    enabled: Boolean(token && organizationId),
  });

  const devices = devicesQuery.data?.items ?? [];
  const selectedId = deviceId || devices[0]?.id || "";
  const topic = selectedId ? eventsTopic(selectedId) : "";
  const canManage = canManageFleet(orgQuery.data?.current_user_role);
  const command = useMemo(() => meteorcliCommand(), []);

  useEffect(() => {
    return () => {
      stopRef.current?.();
    };
  }, []);

  function stopListening() {
    stopRef.current?.();
    stopRef.current = null;
    setListening(false);
  }

  function startListening() {
    if (!token || !selectedId) {
      return;
    }
    setError(null);
    stopListening();
    setEvents([]);
    setListening(true);
    stopRef.current = listenMqttEvents(
      token,
      organizationId,
      selectedId,
      (event) => setEvents((current) => [...current, event]),
      (err) => {
        setError(err instanceof ApiError ? err.message : err.message);
        setListening(false);
        stopRef.current = null;
      },
    );
  }

  const publishMutation = useMutation({
    mutationFn: () => publishMqttTest(token!, organizationId, selectedId),
    onSuccess: () => setError(null),
    onError: (err: unknown) =>
      setError(err instanceof ApiError ? err.message : "Could not publish MQTT test message."),
  });

  async function copyCommand() {
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      setError("Could not copy the meteorcli command.");
    }
  }

  return (
    <section className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">MQTT test</h1>
        <p className="mt-2 text-muted-foreground">{orgQuery.data?.name}</p>
      </div>
      <FleetNav organizationId={organizationId} />

      <div className="space-y-4 rounded-lg border border-border bg-white/80 p-6 shadow-sm">
        <div className="max-w-md space-y-2">
          <Label htmlFor="mqtt-device">Device</Label>
          <select
            id="mqtt-device"
            className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            value={selectedId}
            onChange={(event) => {
              stopListening();
              setEvents([]);
              setDeviceId(event.target.value);
            }}
            disabled={devices.length === 0}
          >
            {devices.length === 0 ? <option value="">No devices</option> : null}
            {devices.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Example topic</p>
          <p className="mt-1 font-mono text-sm">{topic || "—"}</p>
        </div>

        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">On the device</p>
          <pre className="mt-2 overflow-x-auto rounded-md bg-secondary p-3 text-sm">{command}</pre>
          <Button type="button" variant="outline" className="mt-2" onClick={() => void copyCommand()} disabled={!selectedId}>
            Copy command
          </Button>
        </div>

        <div className="flex flex-wrap gap-2">
          {listening ? (
            <Button type="button" variant="outline" onClick={stopListening}>
              Stop
            </Button>
          ) : (
            <Button type="button" onClick={startListening} disabled={!selectedId}>
              Listen
            </Button>
          )}
          {canManage ? (
            <Button
              type="button"
              variant="secondary"
              onClick={() => publishMutation.mutate()}
              disabled={!selectedId || publishMutation.isPending}
            >
              {publishMutation.isPending ? "Publishing…" : "Publish from console"}
            </Button>
          ) : null}
        </div>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        {listening ? <p className="text-sm text-muted-foreground">Listening on {topic}</p> : null}
      </div>

      <div className="rounded-lg border border-border bg-white/80 p-6 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Messages</p>
        {events.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">No messages yet. Listen, then publish from the device or console.</p>
        ) : (
          <ol className="mt-3 space-y-3">
            {events.map((event, index) => (
              <li key={`${event.received_at}-${index}`} className="rounded-md bg-secondary p-3">
                <p className="text-xs text-muted-foreground">{formatDateTime(event.received_at)}</p>
                <p className="mt-1 font-mono text-xs text-muted-foreground">{event.topic}</p>
                <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-sm">{event.payload}</pre>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
