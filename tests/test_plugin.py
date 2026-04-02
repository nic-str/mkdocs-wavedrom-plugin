import pytest
from markdownwavedrom.plugin import (
    _escape,
    fence_wavedrom_format,
    WavedromPlugin,
    WavedromConfig,
)
from bs4 import BeautifulSoup


class TestEscape:
    def test_ampersand(self):
        assert _escape("a&b") == "a&amp;b"

    def test_lt(self):
        assert _escape("a<b") == "a&lt;b"

    def test_gt(self):
        assert _escape("a>b") == "a&gt;b"

    def test_combined(self):
        assert _escape("a&b<c>d") == "a&amp;b&lt;c&gt;d"

    def test_no_special(self):
        assert _escape("abc") == "abc"

    def test_empty(self):
        assert _escape("") == ""


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
