// Theme-switch runtime for mkdocs-wavedrom-plugin, injected by plugin.py when
// `theme_switch: true` is enabled.
//
// Config: the <script> tag carries data-scheme-light / data-scheme-dark /
// data-skin-light / data-skin-dark attributes, read via document.currentScript.
//
// Renders every WaveDrom diagram with the skin matching the active Material
// color scheme and re-renders on palette switches. Both skin files (eg.
// skins/default.min.js and skins/dark.min.js) must be loaded on the page.
(function () {
    "use strict";

    // fallbacks mirror the WavedromConfig defaults in plugin.py
    var dataset = (document.currentScript) ? document.currentScript.dataset : {};
    var CFG = {
        schemeLight: dataset.schemeLight ? dataset.schemeLight.split(",") : ["default"],
        schemeDark: dataset.schemeDark ? dataset.schemeDark.split(",") : ["slate"],
        skinLight: dataset.skinLight || "default",
        skinDark: dataset.skinDark || "dark"
    };
    var current = null;
    var tries = 0;

    function getScheme() {
        var el;
        var scheme = "";
        el = document.body;
        if (el && el.getAttribute) {
            scheme = el.getAttribute("data-md-color-scheme") || "";
        }
        if (!scheme) {
            el = document.documentElement;
            if (el && el.getAttribute) {
                scheme = el.getAttribute("data-md-color-scheme") || "";
            }
        }
        if (!scheme) {
            try {
                var stored = window.localStorage.getItem("theme");
                if (stored) {
                    var value = JSON.parse(stored);
                    scheme = (typeof value === "string")
                        ? value
                        : (value["color-scheme"] || value.colorScheme || "");
                }
            } catch (e) {
                scheme = "";
            }
        }
        return scheme;
    }

    function getMode() {
        var scheme = getScheme();
        var i;
        for (i = 0; i < CFG.schemeDark.length; i++) {
            if (scheme === CFG.schemeDark[i]) {
                return "dark";
            }
        }
        return "light";
    }
    function getSkin() {
        return getMode() === "dark" ? CFG.skinDark : CFG.skinLight;
    }

    function getSources() {
        return Array.prototype.slice.call(
            document.querySelectorAll('script[type="WaveDrom"], script[type="wavedrom"]')
        );
    }

    function setSourceSkin(source, skin) {
        var original = source.textContent.trim();
        if (!original) {
            return;
        }
        try {
            var wave = eval("(" + original + ")");
            if (!wave.config) {
                wave.config = {};
            }
            wave.config.skin = skin;
            source.textContent = JSON.stringify(wave);
        } catch (e) {
            /* leave the diagram untouched */
        }
    }

    function removeRendered() {
        var els = document.querySelectorAll(".WaveDrom");
        var i;
        for (i = 0; i < els.length; i++) {
            els[i].remove();
        }
        els = document.querySelectorAll('[id^="WaveDrom_Display_"]');
        for (i = 0; i < els.length; i++) {
            els[i].remove();
        }
    }

    // WaveDrom >= 3.3.0 hardcodes a white sheet rect in every g#waves_<n>
    // group; make it transparent so the page background shows through.
    function clearSheet(root) {
        var nodes = [];
        if (!root || !root.querySelectorAll) {
            return;
        }
        if (root.localName === "svg") {
            nodes.push(root);
        } else {
            nodes = root.querySelectorAll("svg");
        }
        for (var i = 0; i < nodes.length; i++) {
            var rects = nodes[i].querySelectorAll('g[id^="waves_"] > rect');
            for (var k = 0; k < rects.length; k++) {
                rects[k].setAttribute("style", "stroke:none;fill:transparent");
            }
        }
    }

    function render(force) {
        if (typeof window.WaveDrom === "undefined" ||
            typeof window.WaveDrom.ProcessAll !== "function") {
            return false;
        }
        var mode = getMode();
        if (!force && mode === current) {
            return false;
        }
        current = mode;

        var sources = getSources();
        if (!sources.length) {
            return false;
        }

        var i;
        for (i = 0; i < sources.length; i++) {
            setSourceSkin(sources[i], getSkin());
        }
        removeRendered();

        window.requestAnimationFrame(function () {
            window.WaveDrom.ProcessAll();
            var displays = document.querySelectorAll(
                '[id^="WaveDrom_Display_"], .WaveDrom'
            );
            var j;
            for (j = 0; j < displays.length; j++) {
                if (displays[j].style) {
                    displays[j].style.backgroundColor = "transparent";
                }
                clearSheet(displays[j]);
            }
        });
        return true;
    }

    function initialize() {
        if (typeof window.WaveDrom === "undefined") {
            if (tries < 200) {
                tries += 1;
                window.setTimeout(initialize, 50);
            }
            return;
        }
        render(true);
    }

    window.addEventListener("load", initialize);

    if (typeof window.document$ !== "undefined" &&
        typeof window.document$.subscribe === "function") {
        window.document$.subscribe(function () {
            current = null;
            window.requestAnimationFrame(initialize);
        });
    }

    if (typeof window.MutationObserver !== "undefined") {
        var observer = new MutationObserver(function () { render(false); });
        var targets = [document.documentElement, document.body];
        var k;
        for (k = 0; k < targets.length; k++) {
            if (targets[k]) {
                observer.observe(targets[k], {
                    attributes: true,
                    attributeFilter: ["data-md-color-scheme"]
                });
            }
        }
    }

    window.addEventListener("storage", function () { render(false); });
})();

