/* Ajustes del admin (django-unfold). Lo carga UNFOLD["SCRIPTS"] (config/unfold.py). */
(() => {
  // Unfold dibuja los gráficos (Chart.js) con la fuente Inter, que aquí nunca se descarga porque el
  // admin usa Plus Jakarta Sans (static/css/admin.css); sin esto los ejes caen en una serif.
  // Cuando las fuentes están listas se toma la del body y se redibujan los gráficos.
  window.addEventListener('load', () => {
    document.fonts.ready.then(() => {
      if (!window.Chart) return;
      Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
      Object.values(Chart.instances).forEach((chart) => chart.update());
    });
  });
})();
