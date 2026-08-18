Both things you've tried treat this as a *friction* problem — "the step is too long, so make it feel shorter." But verification drop-off is usually one of three completely different failures, and they need opposite fixes. That's probably why the form and progress bar didn't move it.

## First: split the 60%

Before more ideas, get these four numbers. They'll tell you which of the fixes below is worth building.

- **Never received it.** Email/SMS delivery rate, bounce rate, spam-folder rate — segmented by email domain. Corporate Exchange/Outlook tenants and a few carriers are frequently the whole story.
- **Received but never opened.** Email open rate on the verification message specifically.
- **Opened but didn't complete.** They got the code and still bailed.
- **Never got that far.** They saw "we'll send you a code" and left before requesting it.

Two quick diagnostics that usually give it away:

- **Median time-to-verify.** Under ~60 seconds means delivery is fine and it's a motivation/UX problem. Over 2–3 minutes, or a fat tail, means delivery latency is killing you.
- **Resend rate.** High resends = delivery problem, full stop.

Also segment by traffic source. If you added verification to stop fraud, part of that 60% may be bots doing exactly what you wanted. Real drop-off and fake drop-off look identical in the aggregate funnel.

## Ideas, grouped by what they fix

**Delete or defer the step (biggest lever, usually)**
- Let people into the product unverified, in a limited state, and verify at the first moment it actually matters — inviting a teammate, exporting, connecting a payment method, hitting an admin action. Verification is much easier to ask for after someone has something to lose.
- Magic link that *both* verifies and logs in, so it's one action instead of "get code → return → type code."
- Offer Google/Apple/Microsoft SSO. Those accounts arrive pre-verified and skip the step entirely.
- If you're collecting a phone number purely as a second factor, ask whether you need it at signup at all.

**Fix delivery (cheap, often huge)**
- Audit SPF/DKIM/DMARC and your sending domain reputation. Send transactional mail from a subdomain separate from marketing.
- Put the code **in the subject line**. Most users can verify from the notification without ever opening the email.
- Keep the email nearly plain-text, one button, minimal images and links — heavy HTML templates get filtered.
- Send from a recognizable human-ish address, not `no-reply@`.
- Add provider failover: if the first send isn't confirmed within ~20 seconds, fire through a second provider.
- Add SMS as a fallback offered *after* the email is slow, not as a competing choice up front.

**Kill the context switch (the underrated one)**
The user leaves your tab to check email — often on a different device — and never comes back. That alone can account for most of a 60%.
- Make the "check your email" screen poll, so when they click the link on their phone, the original desktop tab auto-advances.
- Make the emailed link restore full onboarding state, not dump them at a generic login.
- `autocomplete="one-time-code"` on the input, plus the Apple/Android-standard SMS format so the OS autofills it.
- Make the code paste correctly across split input boxes (this is a shockingly common bug).
- Let them edit a mistyped email address *on the verification screen* without restarting onboarding.
- Typo detection on the domain: gmial.com, gmail.co, hotmial.com.

**Recovery (fastest thing to ship)**
- A resume email at ~30 minutes and again at ~24 hours with a one-click link back into the exact step. This doesn't fix the drop-off; it recovers a meaningful slice of it, and you can ship it this week.

**Trust and motivation**
- Say *why* you verify, in one line, at the point of the ask.
- Show what's waiting on the other side rather than just how many steps remain — a progress bar tells people how much work is left, not why to do it.
- Make the email unmistakably yours. Unbranded verification mail reads as phishing.

## What I'd actually do, in order

1. **This week:** instrument the four-way split above, plus code-in-subject-line, OTP autofill, paste handling, and the resume email. All cheap, none require a decision.
2. **Next:** whatever the split points at — deliverability work if it's a delivery problem, polling + state-restoring links if it's a context-switch problem.
3. **The real bet:** defer verification until first sensitive action. That's a product decision with security and abuse implications, so it needs a real conversation, but it's the one that removes the 60% rather than shaving it.

One question that would sharpen this a lot: **why** do you verify at that point — regulatory, fraud, deliverability of later emails, or just convention? If it's convention, option 1 above is likely the whole answer.
