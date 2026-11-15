"""Modo lectura y vídeo flotante (picture-in-picture propio)."""
from .motor import *  # noqa: F401,F403

JS_LECTURA = r"""(()=>{const id='__aurora_lectura';const ya=document.getElementById(id);
const cerrar=()=>{const d=document.getElementById(id);if(d)d.remove();document.documentElement.style.overflow=''};
if(ya){cerrar();return 'cerrado'}
const puntuar=e=>{let t=0;e.querySelectorAll('p').forEach(p=>{const n=p.innerText.trim().length;if(n>40)t+=n});return t};
let mejor=null,pmax=0;
const cands=[...document.querySelectorAll('article,main,[role=main],.post,.article,.entry-content,.post-content,#content,.content')];
(cands.length?cands:[document.body]).forEach(e=>{const s=puntuar(e);if(s>pmax){pmax=s;mejor=e}});
if(!mejor||pmax<400){const m=new Map();document.querySelectorAll('p').forEach(p=>{const par=p.parentElement;
 m.set(par,(m.get(par)||0)+p.innerText.length)});m.forEach((v,k)=>{if(v>pmax){pmax=v;mejor=k}})}
if(!mejor||pmax<300)return 'nada';
const c=mejor.cloneNode(true);
c.querySelectorAll('script,style,noscript,iframe,form,button,input,nav,aside,footer,[aria-hidden=true],.ad,.ads,.advert,.share,.social,.related,.newsletter,svg').forEach(e=>e.remove());
c.querySelectorAll('*').forEach(e=>{['style','class','width','height','id'].forEach(a=>e.removeAttribute(a))});
c.querySelectorAll('img[data-src]').forEach(i=>{if(!i.getAttribute('src'))i.src=i.dataset.src});
const titulo=((document.querySelector('h1')||{}).innerText||document.title).trim();
const h1=c.querySelector('h1');if(h1&&h1.innerText.trim()===titulo)h1.remove();
const palabras=c.innerText.split(/\s+/).filter(Boolean).length;const min=Math.max(1,Math.round(palabras/220));
const d=document.createElement('div');d.id=id;
d.innerHTML=`<style>#${id}{position:fixed;inset:0;z-index:2147483647;overflow:auto;background:#101218;color:#dfe2ea;
animation:__al .35s cubic-bezier(.2,.8,.2,1) both;scroll-behavior:smooth}
@keyframes __al{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
#${id} .h{max-width:720px;margin:0 auto;padding:72px 28px 140px;font:19px/1.8 Georgia,"Iowan Old Style",Cambria,serif}
#${id} .m{font:13px "Segoe UI",system-ui,sans-serif;color:#8a90a2;letter-spacing:.3px;margin-bottom:12px}
#${id} h1.t{font:700 40px/1.2 "Segoe UI",system-ui,sans-serif;margin:0 0 34px;color:#fff;letter-spacing:-.5px}
#${id} img,#${id} video,#${id} figure{max-width:100%;height:auto;border-radius:12px;margin:12px 0}
#${id} figcaption{font:13px "Segoe UI",sans-serif;color:#8a90a2}
#${id} a{color:%%A%%;text-decoration:none;border-bottom:1px solid rgba(%%A_RGB%%,.4)}
#${id} h2,#${id} h3{font-family:"Segoe UI",system-ui,sans-serif;color:#fff;margin-top:1.8em;line-height:1.3}
#${id} pre,#${id} code{font:14px "Cascadia Code",Consolas,monospace;background:#1a1e27;border-radius:6px;padding:2px 6px}
#${id} pre{padding:16px;overflow:auto}#${id} blockquote{border-left:3px solid %%A%%;margin:1.4em 0;padding-left:20px;color:#b8bcc8}
#${id} .b{position:fixed;top:18px;right:24px;display:flex;gap:6px;font:14px "Segoe UI",sans-serif}
#${id} .b button{background:#1e2230;color:#dfe2ea;border:1px solid #2e3445;border-radius:10px;padding:8px 13px;cursor:pointer;transition:background .2s}
#${id} .b button:hover{background:#2a3040}
#${id} .p{position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,%%A%%,%%B%%);width:0}
#${id}.claro{background:#f7f3ea;color:#2b2b2b}#${id}.claro h1.t,#${id}.claro h2,#${id}.claro h3{color:#111}
#${id}.claro .b button{background:#fff;color:#333;border-color:#ddd}#${id}.claro pre,#${id}.claro code{background:#ece6d8}
</style><div class=p></div><div class=b><button data-a=menos title="Letra más pequeña">A−</button><button data-a=mas title="Letra más grande">A+</button>
<button data-a=tema title="Claro / oscuro">◐</button><button data-a=cerrar title="Salir (Esc)">✕</button></div>
<div class=h><div class=m></div><h1 class=t></h1></div>`;
d.querySelector('.m').textContent=location.hostname+' · '+min+' min de lectura';
d.querySelector('h1.t').textContent=titulo;d.querySelector('.h').appendChild(c);
let tam=19;d.addEventListener('click',e=>{const a=e.target.dataset&&e.target.dataset.a;if(!a)return;const h=d.querySelector('.h');
 if(a==='cerrar')cerrar();else if(a==='tema')d.classList.toggle('claro');else{tam=Math.max(14,Math.min(28,tam+(a==='mas'?1:-1)));h.style.fontSize=tam+'px'}});
d.addEventListener('scroll',()=>{const max=d.scrollHeight-d.clientHeight;d.querySelector('.p').style.width=(max>0?d.scrollTop/max*100:0)+'%'});
document.addEventListener('keydown',function k(e){if(e.key==='Escape'&&document.getElementById(id)){cerrar();document.removeEventListener('keydown',k)}});
document.documentElement.style.overflow='hidden';document.body.appendChild(d);return 'abierto'})()"""

