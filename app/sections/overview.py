"""Tab 0: Overview. Owner: Advait.

TODO (Advait): bring the heatmap from the `advait` branch into render().
Keep: a title + one-sentence finding, 3 KPIs about the WHOLE dataset (ignore filters),
the heatmap with a value in every cell, how_to_read and not_shown.
"""
import style


def render(state):
    style.section("How big is the gap?", "TODO: one sentence with the range, e.g. 'The same 200 sentences need 1.0× to 17.1× the tokens of English.'")
    style.kpi_row([("Worst case", "-", "Tokens vs English"), ("Pairs costing more than their script", "-", None),
                   ("Fairest tokenizer", "-", None)])
    style.chart_title("Tokens vs English, every language on every tokenizer", "TODO: what one cell means and how it is sorted.")
    style.placeholder("Heatmap · 15 languages × 12 tokenizers · value printed in every cell", "Advait", 460)
    style.how_to_read("TODO")
    style.not_shown("TODO")
