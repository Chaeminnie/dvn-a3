"""UI tests (Streamlit AppTest): the app renders, filters work, empty states show."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
EMPTY = "No observations match the selected filters."


def run_app(monkeypatch) -> AppTest:
    monkeypatch.setenv("DASHBOARD_SAMPLE_MODE", "1")
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()


def texts(elements) -> list[str]:
    return [item.value for item in elements]


def metric_values(app: AppTest, label_start: str) -> list[str]:
    return [m.value for m in app.metric if m.label.startswith(label_start)]


def test_app_renders(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert not app.exception
    assert app.title[0].value == "Do some languages cost more tokens than others when using AI models?"
    assert any("Question:" in t for t in texts(app.markdown))
    assert any("Last data refresh: 2026-10-11" in t for t in texts(app.markdown))


def test_each_view_states_unit_and_latest_observation(monkeypatch) -> None:
    app = run_app(monkeypatch)
    captions = texts(app.caption)
    assert sum(t.startswith("Latest observation:") for t in captions) == 4
    assert sum(t.startswith("Unit:") for t in captions) == 4


def test_premium_view_filter_and_empty_state(monkeypatch) -> None:
    app = run_app(monkeypatch)
    app.multiselect(key="language_filter").set_value(["Burmese"]).run()
    assert not app.exception
    assert any("Selected: Burmese" in t for t in texts(app.markdown))

    app = run_app(monkeypatch)
    app.multiselect(key="language_filter").set_value([]).run()
    assert not app.exception
    assert any(EMPTY in t for t in texts(app.info))


def test_premium_view_tokenizer_changes_the_metrics(monkeypatch) -> None:
    app = run_app(monkeypatch)
    before = metric_values(app, "Median premium")
    app.selectbox(key="tokenizer_filter").select("gpt2").run()
    assert not app.exception
    assert before != metric_values(app, "Median premium")
    assert not metric_values(app, "Gini")


def test_buffer_view_filter_coverage_and_empty_state(monkeypatch) -> None:
    app = run_app(monkeypatch)
    wide = metric_values(app, "Largest buffer")
    app.multiselect(key="buffer_language_filter").set_value(["Hindi"]).run()
    assert not app.exception
    assert any("Selected: Hindi" in t for t in texts(app.markdown))
    assert metric_values(app, "Largest buffer") == ["Hindi · +31%"]
    assert wide != metric_values(app, "Largest buffer")
    app.radio(key="coverage_level").set_value(0.8).run()
    assert not app.exception
    assert metric_values(app, "Largest buffer") != ["Hindi · +31%"]

    app = run_app(monkeypatch)
    app.multiselect(key="buffer_language_filter").set_value([]).run()
    assert not app.exception
    assert any(EMPTY in t for t in texts(app.info))


def test_tier_view_boundaries_and_empty_state(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert metric_values(app, "Overcharge, one price for all") == ["253%"]
    assert metric_values(app, "Overcharge, these tiers") == ["13%"]
    app.slider(key="tier_bounds").set_value((1.3, 2.0)).run()
    assert not app.exception
    assert metric_values(app, "Overcharge, these tiers") != ["13%"]
    app.multiselect(key="tier_language_filter").set_value(["Hindi"]).run()
    assert any("Selected: Hindi" in t for t in texts(app.markdown))

    app = run_app(monkeypatch)
    app.multiselect(key="tier_language_filter").set_value([]).run()
    assert not app.exception
    assert any(EMPTY in t for t in texts(app.info))


def test_trend_view_measure_and_scope_controls(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert app.radio(key="trend_measure").value == "gini"
    assert app.radio(key="trend_scope").value == "versions"
    assert metric_values(app, "Families that improved") == ["3 of 4"]
    assert metric_values(app, "Biggest improvement") == ["Gemma · −53%"]
    assert any(t.startswith("Selected: Inequality across languages (Gini); 4 families, 9 tokenisers") for t in texts(app.markdown))
    app.radio(key="trend_measure").set_value("max_premium").run()
    assert not app.exception
    assert metric_values(app, "Biggest improvement") == ["GPT · −66%"]
    app.radio(key="trend_scope").set_value("all").run()
    assert not app.exception
    assert any("7 families, 12 tokenisers" in t for t in texts(app.markdown))


def test_trend_takeaway_names_the_families_and_the_flat_one(monkeypatch) -> None:
    app = run_app(monkeypatch)
    takeaway = next(t for t in texts(app.markdown) if t.startswith("**Takeaway:** On the inequality of cost across languages (Gini)"))
    assert "improved in 3 of 4 families, most in Gemma (53% lower from Gemma 2 to Gemma 3)" in takeaway
    assert "Qwen did not change" in takeaway and "has not closed" in takeaway


def test_trend_limits_say_claude_versions_are_different_model_lines(monkeypatch) -> None:
    app = run_app(monkeypatch)
    limits = [e for e in app.expander if e.label == "What this does not show"][0]
    body = " ".join(m.value for m in limits.markdown)
    assert "different model lines" in body and "9 of 12 release dates are unverified" in body


def test_context_paragraph_comes_before_question(monkeypatch) -> None:
    app = run_app(monkeypatch)
    values = texts(app.markdown)
    context = next(i for i, t in enumerate(values) if "Petrov et al., 2023" in t)
    question = next(i for i, t in enumerate(values) if t.startswith("**Question:**"))
    assert context < question


def test_story_headings_state_findings_and_match_manifest(monkeypatch) -> None:
    import yaml

    app = run_app(monkeypatch)
    manifest = yaml.safe_load((ROOT / "dashboard.yml").read_text(encoding="utf-8"))
    headings = texts(app.header)
    assert headings == [view["title"] for view in manifest["views"]]
    assert not any(h.rstrip().endswith("?") for h in headings)
    assert all(any(ch.isdigit() for ch in h) for h in headings)


def test_every_story_has_takeaway_and_limits(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert sum(t.startswith("**Takeaway:**") for t in texts(app.markdown)) == 4
    assert sum(e.label == "What this does not show" for e in app.expander) == 4


def test_chart_families_cover_at_least_three_ft_families(monkeypatch) -> None:
    app = run_app(monkeypatch)
    text = " ".join(texts(app.caption))
    families = [name for name in ("Ranking", "Deviation", "Distribution", "Change over time") if f"{name} (" in text]
    assert len(families) >= 3, families


def test_tokenizer_arrows_step_one_place(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert app.selectbox(key="tokenizer_filter").value == "o200k_base"
    app.button(key="tokenizer_filter_next").click().run()
    assert not app.exception
    assert app.selectbox(key="tokenizer_filter").value == "qwen2.5"
    app.button(key="tokenizer_filter_previous").click().run()
    app.button(key="tokenizer_filter_previous").click().run()
    assert app.selectbox(key="tokenizer_filter").value == "cl100k_base"
    app.button(key="tokenizer_filter_previous").click().run()
    assert app.selectbox(key="tokenizer_filter").value == "gpt2"
    assert app.button(key="tokenizer_filter_previous").disabled


def test_every_tokenizer_selector_has_arrows(monkeypatch) -> None:
    app = run_app(monkeypatch)
    for key in ("tokenizer_filter", "buffer_tokenizer", "tier_tokenizer"):
        app.button(key=f"{key}_next").click().run()
        assert not app.exception
        assert app.selectbox(key=key).value == "qwen2.5"


def test_languages_filter_is_not_in_the_tokenizer_row(monkeypatch) -> None:
    app = run_app(monkeypatch)
    tokenizer = app.selectbox(key="tokenizer_filter")
    languages = app.multiselect(key="language_filter")
    assert languages.proto.id != tokenizer.proto.id


def test_published_comparison_is_a_note_under_the_takeaway(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert not any("published values" in e.label.lower() for e in app.expander)
    note = next(t for t in texts(app.caption) if "Petrov et al. (2023)" in t and t.startswith("Our numbers also match"))
    assert "within 2.6%" in note and "Burmese" in note
    takeaway = next(t for t in texts(app.markdown) if t.startswith("**Takeaway:** On o200k"))
    assert "Petrov" not in takeaway and takeaway.count("×") <= 2


def test_story_three_title_covers_all_tokenizers(monkeypatch) -> None:
    app = run_app(monkeypatch)
    title = texts(app.header)[2]
    assert title.startswith("On all 12 tokenisers") and "o200k" not in title


def test_key_terms_are_explained(monkeypatch) -> None:
    app = run_app(monkeypatch)
    glossary = next(e for e in app.expander if e.label == "Glossary")
    body = " ".join(m.value for m in glossary.markdown)
    for term in ("Token", "Tokeniser", "Premium", "Gini", "Buffer", "overcharge", "Quota"):
        assert term.lower() in body.lower()


def test_no_story_heading_is_tied_to_one_tokeniser(monkeypatch) -> None:
    app = run_app(monkeypatch)
    headings = texts(app.header)
    assert not any("o200k" in h for h in headings)
    assert all("12 tokenisers" in h for h in headings)


def test_every_story_explains_its_controls(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert sum(t.startswith("**How to use this section:**") for t in texts(app.markdown)) == 4


def test_tier_cards_follow_the_slider(monkeypatch) -> None:
    app = run_app(monkeypatch)

    def card(tier: int) -> str:
        return next(t for t in texts(app.markdown) if f">Tier {tier}</div>" in t)

    assert "up to 1.5×" in card(1) and "1.5× to 2.1×" in card(2) and "above 2.1×" in card(3)
    assert "<b>8</b> languages" in card(1) or "<b>9</b> languages" in card(1)
    app.slider(key="tier_bounds").set_value((2.0, 4.0)).run()
    assert not app.exception
    assert "up to 2.0×" in card(1) and "2.0× to 4.0×" in card(2) and "above 4.0×" in card(3)
    app.multiselect(key="tier_language_filter").set_value([]).run()
    assert not app.exception
    assert "up to 2.0×" in card(1)


def test_english_is_explained_where_only_14_languages_are_listed(monkeypatch) -> None:
    app = run_app(monkeypatch)
    notes = [t for t in texts(app.caption) if t.startswith("English is not in this list.")]
    assert len(notes) == 2
    assert any("tier" in n for n in notes) and any("spread" in n for n in notes)


def test_empty_tier_is_reported(monkeypatch) -> None:
    app = run_app(monkeypatch)
    app.selectbox(key="tier_tokenizer").select("gpt2").run()
    assert not app.exception
    assert any(t.startswith("Empty: tier 1") for t in texts(app.caption))


def test_there_is_no_conclusion_section_and_sources_follow_the_last_story(monkeypatch) -> None:
    app = run_app(monkeypatch)
    subs = texts(app.subheader)
    assert "Conclusion" not in subs
    assert subs.index("What this means for pricing") < subs.index("Sources and data refresh")


def test_tier_slider_ends_at_the_costliest_premium(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert app.slider(key="tier_bounds").max == 6.0
    app.selectbox(key="tier_tokenizer").select("gpt2").run()
    assert not app.exception
    assert app.slider(key="tier_bounds").max == 18.0
    app.selectbox(key="tier_tokenizer").select("gemini_3_8_flash").run()
    assert not app.exception
    assert app.slider(key="tier_bounds").max == 3.0
    assert max(app.slider(key="tier_bounds").value) <= 3.0


def test_default_cutoffs_are_fixed_and_there_is_no_best_cutoffs_button(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert tuple(app.slider(key="tier_bounds").value) == (1.5, 2.1)
    assert not [b for b in app.button if b.label == "Use the best cut-offs"]
    assert not any("best cut-offs" in t.lower() for t in texts(app.markdown) + texts(app.caption))


def test_costliest_language_card_shows_burmese_across_tokenisers(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert metric_values(app, "Costliest language") == ["Burmese · 10 of 12"]


def test_default_tokeniser_is_justified_by_reproducibility(monkeypatch) -> None:
    app = run_app(monkeypatch)
    note = next(t for t in texts(app.caption) if t.startswith("Based on 15 languages"))
    assert "start on o200k because it runs locally through tiktoken" in note


def test_tier_takeaway_explains_why_tiers_beat_one_price(monkeypatch) -> None:
    app = run_app(monkeypatch)
    takeaway = next(t for t in texts(app.markdown) if t.startswith("**Takeaway:** **Three tiers"))
    assert "Three tiers reduce overcharging compared with a single price" in takeaway
    assert "(5.84×), so the average language pays 253% more than its real cost" in takeaway
    assert "cut that to 13%" in takeaway
    assert texts(app.header)[3].startswith("Three price tiers beat one price on all 12 tokenisers")
    app.slider(key="tier_bounds").set_value((5.0, 5.8)).run()
    assert not app.exception
    assert any("These cut-offs do not beat one price" in t for t in texts(app.markdown)) or any("Three tiers reduce overcharging" in t for t in texts(app.markdown))


def test_story_order_and_opening_lead_with_tokeniser_design(monkeypatch) -> None:
    app = run_app(monkeypatch)
    headings = texts(app.header)
    assert headings[0].startswith("Newer tokenisers are usually fairer than older ones")
    assert headings[1].startswith("English is the cheapest language on all 12 tokenisers")
    subs = texts(app.subheader)
    assert subs.index("Implications for Pricing Strategies") < subs.index("What this means for pricing") < subs.index("Sources and data refresh")
    answer = next(t for t in texts(app.markdown) if t.startswith("**Tokeniser design matters more than script.**"))
    assert answer.index("Tokeniser design matters more than script") < answer.index("For pricing, use tiers and quota buffers")
    assert any(e.label == "Limitations" for e in app.expander)
    assert [m.label for m in app.metric if m.label.startswith(("Tokenisers where", "Costliest language", "Families where"))] == [
        "Tokenisers where English is cheapest", "Costliest language", "Families where newer versions are fairer"
    ]


def test_question_and_chart_families_are_unchanged(monkeypatch) -> None:
    from src.config import QUESTION

    assert QUESTION == "Is the extra token cost of non-English languages a fixed property of their scripts, or a result of tokeniser design choices that is shrinking?"
    app = run_app(monkeypatch)
    assert f"Question:** {QUESTION}" in next(t for t in texts(app.markdown) if t.startswith("**Question:**"))
    charts = app.get("vega_lite_chart")
    assert len(charts) == 6
    captions = " ".join(texts(app.caption))
    assert sum(f"{name} (" in captions for name in ("Ranking", "Deviation", "Distribution", "Change over time")) >= 3


def test_buffer_view_has_a_plain_english_quota_metric(monkeypatch) -> None:
    app = run_app(monkeypatch)
    assert metric_values(app, "Sentences over a quota set at the average")
