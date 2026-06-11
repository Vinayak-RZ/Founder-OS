# Knowledge vault (local)

Per-world documentation lives here. Each sub-world gets a folder (e.g. `stamped-energy/`) with facet subfolders from its template.

## Startup template folders

- `company-research/` — competitors, company intel
- `leads/` — prospect lists and CRM notes
- `industry/` — industry analysis
- `market/` — market research
- `product-solution/` — product & solution docs
- `clients/` — ICP and client insights
- `gtm/`, `sales/` — go-to-market

## Workflow

1. Clone your docs repo locally (e.g. Stamped Energy documentation)
2. In **Worlds** → select world → **Link & ingest** with the clone path
3. Or copy files into facet folders and click **Re-ingest vault**
4. Query via **Vault** specialist or the vault search box

Vector domains: `vault_company`, `vault_leads`, `vault_industry`, `vault_product`, `vault_clients`.

Override root path: `KNOWLEDGE_VAULT_ROOT` in `.env`.
