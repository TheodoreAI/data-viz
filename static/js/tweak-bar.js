(function () {
  var STORAGE_KEY = 'tweakBarState';

  var FONT_FAMILIES = [
    { group: 'Sans', label: 'Inter (default)', value: 'Inter, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' },
    { group: 'Sans', label: 'System Sans', value: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif' },
    { group: 'Sans', label: 'Helvetica Neue', value: '"Helvetica Neue", Helvetica, Arial, sans-serif' },
    { group: 'Sans', label: 'Trebuchet MS', value: '"Trebuchet MS", sans-serif' },
    { group: 'Sans', label: 'Verdana', value: 'Verdana, Geneva, sans-serif' },
    { group: 'Sans', label: 'Tahoma', value: 'Tahoma, Geneva, sans-serif' },
    { group: 'Sans', label: 'Segoe UI', value: '"Segoe UI", Frutiger, sans-serif' },
    { group: 'Sans', label: 'Century Gothic', value: '"Century Gothic", "Apple Gothic", sans-serif' },
    { group: 'Sans', label: 'Calibri', value: 'Calibri, Candara, sans-serif' },
    { group: 'Sans', label: 'Arial Narrow', value: '"Arial Narrow", Arial, sans-serif' },

    { group: 'Serif', label: 'Georgia', value: 'Georgia, "Times New Roman", serif' },
    { group: 'Serif', label: 'PT Serif', value: '"PT Serif", Georgia, serif' },
    { group: 'Serif', label: 'Times New Roman', value: '"Times New Roman", Times, serif' },
    { group: 'Serif', label: 'Cambria', value: 'Cambria, Georgia, serif' },
    { group: 'Serif', label: 'Palatino', value: '"Palatino Linotype", Palatino, "Book Antiqua", serif' },
    { group: 'Serif', label: 'Garamond', value: 'Garamond, Baskerville, serif' },
    { group: 'Serif', label: 'Iowan Old Style', value: '"Iowan Old Style", "Palatino Linotype", serif' },
    { group: 'Serif', label: 'Didot', value: 'Didot, "Bodoni MT", serif' },

    { group: 'Monospace', label: 'System Mono', value: 'ui-monospace, "SF Mono", Consolas, monospace' },
    { group: 'Monospace', label: 'Courier New', value: '"Courier New", Courier, monospace' },
    { group: 'Monospace', label: 'Consolas', value: 'Consolas, "Lucida Console", monospace' },
    { group: 'Monospace', label: 'Lucida Console', value: '"Lucida Console", Monaco, monospace' },

    { group: 'Display', label: 'Impact', value: 'Impact, "Arial Narrow", sans-serif' },
    { group: 'Display', label: 'Copperplate', value: 'Copperplate, "Copperplate Gothic Light", serif' },
    { group: 'Display', label: 'Brush Script', value: '"Brush Script MT", cursive' },
    { group: 'Display', label: 'Comic Sans MS', value: '"Comic Sans MS", "Comic Sans", cursive' },
    { group: 'Display', label: 'Papyrus', value: 'Papyrus, fantasy' },
  ];

  var MOTION_PRESETS = ['none', 'fade-in', 'rise-in', 'pulse-accent'];

  var COLOR_BLIND_MODES = [
    { value: 'none', label: 'None' },
    { value: 'protanopia', label: 'Protanopia (red-blind)' },
    { value: 'deuteranopia', label: 'Deuteranopia (green-blind)' },
    { value: 'tritanopia', label: 'Tritanopia (blue-blind)' },
    { value: 'achromatopsia', label: 'Achromatopsia (no color)' },
  ];

  // feColorMatrix values approximating each vision-deficiency type (Coblis/Colorblindly matrices).
  var CB_MATRICES = {
    protanopia: '0.567 0.433 0 0 0  0.558 0.442 0 0 0  0 0.242 0.758 0 0  0 0 0 1 0',
    deuteranopia: '0.625 0.375 0 0 0  0.7 0.3 0 0 0  0 0.3 0.7 0 0  0 0 0 1 0',
    tritanopia: '0.95 0.05 0 0 0  0 0.433 0.567 0 0  0 0.475 0.525 0 0  0 0 0 1 0',
    achromatopsia: '0.299 0.587 0.114 0 0  0.299 0.587 0.114 0 0  0.299 0.587 0.114 0 0  0 0 0 1 0',
  };

  // fg/bg resolve state overrides first, falling back to the real token so the
  // checker also flags contrast issues that exist in the app's default theme.
  var CONTRAST_PAIRS = [
    { id: 'text-bg', label: 'Text / Background',
      fg: function () { return state.textColor || getVar('--text-primary'); },
      bg: function () { return state.surfaceColor || getVar('--surface-1'); }, under: null },
    { id: 'secondary-bg', label: 'Secondary text / Background',
      fg: function () { return state.secondaryTextColor || getVar('--text-secondary'); },
      bg: function () { return state.surfaceColor || getVar('--surface-1'); }, under: null },
    { id: 'text-card', label: 'Text / Card',
      fg: function () { return state.textColor || getVar('--text-primary'); },
      bg: function () { return state.cardBgColor || getVar('--card-bg'); }, under: 'surface' },
    { id: 'accent-bg', label: 'Accent / Background',
      fg: function () { return state.accentColor || getVar('--accent-1-strong'); },
      bg: function () { return state.surfaceColor || getVar('--surface-1'); }, under: null },
  ];

  // Maps each live-override control to the real :root custom properties it
  // touches, so the CSS override logic and the export logic read one list.
  var TOKEN_MAP = {
    headingWeight: { vars: ['--heading-weight'], format: function (v) { return String(v); } },
    textColor: { vars: ['--text-primary'], format: function (v) { return v; } },
    secondaryTextColor: { vars: ['--text-secondary', '--muted'], format: function (v) { return v; } },
    surfaceColor: { vars: ['--surface-1'], format: function (v) { return v; } },
    cardBgColor: { vars: ['--card-bg'], format: function (v) { return v; } },
    accentColor: { vars: ['--accent-1-strong', '--series-1'], format: function (v) { return v; } },
    radius: { vars: ['--card-radius'], format: function (v) { return v + 'px'; }, skip: function (v) { return v === 16; } },
  };

  var defaults = {
    enabled: true,
    open: false,
    fontFamily: FONT_FAMILIES[0].value,
    fontWeight: 400,
    headingWeight: 800,
    fontSize: 16,
    textColor: '',
    secondaryTextColor: '',
    surfaceColor: '',
    cardBgColor: '',
    accentColor: '',
    margin: 0,
    padding: 0,
    radius: 16,
    motion: 'none',
    motionSpeed: 0.6,
    colorBlindMode: 'none',
  };

  function loadState() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return Object.assign({}, defaults);
      return Object.assign({}, defaults, JSON.parse(raw));
    } catch (e) {
      return Object.assign({}, defaults);
    }
  }

  function saveState(state) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {}
  }

  var state = loadState();
  var root = document.documentElement;
  var styleTag = document.createElement('style');
  styleTag.id = 'tweak-bar-overrides';
  document.head.appendChild(styleTag);

  var colorProbe = document.createElement('div');
  colorProbe.style.display = 'none';
  document.body.appendChild(colorProbe);

  function getVar(name) {
    return getComputedStyle(root).getPropertyValue(name).trim();
  }

  // Normalizes any valid CSS color (hex, rgb(a), hsl, named) to {r,g,b,a} via
  // the computed-style trick, so the contrast checker doesn't need its own parser.
  function parseColorToRgba(value) {
    colorProbe.style.color = value;
    var computed = getComputedStyle(colorProbe).color;
    var m = computed.match(/rgba?\(([^)]+)\)/);
    if (!m) return { r: 0, g: 0, b: 0, a: 1 };
    var parts = m[1].split(',').map(function (s) { return parseFloat(s); });
    return { r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1 };
  }

  function compositeOver(fg, bg) {
    if (fg.a >= 1) return fg;
    var a = fg.a;
    return {
      r: fg.r * a + bg.r * (1 - a),
      g: fg.g * a + bg.g * (1 - a),
      b: fg.b * a + bg.b * (1 - a),
      a: 1,
    };
  }

  function relLuminance(rgb) {
    var chans = [rgb.r, rgb.g, rgb.b].map(function (v) {
      v = v / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * chans[0] + 0.7152 * chans[1] + 0.0722 * chans[2];
  }

  // WCAG contrast ratio; `underValue` composites a semi-transparent bg (e.g.
  // card-bg) over the page surface color first, so alpha is accounted for.
  function contrastRatio(fgValue, bgValue, underValue) {
    var white = { r: 255, g: 255, b: 255, a: 1 };
    var underRgb = underValue ? compositeOver(parseColorToRgba(underValue), white) : white;
    var bgRgb = compositeOver(parseColorToRgba(bgValue), underRgb);
    var fgRgb = compositeOver(parseColorToRgba(fgValue), bgRgb);
    var l1 = relLuminance(fgRgb);
    var l2 = relLuminance(bgRgb);
    var lighter = Math.max(l1, l2);
    var darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  function contrastGrade(ratio) {
    return { aa: ratio >= 4.5, aaa: ratio >= 7 };
  }

  function updateContrastReadouts() {
    var surface = state.surfaceColor || getVar('--surface-1');
    CONTRAST_PAIRS.forEach(function (pair) {
      var valueEl = document.getElementById('tb-contrast-' + pair.id + '-value');
      var aaEl = document.getElementById('tb-contrast-' + pair.id + '-aa');
      var aaaEl = document.getElementById('tb-contrast-' + pair.id + '-aaa');
      if (!valueEl) return;
      var ratio = contrastRatio(pair.fg(), pair.bg(), pair.under === 'surface' ? surface : null);
      var grade = contrastGrade(ratio);
      valueEl.textContent = ratio.toFixed(2) + ':1';
      aaEl.textContent = grade.aa ? 'AA' : 'AA ✕';
      aaEl.title = 'WCAG AA requires 4.5:1 for normal text';
      aaEl.className = 'tb-contrast-badge ' + (grade.aa ? 'tb-pass' : 'tb-fail');
      aaaEl.textContent = grade.aaa ? 'AAA' : 'AAA ✕';
      aaaEl.title = 'WCAG AAA requires 7:1 for normal text';
      aaaEl.className = 'tb-contrast-badge ' + (grade.aaa ? 'tb-pass' : 'tb-fail');
    });
  }

  function injectColorBlindFilters() {
    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('id', 'tweak-bar-cb-filters');
    svg.setAttribute('aria-hidden', 'true');
    svg.style.cssText = 'position:absolute;width:0;height:0;overflow:hidden;';
    var defs = document.createElementNS(svgNS, 'defs');
    Object.keys(CB_MATRICES).forEach(function (key) {
      var filter = document.createElementNS(svgNS, 'filter');
      filter.setAttribute('id', 'tb-cb-' + key);
      var cm = document.createElementNS(svgNS, 'feColorMatrix');
      cm.setAttribute('type', 'matrix');
      cm.setAttribute('values', CB_MATRICES[key]);
      filter.appendChild(cm);
      defs.appendChild(filter);
    });
    svg.appendChild(defs);
    document.body.appendChild(svg);
  }

  var STYLE_PROPS_TO_REPORT = [
    'color', 'background-color', 'font-family', 'font-size', 'font-weight',
    'line-height', 'letter-spacing', 'margin', 'padding', 'border-radius',
    'display', 'width', 'height',
  ];

  function cssPath(el) {
    if (!(el instanceof Element)) return '';
    var parts = [];
    var node = el;
    while (node && node.nodeType === 1 && parts.length < 6) {
      var part = node.tagName.toLowerCase();
      if (node.id) {
        part += '#' + node.id;
        parts.unshift(part);
        break;
      }
      var classes = Array.prototype.filter.call(node.classList, function (c) {
        return c && c !== 'tb-hover-outline';
      });
      if (classes.length) part += '.' + classes.join('.');
      var parent = node.parentElement;
      if (parent) {
        var siblings = Array.prototype.filter.call(parent.children, function (c) {
          return c.tagName === node.tagName;
        });
        if (siblings.length > 1) {
          part += ':nth-of-type(' + (siblings.indexOf(node) + 1) + ')';
        }
      }
      parts.unshift(part);
      node = node.parentElement;
    }
    return parts.join(' > ');
  }

  function describeElement(el) {
    var computed = window.getComputedStyle(el);
    var styleLines = STYLE_PROPS_TO_REPORT.map(function (prop) {
      return '  ' + prop + ': ' + computed.getPropertyValue(prop) + ';';
    }).join('\n');

    var attrs = Array.prototype.map.call(el.attributes || [], function (a) {
      return a.name + '="' + a.value + '"';
    }).join(' ');

    var text = (el.textContent || '').trim().replace(/\s+/g, ' ');
    if (text.length > 140) text = text.slice(0, 140) + '…';

    var outer = el.outerHTML || '';
    if (outer.length > 500) {
      outer = el.cloneNode(false).outerHTML;
    }

    return (
      'Element selected via tweak bar\n' +
      'Selector: ' + cssPath(el) + '\n' +
      'Tag: <' + el.tagName.toLowerCase() + '>\n' +
      (attrs ? 'Attributes: ' + attrs + '\n' : '') +
      (text ? 'Text: "' + text + '"\n' : '') +
      'Computed styles:\n' + styleLines + '\n' +
      'Markup:\n' + outer
    );
  }

  var pickerActive = false;
  var pickerHoverEl = null;
  var pickerOutline = document.createElement('div');
  pickerOutline.id = 'tweak-bar-picker-outline';
  var pickerLabel = document.createElement('div');
  pickerLabel.id = 'tweak-bar-picker-label';
  pickerOutline.appendChild(pickerLabel);

  function positionOutline(el) {
    var rect = el.getBoundingClientRect();
    pickerOutline.style.top = (rect.top + window.scrollY) + 'px';
    pickerOutline.style.left = (rect.left + window.scrollX) + 'px';
    pickerOutline.style.width = rect.width + 'px';
    pickerOutline.style.height = rect.height + 'px';
    var label = el.tagName.toLowerCase();
    if (el.id) label += '#' + el.id;
    else if (el.classList.length) label += '.' + el.classList[0];
    pickerLabel.textContent = label;
  }

  function onPickerMouseMove(event) {
    var el = document.elementFromPoint(event.clientX, event.clientY);
    if (!el || el === pickerHoverEl || pickerOutline.contains(el)) return;
    if (el.closest('#tweak-bar-panel, #tweak-bar-toggle, #tweak-bar-picker-outline')) {
      pickerOutline.style.display = 'none';
      pickerHoverEl = null;
      return;
    }
    pickerHoverEl = el;
    pickerOutline.style.display = 'block';
    positionOutline(el);
  }

  function onPickerClick(event) {
    if (event.target.closest('#tweak-bar-panel, #tweak-bar-toggle')) return;
    event.preventDefault();
    event.stopPropagation();
    var el = pickerHoverEl || event.target;
    var description = describeElement(el);
    copyToClipboard(description);
    stopPicking();
    flashPickerStatus('Copied ' + cssPath(el));
  }

  function onPickerKeydown(event) {
    if (event.key === 'Escape') stopPicking();
  }

  function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {
        fallbackCopy(text);
      });
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); } catch (e) {}
    document.body.removeChild(ta);
  }

  function flashStatus(el, message, timerKey) {
    if (!el) return;
    el.textContent = message;
    el.classList.add('tb-status-visible');
    window.clearTimeout(flashStatus[timerKey]);
    flashStatus[timerKey] = window.setTimeout(function () {
      el.classList.remove('tb-status-visible');
    }, 2200);
  }

  var pickerStatusEl = null;
  function flashPickerStatus(message) {
    flashStatus(pickerStatusEl, message, '_pickerTimer');
  }

  var exportStatusEl = null;
  function flashExportStatus(message) {
    flashStatus(exportStatusEl, message, '_exportTimer');
  }

  function startPicking() {
    if (pickerActive) return;
    pickerActive = true;
    document.body.classList.add('tb-picking');
    document.body.appendChild(pickerOutline);
    document.addEventListener('mousemove', onPickerMouseMove, true);
    document.addEventListener('click', onPickerClick, true);
    document.addEventListener('keydown', onPickerKeydown, true);
  }

  function stopPicking() {
    pickerActive = false;
    pickerHoverEl = null;
    document.body.classList.remove('tb-picking');
    pickerOutline.style.display = 'none';
    if (pickerOutline.parentNode) pickerOutline.parentNode.removeChild(pickerOutline);
    document.removeEventListener('mousemove', onPickerMouseMove, true);
    document.removeEventListener('click', onPickerClick, true);
    document.removeEventListener('keydown', onPickerKeydown, true);
    var btn = document.getElementById('tb-select-el');
    if (btn) {
      btn.textContent = 'Select element';
      btn.setAttribute('aria-pressed', 'false');
    }
  }

  function applyStyles() {
    var rules = [];

    if (state.fontFamily) {
      rules.push('body, button, input, select, textarea { font-family: ' + state.fontFamily + ' !important; }');
    }
    if (state.fontWeight) {
      rules.push('body, p, a, button, span, li { font-weight: ' + state.fontWeight + ' !important; }');
    }
    if (state.fontSize) {
      rules.push('html { font-size: ' + state.fontSize + 'px !important; }');
    }

    Object.keys(TOKEN_MAP).forEach(function (key) {
      var value = state[key];
      var token = TOKEN_MAP[key];
      if (!value || (token.skip && token.skip(value))) return;
      var formatted = token.format(value);
      var decls = token.vars.map(function (v) { return v + ': ' + formatted + ' !important;'; }).join(' ');
      rules.push(':root { ' + decls + ' }');
    });

    if (state.textColor) {
      rules.push('body { color: ' + state.textColor + ' !important; }');
    }
    if (state.secondaryTextColor) {
      rules.push('.subtitle, .navbar a, .theme-toggle { color: ' + state.secondaryTextColor + ' !important; }');
    }
    if (state.surfaceColor) {
      rules.push('body { background: ' + state.surfaceColor + ' !important; }');
    }
    if (state.accentColor) {
      rules.push('.navbar a.active, .save-button, .article-title a { color: ' + state.accentColor + ' !important; border-color: ' + state.accentColor + ' !important; }');
    }
    if (state.margin) {
      rules.push('.viz-root, .navbar, .footer { margin-left: ' + state.margin + 'px !important; margin-right: ' + state.margin + 'px !important; }');
    }
    if (state.padding) {
      rules.push('.viz-root { padding: ' + state.padding + 'px !important; }');
    }

    if (state.colorBlindMode && state.colorBlindMode !== 'none') {
      rules.push('html { filter: url(#tb-cb-' + state.colorBlindMode + ') !important; }');
    }

    if (state.motion === 'fade-in') {
      rules.push('@keyframes tweak-fade { from { opacity: 0; } to { opacity: 1; } }');
      rules.push('.viz-root, .navbar { animation: tweak-fade ' + state.motionSpeed + 's ease both; }');
    } else if (state.motion === 'rise-in') {
      rules.push('@keyframes tweak-rise { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: translateY(0); } }');
      rules.push('.viz-root, .navbar { animation: tweak-rise ' + state.motionSpeed + 's cubic-bezier(0.16, 1, 0.3, 1) both; }');
    } else if (state.motion === 'pulse-accent') {
      rules.push('@keyframes tweak-pulse { 0%, 100% { filter: brightness(1); } 50% { filter: brightness(1.15); } }');
      rules.push('.navbar a.active, .theme-toggle { animation: tweak-pulse ' + state.motionSpeed + 's ease-in-out infinite; }');
    }

    styleTag.textContent = rules.join('\n');
    updateContrastReadouts();
  }

  function buildExportCss() {
    var lines = [];
    Object.keys(TOKEN_MAP).forEach(function (key) {
      var value = state[key];
      var token = TOKEN_MAP[key];
      if (!value || (token.skip && token.skip(value))) return;
      var formatted = token.format(value);
      token.vars.forEach(function (v) {
        lines.push('  ' + v + ': ' + formatted + ';');
      });
    });
    if (!lines.length) return '';
    return ':root {\n' + lines.join('\n') + '\n}\n\n[data-theme="dark"] {\n' + lines.join('\n') + '\n}';
  }

  function buildPanel() {
    var panel = document.createElement('div');
    panel.id = 'tweak-bar-panel';
    panel.setAttribute('role', 'region');
    panel.setAttribute('aria-label', 'Dev tweak bar');

    var fontOptions = FONT_FAMILIES.reduce(function (acc, f, i) {
      var prevGroup = i > 0 ? FONT_FAMILIES[i - 1].group : null;
      if (f.group !== prevGroup) {
        if (prevGroup) acc.push('</optgroup>');
        acc.push('<optgroup label="' + f.group + '">');
      }
      var selected = f.value === state.fontFamily ? ' selected' : '';
      acc.push('<option value="' + f.value.replace(/"/g, '&quot;') + '"' + selected + '>' + f.label + '</option>');
      if (i === FONT_FAMILIES.length - 1) acc.push('</optgroup>');
      return acc;
    }, []).join('');

    var motionOptions = MOTION_PRESETS.map(function (m) {
      var selected = m === state.motion ? ' selected' : '';
      return '<option value="' + m + '"' + selected + '>' + m + '</option>';
    }).join('');

    var colorBlindOptions = COLOR_BLIND_MODES.map(function (m) {
      var selected = m.value === state.colorBlindMode ? ' selected' : '';
      return '<option value="' + m.value + '"' + selected + '>' + m.label + '</option>';
    }).join('');

    var contrastRows = CONTRAST_PAIRS.map(function (pair) {
      return (
        '<div class="tb-contrast-row">' +
          '<span class="tb-contrast-label">' + pair.label + '</span>' +
          '<span class="tb-contrast-meta">' +
            '<b id="tb-contrast-' + pair.id + '-value">—</b>' +
            '<span id="tb-contrast-' + pair.id + '-aa" class="tb-contrast-badge"></span>' +
            '<span id="tb-contrast-' + pair.id + '-aaa" class="tb-contrast-badge"></span>' +
          '</span>' +
        '</div>'
      );
    }).join('');

    panel.innerHTML =
      '<div class="tb-row tb-head">' +
        '<span class="tb-title">Tweak Bar <span class="tb-badge">dev</span></span>' +
        '<span class="tb-head-actions">' +
          '<button type="button" id="tb-export" class="tb-btn-ghost">Export CSS</button>' +
          '<button type="button" id="tb-reset" class="tb-btn-ghost">Reset</button>' +
        '</span>' +
      '</div>' +

      '<div class="tb-field">' +
        '<span>Element inspector</span>' +
        '<button type="button" id="tb-select-el" class="tb-btn-primary" aria-pressed="false">Select element</button>' +
        '<p id="tb-select-status" class="tb-status"></p>' +
      '</div>' +
      '<p id="tb-export-status" class="tb-status"></p>' +

      '<label class="tb-field">' +
        '<span>Font family</span>' +
        '<select id="tb-fontFamily">' + fontOptions + '</select>' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Font weight <b id="tb-fontWeight-val">' + state.fontWeight + '</b></span>' +
        '<input type="range" id="tb-fontWeight" min="100" max="900" step="100" value="' + state.fontWeight + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Heading weight <b id="tb-headingWeight-val">' + state.headingWeight + '</b></span>' +
        '<input type="range" id="tb-headingWeight" min="400" max="900" step="100" value="' + state.headingWeight + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Base font size <b id="tb-fontSize-val">' + state.fontSize + 'px</b></span>' +
        '<input type="range" id="tb-fontSize" min="12" max="22" step="1" value="' + state.fontSize + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Text color</span>' +
        '<input type="color" id="tb-textColor" value="' + (state.textColor || '#000000') + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Secondary text color</span>' +
        '<input type="color" id="tb-secondaryTextColor" value="' + (state.secondaryTextColor || '#6c6c70') + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Background color</span>' +
        '<input type="color" id="tb-surfaceColor" value="' + (state.surfaceColor || '#f2f2f7') + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Card background</span>' +
        '<input type="color" id="tb-cardBgColor" value="' + (state.cardBgColor || '#ffffff') + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Accent color</span>' +
        '<input type="color" id="tb-accentColor" value="' + (state.accentColor || '#5b5bf0') + '">' +
      '</label>' +

      '<div class="tb-group-title">Accessibility</div>' +
      contrastRows +

      '<label class="tb-field">' +
        '<span>Simulate color vision</span>' +
        '<select id="tb-colorBlindMode">' + colorBlindOptions + '</select>' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Page margin <b id="tb-margin-val">' + state.margin + 'px</b></span>' +
        '<input type="range" id="tb-margin" min="0" max="64" step="2" value="' + state.margin + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Content padding <b id="tb-padding-val">' + state.padding + 'px</b></span>' +
        '<input type="range" id="tb-padding" min="0" max="64" step="2" value="' + state.padding + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Card radius <b id="tb-radius-val">' + state.radius + 'px</b></span>' +
        '<input type="range" id="tb-radius" min="0" max="32" step="1" value="' + state.radius + '">' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Motion</span>' +
        '<select id="tb-motion">' + motionOptions + '</select>' +
      '</label>' +

      '<label class="tb-field">' +
        '<span>Motion speed <b id="tb-motionSpeed-val">' + state.motionSpeed + 's</b></span>' +
        '<input type="range" id="tb-motionSpeed" min="0.1" max="2" step="0.1" value="' + state.motionSpeed + '">' +
      '</label>';

    return panel;
  }

  function wirePanel(panel) {
    function bindRange(id, key, format) {
      var input = panel.querySelector('#' + id);
      var out = panel.querySelector('#' + id + '-val');
      input.addEventListener('input', function () {
        state[key] = Number(input.value);
        if (out) out.textContent = format ? format(state[key]) : state[key];
        applyStyles();
        saveState(state);
      });
    }

    function bindSelect(id, key) {
      var input = panel.querySelector('#' + id);
      input.addEventListener('change', function () {
        state[key] = input.value;
        applyStyles();
        saveState(state);
      });
    }

    function bindColor(id, key) {
      var input = panel.querySelector('#' + id);
      input.addEventListener('input', function () {
        state[key] = input.value;
        applyStyles();
        saveState(state);
      });
    }

    bindSelect('tb-fontFamily', 'fontFamily');
    bindRange('tb-fontWeight', 'fontWeight');
    bindRange('tb-headingWeight', 'headingWeight');
    bindRange('tb-fontSize', 'fontSize', function (v) { return v + 'px'; });
    bindColor('tb-textColor', 'textColor');
    bindColor('tb-secondaryTextColor', 'secondaryTextColor');
    bindColor('tb-surfaceColor', 'surfaceColor');
    bindColor('tb-cardBgColor', 'cardBgColor');
    bindColor('tb-accentColor', 'accentColor');
    bindSelect('tb-colorBlindMode', 'colorBlindMode');
    bindRange('tb-margin', 'margin', function (v) { return v + 'px'; });
    bindRange('tb-padding', 'padding', function (v) { return v + 'px'; });
    bindRange('tb-radius', 'radius', function (v) { return v + 'px'; });
    bindSelect('tb-motion', 'motion');
    bindRange('tb-motionSpeed', 'motionSpeed', function (v) { return v + 's'; });

    panel.querySelector('#tb-reset').addEventListener('click', function () {
      var open = state.open;
      state = Object.assign({}, defaults, { open: open });
      saveState(state);
      applyStyles();
      panel.replaceWith(buildAndWire());
    });

    exportStatusEl = panel.querySelector('#tb-export-status');
    panel.querySelector('#tb-export').addEventListener('click', function () {
      var css = buildExportCss();
      if (!css) {
        flashExportStatus('No token changes to export yet.');
        return;
      }
      copyToClipboard(css);
      flashExportStatus('Copied — paste over the token declarations in style.css.');
    });

    pickerStatusEl = panel.querySelector('#tb-select-status');

    panel.querySelector('#tb-select-el').addEventListener('click', function (event) {
      if (pickerActive) {
        stopPicking();
        return;
      }
      event.target.textContent = 'Click an element… (Esc to cancel)';
      event.target.setAttribute('aria-pressed', 'true');
      startPicking();
    });
  }

  function buildAndWire() {
    var panel = buildPanel();
    wirePanel(panel);
    return panel;
  }

  function init() {
    injectColorBlindFilters();

    var toggle = document.createElement('button');
    toggle.id = 'tweak-bar-toggle';
    toggle.type = 'button';
    toggle.setAttribute('aria-label', 'Toggle dev tweak bar');
    toggle.setAttribute('aria-expanded', String(state.open));
    toggle.title = 'Dev tweak bar';
    toggle.textContent = '🎛️';

    var panel = buildAndWire();
    panel.classList.toggle('tb-open', state.open);

    toggle.addEventListener('click', function () {
      state.open = !state.open;
      toggle.setAttribute('aria-expanded', String(state.open));
      panel.classList.toggle('tb-open', state.open);
      saveState(state);
    });

    document.body.appendChild(toggle);
    document.body.appendChild(panel);

    applyStyles();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
