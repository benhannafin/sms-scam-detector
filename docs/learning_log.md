# Learning log

After each stage, write 2–3 sentences in your own words: what the code does, why it's built that way, and anything new you learned. If you can't explain it, ask until you can.

| Stage | What it does and why (my words) |
| --- | --- |
| 0 – Setup | |
| 1 – Data loading and cleaning | `load_dataset()` reads the CSV as UTF-8 and returns only labels and text, with whitespace trimmed and label spelling fixed. It removes every message labelled both spam and smishing, then removes duplicates, because conflicting labels can't teach the model anything and a message in both the training and test sets would inflate the scores (data leakage). I learned to check assumptions against the real file: `latin-1` garbled every £, and leading tabs were hiding most of the duplicates and conflicts, leaving 5,797 messages rather than 5,947. |
| 2 – Text preprocessor | `clean_text()` lowercases a message, removes HTML-style codes, then replaces links, money and phone numbers with `urltoken`, `moneytoken` and `phonetoken`, in that order so that digits in a link aren't mistaken for a phone number. Tokens let the model learn general patterns like "asks you to call a number" instead of treating every number as a rare word, and training and live checks share the function so the model always sees text cleaned the same way. I learned that a dataset can contain accidental giveaways: HTML codes appeared only in ham, so someone could have pasted one into a scam to make it look legitimate. |
