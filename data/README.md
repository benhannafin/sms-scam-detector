# Data

`sms_phishing_dataset.csv`

**Source:** Mishra, S. and Soni, D. (2022) *SMS Phishing Dataset for Machine Learning and Pattern Recognition*, Mendeley Data, V1. doi: 10.17632/f45bkkt8pr.1 – https://data.mendeley.com/datasets/f45bkkt8pr

**Licence:** CC BY 4.0. Used unchanged; renamed from `Dataset_5971.csv`. Cleaning happens in code, not in this file.

**Columns:** `LABEL` (ham / spam / smishing), `TEXT`, `URL`, `EMAIL`, `PHONE` (yes/no flags).

**Known issues:** inconsistent label spelling; leading and trailing whitespace; once whitespace is trimmed, 140 repeated rows, including 34 messages with conflicting labels; 185 `�` characters. The file is UTF-8. See decision 029 in `docs/decisions.md`.

---

`reference_set.csv`

A small evaluation set for Stage 11 (decision 040). It is **never used for training**. Scored with `python -m training.evaluate_reference`.

**Columns:** `id`, `text`, `expected` (ham / spam / smishing), `origin`, `source`, `notes`.

**Origins:**
- `verbatim`: a scam text quoted word for word in an Irish public warning. `source` is the page it came from. Quoted briefly for evaluation, with the source credited.
- `modelled`: a scam written for this project, based on the scam a public warning describes. `source` is that warning. The phone numbers and links are invented.
- `made_up`: genuine and marketing texts written for this project, using no real personal data (decision 025).

**Halves:** the code splits each class and origin evenly into a design half and a held-out half. Fixes are designed on the design half only; the held-out half is scored once, at the end of Stage 11.
