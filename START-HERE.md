# Rolewise: start here

Rolewise is a job-search assistant that runs inside Claude. Each morning it finds jobs that fit you, tailors your
CV, prepares the application and emails you a short briefing with buttons. It works from the Claude website and the
Claude phone app. Nothing to install.

Setup takes about 20 minutes. Have your CV (PDF or Word) to hand.

## What you need
- A Claude **Pro or Max** plan (claude.ai).
- A **Gmail** address: your briefing goes there.
- A free **GitHub** account (github.com/signup). It's where your private copy of Rolewise lives. You only use it
  during setup.

## Setup
1. **Make your own private copy.** Open github.com/swapnilproducts25/rolewise and click **Use this template** →
   **Create a new repository**. Name it `rolewise`, choose **Private**, and click **Create repository**.
2. **Connect Claude to GitHub and Google.** Go to claude.ai → Settings → **Connectors** and turn on **Gmail** and
   **Google Drive**. Then go to **claude.ai/code** and connect GitHub when it asks. Give it access to your `rolewise` repository.
3. **Start.** At claude.ai/code (or the **Code** tab in the Claude phone app), pick your `rolewise` repository and
   type **`/onboard`**. Rolewise reads your CV, asks about 8 quick questions, mostly taps (roles, places, salary
   floor, notice period...), shows you a preview of your CV and sets up your daily run.

You'll get your first briefing the same day.

## Every day (10–20 minutes)
1. Read the **Rolewise briefing** email (phone is fine). Rolewise has already prepared the good matches: a tailored
   CV, a cover letter and form answers for each. Buttons let you skip one, pause Rolewise, or answer a question; a tap
   opens an email to yourself, hit send, and the next run acts on it.
2. Apply to the **New** ones first: postings from the last 3 days, when early applications get read first. The queue
   keeps about 10 ready jobs per location; ones you don't act on for 3 weeks retire themselves.
3. To apply: with the add-on (laptop), click a job in its queue, check the filled form and click Submit. Without it,
   tap **Open job**, upload the CV from the **CV** link and paste the answers from the card.
4. After an interview, jot rough notes (the add-on's **Debrief** button, or `/debrief <company>`).

Change anything, any time, in plain words: open a session in claude.ai/code and type `/profile` ("add Berlin",
"my notice is now 2 weeks", "use the compact CV"). Also handy: `/prep <company>` before an interview,
`/debrief <company>` after one, `/coach` for a weekly review.

**Optional, if you have a laptop with Chrome:** the **Rolewise Fill** add-on fills application forms for you, including
LinkedIn Easy Apply (step by step) and any other form via **Fill this page**. It needs Chrome, Python and Git on that
laptop (about 10 minutes). Ask Rolewise
"set up Rolewise Fill" and it walks you through it, including the small local helper that makes Skip, Pause and
Debrief one click. Add your own Anthropic API key in its settings for **✨ Draft** answers inside forms.

**Optional, after your first week:** import your LinkedIn data (LinkedIn → Settings → Data privacy → Get a copy of your data).
Rolewise uses your connections to suggest referrals, your past applications so nothing is suggested twice, and
shows where your LinkedIn profile and CV disagree.

## What Rolewise never does
- Submit an application, send an email or message anyone without your yes.
- Invent anything: every CV line and answer comes from your own CV and answers.
- Enter passwords, codes or payment details.
- Message people or send connection requests on LinkedIn for you.

## Your data
Your CV, answers and job tracker live in your own **private** GitHub copy and your own Gmail/Drive. Claude processes
them to do the work. Nobody else can see them, including the maker of Rolewise. Check every CV, letter and form before you submit:
AI can make mistakes, and you're responsible for what you send (see README).

## Feedback
On the Rolewise GitHub page, go to **Issues → New issue**. Pick **Feedback** (2 minutes; once a week helps a lot) or
**Something went wrong** (a screenshot is perfect). Issues are public, so leave out personal details.
