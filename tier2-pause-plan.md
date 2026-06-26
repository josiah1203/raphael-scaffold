# Tier-2 Stub Pause Notes

Calliope does not provide standalone source packages for these domains, so Raphael keeps them paused rather than extending SQLite scaffolds:

- `comments`
- `messaging`
- `links`
- `workflows`
- `registry`
- `environments`
- `analytics`
- `search`

Gateway behavior in `raphael-core` now returns `501 not_implemented` for `/v1/<service>` requests above, with a response message indicating the endpoint is paused pending Calliope parity.

Near-term ownership:

- search concerns should fold into `raphael-audit` / `raphael-graph`
- licensing and billing concerns should fold into `raphael-admin` / `raphael-orgs`
- slice/fork concerns should stay thin wrappers around `raphael-workspaces`
