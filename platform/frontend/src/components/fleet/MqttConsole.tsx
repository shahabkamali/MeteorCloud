import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { listenMqttEvents, publishMqttTest, type MqttTestEvent } from "@/api/fleet";
import { ApiError } from "@/api/http";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatDateTime } from "@/lib/utils";

type MqttConsoleProps = {
  token: string;
  organizationId: string;
  defaultTopic?: string;
  topicLocked?: boolean;
  canPublish: boolean;
  topicPlaceholder?: string;
};

export function MqttConsole({
  token,
  organizationId,
  defaultTopic = "",
  topicLocked = false,
  canPublish,
  topicPlaceholder = "devices/<device-id>/events",
}: MqttConsoleProps) {
  const [topic, setTopic] = useState(defaultTopic);
  const [payload, setPayload] = useState("hello from console");
  const [listening, setListening] = useState(false);
  const [events, setEvents] = useState<MqttTestEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const stopRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    setTopic(defaultTopic);
  }, [defaultTopic]);

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
    const nextTopic = topic.trim();
    if (!nextTopic) {
      setError("Enter a topic to listen on.");
      return;
    }
    setError(null);
    stopListening();
    setEvents([]);
    setListening(true);
    stopRef.current = listenMqttEvents(
      token,
      organizationId,
      nextTopic,
      (event) => setEvents((current) => [...current, event]),
      (err) => {
        setError(err instanceof ApiError ? err.message : err.message);
        setListening(false);
        stopRef.current = null;
      },
    );
  }

  const publishMutation = useMutation({
    mutationFn: () =>
      publishMqttTest(token, organizationId, {
        topic: topic.trim(),
        payload,
      }),
    onSuccess: () => setError(null),
    onError: (err: unknown) =>
      setError(err instanceof ApiError ? err.message : "Could not publish MQTT message."),
  });

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="mqtt-topic">Topic</Label>
        <Input
          id="mqtt-topic"
          value={topic}
          onChange={(event) => {
            stopListening();
            setEvents([]);
            setTopic(event.target.value);
          }}
          placeholder={topicPlaceholder}
          readOnly={topicLocked}
          disabled={topicLocked}
        />
      </div>
      {canPublish ? (
        <div className="space-y-2">
          <Label htmlFor="mqtt-payload">Payload</Label>
          <textarea
            id="mqtt-payload"
            className="min-h-24 w-full rounded-md border border-input bg-white px-3 py-2 font-mono text-sm"
            value={payload}
            onChange={(event) => setPayload(event.target.value)}
          />
        </div>
      ) : null}
      <div className="flex flex-wrap gap-2">
        {listening ? (
          <Button type="button" variant="outline" onClick={stopListening}>
            Stop
          </Button>
        ) : (
          <Button type="button" onClick={startListening} disabled={!topic.trim()}>
            Listen
          </Button>
        )}
        {canPublish ? (
          <Button
            type="button"
            variant="secondary"
            onClick={() => publishMutation.mutate()}
            disabled={!topic.trim() || publishMutation.isPending}
          >
            {publishMutation.isPending ? "Publishing…" : "Publish"}
          </Button>
        ) : null}
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {listening ? <p className="text-sm text-muted-foreground">Listening on {topic.trim()}</p> : null}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Messages</p>
        {events.length === 0 ? (
          <p className="mt-3 text-sm text-muted-foreground">
            No messages yet. Listen, then publish from this page or a device.
          </p>
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
    </div>
  );
}
