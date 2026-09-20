import unittest
from pathlib import Path
from unittest.mock import patch

import app.ui as ui

ROOT = Path(__file__).resolve().parents[1]


class TestUiRendering(unittest.TestCase):
    def _capture_component(self, fn, *args, **kwargs):
        with patch.object(ui.st, "markdown") as markdown:
            fn(*args, **kwargs)
        markdown.assert_called_once()
        html = markdown.call_args.args[0]
        self.assertTrue(markdown.call_args.kwargs.get("unsafe_allow_html"))
        return html

    def test_info_card_html_is_compact_and_not_markdown_code(self):
        html = self._capture_component(ui.info_card, "1 · Generate", "Create deterministic OHLCV.")
        self.assertNotIn("\n", html)
        self.assertIn('<div class="fvg-card-body">Create deterministic OHLCV.</div>', html)
        self.assertFalse(html.startswith("    "))

    def test_empty_optional_value_does_not_create_blank_html_block(self):
        html = self._capture_component(ui.info_card, "Audit trail", "Readable body", None)
        self.assertNotIn("\n\n", html)
        self.assertNotIn("fvg-big-value", html)

    def test_warning_callout_has_explicit_readable_tone(self):
        html = self._capture_component(ui.callout, "Limitation", "Important caveat", kind="warning")
        self.assertIn('class="fvg-callout warning"', html)
        self.assertIn('class="fvg-callout-body">Important caveat</div>', html)

    def test_user_text_is_html_escaped(self):
        html = self._capture_component(ui.info_card, "<script>", "<b>unsafe</b>")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>unsafe</b>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;b&gt;unsafe&lt;/b&gt;", html)

    def test_method_steps_render_as_one_html_block(self):
        html = self._capture_component(ui.method_steps, ["First step", "Second step"])
        self.assertNotIn("\n", html)
        self.assertEqual(html.count('class="fvg-method-step"'), 2)
        self.assertIn('class="fvg-step-text">First step</div>', html)

    def test_streamlit_theme_is_explicit_high_contrast_dark(self):
        config = (ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        self.assertIn('base = "dark"', config)
        self.assertIn('backgroundColor = "#0b0f17"', config)
        self.assertIn('secondaryBackgroundColor = "#111827"', config)
        self.assertIn('textColor = "#f8fafc"', config)
        self.assertIn('primaryColor = "#3b82f6"', config)

    def test_ui_no_longer_derives_text_contrast_from_color_mix(self):
        source = (ROOT / "app" / "ui.py").read_text(encoding="utf-8")
        self.assertNotIn("color-mix(", source)
        self.assertIn("--fvg-text: #f8fafc", source)
        self.assertIn("--fvg-muted: #cbd5e1", source)


if __name__ == "__main__":
    unittest.main()
