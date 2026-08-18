Before more ideas: the two things you tried are both cosmetic changes to a screen. Neither touches delivery, timing, or motive — so their failure tells you almost nothing, and it's likely the 60% is several different failures stacked. Worth splitting them first, because the fixes don't overlap.

(I'm assuming this is an emailed link or a one-time code. If it's document KYC — ID upload, selfie — 60% is near industry-normal and the leverage moves to capture quality and retry handling instead.)

**Four candidate causes**

1. *They never got it.* Spam/promotions placement, unaligned sending domain, SMS carrier filtering, typo'd addresses.
2. *They got it and couldn't finish.* On mobile, switching to the mail app and back is where sessions die — deep link opens a different browser without the cookie, code expired, requesting a second code invalidated the first.
3. *They got it and chose not to.* No value delivered yet, or the message reads as phishing.
4. *Some of them shouldn't be counted.* Bots, duplicate signups, people who already have an account.

**The cheapest test that splits all four:** pull one week of your email/SMS provider logs and join them to funnel events at the individual level — sent, delivered, opened, clicked, completed, returned-within-7-days. That single join separates 1 from 2 from 3, and a dedupe pass against existing accounts sizes 4. About a day of work. Everything below is cheaper to choose after it.

---

### Occupy the wait instead of shortening it

The 30–90 seconds between requesting a code and it arriving is the only moment in the whole lifecycle when the user is idle and paying attention. Put the first real setup question there, or a live preview built from what they've already entered. The abandon decision changes from "I'm blocked" to "I'm interrupted mid-task," and people walk away from being blocked far more readily than from being interrupted.
- What has to be true: they're still on a screen you control, not already in the mail app.
- Cost: you now have to persist whatever they entered when the code never arrives.

### Prove yourself to them before asking them to prove themselves

Show the exact sender address and a two-word phrase that will appear in the message, on the page they're already looking at. Someone who half-suspects you have no way to tell your message from an attack — and a suspicion abandon is invisible in your analytics because it looks identical to disinterest.
- What has to be true: some meaningful slice of the 60% is distrust rather than absence.
- Cost: essentially none. Do this one regardless of what the diagnosis says.

### Temporary identifier, reconciled afterwards

Grant a fully working account under a system-issued placeholder with no confirmed address, and run confirmation as a background job that merges into the record when it lands. This is the shape emergency intake uses — service delivery and identity resolution as two separate pipelines rather than one gate. The real work is the merge machinery, not the screen.
- What has to be true: nothing available in the unconfirmed state is expensive to reverse.
- Cost: duplicate records and support load when merges go wrong. Someone has to own dedupe permanently.

### Bind the requirement to the action, not the account

Nothing needs proving at signup. Attach it to the first action that's costly to reverse — inviting a teammate, exporting, paying, sending on the user's behalf. Most people reach that days later in a much higher-intent session, and a large fraction never reach it at all.
- What has to be true: you can enumerate the risky actions, and compliance doesn't force the check at account creation.
- Cost: gates scattered through the product instead of one, plus a growing population of unconfirmed accounts to clean up.
- Who runs it: this is as much a security/compliance decision as a product one. If you don't own that rule, this is the conversation, not the ticket.

### Treat abandonment as a pause, not an exit

Everything you have is built as though the person left permanently. Make returning trivial for two weeks: a link that restores exact state, sent at the same hour of day they originally signed up, on a second channel if the first went silent.
- What has to be true: you keep partial state, and you have a second way to reach them.
- Cost: recovers people slowly and looks bad on any same-session dashboard. You have to be willing to be judged on a 14-day number.

---

**Cut, and why**

- Shorter code, longer expiry, bigger button — same family as what you already tried. No screen-level change fixes a message that didn't arrive.
- Dropping the check entirely — breaks the first time you send anything on a user's behalf. The disciplined version is binding it to the action.
- Paying people to complete it (credits, discount) — buys something they'd do free if it worked, and hides the broken mechanic.
- Human outreach to abandoners — genuinely works, doesn't scale, and only pays if cause 3 dominates.
- Inheriting the proof instead of collecting it (passkey, SSO, a vouch from the inviter) — deletes the whole undelivered-message failure class, and it's the one thing here you can buy rather than build. Cut only because it does nothing for the cold, unsponsored, generic-address signup, which is probably the segment you're losing. Reinstate it if the diagnosis says otherwise.

**What would change my ranking**

- The delivered/opened split. Under ~95% delivered and this is a deliverability project, not a design one.
- Whether 60% is new or always was. A number that moved last quarter has a cause you can find; one that's always been 60% is structural.
- Whether the check is required at account creation for compliance. If so, "bind it to the action" is off the table and the first two ideas carry the weight.
