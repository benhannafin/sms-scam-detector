# Self-review checklist (Stage 10, Part B)

Walk through the live site yourself before tuning (Stage 11). This finds bugs and anything confusing on a fresh read. It can't show whether *other* people misread a result, because you know the design – that's Stage 13 (decision 038).

**Site:** https://sms-scam-detector-ie.azurewebsites.net (open it a minute early – the free plan sleeps).
**Time:** about an hour.
**Do it twice:** once on your **phone**, once on your **laptop**. Each run uses about 9 checks, under the 20-per-hour limit.
**All messages below are made up.** Don't use real texts (decision 025).

Note anything broken, confusing, ugly or slow in the "Notes" column. Use the "Problem log" at the end for anything worth fixing.

---

## 1. Tasks

For each task, check the result matches the "Expect" column, then answer the questions. ✓ or ✗ in each column, or a short note.

| # | Do this | Expect |
| --- | --- | --- |
| 1 | Press the **Parcel fee** example key, then **Check message** | Likely scam (red), about 86%, reasons include a phone number |
| 2 | Press **Prize offer**, then **Check message** | Marketing spam (amber), about 95% |
| 3 | Press **Friend running late**, then **Check message** | Looks legitimate (blue), "No common scam signs found" |
| 4 | Paste: `Your account is locked, verify now at account-verify-login.com` | Unsure (purple), "64%, too low to rate", link and "account" as reasons |
| 5 | Paste: `Hi mum, my phone is broken, this is my new number, can you send me money` | Looks legitimate, but with **Signs to be careful of**: "new", "send" highlighted |
| 6 | Paste: `xyzzy qwertyuiop` | Unsure, "We didn't recognise enough of this message to rate it.", no meter |
| 7 | Clear the box and press **Check message** | Inline error "The box is empty…", red ring, no pop-up |
| 8 | Paste any text over 1,000 characters (copy a paragraph several times) | Counter goes over 1000; "That message is too long…" error; your text is kept |
| 9 | On any result, press **Check another message** (both the top key and the bottom one) | Back to the home view, box empty, cursor in the box |

| # | Result as expected? | Verdict clear at a glance? | Reasons make sense? | Noticed the "can be wrong" reminder? | Notes (phone) | Notes (laptop) |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |
| 6 | | | | | | |
| 7 | | — | — | — | | |
| 8 | | — | — | — | | |
| 9 | | — | — | — | | |

**Task 5 is the important one.** Read the result as if you'd never seen the app: does "Looks legitimate" with "Signs to be careful of" tell you clearly enough not to send money? Write down your honest first impression.

## 2. Look and feel

| Check | ✓ / ✗ | Notes |
| --- | --- | --- |
| Keys look pressable; panels look sunken; nothing that isn't a button looks like one | | |
| Pressing a key sinks it straight away (on press, not on release) | | |
| The header scrolls away; nothing covers content when you scroll | | |
| Mono labels are readable; nothing looks cramped or too small | | |
| The coral, charcoal and grey keys feel consistent | | |
| On the phone: no sideways scrolling, keys easy to tap, text readable without zooming | | |
| The result appears smoothly, without a jump | | |
| Highlights in "Your message" are easy to spot, and the right words are highlighted | | |
| Wording: nothing sounds alarming, vague or like a guarantee; "safe" never appears | | |

## 3. Keyboard and accessibility (laptop)

| Check | ✓ / ✗ | Notes |
| --- | --- | --- |
| Tab through the whole flow: every key reachable, focus ring always visible | | |
| Enter or Space presses the focused key | | |
| After a result, the next Tab starts somewhere sensible | | |
| Zoom the browser to 200% (Ctrl and +): still usable, nothing cut off | | |

## 4. Anything else

Did anything feel slow, surprising or missing? Is there anything you'd be embarrassed to show your lecturer?

---

## Problem log

Rate each problem: **critical** (would misread a result or do something risky), **serious** (struggled or confused), **minor** (cosmetic). Critical and serious problems get fixed in Stage 10; minor ones are logged for later.

| # | Where | What happened | Severity | Fix idea |
| --- | --- | --- | --- | --- |
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
