# Data

`sms_phishing_dataset.csv`

**Source:** Mishra, S. and Soni, D. (2022) *SMS Phishing Dataset for Machine Learning and Pattern Recognition*, Mendeley Data, V1. doi: 10.17632/f45bkkt8pr.1 – https://data.mendeley.com/datasets/f45bkkt8pr

**Licence:** CC BY 4.0. Used unchanged; renamed from `Dataset_5971.csv`. Cleaning happens in code, not in this file.

**Columns:** `LABEL` (ham / spam / smishing), `TEXT`, `URL`, `EMAIL`, `PHONE` (yes/no flags).

**Known issues:** inconsistent label spelling; leading and trailing whitespace; once whitespace is trimmed, 140 repeated rows, including 34 messages with conflicting labels; 185 `�` characters. The file is UTF-8. See decision 029 in `docs/decisions.md`.
