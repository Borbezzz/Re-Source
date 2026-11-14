# Linkup setup for Re-Source

## Installed

The project contains all six skills from
[Linkup for Agents](https://github.com/LinkupPlatform/linkup-for-agents), including
their bundled references, in `.agents/skills/`:

| Skill | Use |
| --- | --- |
| `linkup-search` | Discover sources, verify facts, and retrieve structured evidence. |
| `linkup-fetch` | Read a known URL as Markdown or typed JSON. |
| `linkup-research` | Explicitly requested, extensive investigations that can take minutes. |
| `linkup-tasks` | Run up to 100 search, fetch or research jobs in an async batch. |
| `linkup-extract` | Extract many records from listing pages; requires closed-beta access. |
| `linkup-workflow` | Design a sequence of Linkup calls and downstream handoffs. |

The skills are instructions for coding agents. The product's server-side discovery
adapter described in `PRD.md` still needs to be implemented against its canonical
contracts. Skill installation alone does not enable live discovery in the app.

## Activate and authenticate

Open this repository checkout in your coding agent. Codex discovers project skills
under `.agents/skills/`; they are available on the next turn. If a session does not
pick them up, start a new session in this checkout. Agents reading `AGENTS.md`
(including Claude Code through `CLAUDE.md`) can open the matching `SKILL.md` directly.
For example: "Use linkup-search to find supplier evidence and preserve source URLs."

Create an API key in your [Linkup account](https://app.linkup.so). Store it in an
ignored local file, or supply `LINKUP_API_KEY` through your process environment:

```sh
cp -n .env.example .env
```

Edit `.env` locally to populate `LINKUP_API_KEY`. Load this trusted local file in the
terminal that will make calls:

```sh
set -a
. ./.env
set +a
```

An agent started elsewhere may not inherit this terminal's environment. Make the
key available to the agent's actual execution environment before asking for a live
call. Keep it out of prompts, commits, logs and frontend bundles. `.env` and local
variants are ignored; `.env.example` is intentionally tracked.

These skills support direct HTTPS calls, so no SDK dependency or MCP server is
required. If a Linkup MCP tool is already available, follow the skill's MCP route.
Otherwise use REST with `Authorization: Bearer $LINKUP_API_KEY`.

## Live smoke check

Run this from the repository root after loading the key. It performs one billed
standard search when successful, and returns source URLs/snippets:

```sh
(
  : "${LINKUP_API_KEY:?Set LINKUP_API_KEY locally before running this check}"
  curl --fail-with-body --silent --show-error --max-time 60 \
    --request POST https://api.linkup.so/v1/search \
    --header "Authorization: Bearer $LINKUP_API_KEY" \
    --header 'Content-Type: application/json' \
    --data '{"q":"Find the official UK Civil Aviation Authority page explaining UK Part-145 maintenance organisation approval. Return source URLs.","depth":"standard","outputType":"searchResults"}'
)
```

Expect a successful JSON response with a nonempty `results` array. Authentication,
credits, permissions and network errors must be resolved before reporting live
access as verified. An empty result is not evidence that a supplier or approval
does not exist.

Verified on 2026-11-14 with the request above: HTTP 200, 20 results, including the
CAA's official Part-145 approval pages. The key was loaded from a user-provided
local document and configured in the ignored local `.env` with owner-only file
permissions. No credential is included in this branch; each new checkout needs its
own local configuration. This verifies Search connectivity, not access to every
endpoint or the product's future runtime adapter.

The REST field is **`q`**, as specified in the
[current Search endpoint reference](https://docs.linkup.so/pages/documentation/endpoints/search/reference).
Some overview examples in the upstream context pack use `query`; use the endpoint
reference and the skill's REST examples when constructing actual requests.

## Applying Linkup to Re-Source

Follow the PRD's evidence, applicability and provenance requirements:

- Use Search for supplier and risk discovery. Use `deep` when discovering a URL
  and then scraping it depends on the discovery result; use Fetch for known URLs.
- For machine-consumed fields, use Search's `outputType: "structured"` with
  `structuredOutputSchema`, or Fetch's `schema` with optional `instructions`.
- Preserve original source URLs, observation times and the provenance required by
  the product contract. Missing or uncertain evidence remains missing or uncertain.
- Use the smallest capable endpoint. Restrict domains only when the exact target
  domains are known; express time windows in query text instead of date filters.
- Make production calls in the backend. On unavailable access, retain the seeded
  connector with the same contract and label its data origin as required by the PRD.

## Provenance and updates

Installed from `LinkupPlatform/linkup-for-agents` at commit
`de40e04c39f6740bb4f70b00f2ef3ce04b6b88bc` on 2026-11-14. The six skill folders and
their references are unchanged upstream copies. The upstream MIT license is kept
at `.agents/LINKUP-LICENSE`.

The full pack was used because the separate `LinkupPlatform/skills` registry at
installation time contained five skills and omitted `linkup-tasks`.

For an update, create a branch, review the full pack's `AGENTS.md` and skill changes,
then replace these six folders together from a reviewed upstream commit. Update
this revision and retain the license. Bundled `references/` files are generated
upstream; make upstream content changes in `knowledge/` or `workflows/` and use
its sync script rather than hand-editing the installed references.
