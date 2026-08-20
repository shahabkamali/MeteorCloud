# MQTT (Milestone 5)

Local development uses **one-way TLS** plus a unique MQTT username/password per
device and a strict topic ACL. This is enough to prove:

```text
Registered device → authenticates to MQTT → sends a message → receives a ping → returns pong
```

Certificate-based device authentication (mTLS) is **not** implemented yet.

## Security model

| Control | What it does |
| --- | --- |
| Per-device MQTT password | Each device has `device_<device_id>` / a random secret. The platform stores only the SHA-256 hash. The plaintext is returned **once** at registration/claim. |
| Broker TLS (`mqtts://localhost:8883`) | Protects the password in transit. Devices verify `ca.crt`. |
| Topic ACL | A device can only publish/subscribe its own `devices/{id}/…` topics. A stolen credential impersonates **that device only**. |
| Revoke / disable | MQTT auth rejects disabled devices and revoked MQTT credentials. |
| HTTP vs MQTT | The `dev_` HTTP token and the MQTT password are separate secrets. |

Internal broker callbacks:

```text
POST /internal/mqtt/authenticate
POST /internal/mqtt/authorize
```

These require `X-MQTT-Internal-Token` and are not user APIs.

## Local setup

```bash
make mqtt-certs   # or make dev, which generates certs if missing
make dev
```

- MQTT TLS: `mqtts://localhost:8883`
- EMQX dashboard (dev only): http://localhost:18083 (`admin` / `public`)
- Port `1883` is not exposed.

Then register a device (`meteorcli register` or request-token/claim). The agent
stores MQTT credentials in `mqtt.json` (`0600`) and `mqtt-ca.crt`. Start
`meteorcli run` so the agent connects, publishes `online`, and answers ping.

On the device detail page: **Test Connection**.

## Manual mosquitto checks

Subscribe (as the device):

```bash
mosquitto_sub \
  -h localhost -p 8883 --cafile certs/ca.crt \
  -u device_DEVICE_ID -P MQTT_PASSWORD \
  -t devices/DEVICE_ID/commands
```

Publish status:

```bash
mosquitto_pub \
  -h localhost -p 8883 --cafile certs/ca.crt \
  -u device_DEVICE_ID -P MQTT_PASSWORD \
  -t devices/DEVICE_ID/status \
  -m '{"status":"online"}'
```

A second device username must be **denied** on `devices/OTHER_ID/#`.

## Topics

```text
devices/{device_id}/status              PUBLISH (device, LWT)
devices/{device_id}/events              PUBLISH (device)
devices/{device_id}/commands            SUBSCRIBE (device) / PUBLISH (platform)
devices/{device_id}/commands/result     PUBLISH (device)
```

QoS 1 for commands, results, and status.
