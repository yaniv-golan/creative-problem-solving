# 60% drop-off at account verification

Shortening the form and adding a progress bar are both **friction** fixes. They assume the user is trying to get through and finding it tedious. At verification, that's usually the wrong model — and it explains why those two didn't move the number.

Verification is different from every other step in your funnel in one crucial way: **it requires the user to leave your product and come back.** That single property generates failure modes the rest of your onboarding doesn't have. A 60% drop there is rarely one problem; it's typically three or four stacked on top of each other, and each needs a different fix.

---

## First: split the 60% before you spend another sprint

You almost certainly have several distinct populations mixed into that number, and they need opposite interventions. A day or two of instrumentation will tell you which one you're actually fighting:

| Bucket | How to detect it | What it means |
|---|---|---|
| **Never received it** | Sent vs. delivered vs. opened rates from your ESP/SMS provider | Deliverability problem, not UX |
| **Received, never opened** | Delivered but no open event | Motivation, timing, or sender/subject problem |
| **Opened, never clicked** | Open without click | Trust or copy problem |
| **Clicked, but failed** | Click event with no verified event | Technical — expired codes, broken session, deep-link failure |
| **Verified later, counted as lost** | Verified events beyond your attribution window | Measurement artifact — your 60% may be overstated |

That last row matters more than people expect. If you're measuring completion within a single session, users who verify from their phone an hour later look like drop-offs. It's not unusual to find 10–15 points of the "loss" is a reporting artifact.

Also segment by email domain (corporate vs. Gmail vs. Outlook), country, and device. Verification drop-off is famously lumpy — one carrier or one corporate mail filter can account for a huge share.

---

## Idea bank

### 1. Stop requiring verification here at all
The highest-leverage move is usually not making the step better — it's **moving or removing it**.

- **Progressive verification.** Let people in unverified. Gate only the actions that genuinely need a verified identity (payment, inviting teammates, exporting data, receiving notifications). Most products verify at signup out of habit, not necessity.
- **Verify on the way out, not the way in.** Let them experience value first. Someone who's configured a workspace will verify; someone who's seen nothing won't.
- **Time-box it instead of blocking.** "You have 7 days to verify" converts far better than a hard wall, and you keep the account either way.
- **Ask what verification is actually for.** If it's bot prevention, a CAPTCHA or device fingerprinting may cost you 2% instead of 60%. If it's deliverability hygiene, real-time email validation at input catches most of it. If it's regulatory, that constrains you — but confirm it actually does before assuming.

### 2. Change the mechanism
- **OTP code instead of a magic link** (or offer both). Links break constantly: they open in a different browser than the one holding the session, they get pre-fetched and consumed by corporate security scanners, they die in in-app webviews.
- **Autofill-compatible codes.** iOS and Android will auto-populate SMS/email OTPs if your message format and input fields are set up correctly. This alone is often worth double-digit gains.
- **Don't force an app switch.** An "Open Mail" button, or better, an inline code field that keeps them on the page.
- **Social/SSO login** as an alternate path — verification comes free with the identity provider.
- **Passkeys** where supported.
- **Fallback channel.** If email fails, offer SMS, and vice versa. Don't make a bad channel the only channel.

### 3. Fix the plumbing (this is where the surprises live)
- **Deliverability audit**: SPF, DKIM, DMARC, dedicated sending IP, sender reputation. If you're on a shared IP with a spammy neighbor, no UX change will save you.
- **Latency.** If the code takes 90 seconds to arrive, users leave. Measure p50 *and* p95 delivery time — the tail is what kills you.
- **Expiry windows.** 5-minute expiry is hostile if delivery takes 2 minutes. Extend it.
- **Session persistence.** If the user clicks the link on a different device, do they land in a working state or a dead end? This is the single most common broken path I'd check first.
- **Typo'd emails.** Real-time validation with a "did you mean gmail.com?" suggestion, plus an easy "change my email" affordance on the verification screen. A meaningful chunk of the 60% may be people who literally cannot receive the message and have no way to fix it.
- **Rendering.** Check the email on dark mode, Outlook, and mobile. Invisible buttons happen.

### 4. Address motivation and trust
- **Say why.** "We're confirming it's you so we can recover your account" beats "Verify your email."
- **Show what's behind the door.** A preview of the configured account, or the value they're one click from.
- **Sender identity.** `noreply@` from an unfamiliar domain reads as phishing. Use a recognizable from-name and domain.
- **Match the moment.** If they signed up on a whim at 11pm, they're not coming back. Timing and re-engagement matter more than copy here.

### 5. Treat drop-off as recoverable, not terminal
This is the most under-used lever. Right now a drop-off is probably a permanent loss. It doesn't have to be.

- **Resend nudges** at +15 min, +24 hr, +3 days, with escalating clarity and a channel switch.
- **Preserve their state** so returning feels like resuming, not restarting.
- **Make the resend button obvious** and don't rate-limit it so aggressively that legitimate retries get blocked.
- **Exit survey / micro-prompt** on the verification screen: "Didn't get it?" with options. Cheap qualitative signal.

### 6. Go look at it
Ten session replays of people who dropped, and five calls with them, will probably tell you the answer in an afternoon. Also: have five colleagues sign up with corporate email addresses on their own phones and watch what happens. Team members test on clean accounts with company Gmail; real users don't.

---

## What I'd do in the first two weeks

1. **Days 1–3** — Instrument the funnel into the five buckets above. Segment by domain, country, device. Run 10 session replays.
2. **Days 3–5** — Deliverability audit and p95 delivery-time measurement. These are cheap and frequently explain 20+ points on their own.
3. **Week 2** — Ship the two highest-confidence fixes regardless of what you find, because they're near-universally positive: **OTP with autofill as an alternative to the link**, and a **resend/re-engagement sequence** to recover drop-offs.
4. **In parallel** — Have the conversation about whether this gate needs to exist at signup at all. That's the change with the biggest ceiling, and it's a product decision, not an optimization.

---

## One caution on the metric

When this improves, watch the downstream numbers, not just the verification rate. Removing or deferring the gate will increase step-completion mechanically while potentially letting through lower-intent or lower-quality accounts. The metric that matters is activated, retained users — not verified ones. Make sure whatever you ship is judged on that.

**The short version:** you've been optimizing the step. The bigger wins are almost certainly in *bypassing* it, *changing the mechanism*, *fixing delivery*, and *recovering the people who drop* — and a few days of segmentation will tell you which of those four is your actual problem.
