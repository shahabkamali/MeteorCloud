# Device types and groups

Device types and device groups are organization-scoped catalogs used to classify
and organize devices. They are optional: a device can register without either.

## Device types

A **device type** describes a class of hardware/software (e.g. "Gateway",
"Sensor Hub"). Each type has:

- `name` — unique within the organization (case-insensitive)
- `description` — optional free text
- `capabilities` — optional JSON object for declared features

### API

All routes require an authenticated user who is a member of the organization.
Creating, updating, and deleting require the **owner** or **admin** role;
members and viewers have read-only access.

| Method | Path |
|--------|------|
| `GET` | `/api/v1/organizations/{org}/device-types` |
| `POST` | `/api/v1/organizations/{org}/device-types` |
| `GET` | `/api/v1/organizations/{org}/device-types/{id}` |
| `PATCH` | `/api/v1/organizations/{org}/device-types/{id}` |
| `DELETE` | `/api/v1/organizations/{org}/device-types/{id}` |

A device type that is still assigned to one or more devices cannot be deleted
(`device_type_in_use`); reassign or remove those devices first.

## Device groups

A **device group** is a logical grouping (e.g. "Production", "Lab"). It has the
same shape as a device type except it carries `labels` instead of
`capabilities`. The routes mirror device types under `/device-groups`. A group
that is still in use cannot be deleted (`device_group_in_use`).

## Assigning devices

Devices are assigned a type/group in three ways:

1. Bound to a registration token — every device that registers with the token
   inherits the token's type and group.
2. Manually from the device detail page or the update API.
3. Cleared via the update API using `clear_device_type` / `clear_device_group`.

## UI

Manage both from **Fleet → Device types** and **Fleet → Device groups**. The
create/edit/delete controls are only shown to owners and admins.
