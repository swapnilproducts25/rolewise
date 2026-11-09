# CV principles (shared by the cv-writer and cv-reviewer agents)

The user is a **seasoned senior PM**. A tailored CV must read as the same senior person, aimed at this role,
never a thinner or more junior version of the master CV. Changes must be meaningful, never dilute depth, and never
turn bullets vague or tactical just to look tailored.

## 1. The master CV is the default
- `profile/master-cv.yaml` is already the best general version. **"No change" is a good outcome**; most roles need
  only a sharper summary angle and, at most, two or three meaningful moves.
- Every change needs a reason that names a specific JD requirement. "To mirror the JD" alone is not a reason.
- Never change things to show effort. If you can't say why a change makes this CV stronger *for this role*, don't make it.

## 2. Anchors that every version keeps
The user's `anchors` list in `profile/master-cv.yaml` (e.g. years and companies, the flagship result, AI-native
building; no list → the master summary's key facts). The summary may re-angle them for the role, but **never drops one**. Never hide a bullet marked
`flagship: true`.

## 3. Summary and headline
- Headline: the target level and, at most, one focus area ("Senior Product Manager · Growth"). No keyword chains.
- Summary (4 lines, ~420 characters): who they are (level, years, companies), 2 proof points chosen for this role
  from the strongest evidence (prefer recent and large-scale), how they work (strategic, experiment-led,
  AI-native), and nothing else. Lead with the most senior, most recent proof, not an old early-career number.

## 4. Bullets: strategic altitude
Each bullet = **what was decided or built + why it mattered (scope, users, money, adoption) + the result**.
- **Too vague** (rewrite or leave alone): no outcome or no scope: "drive sustained ROI gains", "improved
  alignment", "enabling data-driven decision-making", "reducing escalations" with nothing to size it.
- **Too granular / tactical** (lift it up a level): a list of micro-metrics or UI details ("+1.5%, +1.1%…"),
  a single meeting, a single badge. Keep the one number that matters and say what it changed for the business.
- Strong verbs of ownership and judgement: set, decided, launched, built, scaled, killed, aligned X and Y on Z.
- Keep every number exactly as in the master. Never add a number, tool, title, date or claim (CLAUDE.md rule 2).
- Length: each bullet 2 lines or fewer (≤ 210 characters without `**`); bold one lead phrase and the key result.

## 5. AI-native, where it is true
Show AI-native skill and inclination wherever the facts support it: AI products built end to end, AI tools used to
build and ship (Claude Code, Cursor), LLM feature design, AI strategy. Bring it forward for AI-heavy roles; keep it
visible for every role. Never claim AI work at an employer that the master CV or story bank doesn't show.

## 6. Tailoring moves, in order of preference
1. Summary angle (always allowed, keeps the anchors).
2. Reorder bullets inside a role so the most relevant is first, **only in the 3 most recent roles**, and only if
   the moved bullet is genuinely more relevant than the current first one.
3. Reword a bullet to surface an aspect the JD cares about that the master phrasing hides (same facts).
4. Skills line: reorder so the role's core skills come first (only skills already evidenced).
5. Hide a bullet only if the CV would otherwise exceed 2 pages; hide oldest and least relevant first; never a flagship.
