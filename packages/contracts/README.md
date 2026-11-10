# @imbooored/contracts

TypeScript types for the REST API, generated from [docs/api/openapi.yaml](../../docs/api/openapi.yaml), plus JSON Schemas for Socket.IO event payloads.

Nothing is generated yet. Generation starts in S02, when the web app makes its first typed API call. Rules:

- Never hand-edit generated files. Change `docs/api/openapi.yaml`, then regenerate.
- CI will fail if the generated output differs from what is committed.
