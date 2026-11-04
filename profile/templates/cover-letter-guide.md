# Cover letter guide

**Approved sample: `profile/cover-letter-sample.md`.** Until the user approves a letter of their own, use the shape below.
Once they approve one ("this is good, use it as the model"), save it as the sample and note what they liked here.

Write a cover letter whenever an application asks for one or offers an optional upload or field for one. Save it to
`applications/<id>/cover-letter.md`; `scripts/build_cover_letter.py <id>` checks it and builds the .docx.

## Voice
- A confident, professional letter in the user's own natural voice: specific and achievement-led, not boilerplate.
- Sentences mostly 12–25 words, a few short ones, none over about 35. 300–450 words in five or six paragraphs.
  Formal greeting and sign-off. No headings, bullets or bold.
- Pitch it at the user's level and field: a nurse writes about patients, wards and care quality; an engineer about
  systems and reliability; a sales lead about accounts and revenue. Use the words people in that job use.

## Shape
1. **Warm opening (2–3 sentences).** "I am excited to apply for <role> at <company>." Then one line tying the
   user's strongest relevant experience to what this team does, and their years of experience.
2. **One paragraph per main employer or chapter of the CV**, most relevant first and longest. Each says the
   high-level outcome and the key things the user did, with one or two results from `master-cv.yaml` (exact numbers).
   No granular detail (screens, colours, team in-jokes, failed attempts, baselines the CV doesn't state).
3. **Optional: side projects, study or volunteering**, only when they support this role, introduced in plain words
   ("I built X, a ... for ...").
4. **Close (2 sentences).** Practical points the employer needs (right to work, notice, relocation, from
   `answers.yaml`), then one confident line about what the user would help the team achieve.
- Map 3–4 must-haves from the job description to evidence. Use the JD's own words where truthful.
- Facts come only from `master-cv.yaml`, `story-bank.md` or the JD. Check durations and each number's scope.

## Never use (signs of AI writing)
- **Words:** delve, tapestry, testament, pivotal, underscore, crucial, intricate, meticulous(ly), vibrant, landscape
  (abstract), interplay, garner, bolster, enhance, foster, fostering, leverage, multifaceted, showcase, highlighting,
  emphasizing, align with, resonate, seamless, robust, dynamic, passionate, thrilled, synergy, spearhead,
  cutting-edge, game-changer, unwavering, invaluable, "boasts", sentence-initial "Additionally", "Moreover", "Furthermore".
- **Puffery:** "stands as", "serves as", "is a testament to", "plays a pivotal/vital/key role", "setting the stage for",
  "evolving landscape", "renowned", "groundbreaking", "commitment to excellence".
- **Patterns:** trailing "-ing" clauses ("..., ensuring X"); "not just X, but Y"; lists of three adjectives; em dashes;
  vague attributions; "serves as/represents" instead of "is/has"; synonym-swapping; generic praise of the company.
- **Chatbot residue:** placeholders, "[Company]", "I hope this finds you well", hedging, curly quotes, emoji, title case.

## Before saving
- Read it aloud; rewrite any sentence that sounds like a press release.
- Zero hits for the banned words above and for "—".
- Every claim traces to `master-cv.yaml`, `story-bank.md` or the JD.
