(function () {
  var toggle = document.getElementById('nav-toggle');
  var links = document.getElementById('nav-links');
  var backdrop = document.getElementById('nav-backdrop');
  if (!toggle || !links) return;

  function isOpen() {
    return links.classList.contains('nav-open');
  }

  function setOpen(open) {
    links.classList.toggle('nav-open', open);
    if (backdrop) backdrop.classList.toggle('nav-backdrop-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    toggle.classList.toggle('nav-toggle-open', open);
    document.body.classList.toggle('nav-drawer-open', open);
  }

  toggle.addEventListener('click', function () {
    setOpen(!isOpen());
  });

  links.addEventListener('click', function (event) {
    if (event.target.tagName === 'A') setOpen(false);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape' && isOpen()) {
      setOpen(false);
      toggle.focus();
    }
  });

  document.addEventListener('click', function (event) {
    if (!isOpen()) return;
    if (links.contains(event.target) || toggle.contains(event.target)) return;
    setOpen(false);
  });

  window.addEventListener('resize', function () {
    if (window.innerWidth > 640) setOpen(false);
  });
})();
