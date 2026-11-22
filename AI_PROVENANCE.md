# AI provenance matrix and Data and AI disclosure

One row per substantive AI use. Every member owns at least one row. "Verified" names a check that could have failed (for example recomputing a number from a CSV), not "looked fine".

Columns: Artefact (what was made) / Who / Tool / Asked / Came back / Verified / Outcome.

## Matrix

| # | Artefact | Who | Tool | Asked | Came back | Verified | Outcome |
|---|---|---|---|---|---|---|---|
| 1 | `app/sections/shrinking.py` | Saloni | Claude | Write the "Is it shrinking?" tab using style.py, data.py and the stub | Cards, a change-over-time chart, a table and text boxes | Ran the app and compared the Gemma -53% card with the gemma2 and gemma3 rows in `tokenizer_gini.csv` | gemma2 = 0.2486 and gemma3 = 0.1173. 0.1173 / 0.2486 - 1 = -0.528, so the card's -53% is right |
| 2 | `app/app.py`, `app/style.py`, `app/data.py`, tab stubs (app shell, shared controls, navigation, style) | Chaemin | Claude | Build the app skeleton from the wireframe: sidebar controls shared by all tabs, four tab stubs, one shared style module | Working skeleton with navigation, shared sidebar state, chart theme and layout blocks | Ran it locally and opened all four tabs; changed the tokenizer in the sidebar and checked the choice stayed on every tab. Diffed the local files against the pushed commit `9b68c72` to confirm they were identical | Two warnings (widget default values) and a broken icon font were found on the first run and fixed. Final diff against `9b68c72`: no differences |
| 3 | Pre-submission QA of the deployed layout at 1366x768 | Chaemin | Claude | Open every tab at 1366x768 and list overlapping elements and errors | List of label overlaps (heatmap colour bar, scatter labels, Gini chart axis) and "no exceptions on all four tabs" | Re-checked each listed overlap by opening the tab myself at 1366x768 | TODO: Chaemin to fill in what was fixed |
| 4 | `app/sections/costs.py` | Amanda | TODO | TODO | TODO | TODO | TODO |
| 5 | `app/sections/script.py` | Chandan | TODO | TODO | TODO | TODO | TODO |
| 6 | `app/sections/overview.py`, `app/sections/verify.py` | Advait | TODO | TODO | TODO | TODO | TODO |

Add more rows if you used AI for something else (data pipeline, data dictionary, README, wording on screen). Delete every TODO before submission.

## Data and AI disclosure

**Data.** Sentences come from FLORES+ devtest (CC BY-SA 4.0, Open Language Data Initiative), a fixed-seed sample of 200 sentences in 15 languages. Token counts were produced by running 9 open tokenizers locally and by calling the free token-counting APIs of Anthropic and Google for 3 more. Prices are public list prices copied by hand from the providers' pricing pages. The language mix in the cost calculator is an equal-weight placeholder, not real usage data. Every file, its source, licence and transform is listed in `data_dictionary.md`, and `bash run_all.sh` rebuilds the processed files from the source files.

**AI use.** We used Claude (Anthropic) to help write the Streamlit code, the style module and some of the on-screen wording, and to review the app for layout problems. Each use is listed in the matrix above with the person responsible and the check we ran. AI was not used to produce or alter any number in the data files: all counts, premiums and Gini values come from the scripts in `scripts/`. Numbers shown on screen are computed from the processed files, and the "Check a number" box in the app recomputes one of them from the raw token counts.

**Limits.** AI-written code and text can be wrong in ways that look fine, so each member checked their own part against the data files before it was merged. We did not check every sentence of on-screen text against a second source.
