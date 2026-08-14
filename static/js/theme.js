(function () {
  var root = document.documentElement;
  var button = document.getElementById('theme-toggle');
  if (!button) return;

  function currentTheme() {
    var stored = localStorage.getItem('theme');
    if (stored === 'dark' || stored === 'light') return stored;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    root.setAttribute('data-theme', theme);
    button.textContent = theme === 'dark' ? '☀️' : '🌙';
    var label = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
    button.setAttribute('aria-label', label);
    button.setAttribute('title', label);

    var color = theme === 'dark' ? '#1c1c1e' : '#f2f2f7';
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
      meta.removeAttribute('media');
      meta.setAttribute('content', color);
    });
  }

  applyTheme(currentTheme());

  button.addEventListener('click', function () {
    var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
  });
})();