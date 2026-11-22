# AI Provenance Matrix and Data and AI Disclosure

One row per substantive AI use. Every member owns at least one row. "Verified" names a check that could have failed (for example, recomputing a number from a CSV), not simply "looked fine".

## Matrix

| # | Artefact | Who | Tool | Asked | Came back | Verified | Outcome |
|---|---|---|---|---|---|---|---|
| 1 | `app/sections/shrinking.py` | Saloni | Claude | Implement the "Is it shrinking?" tab using the existing `style.py`, `data.py` and tab stub. | Cards, a change-over-time chart, a table and explanatory text. | Ran the app and compared the Gemma -53% card with the gemma2 and gemma3 rows in `tokenizer_gini.csv`. | gemma2 = 0.2486 and gemma3 = 0.1173. 0.1173 / 0.2486 - 1 = -0.528, confirming that the card's -53% is correct. |
| 2 | `app/app.py`, `app/style.py`, `app/data.py`, tab stubs (app structure, visual system, navigation and shared controls) | Chaemin | Claude | Created the overall app wireframes, defining the visual direction, information hierarchy, page layouts and shared UI elements across the four tabs. Used Claude for technical support when translating the wireframes and design decisions into Streamlit code, including the app structure, shared components and styling. | Code implementation of the app shell, shared sidebar controls, navigation, chart styling and four tab layouts based on the wireframes. | Ran the app locally and reviewed all four tabs against the original wireframes. Changed the tokenizer in the sidebar and confirmed that the selection persisted across tabs. Compared local files against the pushed commit `9b68c72` to confirm they matched. | Two widget default-value warnings and a broken icon font were identified during testing and fixed. Final diff against `9b68c72`: no differences. |
| 3 | Pre-submission visual QA and layout refinements at 1366x768 | Chaemin | Claude | Reviewed the implemented interface against the intended visual layout, identifying overlapping labels and other visual inconsistencies. Asked Claude for technical guidance on the relevant code changes needed to refine the layout and improve visual presentation. | Identified potential overlaps involving the heatmap colour bar, scatter plot labels and Gini chart axis, along with suggestions for relevant code adjustments. No application exceptions were reported across the four tabs. | Independently reopened each tab at 1366x768, checked the reported visual issues and reviewed the resulting layout after making adjustments. | TODO: Specify which visual issues were fixed and which were retained or accepted after review. |
| 4 | `app/sections/costs.py` | Amanda | TODO | TODO | TODO | TODO | TODO |
| 5 | `app/sections/script.py` | Chandan | TODO | TODO | TODO | TODO | TODO |
| 6 | `app/sections/overview.py`, `app/sections/verify.py` | Advait | TODO | TODO | TODO | TODO | TODO |

Add more rows if AI was used for other substantive work, such as the data pipeline, data dictionary, README or on-screen wording. Delete every TODO before submission.

## Data and AI Disclosure

**Data.** Sentences come from FLORES+ devtest (CC BY-SA 4.0, Open Language Data Initiative), a fixed-seed sample of 200 sentences in 15 languages. Token counts were produced by running 9 open tokenizers locally and by calling the free token-counting APIs of Anthropic and Google for 3 more. Prices are public list prices copied by hand from the providers' pricing pages. The language mix in the cost calculator is an equal-weight placeholder, not real usage data. Every file, its source, licence and transform is listed in `data_dictionary.md`, and `bash run_all.sh` rebuilds the processed files from the source files.

**AI use.** We used Claude as a supporting tool during the development of the Streamlit application. Its use included technical assistance with translating the team's designs and wireframes into code, implementing UI components, resolving coding issues and reviewing visual layouts. The app's overall structure, information hierarchy, visual direction and wireframes were designed by the team. Individual members were responsible for defining and reviewing their respective sections, while AI-assisted suggestions and code were evaluated and tested before being incorporated into the project.

Each substantive AI use is documented in the matrix above, including the responsible team member and the verification performed. AI was not used to generate or alter numerical values in the data files: all counts, premiums and Gini values come from the scripts in `scripts/`. Numbers shown on screen are computed from the processed files, and the "Check a number" box in the app recomputes one of them from the raw token counts.

**Limits.** AI-generated code and suggestions can contain errors or introduce unintended behaviour. Team members reviewed and tested their respective contributions against the application requirements and underlying data before merging. However, not every sentence of on-screen text was independently checked against a second source.
