# Contact Center Agents

Modular Python (Flask) + HTML app for contact-center agent training and operation.

## Navigation

- **Technical Support Call Training** — practice calls against a simulated customer
  (reuses `app/tech_support_training.py`).
- **Agentic Call Center Agent** — technical support agent that helps callers.
- **Admin Panel** — configure four independent settings.

## Admin settings (granular, independent)

| Setting                  | Scope    | Purpose                                  |
|--------------------------|----------|------------------------------------------|
| `agent_system_prompt`    | role     | The support agent's instructions         |
| `customer_system_prompt` | role     | The simulated customer's instructions    |
| `system_prompt`          | platform | Cross-session platform guidance          |
| `grading_rubric`         | platform | Call scoring guide                       |

The platform `system_prompt` and `grading_rubric` are edited separately from each
other and separately from the agent/customer prompts.

## Structure

```
run.py                      entrypoint (443 + SSL)
app/
  __init__.py               app factory, registers blueprints
  config.py                 env-driven config
  settings_store.py         JSON-backed, atomic, admin-editable settings
  tech_support_training.py  reused customer simulation
  blueprints/               one module per nav area (training, agent, admin)
  templates/                base.html holds the single nav; pages extend it
  static/style.css
tests/test_settings_store.py
```

## Run

```bash
python3 -m venv venv && . venv/bin/activate
pip install -r requirements.txt
python run.py
```

### Port 443 + SSL

`run.py` serves HTTPS on 443 when a cert/key exist at `CCA_SSL_CERT` / `CCA_SSL_KEY`
(defaults `certs/server.crt` and `certs/server.key`). Binding 443 needs privilege:
run behind a reverse proxy, or grant the capability once:

```bash
sudo setcap 'cap_net_bind_service=+ep' $(readlink -f $(which python3))
```

Local dev cert:

```bash
mkdir -p certs
openssl req -x509 -newkey rsa:2048 -nodes -keyout certs/server.key \
  -out certs/server.crt -days 365 -subj "/CN=localhost"
```

If no cert is present the app falls back to HTTP (dev only).

## Test

```bash
python tests/test_settings_store.py
```

## Planned later phases

- Live voice with interruption/barge-in handling and natural backchannels
  ("uh-huh", "yeah", "okay") that don't disrupt listening or reasoning.
- Agent tool calls (device health checks, etc.).
- Automated grading using the configured rubric.
