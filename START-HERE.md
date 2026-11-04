# Rolewise: start here

Rolewise is a job-search assistant that runs inside Claude. Each morning it finds jobs that fit you, tailors your
CV, prepares the application and emails you a short briefing with buttons. It works from the Claude website and the
Claude phone app. Nothing to install.

Setup takes about 30 minutes. Have your CV (PDF or Word) to hand.

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
   type **`/onboard`**. Rolewise reads your CV, asks about 10 short questions (roles, places, salary floor, notice
   period...), shows you three CV styles and sets up your daily run.

You'll get your first briefing the same day.

## Every day (5–10 minutes, phone is fine)
1. Read the **Rolewise briefing** email.
2. Tap the buttons, such as **Prepare** or **Skip**, or answer a question. A tap opens an email to yourself; hit send.
   Rolewise reads it on the next run.
3. To apply, tap **Open job** and upload the CV from the **CV** link. The answers to paste are in the card.
   You always click Submit yourself.

Change anything, any time, in plain words: open a session in claude.ai/code and type `/profile` ("add Berlin",
"my notice is now 2 weeks", "use the compact CV"). Also handy: `/prep <company>` before an interview,
`/debrief <company>` after one, `/coach` for a weekly review.

**Optional, if you have a laptop with Chrome:** the **Rolewise Fill** add-on fills application forms for you.
Ask Rolewise "set up Rolewise Fill" and it walks you through it in about 5 minutes.

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
