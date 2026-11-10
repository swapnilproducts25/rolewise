# Rolewise

**A job-search assistant that runs inside Claude.** Each morning Rolewise finds jobs that fit you, tailors your
CV, drafts the cover letter and form answers, and emails you a short briefing with buttons. You decide what to
apply for and you click Submit. It works from the Claude website and the Claude phone app, and suits any profession.

Free and open source. Your data stays in your own accounts.

## What it does
- **Finds jobs**: company career pages for the companies you pick, your LinkedIn job-alert emails, and job boards.
  Each role is scored for fit with a one-line reason; closed postings and roles you already applied to are dropped.
- **One-tap Inbox**: a private page with your ready jobs and **Applied / Later / Skip / Pause** buttons, linked from
  every briefing. No forms, no emails to yourself.
- **Prepares every good match without waiting for you**: a tailored CV (only facts from your own CV, in one of three
  clean styles), a cover letter, and answers to the form's own questions, ready in a queue.
- **A queue that keeps moving**: about 10 ready jobs per location you target, newest postings first (early
  applications get read first). Jobs you leave alone for 3 weeks retire themselves to make room.
- **Two agents for every CV**: a writer tailors it, and a separate reviewer checks it against your own CV and the job
  (true facts only, nothing important dropped, no vague or nit-picky bullets). A weak tailoring is never used; your
  own CV goes out instead.
- **Ranks jobs your way**: fit score includes your preferred locations, in order, and the pay on offer.
- **Drafts cover letters and form answers** in plain, human language.
- **Finds warm referrals** in your own LinkedIn connections at the companies you apply to (optional data import),
  and drafts the message for you to send.
- **Tracks every application** by reading your Gmail for confirmations, rejections and interview invites.
- **Prepares you for interviews** and helps afterwards with debriefs, follow-ups and offer negotiation.
- **Coaches you** each week: what's working and what to change.
- Optional **Rolewise Fill** Chrome add-on (laptop): a queue of ready jobs; one click opens the form and fills it
  (CV, cover letter, answers, salary band, dropdowns). Works on Greenhouse, Lever, Ashby, Workable, SmartRecruiters,
  Homerun, LinkedIn Easy Apply (step by step, you click Next) and Workday, and on any other form with
  **Fill this page** (Alt+Shift+F). You check the form and click Submit. Skip, Pause and interview Debrief notes are
  one click in the add-on. Setup needs Chrome, Python and Git on your laptop and one command, `python scripts/setup_fill.py` (about 10 minutes).
  Optional: your own Anthropic API key in the add-on's settings adds **✨ Draft / Redraft / Shorter** under unusual
  questions, written into the field from your CV and the job description (a fraction of a cent per answer).

## What you need
- A Claude **Pro or Max** plan (claude.ai).
- A **Gmail** address.
- A free **GitHub** account (for your private copy).

## Get started (about 20 minutes)
Click **Use this template** → **Create a new repository**, choose **Private**, then follow
**[START-HERE.md](START-HERE.md)**.

## Ground rules Rolewise follows
- It never submits an application, sends an email or messages anyone without your yes. The one exception is your
  own daily briefing.
- It never invents experience: every CV line and answer traces back to your own CV and answers.
- It never enters passwords, codes or payment details.
- It doesn't automate LinkedIn: no scraping, no automated messages or connection requests.
- It flags likely scams (fees, crypto, ID requests before an interview, chat-app-only "recruiters").

## Your data and privacy
Rolewise has no servers and no account with us. Your CV, answers and job tracker live in **your own private
GitHub copy** and **your own Gmail and Google Drive**. Claude (Anthropic) processes them to do the work, under your
Claude account's terms. Nobody else, including the maker of Rolewise, can see your copy.

## Please note
- **Use at your own risk.** Rolewise is provided as is, with no warranty (see [LICENSE](LICENSE)). AI can make
  mistakes: **check every CV, letter and form before you submit it.** You are responsible for what you send.
- Follow the terms of the sites you use (LinkedIn, job boards, employer portals).
- Rolewise isn't affiliated with Anthropic, LinkedIn, GitHub or any employer or job site.
- It doesn't give legal, immigration, tax or financial advice. Salary suggestions are market estimates, not advice.

## Feedback and problems
Use **[Issues → New issue](https://github.com/swapnilproducts25/rolewise/issues/new/choose)**: "Something went wrong" or "Feedback". Please don't paste
your CV, email address, phone number or other personal details there. Issues are public.
