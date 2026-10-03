# Copyright (c) 2019, Shimoda <kuri65536 at hotmail dot com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
import html
import logging
from importlib.resources import files
from typing import Text
from mkdocs.plugins import BasePlugin
from mkdocs.config.base import Config
from mkdocs.config.config_options import Type
from bs4 import BeautifulSoup
import wavedrom

log = logging.getLogger("markdownwavedrom")

# Theme-switch runtime; kept in a separate file for easier JS maintenance.
_THEME_SWITCH_JS = files(__package__).joinpath("theme_switch.js").read_text(
    encoding="utf-8"
)

# Renders all diagrams once the page is loaded.
_PROCESS_ALL_JS = (
    "window.addEventListener('load', function() {WaveDrom.ProcessAll();});"
)


# for pymdownx custom fences
def fence_wavedrom_format(source, language, class_name, options, md, **kwargs):
    return '<script type="WaveDrom">%s</script>' % html.escape(source, quote=False)


class WavedromConfig(Config):
    embed_svg = Type(bool, default=False)
    pymdownx = Type(bool, default=False)
    # Follow the Material light/dark scheme, switching the WaveDrom skin.
    theme_switch = Type(bool, default=False)
    # Material scheme names and WaveDrom skin names (WaveSkin keys).
    light_scheme = Type(Text, default="default")
    dark_scheme = Type(Text, default="slate")
    light_skin = Type(Text, default="default")
    dark_skin = Type(Text, default="dark")


class WavedromPlugin(BasePlugin[WavedromConfig]):
    def on_pre_build(self, config, **kwargs):
        self.embed_svg = self.config.get("embed_svg", False)
        self.pymdownx = self.config.get("pymdownx", False)
        self.theme_switch = self.config.get("theme_switch", False)
        self.light_scheme = self.config.get("light_scheme", "default")
        self.dark_scheme = self.config.get("dark_scheme", "slate")
        self.light_skin = self.config.get("light_skin", "default")
        self.dark_skin = self.config.get("dark_skin", "dark")

        if self.theme_switch and self.embed_svg:
            log.warning("wavedrom: theme_switch is ignored when embed_svg=True")
            self.theme_switch = False

    def _theme_switch_script(self):
        """<script> element with the self-contained theme-switch runtime."""
        attrs = " ".join(
            'data-%s="%s"' % (key, html.escape(str(value), quote=True))
            for key, value in (
                ("scheme-light", self.light_scheme),
                ("scheme-dark", self.dark_scheme),
                ("skin-light", self.light_skin),
                ("skin-dark", self.dark_skin),
            )
        )
        return "<script %s>\n%s</script>" % (attrs, _THEME_SWITCH_JS)

    def on_post_page(self, output_content, config, **kwargs):
        # skip parsing when no diagrams are present
        if not "WaveDrom" in output_content and not "wavedrom" in output_content:
            return

        if self.pymdownx and not self.embed_svg:
            # avoid bs4's slow parse on large pages
            if "WaveDrom" in output_content:
                if self.theme_switch:
                    # also performs the initial render
                    runtime = self._theme_switch_script()
                else:
                    runtime = "<script>" + _PROCESS_ALL_JS + "</script>"
                output_content = output_content.replace(
                    "</body>",
                    runtime + "</body>",
                )
            return output_content

        soup = BeautifulSoup(output_content, "html.parser")
        if self.pymdownx:
            sections = soup.find_all("script", type="WaveDrom")
        else:
            # both classic (wavedrom) and modern (language-wavedrom) classes
            sections = soup.select("code.wavedrom, code.language-wavedrom")

        f_exists = False
        for section in sections:
            f_exists = True
            is_code = section.name == "code"
            if self.embed_svg:
                # render to svg and embed at build time
                source = section.get_text()
                svg = wavedrom.render(source).tostring()
                new_soup = BeautifulSoup(svg, "html.parser")
            else:
                # replace code with script
                new_soup = section
                new_soup.name = "script"
                new_soup["type"] = "WaveDrom"

            # replace existing element
            if is_code:
                # replace <pre>
                section.parent.replace_with(new_soup)
            else:
                # replace <script>
                section.replace_with(new_soup)

        # pymdownx
        if len(soup.find_all("script", type="WaveDrom")) > 0:
            f_exists = True

        if f_exists and not self.embed_svg and not self.theme_switch:
            new_tag = soup.new_tag("script")
            new_tag.string = _PROCESS_ALL_JS
            soup.find("body").append(new_tag)

        html = str(soup)
        if f_exists and not self.embed_svg and self.theme_switch:
            # appended after serialization: bs4 escapes "<" in script tags
            html = html.replace("</body>", self._theme_switch_script() + "</body>")
        return html
