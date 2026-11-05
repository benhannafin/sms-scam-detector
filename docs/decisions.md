# SMS Scam Detector – Architecture Decision Record

Every significant design decision, with the reasoning behind it. Add a new entry whenever a decision is made or changed; never delete old ones – mark them *Superseded* and link to the replacement.

**Status key:** *Accepted* = decided · *Proposed* = suggested, not yet confirmed · *Open* = still to decide · *Superseded* = replaced by a later decision.

## Index

| # | Decision | Status |
| --- | --- | --- |
| 001 | Project: SMS scam detector using one dataset | Accepted |
| 002 | Product: public web app, paste a message and get a rating | Accepted |
| 003 | Dataset: Mishra & Soni SMS Phishing Dataset (three classes) | Accepted |
| 004 | Framing: risk assessment, never "safe" | Accepted |
| 005 | Result: three labels plus confidence, with Unsure | Accepted |
| 006 | Architectural pattern: layered modular monolith | Accepted |
| 007 | Hosting: Microsoft Azure (not Firebase) | Accepted |
| 008 | Web hosting: Azure App Service | Accepted |
| 009 | Model: TF-IDF + logistic regression | Accepted |
| 010 | Success targets: ≥95% scam-vs-safe recall, ≤5% false alarms | Accepted |
| 011 | No external AI services | Accepted |
| 012 | No storage or logging of checked messages | Accepted |
| 013 | Rate limiting | Accepted |
| 014 | Feedback loop in target design only | Accepted |
| 015 | Feedback data: opt-in consent and redaction | Accepted |
| 016 | Retraining: monthly, human-approved | Accepted |
| 017 | Data stores: Azure Blob Storage and Azure SQL Database | Proposed |
| 018 | Monitoring: Application Insights (target), deferred in prototype | Proposed |
| 019 | Prototype scope: Built / Simplified / Deferred | Accepted |
| 020 | Prototype hosting: Azure App Service free tier | Accepted |
| 021 | Interfaces defined by purpose; exact names fixed during implementation | Accepted |
| 022 | Data cleaning: normalise labels, remove duplicates and conflicting labels | Superseded by 029 |
| 023 | Model evaluation: held-out test set + 5-fold cross-validation | Accepted |
| 024 | Testing the AI with a fixed reference set after every retrain | Proposed |
| 025 | Irish real-world check uses public warnings only | Accepted |
| 026 | Primary safety feature: no false reassurance | Accepted |
| 027 | Wireframes made in draw.io | Accepted |
| 028 | Reliability of user feedback labels | Open |
| 029 | Data loading and cleaning rules | Accepted |
| 030 | Text preprocessing rules | Accepted |
| 031 | Training data and model file rules | Accepted |

---

## 001 – Project: SMS scam detector using one dataset
**Status:** Accepted (12 Oct 2026)
**Context:** The earlier FireWatch idea needed many datasets (weather, vegetation, fire records), which made it mostly data engineering. Heart disease and wine quality were too common.
**Decision:** Build an SMS scam (smishing) detector using a single public dataset.
**Alternatives considered:** FireWatch wildfire risk; heart disease risk; student dropout; hotel cancellations; fake job postings; bank account fraud.
**Consequences:** All effort goes into ML and architecture rather than merging data. Strong, relatable problem with clear precision/recall trade-offs. Irish evidence available (AIB, Ekco, ENISA).

