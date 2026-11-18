"""Tab 2: Is it shrinking? Owner: Saloni.

TODO (Saloni): build the change-over-time chart. Starting points: the release-date timeline in the `Chaemin`
branch (Tab "Is it shrinking?") and the trend chart in the `amanda` branch (Altair is fine: the theme is in style.py).
End with the bridge callout that leads into Tab 3.
"""
import style


def render(state):
    style.section("Is it shrinking?", "TODO: one sentence, e.g. 'Newer versions are fairer in 3 of 4 families.'")
    style.kpi_row([("Families that improved", "-", None), ("Biggest improvement", "-", None), ("Fairest tokenizer", "-", None)])
    style.chart_title("Inequality across languages, older → newer", "TODO: caption with the measure and its unit.")
    style.placeholder("Change over time · one line per family · value label on every dot", "Saloni", 420)
    style.callout("TODO: 'Even on the fairest tokenizer, <focus> is still N× English.'",
                  "Next: what the remaining gap costs you, and your three options →")
    style.how_to_read("TODO")
    style.not_shown("TODO")
