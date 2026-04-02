import subprocess
import os
import shutil
import tempfile
import glob

import pytest

PROJECTS_DIR = os.path.dirname(__file__)


def _build_project(project_name):
    project_dir = os.path.join(PROJECTS_DIR, project_name)
    site_dir = os.path.join(project_dir, "site")
    if os.path.exists(site_dir):
        shutil.rmtree(site_dir)
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    subprocess.run(
        ["uv", "sync"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    subprocess.run(
        ["uv", "run", "mkdocs", "build"],
        cwd=project_dir,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    html_files = glob.glob(os.path.join(site_dir, "**", "*.html"), recursive=True)
    return site_dir, html_files


def _read_file(path):
    with open(path, "r") as f:
        return f.read()


class TestDefaultMode:
    """Default mode: code blocks are replaced with <script type="WaveDrom">
    and ProcessAll() is appended."""

    def test_html_contains_wavedrom_script(self):
        site_dir, html_files = _build_project("e2e_default")
        for f in html_files:
            content = _read_file(f)
            if "signal" in content:
                assert 'type="WaveDrom"' in content

    def test_no_svg_embedded(self):
        site_dir, html_files = _build_project("e2e_default")
        for f in html_files:
            content = _read_file(f)
            assert "<svg" not in content

    def test_process_all_present(self):
        site_dir, html_files = _build_project("e2e_default")
        for f in html_files:
            content = _read_file(f)
            if "WaveDrom" in content:
                assert "WaveDrom.ProcessAll()" in content

    def test_no_code_block_remains(self):
        site_dir, html_files = _build_project("e2e_default")
        for f in html_files:
            content = _read_file(f)
            assert "<code" not in content
            assert "<pre>" not in content


class TestPymdownxMode:
    """Pymdownx mode: script tags inserted by superfences are kept,
    ProcessAll() is appended via string replacement."""

    def test_wavedrom_script_preserved(self):
        site_dir, html_files = _build_project("e2e_pymdownx")
        for f in html_files:
            content = _read_file(f)
            if "signal" in content:
                assert 'type="WaveDrom"' in content
                assert (
                    '{ signal: [{ name: "Alfa", wave: "01.zx=ud.23.45" }] }' in content
                )

    def test_no_svg_embedded(self):
        site_dir, html_files = _build_project("e2e_pymdownx")
        for f in html_files:
            content = _read_file(f)
            assert "<svg" not in content

    def test_process_all_present(self):
        site_dir, html_files = _build_project("e2e_pymdownx")
        for f in html_files:
            content = _read_file(f)
            if "WaveDrom" in content:
                assert "WaveDrom.ProcessAll()" in content


class TestEmbedSvgMode:
    """Embed SVG mode: wavedrom JSON is rendered to SVG at build time,
    no JavaScript required."""

    def test_svg_embedded(self):
        site_dir, html_files = _build_project("e2e_embed_svg")
        found_svg = False
        for f in html_files:
            content = _read_file(f)
            if "<svg" in content:
                found_svg = True
        assert found_svg

    def test_no_wavedrom_script(self):
        site_dir, html_files = _build_project("e2e_embed_svg")
        for f in html_files:
            content = _read_file(f)
            assert 'type="WaveDrom"' not in content

    def test_no_process_all(self):
        site_dir, html_files = _build_project("e2e_embed_svg")
        for f in html_files:
            content = _read_file(f)
            assert "WaveDrom.ProcessAll()" not in content

    def test_svg_has_signal_name(self):
        site_dir, html_files = _build_project("e2e_embed_svg")
        for f in html_files:
            content = _read_file(f)
            if "<svg" in content:
                assert "Alfa" in content


class TestPymdownxEmbedSvgMode:
    """Pymdownx + embed SVG: superfences script tags are rendered to SVG,
    useful with navigation.instant."""

    def test_svg_embedded(self):
        site_dir, html_files = _build_project("e2e_pymdownx_embed_svg")
        found_svg = False
        for f in html_files:
            content = _read_file(f)
            if "<svg" in content:
                found_svg = True
        assert found_svg

    def test_no_wavedrom_script(self):
        site_dir, html_files = _build_project("e2e_pymdownx_embed_svg")
        for f in html_files:
            content = _read_file(f)
            assert 'type="WaveDrom"' not in content

    def test_no_process_all(self):
        site_dir, html_files = _build_project("e2e_pymdownx_embed_svg")
        for f in html_files:
            content = _read_file(f)
            assert "WaveDrom.ProcessAll()" not in content

    def test_svg_has_signal_name(self):
        site_dir, html_files = _build_project("e2e_pymdownx_embed_svg")
        for f in html_files:
            content = _read_file(f)
            if "<svg" in content:
                assert "Alfa" in content