JS_VIDEO_INFO = r"""(()=>{const v=[...document.querySelectorAll('video')].filter(v=>v.offsetWidth*v.offsetHeight>0)
.sort((a,b)=>b.offsetWidth*b.offsetHeight-a.offsetWidth*a.offsetHeight)[0];
if(!v)return null;const r={t:v.currentTime||0};v.pause();return JSON.stringify(r)})()"""

JS_VIDEO_SOLO = r"""((t)=>{const v=[...document.querySelectorAll('video')].sort((a,b)=>b.offsetWidth*b.offsetHeight-a.offsetWidth*a.offsetHeight)[0];
if(!v)return 0;if(!document.getElementById('__aurora_pip')){const s=document.createElement('style');s.id='__aurora_pip';
s.textContent='html,body{overflow:hidden!important;background:#000!important}video.__aurora_v{position:fixed!important;inset:0!important;'+
'width:100vw!important;height:100vh!important;z-index:2147483647!important;object-fit:contain!important;background:#000!important;'+
'max-width:none!important;max-height:none!important;transform:none!important;left:0!important;top:0!important}';
document.documentElement.appendChild(s)}
v.classList.add('__aurora_v');if(!v.__aurora_t&&t>0){v.__aurora_t=1;v.currentTime=t}v.play().catch(()=>{});return 1})(%s)"""

JS_VIDEO_TIEMPO = r"""(()=>{const v=document.querySelector('video.__aurora_v')||document.querySelector('video');if(!v)return -1;
v.pause();return v.currentTime})()"""

JS_VIDEO_SEGUIR = r"""((t)=>{const v=[...document.querySelectorAll('video')].sort((a,b)=>b.offsetWidth*b.offsetHeight-a.offsetWidth*a.offsetHeight)[0];
if(v){if(t>=0)v.currentTime=t;v.play().catch(()=>{})}})(%s)"""


