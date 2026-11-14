# UI design spec

The approved design for the web UI (Stage 8; restyled in Stage 10, see decision 039). Desktop-first, then adapts to phone widths. Style: **intense neumorphism (soft UI) with a hardware synth feel**, inspired by portable synthesizers such as Teenage Engineering's OP-1 (inspiration only – no logos, names or product shapes are copied). Apple-style interaction principles. Build the Flask templates and CSS to match this spec.

---

## 1. Design principles

1. **One surface material, like a device body.** The page background, cards and boxes share one cool grey. Shapes come from a light shadow (top-left) and a dark shadow (bottom-right), deep enough to read as physical. Keys are the exception: they have a lit face (a soft gradient) in light grey, coral (main action) or charcoal (navigation), like synth keys.
2. **One physical rule, used everywhere:**
   - **Raised** = something you can press (buttons, links styled as buttons, example chips).
   - **Sunken** (inset shadow) = something you type into, or information to read (text box, message panel, reasons, notices, progress tracks).
   - **Flat** = plain text and headings.
   Never make non-interactive content raised – it looks clickable.
3. **Instant response.** Buttons react on press (pointer-down), not on release: raised → sunken + scale 0.98, 120 ms.
4. **Four kinds of feedback:** status ("Checking your message…"), completion (the result), warning (the verdict), error (inline under the text box – never a pop-up, and the user's text is kept).
5. **Never say "safe".** Every result shows the "can be wrong" reminder.
6. **Accessible by default.** Text contrast ≥ 4.5:1, visible focus ring, touch targets ≥ 44 px, and it respects the user's reduced-motion and high-contrast settings. (The header is no longer translucent, so reduced transparency needs no special rule.)
7. **Hardware feel without fake hardware.** The synth look comes from keys, deep panels, the LED meter and mono panel labels. No decorative knobs, screws or grilles: anything raised must be pressable (rule 2).

## 2. Design tokens

Put these in one CSS file (e.g. `app/web/static/css/styles.css`) as custom properties.

```css
:root {
  /* Surface */
  --base: #e3e5e8;                /* cool aluminium grey */
  --shadow-dark: #b3b8bf;
  --shadow-light: #ffffff;
  --track: #d0d4d9;               /* meter and progress-bar tracks */

  /* Keys */
  --key-face: linear-gradient(145deg, #f6f7f9, #dcdfe3);   /* light keys (examples) */
  --key-dark: #2e3238;            /* navigation keys and logo */
  --on-key-dark: #ffffff;

  /* Text */
  --ink: #1f2328;                 /* headings, body */
  --ink-2: #353a40;               /* secondary body */
  --ink-3: #4f555c;               /* muted labels */
  --link: #a3402a;
  --link-hover: #7d2f1e;

  /* Accent */
  --accent: #e17055;
  --accent-face: linear-gradient(145deg, #ea8268, #d9634a);  /* main action keys */
  --on-accent: #2a140e;           /* text on accent: near-black (white fails contrast) */
  --focus: #a3402a;               /* focus ring: the accent is under 3:1 on the base */

  /* Results */
  --scam-ink: #9f1d14;  --scam-fill: #c0392b;  --scam-mark: #f8cdc6;  --scam-mark-ink: #7a1a11;
  --spam-ink: #8a4b08;  --spam-fill: #d68910;  --spam-mark: #fbe2b0;  --spam-mark-ink: #6b3a06;
  --legit-ink: #2f4f7f; --legit-fill: #4a6fa5; --legit-mark: #d6e2f3; --legit-mark-ink: #1f3657;
  --unsure-ink: #55468a;--unsure-fill: #7a6bb0;--unsure-mark: #e2dcf3;--unsure-mark-ink: #3d3266;
  --error: #9f1d14;

  /* Shadows – deep, so keys read as physical */
  --raised-lg: 22px 22px 44px var(--shadow-dark), -22px -22px 44px var(--shadow-light);  /* main cards */
  --raised-md: 12px 12px 24px var(--shadow-dark), -12px -12px 24px var(--shadow-light);  /* main action keys */
  --raised-sm: 7px 7px 14px var(--shadow-dark), -7px -7px 14px var(--shadow-light);      /* example and nav keys */
  --inset-md: inset 9px 9px 18px var(--shadow-dark), inset -9px -9px 18px var(--shadow-light); /* text box, message, pressed */
  --inset-sm: inset 6px 6px 12px var(--shadow-dark), inset -6px -6px 12px var(--shadow-light); /* reasons, notices, tracks */

  /* Shape */
  --radius-card: 1.75rem;
  --radius-box: 1.25rem;
  --radius-key: 0.875rem;         /* keys are rounded squares, not pills */
  --radius-pill: 999px;

  /* Type */
  --font: ui-rounded, Nunito, -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", Roboto, system-ui, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "Cascadia Mono", Consolas, monospace;
}
```

- Load **Nunito** (weights 400, 600, 700, 800) from Google Fonts as the fallback for `ui-rounded`, and **JetBrains Mono** (weights 500, 700, 800) for `--mono`.
- Sizes and spacing in **rem**, so the layout scales with the browser's text-size setting.

## 3. Typography

| Use | Size | Weight | Line height | Letter spacing |
| --- | --- | --- | --- | --- |
| Home headline | 3.5rem | 800 | 1.05 | −0.03em |
| Result verdict | 2.75rem | 800 | 1.05 | −0.025em |
| Section heading | 1.25–1.75rem | 700–800 | 1.2 | −0.01 to −0.02em |
| Lead paragraph | 1.1875rem | 400 | 1.6 | 0 |
| Body | 1rem | 400 | 1.5 | 0 |
| Small / labels | 0.875rem | 600 | 1.5 | 0 (uppercase labels +0.06em) |
| Panel labels (`--mono`) | 0.75–0.9375rem | 700 | 1.5 | uppercase, +0.08em |
| Step numbers (`--mono`) | 1.5rem | 700 | 1.2 | 0, in `--link` |

Tighter letter-spacing on large text, none on body text. **Mono is for the "printed panel" text only:** field and section labels, the counter and helper line, the confidence label, "RESULT", step numbers and key labels. Messages, the verdict, summaries and advice stay in `--font` for easy reading.

## 4. Components

| Component | Style |
| --- | --- |
| **Header** | **Not fixed: scrolls away with the page.** Same background as the page, no blur, no divider line. Logo (shield icon, coral stroke, on a charcoal `--key-dark` key, `--radius-key`) + "SMS Scam Detector" – links home. |
| **Nav key** | Charcoal key: `--key-dark` fill, `--on-key-dark` text, `--radius-key`, `--raised-sm`, `--mono` 0.8125rem/700 uppercase, min height 2.75rem. |
| **Card (device body)** | `--base` background, `--radius-card`, `--raised-lg` plus a 1px top highlight (`inset 0 1px 0 rgba(255,255,255,0.9)`), 1px border `rgba(255,255,255,0.7)`, 2–2.25rem padding. |
| **Text box** | Sunken (`--inset-md`), `--radius-box`, no fill change, 1px border `rgba(87,81,75,0.18)`, 1.0625rem text, resizable vertically. Real `<label>`. |
| **Main action key** | Rounded square (`--radius-key`), `--accent-face` fill, `--on-accent` text, `--mono` 1rem/800 uppercase, height 4.25rem, `--raised-md` plus a 1px top highlight, 1px border `rgba(255,255,255,0.35)`. |
| **Example key** | Rounded square (`--radius-key`), `--key-face` fill, `--raised-sm` plus a 1px top highlight, 1px border `rgba(255,255,255,0.7)`, min 7rem × 3.5rem, `--mono` 0.75rem/700 uppercase. |
| **Pressed state** | Any raised control on `:active` → `box-shadow: var(--inset-md); transform: scale(0.98)`; transition 120 ms ease-out. |
| **Info panel / notice** | Sunken (`--inset-sm` or `--inset-md`), `--radius-box`, icon + text. |
| **Confidence meter** | LED segment bar: sunken track (height 1.375rem, 4px padding, 0.5rem radius) with a fill of segments in the result's `-fill` colour (9px lit, 3px gap); percentage label above in `--mono`. `role="img"` with an `aria-label`. |
| **Step tiles** | Sunken; step number large in `--mono` and `--link`, step name as a mono label, description in `--font`. |
| **Highlight** | `<mark>` with the result's `-mark` background and `-mark-ink` text, 600 weight, small rounded padding. |
| **Focus** | `:focus-visible { outline: 3px solid var(--focus); outline-offset: 3px; }` |
| **Icons** | Inline stroke SVGs (24px grid, stroke 2–2.2), `aria-hidden="true"` when decorative. No emoji. |

## 5. Screens and states

### Home (check a message)

**Layout (desktop):** header; then a two-column hero (max width 72rem, columns wrap on narrow screens):
- **Left:** headline "Not sure about a text message?"; lead "Paste it in and we'll tell you whether it looks legitimate, like marketing spam, or like a scam, and show you why."; sunken privacy notice with a lock icon: "Your message is checked and then discarded. It is never stored."
- **Right:** card containing:
  - label "Paste the text message" + text box (placeholder "e.g. Your parcel is held. Pay the fee at…")
  - helper row: "Paste the whole message for the best result." and a live counter "N / MAX characters" (MAX = the limit already enforced by the API's input validation)
  - primary button **Check message**
  - "Or try an example" + three chip buttons: **Parcel fee**, **Prize offer**, **Friend running late** (each fills the text box with a sample message)

Below: **How it works** – three sunken tiles (STEP 1 Paste / STEP 2 Check / STEP 3 Decide) with one-line descriptions.

**States:**
- **Empty** – as above.
- **Checking** – the button is replaced by a sunken status bar: "Checking your message…" with a coral progress bar (`role="status"`). Text box keeps the message.
- **Problem with input** – inline error under the text box (`role="alert"`, error colour, alert icon), the text box gets a 2px error ring, the user's text is kept and focus returns to the box. Messages:
  - Empty: "**The box is empty.** Paste the text message you want to check, then press Check message."
  - Too long: "**That message is too long.** Paste a message of up to MAX characters."
  - Any other invalid input / server error: "**We couldn't check that message.** Please try again."

### Result

**Layout (desktop):** header with a "← Check another message" pill link; two columns (wrap on narrow screens):
- **Left – verdict card (raised):** icon in a sunken circle; small uppercase "RESULT"; verdict in the result's ink colour; one-line summary; confidence meter; "What to do" list.
- **Right:** "Your message" (sunken panel showing the message with highlighted words, plus a small note "Highlighted: the words that most influenced the result." when there are highlights); "Why we think this" – the reasons as sunken rows, each with a small dot in the result's fill colour.

**Bottom row:** sunken reminder with an info icon: "This is an automated check and can be wrong. If a message claims to be from an organisation, contact them using a number or website you already know." + primary button **Check another message**.

**Per-result content:**

| Result | Verdict text | Icon | Summary | What to do |
| --- | --- | --- | --- | --- |
| scam | Likely scam | Warning triangle | This message has strong signs of a scam. | Don't click the link or call any number in the message. · Don't reply or share any details. · If you are worried, contact the organisation using a number or website you already know. |
| spam | Marketing spam | Megaphone | This looks like advertising: unwanted, but not a scam. | You can ignore or delete it. · Only reply STOP if it's from a company you recognise. · Never share personal or payment details by text. |
| ham | Looks legitimate | Speech bubble (no tick – never implies "safe") | We found none of the common scam or spam signs. | No check is perfect. If the number is unknown to you, stay cautious. · If a later message asks for money or details, check that one too. |
| unsure | Unsure | Question mark in a circle | We can't tell confidently what this is, so treat it with caution. | Treat it with caution until you are sure who sent it. · Don't call the number in the message. · Contact the organisation using a number or website you already know. |

- **Confidence label:** "Confidence N%" for rated results. For **Unsure**: "Closest match: <label>" and "N%, too low to rate".
- **Reasons and highlights** come from the explainer's output – render whatever it returns; don't hard-code them.

## 6. Motion

- Press feedback: 120 ms, on pointer-down.
- Result appears in place: opacity 0→1 and scale 0.98→1, critically damped (no bounce), ~350 ms. "Check another message" returns along the same path.
- **`prefers-reduced-motion: reduce`** → no scale or movement; short opacity fades only.

## 7. Accessibility settings

```css
@media (prefers-reduced-motion: reduce) { /* no press scale, no movement */ }
@media (prefers-contrast: more) { /* 2px solid #475569 outline on every raised and sunken surface */ }
```

- Real `<button>`, `<a href>`, `<label>` + `<textarea>`; no clickable `<div>`s.
- Error message linked to the text box with `aria-describedby`; `aria-invalid="true"` when in error.
- Result verdict is the page's `<h1>`.

## 8. Responsive behaviour

Designed for desktop/laptop first (content max width 72rem). Below ~900px the two columns stack (left column first); below ~600px reduce the headline to ~2.5rem, the verdict to ~2.25rem, card padding to ~1.25rem, and let the nav links wrap. Everything must work at 390px wide with no horizontal scrolling.
