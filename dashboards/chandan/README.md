# Script or tokenizer? (Chandan's dashboard)

My Part 1 contribution to the group app. It takes the first half of our question head on:
is the extra token cost of a language fixed by its script, or set by the tokenizer?

The test is simple. `byte_premium_vs_en` is how much bigger a language's text is than English
in UTF-8 bytes. That depends only on the script and is the same for every tokenizer.
`premium_vs_en` is what the tokenizer actually charges. If the script decided the cost, the two
would match.

## Run it

From the repository root:

```bash
pip install -r dashboards/chandan/requirements.txt
streamlit run dashboards/chandan/app.py
```

It only reads files that are already in `data/`, so no API keys or Hugging Face login are needed.

## Files

| File | What it does |
|---|---|
| `app.py` | Page layout, filters, the answer text, limits and sources |
| `loaders.py` | Reads the CSVs once (cached) and works out the headline numbers |
| `charts.py` | One function per chart, each returns a Plotly figure |

Data read: `data/processed/token_premium.csv`, `data/processed/tokenizer_gini.csv`,
`data/source/lang_meta.csv`, `data/source/tokenizers.csv`, `data/source/api_overhead.csv`
(only for the refresh date).

## The charts

| Chart | Task | Form | Visual Vocabulary family |
|---|---|---|---|
| A. Who pays the most? | Rank languages by premium for one tokenizer | Sorted horizontal bar | Ranking |
| B. Is it the script? | Does token cost follow script size? | Scatter, log axes, y = x line | Correlation |
| C. Are newer tokenizers fairer? | Change across generations in each family | Small multiple slope charts | Change over time |
| D. Fairest tokenizers overall | Distance from a script-only baseline | Bar with reference line | Deviation |

Interactions: tokenizer picker, focus language picker, script group filter. With no script
group selected, charts A and B show a message instead of an empty chart.

Colour: blue is the tokenizer you picked, orange is the focus language, grey is context.
The blue and orange pair passes a colour vision deficiency check in light and dark mode
(worst protan ΔE 24.7, target 8 or more). Every value is also printed as a label.

## Design decisions

**Chart B: scatter with a y = x line, not grouped bars.** The task is a relationship: does the
token premium follow the byte premium? With a scatter, "the script decides" becomes a line you
can see, and every dot above it counts against that idea. Grouped bars (bytes next to tokens per
language) would mean comparing 30 bar lengths in pairs, and the other tokenizers could not be
shown as context.

**Chart B: log axes, not linear.** Premiums are ratios, so 2× to 4× should look the same as 4× to
8×. On a linear axis GPT-2's 17× squashes every modern tokenizer into the bottom fifth of the
chart. The axes are fixed, so switching tokenizer moves the dots, not the scale.

**Chart C: small multiples, not one line chart with four colours.** Generations in different
families are not on the same timeline, and four lines would need four colours that do not all
survive a CVD check. Separate panels with one colour avoid both problems.

## Verifying a number

Burmese on o200k (GPT-4o) shows **3.2×** in chart A.

1. `data/processed/token_premium.csv`, row `mya_Mymr, o200k_base`: `total_tokens = 17081`,
   `premium_vs_en = 3.2089`.
2. English row for `o200k_base`: `total_tokens = 5323`.
3. 17081 / 5323 = 3.2089.
4. `total_tokens` is the sum of `n_tokens` over the 200 sentences in
   `data/processed/token_counts_long.csv` (filter `lang_code = mya_Mymr`, `tokenizer_id = o200k_base`).


## AI Use

| Who | Tool | How AI was used |
|---|---|---|
| Chandan | Claude (Opus 5.5) | Used Claude to assist with data analysis, review my work, and identify potential errors or inconsistencies. It helped me examine the results, check calculations, and improve the clarity of my analysis. I independently reviewed and verified the AI-assisted outputs before incorporating them into my final work. |