class VentanaFlotante(QWidget):
    """Mini ventana siempre encima con el vídeo. Se mueve arrastrando la barra y se redimensiona por la esquina."""

    def __init__(self, ventana, url, tiempo):
        super().__init__(None, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.v, self.tiempo, self.origen = ventana, tiempo, ventana.vista()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setObjectName("flotante")
        self.resize(520, 322)
        pantalla = QApplication.primaryScreen().availableGeometry()
        self.move(pantalla.right() - self.width() - 24, pantalla.bottom() - self.height() - 24)
        l = QVBoxLayout(self)
        l.setContentsMargins(1, 1, 1, 1)
        l.setSpacing(0)
        barra = QWidget(objectName="barraFlotante")
        barra.setFixedHeight(32)
        hb = QHBoxLayout(barra)
        hb.setContentsMargins(12, 0, 4, 0)
        self.titulo = QLabel(ventana.vista().title(), objectName="tenue")
        volver = BotonIcono("abrir", "Volver a la pestaña", tam=28)
        cerrar = BotonIcono("cerrar", "Cerrar", tam=28)
        volver.clicked.connect(self.volver)
        cerrar.clicked.connect(self.close)
        hb.addWidget(self.titulo, 1)
        hb.addWidget(volver)
        hb.addWidget(cerrar)
        self.web = QWebEngineView()
        self.web.setPage(QWebEnginePage(ventana.perfil, self.web))
        l.addWidget(barra)
        l.addWidget(self.web, 1)
        esquina = QSizeGrip(self)
        esquina.setFixedSize(16, 16)
        self._esquina = esquina
        barra.installEventFilter(self)
        self.titulo.installEventFilter(self)
        self._arrastre = None
        self.intentos = 0
        self.reloj = QTimer(self, interval=700)
        self.reloj.timeout.connect(self._preparar)
        self.web.loadFinished.connect(lambda ok: (self.reloj.start(), self._preparar()))
        self.web.setUrl(url)

    def _preparar(self):
        self.intentos += 1
        if self.intentos > 20:
            self.reloj.stop()
        self.web.page().runJavaScript(JS_VIDEO_SOLO % json.dumps(self.tiempo),
                                      lambda r: self.reloj.stop() if r == 1 and self.intentos > 3 else None)

    def volver(self):
        def seguir(t):
            try:
                self.origen.page().runJavaScript(JS_VIDEO_SEGUIR % json.dumps(float(t)))
            except RuntimeError:
                pass
            self.close()
        self.web.page().runJavaScript(JS_VIDEO_TIEMPO, seguir)

    def resizeEvent(self, e):
        self._esquina.move(self.width() - 16, self.height() - 16)
        self._esquina.raise_()

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Type.MouseButtonPress and e.button() == Qt.MouseButton.LeftButton:
            self._arrastre = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            return True
        if e.type() == QEvent.Type.MouseMove and self._arrastre is not None:
            self.move(e.globalPosition().toPoint() - self._arrastre)
            return True
        if e.type() == QEvent.Type.MouseButtonRelease:
            self._arrastre = None
        return False

    def closeEvent(self, e):
        self.reloj.stop()
        self.web.setUrl(QUrl("about:blank"))
        if self in self.v.flotantes:
            self.v.flotantes.remove(self)
        super().closeEvent(e)


class MixinMultimedia:
    def iniciar_multimedia(self):
        self.flotantes = []

    def modo_lectura(self):
        js = (JS_LECTURA.replace("%%A_RGB%%", rgb(T.a1)).replace("%%A%%", T.a1).replace("%%B%%", T.a2))

        def hecho(r):
            if r == "nada":
                self.aviso.mostrar("📖  No encuentro un artículo para leer en esta página")
            elif r == "abierto":
                self.aviso.mostrar("📖  Modo lectura · Esc para salir")
        self.vista().page().runJavaScript(js, hecho)

    def video_flotante(self):
        vista = self.vista()

        def abrir(info):
            if not info:
                self.aviso.mostrar("🎬  No hay ningún vídeo en esta página")
                return
            t = float(json.loads(info).get("t", 0))
            url = QUrl(vista.url())
            f = VentanaFlotante(self, url, t)
            self.flotantes.append(f)
            f.show()
            self.aviso.mostrar("🎬  Vídeo flotante · arrastra la barra para moverlo")
        vista.page().runJavaScript(JS_VIDEO_INFO, abrir)