## 002 – Product: public web app, paste a message and get a rating
**Status:** Accepted (20 Oct 2026)
**Context:** The real product could serve the public or businesses (banks, mobile networks).
**Decision:** A public web app: users paste a text and get a rating. Web only, no mobile app or forward-by-SMS.
**Alternatives considered:** Service for banks/telcos to filter texts (now a Won't have); web + mobile app; web + forward-by-SMS.
**Consequences:** Simpler target architecture; users stay in control of what they share.

## 003 – Dataset: Mishra & Soni SMS Phishing Dataset
**Status:** Accepted (12 Oct 2026)
**Context:** Need one clean, labelled, public dataset that separates dangerous scams from ordinary spam.
**Decision:** Mishra & Soni (2022), Mendeley Data, CC BY 4.0 – 5,971 messages labelled ham / spam / smishing.
**Alternatives considered:** UCI SMS Spam Collection (only spam vs not – too common, no smishing class); LLM-generated balanced version (synthetic messages, removes the class imbalance).
**Consequences:** Three-way split is the project's hook. Imbalance (11% smishing) makes precision/recall central. Limitation: mostly older UK and Indian messages, so Irish wording may be handled poorly (see 025).

## 004 – Framing: risk assessment, never "safe"
**Status:** Accepted
**Context:** A scam rated legitimate that the user trusts is the most harmful failure.
**Decision:** The tool assesses risk and gives reasons; it never declares a message "safe", never blocks or deletes messages, and always reminds users to verify with the organisation directly.
**Consequences:** Underpins the primary safety feature (026).

## 005 – Result: three labels plus confidence, with Unsure
**Status:** Accepted (20 Oct 2026)
**Decision:** Show "Legitimate", "Marketing spam" or "Likely scam" with a confidence level; show "Unsure" when no class is confident enough.
**Alternatives considered:** Low/Medium/High risk level; traffic-light colours.
**Consequences:** Needs a model that outputs probabilities (see 009). The Unsure threshold is set in Stage 11.

## 006 – Architectural pattern: layered modular monolith
**Status:** Accepted (20 Oct 2026)
**Context:** One core workflow, a solo developer, fast and independent checks, modest uniform load.
**Decision:** One deployable application split into layers (presentation, API, application, ML, data) and modules that talk only through defined interfaces.
**Alternatives considered:** Microservices – independent scaling, but more cost, network calls, failure points and container skills needed; no part of the system is much busier than the rest. Layered app with a separate model service – middle ground, rejected as unnecessary complexity.
**Consequences:** Cheap and simple; the Classify interface keeps the option of moving the model into its own service later.

## 007 – Hosting: Microsoft Azure (not Firebase)
**Status:** Accepted (20 Oct 2026; re-confirmed 4 Nov 2026)
**Context:** Need cloud hosting that runs a Python app with a scikit-learn model at no cost.
**Decision:** Microsoft Azure.
**Alternatives considered:** Firebase – Hosting serves static files only; Python needs Cloud Functions, which require the pay-as-you-go Blaze plan with a card; serverless cold starts reload the model; would push the design towards serverless and Firestore. AWS; Render; cloud-agnostic containers.
**Consequences:** Azure for Students gives $100 credit without a card. Fits the modular monolith directly.

## 008 – Web hosting: Azure App Service
**Status:** Accepted (20 Oct 2026)
**Decision:** Run the whole application on Azure App Service.
**Alternatives considered:** Azure Container Apps (scales to zero, container setup); Azure Functions (serverless – would change the pattern).
**Consequences:** Managed Python hosting; can run several copies behind a load balancer if traffic grows.

## 009 – Model: TF-IDF + logistic regression
**Status:** Accepted (20 Oct 2026)
**Context:** Baseline on a 20% held-out test set: Naive Bayes 73.8% smishing recall; logistic regression 88.1%; linear SVM 88.9%.
**Decision:** TF-IDF features (words and word pairs) with class-weighted logistic regression.
**Alternatives considered:** Linear SVM (≈1 point better, but no probabilities without calibration); Naive Bayes (much weaker on rare classes); fine-tuned transformer such as DistilBERT (likely better on unseen wording, but large, slow, hard to explain, doubtful on the free tier); LLM via API (cost, privacy, varying answers, no probabilities).
**Consequences:** Gives probabilities for the confidence level and Unsure rule; word weights provide the reasons; small and fast; deterministic. A DistilBERT comparison is a possible later experiment.

## 010 – Success targets
**Status:** Accepted (20 Oct 2026)
**Decision:** Headline target ≥95% scam-vs-safe recall (spam or smishing not rated Legitimate); false alarms ≤5% of genuine texts.
**Alternatives considered:** 90% strict smishing recall; both.
**Consequences:** Treats smishing rated as spam as caught, because the user is still warned. Baseline already meets both (96.0%, 0.4%). Per-class metrics still reported so the spam/smishing confusion stays visible.

## 011 – No external AI services
**Status:** Accepted
**Decision:** The model runs inside the application.
**Consequences:** No per-request cost; no third party sees users' messages; no external outage risk.

## 012 – No storage or logging of checked messages
**Status:** Accepted
**Decision:** Messages are processed in memory and never written to disk or logs; request bodies excluded from logging; HTTPS only.
**Consequences:** Must be configured deliberately (server logs, error reports, monitoring can capture inputs by default). Privacy risk mitigation in the register.

## 013 – Rate limiting
**Status:** Accepted (20 Oct 2026)
**Context:** Scammers could repeatedly test their texts until one is rated Legitimate.
**Decision:** Limit checks per client. Prototype: one fixed limit (e.g. Flask-Limiter).
**Consequences:** Security risk mitigation.

## 014 – Feedback loop in target design only
**Status:** Accepted (20 Oct 2026)
**Decision:** "Report a wrong result" and retraining from reports are in the target design; deferred in the prototype.
**Consequences:** `POST /api/feedback`, Feedback Service and Feedback Store are designed but not built. See 028 for the reliability question.

## 015 – Feedback data: opt-in consent and redaction
**Status:** Accepted (20 Oct 2026)
**Decision:** Store a reported message only if the user consents; remove phone numbers, email addresses and long digit strings before saving.
**Alternatives considered:** Store labels only, no text (less useful for retraining); store full text with consent.
**Consequences:** The only place message text is stored. Privacy risk mitigation.

## 016 – Retraining: monthly, human-approved
**Status:** Accepted (20 Oct 2026)
**Decision:** A monthly job trains a candidate model from the dataset plus approved reports; a person reviews labels and scores before it goes live.
**Alternatives considered:** Fully automatic retraining and deployment; manual retraining only.
**Consequences:** Protects against data poisoning and bad labels. In the prototype: a training script run by hand.

## 017 – Data stores: Azure Blob Storage and Azure SQL Database
**Status:** Proposed – confirm
**Decision:** Model files in Azure Blob Storage; feedback reports in Azure SQL Database.
**Consequences:** Prototype keeps the model file in the app (Simplified); Feedback Store deferred.

## 018 – Monitoring: Application Insights
**Status:** Proposed – confirm
**Decision:** Target uses Application Insights for response times and error rates only, never message text. Prototype uses App Service's built-in logs (Deferred).

## 019 – Prototype scope
**Status:** Accepted (20 Oct 2026)
**Decision:**
- **Built:** Web UI (with example messages), Check Service, Text Preprocessor, Classifier, Explainer, `POST /api/check`, input validation.
- **Simplified:** rate limiting (one fixed limit); Model Store (file with the app); Retraining Pipeline (script run by hand); App Service (free tier, one instance).
- **Deferred:** Feedback Service, Feedback Store, `POST /api/feedback`, Application Insights.
**Consequences:** Keeps the logical architecture; only the storage behind Load model changes between prototype and target.

## 020 – Prototype hosting: Azure App Service free tier
**Status:** Accepted (20 Oct 2026)
**Alternatives considered:** Run locally only.
**Consequences:** Demo runs on the same platform as the target. Risk: free tier sleeps or hits its quota – wake before demos, keep a local fallback.

## 021 – Interfaces defined by purpose
**Status:** Accepted (4 Nov 2026)
**Decision:** Interfaces are defined by what they do and what they pass (Check a message, Clean the text, Classify, Explain, Load model, Save report, Publish model); REST endpoints keep exact names. Exact function and field names are fixed during implementation.
**Consequences:** Naming changes are recorded here.

## 022 – Data cleaning
**Status:** Superseded by 029
**Decision:** Normalise label spelling; remove 22 exact duplicates; remove the 2 messages with conflicting labels.
**Note:** The initial baseline kept one copy of each conflicting message rather than removing them; Stage 1 fixes this.

## 023 – Model evaluation method
**Status:** Accepted (5 Nov 2026)
**Decision:** Stratified 80/20 split with a fixed random seed (42); final test set used once; model settings chosen with 5-fold cross-validation on training data only. `C` is chosen from 0.1, 1, 10 and 100 by highest macro F1.
**Alternatives considered:** Choosing `C` by scam-vs-safe recall (it barely changes across these values, 94.5% to 95.7%, and ignores whether the model separates spam from smishing). It is still reported as the main result.

## 024 – Fixed reference set after every retrain
**Status:** Proposed – confirm
**Decision:** A small set of messages with known expected results is re-run after every retraining; any changed result is reviewed. A new model must beat the current model's test scores before publishing.

## 025 – Irish real-world check uses public warnings only
**Status:** Accepted (20 Oct 2026)
**Context:** No real personal data is used anywhere in the project.
**Decision:** Irish test messages come from scam examples published by banks, An Post, Revenue, Gardaí and FraudSMART.
**Alternatives considered:** Public + self-written synthetic genuine messages; skip the Irish check.

## 026 – Primary safety feature: no false reassurance
**Status:** Accepted (20 Oct 2026)
**Decision:** Never say "safe"; show Unsure for low confidence; show a reminder to verify with the organisation on every result.
**Context:** A scam rated Legitimate and trusted is the most harmful failure.
**Consequences:** Needs calibrated probabilities and a tuned threshold (Stage 11).

## 027 – Wireframes made in draw.io
**Status:** Accepted (4 Nov 2026)
**Decision:** Low-fidelity wireframes in draw.io (open source, Apache-2.0, connected to Claude), three screens: check, result, problem with input.
**Alternatives considered:** Balsamiq; Excalidraw; Penpot.

## 028 – Reliability of user feedback labels
**Status:** Open
**Context:** Users often don't know whether a message was really a scam – that's why they used the tool – so "this was wrong" reports may be guesses.
**Options:** (1) ask "How do you know?" and only accept reports with a real reason; (2) only invite feedback after the fact; (3) retrain mainly on verified scam examples from public warnings, with user reports as a supplement; (4) keep as is and record as a limitation.
**Suggested:** combine 1 and 3. To decide.

## 029 – Data loading and cleaning rules
**Status:** Accepted (5 Nov 2026)
**Context:** Checking the real file showed two earlier assumptions were wrong. The file is valid UTF-8; reading it as `latin-1` turns all 283 messages containing `£` into `Â£`. Many messages also appear with and without a leading tab, so the 22 duplicates and 2 conflicts in 022 only hold before trimming. After trimming there are 140 repeated rows, including 34 messages labelled both spam and smishing.
**Decision:** The code lives in `training/data.py` and cleans on every load, with no cleaned CSV saved. Read as UTF-8; keep only `LABEL` and `TEXT`, because the preprocessor detects links and phone numbers itself and live messages won't have those columns; trim whitespace; normalise label spelling; remove every copy of the 34 conflicting messages; then remove remaining duplicates. Result: 5,797 messages (4,834 ham, 528 smishing, 435 spam).
**Alternatives considered:** Keep one copy of each conflict labelled smishing (keeps more scam examples, but means choosing labels without evidence); don't trim (5,947 messages, but the same message could land in both the training and test sets, inflating results); `latin-1` (garbles `£`).
**Consequences:** 98 fewer smishing and 52 fewer spam examples than without trimming. The baseline used different cleaning, so its figures may not reproduce exactly and the Stage 3 expectation needs reviewing. The 185 `�` characters already in the file stay as they are, because they can't be recovered.

## 030 – Text preprocessing rules
**Status:** Accepted (5 Nov 2026)
**Context:** The design named three tokens but not exactly what each covers. The cleaned dataset also showed that HTML-style codes such as `&lt;#&gt;` and `&amp;` appear in 254 messages, all ham. They are leftovers from how the data was collected, so a model could learn them as a sign of "Legitimate", and someone could paste one into a scam text to exploit that.
**Decision:** Lowercase; remove HTML-style codes (`&amp;` becomes `&`, placeholders are deleted); then replace links, money and phone numbers, in that order. `urltoken` includes bare domains with a common ending (91 messages). `moneytoken` includes currency symbols with `€`, currency words and codes, and pence rates such as `150p`. `phonetoken` means 7 or more digits, with spaces or dashes allowed (575 messages, 6 of them ham).
**Alternatives considered:** Leave the HTML-style codes in (keeps the shortcut described above); add an `emailtoken` (not in the design, and words like `gmail` still reach the model when addresses are left as they are); treat 5-digit short codes as `phonetoken` (186 messages, 1 of them ham, but this may reflect old UK premium-rate texts and could cause false alarms on genuine bank or delivery texts).
**Consequences:** Removing the codes may lower the Stage 3 results a little compared with the baseline, but the score no longer benefits from that shortcut. Short codes are revisited in Stage 11. `�` characters need no handling, because the word-splitting planned for Stage 3 ignores them (confirmed: none appear in the model's vocabulary).

## 031 – Training data and model file rules
**Status:** Accepted (5 Nov 2026)
**Context:** Replacing numbers and amounts with tokens makes many template scam texts identical: 89 more repeats, mostly smishing, and 1 new conflicting message. With them left in, 22 test messages also appeared in the training set. In cross-validation on the training portion, scam-vs-safe recall was 95.7% with repeats left in and 94.6% with them removed, and smishing recall was 90.3% and 85.8%.
**Decision:** After `clean_text`, keep one copy of each repeated message and remove conflicting messages completely, leaving 5,707 messages. The saved model trains on the 80% training set only. It is saved as `models/model_v1.joblib`, committed to the repo, with scores in `models/model_v1_metrics.json`. Pin `scikit-learn==1.9.1`, because a model saved with one version may fail or misbehave on another. The Stage 3 test checks cross-validation on the training portion (at least 92% scam-vs-safe recall, at most 5% false alarms) instead of reproducing the old baseline.
**Alternatives considered:** Keep the repeats (scores look better, but are inflated by leakage); retrain on 100% after evaluating (more data, but no untouched data would be left to score that model); run tests against the test set (would break "used once").
**Consequences:** The honest estimate is just under the 95% target. If the test score is under it, the result is recorded and handled in Stage 11, not by retraining until the test set looks better. The dedupe step lives in training, not in `load_dataset`, because it depends on the preprocessor.
