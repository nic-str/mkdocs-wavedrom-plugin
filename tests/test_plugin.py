import pytest
from markdownwavedrom.plugin import (
    fence_wavedrom_format,
    WavedromPlugin,
    WavedromConfig,
)
from bs4 import BeautifulSoup


class TestFenceWavedromFormat:
    def test_basic(self):
        source = '{ signal: [{ name: "A", wave: "01" }] }'
        result = fence_wavedrom_format(source, "wavedrom", "", {}, None)
        assert (
            result
            == '<script type="WaveDrom">{ signal: [{ name: "A", wave: "01" }] }</script>'
        )

    def test_escapes_special_chars(self):
        source = '{ signal: [{ name: "A<B", wave: "01" }] }'
        result = fence_wavedrom_format(source, "wavedrom", "", {}, None)
        assert "A&lt;B" in result


def _make_plugin(**config_kwargs):
    plugin = WavedromPlugin()
    plugin.load_config(config_kwargs)
    plugin.on_pre_build(config={})
    return plugin


HTML_NO_WAVEDROM = """<!DOCTYPE html>
<html><head><title>Test</title></head>
<body><p>Hello</p></body></html>"""

HTML_WITH_CODE_BLOCK = """<!DOCTYPE html>
<html><head><title>Test</title></head>
<body><pre><code class="language-wavedrom">{ signal: [{ name: "A", wave: "01" }] }</code></pre>
</body></html>"""

HTML_WITH_SCRIPT_TAG = """<!DOCTYPE html>
<html><head><title>Test</title></head>
<body><script type="WaveDrom">{ signal: [{ name: "A", wave: "01" }] }</script>
</body></html>"""


class TestOnPreBuild:
    def test_defaults(self):
        p = _make_plugin()
        assert p.embed_svg is False
        assert p.pymdownx is False

    def test_embed_svg_true(self):
        p = _make_plugin(embed_svg=True)
        assert p.embed_svg is True
        assert p.pymdownx is False

    def test_pymdownx_true(self):
        p = _make_plugin(pymdownx=True)
        assert p.pymdownx is True
        assert p.embed_svg is False

    def test_both_true(self):
        p = _make_plugin(embed_svg=True, pymdownx=True)
        assert p.embed_svg is True
        assert p.pymdownx is True


class TestOnPostPageNoWavedrom:
    def test_returns_none(self):
        p = _make_plugin()
        assert p.on_post_page(HTML_NO_WAVEDROM, config={}) is None

    def test_plain_html(self):
        p = _make_plugin()
        assert p.on_post_page("<html><body>No charts</body></html>", config={}) is None


class TestDefaultMode:
    def test_code_replaced_with_script(self):
        p = _make_plugin()
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        assert 'type="WaveDrom"' in result
        assert "<code" not in result

    def test_pre_removed(self):
        p = _make_plugin()
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        assert "<pre>" not in result

    def test_process_all_appended(self):
        p = _make_plugin()
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        assert "WaveDrom.ProcessAll()" in result

    def test_content_preserved(self):
        p = _make_plugin()
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        assert '{ signal: [{ name: "A", wave: "01" }] }' in result

    def test_plain_wavedrom_class_also_matched(self):
        # classic output without the "language-" prefix must work too
        p = _make_plugin()
        html = HTML_WITH_CODE_BLOCK.replace("language-wavedrom", "wavedrom")
        result = p.on_post_page(html, config={})
        assert 'type="WaveDrom"' in result
        assert "WaveDrom.ProcessAll()" in result


class TestEmbedSvgMode:
    def test_renders_svg(self):
        p = _make_plugin(embed_svg=True)
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        assert "<svg" in result
        assert '<script type="WaveDrom">' not in result

    def test_no_process_all(self):
        p = _make_plugin(embed_svg=True)
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        assert "WaveDrom.ProcessAll()" not in result


class TestPymdownxMode:
    def test_script_tag_unchanged(self):
        p = _make_plugin(pymdownx=True)
        result = p.on_post_page(HTML_WITH_SCRIPT_TAG, config={})
        assert '<script type="WaveDrom">' in result
        assert '{ signal: [{ name: "A", wave: "01" }] }' in result

    def test_process_all_appended(self):
        p = _make_plugin(pymdownx=True)
        result = p.on_post_page(HTML_WITH_SCRIPT_TAG, config={})
        assert "WaveDrom.ProcessAll()" in result


class TestPymdownxEmbedSvg:
    def test_renders_svg(self):
        p = _make_plugin(pymdownx=True, embed_svg=True)
        result = p.on_post_page(HTML_WITH_SCRIPT_TAG, config={})
        assert "<svg" in result


class TestThemeSwitch:
    def test_script_has_data_attributes(self):
        p = _make_plugin(
            theme_switch=True,
            light_scheme="light",
            dark_scheme="slate",
            light_skin="default",
            dark_skin="dark",
        )
        script = p._theme_switch_script()
        assert 'data-scheme-light="light"' in script
        assert 'data-scheme-dark="slate"' in script
        assert 'data-skin-light="default"' in script
        assert 'data-skin-dark="dark"' in script
        assert script.startswith("<script ")

    def test_attribute_values_are_escaped(self):
        p = _make_plugin(theme_switch=True, light_scheme='a"b')
        script = p._theme_switch_script()
        assert 'data-scheme-light="a&quot;b"' in script

    def test_runtime_loaded_from_separate_file(self):
        p = _make_plugin(theme_switch=True)
        script = p._theme_switch_script()
        assert "document.currentScript" in script
        assert "MutationObserver" in script
        assert "WaveDrom.ProcessAll" in script
        assert "{{" not in script  # no template placeholders left

    def test_injected_before_body_end(self):
        p = _make_plugin(theme_switch=True)
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        # theme switch runtime replaces the plain ProcessAll script
        assert 'data-md-color-scheme' in result
        assert "WaveDrom.ProcessAll" in result

    def test_not_injected_when_disabled(self):
        p = _make_plugin(theme_switch=False)
        result = p.on_post_page(HTML_WITH_CODE_BLOCK, config={})
        assert "data-md-color-scheme" not in result
        assert "WaveDrom.ProcessAll" in result
