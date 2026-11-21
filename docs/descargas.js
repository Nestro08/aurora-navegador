// Lee la última Release de GitHub y prepara los botones de descarga según tu sistema.
// Si la API no responde, los botones siguen llevando a la página de la Release.
(() => {
  const REPO = "Nestro08/aurora-navegador";
  const ARCHIVOS = {
    instalador: /^Aurora-Setup-[\d.]+\.exe$/,
    portable: /^Aurora-[\d.]+-Windows-portable\.zip$/,
    linux: /^Aurora-[\d.]+-Linux\.zip$/,
    sumas: /^SHA256SUMS\.txt$/,
  };

  const ua = navigator.userAgent;
  const sistema = /Windows/i.test(ua) ? "windows"
    : /Android|iPhone|iPad/i.test(ua) ? "movil"
    : /Mac OS/i.test(ua) ? "mac"
    : /Linux|X11/i.test(ua) ? "linux" : "otro";

  const $ = (s) => document.querySelector(s);
  const mb = (bytes) => bytes < 1048576
    ? Math.max(1, Math.round(bytes / 1024)).toLocaleString("es-ES") + " KB"
    : (bytes / 1048576).toLocaleString("es-ES", { maximumFractionDigits: bytes < 10485760 ? 1 : 0 }) + " MB";

  // destaca la tarjeta de tu sistema
  const tarjeta = { windows: "#tarjeta-windows", linux: "#tarjeta-linux" }[sistema];
  if (tarjeta) $(tarjeta).classList.add("destacada");
  const notas = {
    mac: "Por ahora Aurora es para Windows y Linux.",
    movil: "Aurora es un navegador de escritorio: descárgalo desde tu ordenador con Windows o Linux.",
  };
  if (notas[sistema]) $("#nota-sistema").textContent = notas[sistema];

  fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { headers: { Accept: "application/vnd.github+json" } })
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((release) => {
      const version = String(release.tag_name || "").replace(/^v/, "");
      const archivos = {};
      for (const a of release.assets || []) {
        for (const [clave, patron] of Object.entries(ARCHIVOS)) {
          if (patron.test(a.name)) archivos[clave] = a;
        }
      }
      for (const enlace of document.querySelectorAll("[data-archivo]")) {
        const a = archivos[enlace.dataset.archivo];
        if (!a) continue;
        enlace.href = a.browser_download_url;
        const tam = enlace.querySelector("[data-tam]");
        if (tam) tam.textContent = `${a.name} · ${mb(a.size)}`;
      }
      if (archivos.sumas) $("#enlace-sumas").href = archivos.sumas.browser_download_url;
      if (version) $("#version-titulo").textContent = version;
      if (release.published_at) {
        const fecha = new Date(release.published_at).toLocaleDateString("es-ES", { day: "numeric", month: "long", year: "numeric" });
        $("#fecha-version").textContent = `Versión ${version}, publicada el ${fecha}.`;
      }

      // el botón grande de la portada: lo de tu sistema
      const principal = $("#boton-principal");
      const elegido = sistema === "windows" ? ["instalador", "Descargar para Windows", "Instalador"]
        : sistema === "linux" ? ["linux", "Descargar para Linux", "Paquete para Fedora"] : null;
      if (elegido && archivos[elegido[0]]) {
        const a = archivos[elegido[0]];
        principal.href = a.browser_download_url;
        $("#texto-principal").textContent = elegido[1];
        $("#detalle-principal").textContent = `Versión ${version} · ${elegido[2]} · ${mb(a.size)}`;
      } else {
        principal.href = "#descargar";
        $("#detalle-principal").textContent = `Versión ${version} · Windows y Linux`;
      }
    })
    .catch(() => { /* sin conexión con la API: los enlaces ya llevan a la página de la Release */ });
})();
