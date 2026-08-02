if ('serviceWorker' in navigator) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('/static/sw.js').catch(function () {
      // Offline caching is a nice-to-have; ignore registration failures.
    });
  });
}
