# dashboard.config.json — per-project content schema

This file lives in the **target project root** (or `.claude/dashboard.config.json`),
NOT in the skill folder. It is the only thing you edit per project — it supplies the
"내용" while the dashboard UI stays frozen. JSON, no comments (zero-dependency parse).

If the file is absent, the skill auto-derives a minimal board from discovered
worklists, but labels will be raw codes — write this file for a real board.

## Top-level fields

| field | type | required | meaning |
|---|---|---|---|
| `projectName` | string | yes | Shown in the tree root and summary. |
| `lanes` | Lane[] | yes | Swimlanes, in display order. |
| `workPackages` | WorkPackage[] | yes | The cards placed on Product lanes. |
| `metaItems` | MetaItem[] | no | Candidate/meta cards on the Meta lane. |
| `metaSprint` | MetaSprint \| null | no | A single highlighted meta card. |
| `architecturalHcps` | ArchHcp[] | no | Forever-pending boundary reminders on Control. |
| `vocabulary` | object | no | `CODE → 친근한 라벨` overrides (e.g. HCP plain names). |

### Lane
| field | type | meaning |
|---|---|---|
| `id` | string | Stable id; work-packages reference it via `laneId`. |
| `label` | string | Lane heading. |
| `parent` | `"Product"` \| `"Meta"` \| `"Control"` | Grouping. Product lanes get the phase-status suffix (· ACTIVE / · CLOSED …) and feed the summary. Exactly one `Control` lane is expected (decision log + queue land there). |
| `outcome` | string (optional) | One-line "what this phase is for", shown as the lane subtitle. |

### WorkPackage
| field | type | meaning |
|---|---|---|
| `laneId` | string | Which lane this card sits on. |
| `wp` | string | Primary code, e.g. `WP-001`. Matched against worklists / decisions / commits. |
| `legacy` | string (optional) | Alias code, e.g. `F-001`. Matched too; shown as `F-001 / WP-001`. Set equal to `wp` if there's no alias. |
| `title` | string | Developer-facing title. |
| `plainTitle` | string (optional) | Director-facing headline (큰 글씨). A `director_one_liner` in the spec frontmatter overrides this. |

Column placement is **automatic** from canonical signals — you do not set it.
Closure (D-NNN) → Done; all worklist tasks committed, no closure → Verification;
commits in progress → Development; worklist written, no commits → Plan; else Backlog.

### MetaItem
`{ ip, legacy?, title, plainTitle?, nextAction?, description? }` — rendered as Backlog
cards on the Meta lane (candidates).

### MetaSprint
`{ code, title, plainTitle?, nextAction?, lane?, column?, description? }` — one
highlighted card (defaults: lane `meta`, column `Development`).

### ArchHcp
`{ code, title, anchor, reason, status }` where `status` is `"out-of-cycle"` (absolute
zero this cycle) or `"future"` (trigger TBD). Rendered as Backlog HCP reminders.

## Where the data comes from (npi-docs adapter)

| signal | source file |
|---|---|
| decision log (D-NNN), closures | `meta/decisions.md` |
| pending decisions / HCP gates (DQ-NNN) | `meta/decision-queue.md` |
| work-package task tables (T-NNN) | `ai-npi/WP-*_Worklist.md` (or legacy `F-*_NPI_Worklist.md`) |
| progress (which T-NNN are done) | `git log` cross-referenced with worklists |
| re-review flags | `meta/re-review.md` |
| spec one-liners | `ai-npi/*.md` `director_one_liner` frontmatter |
| last-commit chip + doc links | `git log` + repo markdown scan |

A project whose status lives somewhere else needs a new adapter under
`core/adapters/` returning the same shape; the config and UI are unchanged.
