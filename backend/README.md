# PerfectBlue Runtime

The Python service is the local runtime behind the PerfectBlue dashboard and the
Claw3D custom-runtime adapter. It owns persistent agents, tasks, activities, and
chat history in SQLite.

## Setup

```powershell
conda activate exact-env
pip install -r backend/requirements.txt
python backend/main.py
```

The runtime listens on `127.0.0.1:7770` by default and stores local state under
`.perfectblue/`. Both can be changed with environment variables documented in
the root `.env.example`.

## Security defaults

- Non-loopback binding requires `PERFECTBLUE_RUNTIME_TOKEN`.
- CORS accepts only the local Vite and Claw3D origins by default.
- Agent-created files must live under `projects/<project-name>/`.
- Arbitrary Python execution is disabled unless
  `PERFECTBLUE_ENABLE_PYTHON_TOOL=true` is explicitly configured.
- Claw3D and the Vite dashboard both support bearer-token authentication.

Enabling the Python tool does not turn it into a container sandbox. Only enable
it on a trusted local machine; a containerized run executor remains the safer
long-term design.

## API surface

- `GET /health`
- `GET /state`
- `GET /registry`
- `POST /v1/chat/completions`
- `POST /agents/add`
- `DELETE /agents/{agent_id}`
- `GET /sessions/{session_id}/messages`
- `GET|POST /api/v1/tasks`
- `POST|DELETE /api/v1/tasks/{task_id}`
- `GET /api/v1/activities`

All routes except `/health` require a bearer token when
`PERFECTBLUE_RUNTIME_TOKEN` is configured.

## Tests

```powershell
conda run -n exact-env python -m unittest discover -s backend/tests -v
```

The runtime currently uses the legacy `google.generativeai` SDK. Its replacement
with the supported `google-genai` SDK should happen before a public release.
