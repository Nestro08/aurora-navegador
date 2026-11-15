"""Organización de pestañas: menús contextuales, grupos, fijar, silenciar, dormir y pantalla dividida."""
import time

from .pestanas import *  # noqa: F401,F403


class MixinOrganizacion:
    """Métodos que se añaden a la Ventana."""

    def iniciar_organizacion(self):
        self.grupos = self.tira.grupos
        self.division = None  # (chip_izquierda, chip_derecha, divisor)
        self._ignorar_foco_hasta = 0.0
        self.tira.menu_pedido.connect(self.menu_pestana)
        self.tira.menu_grupo_pedido.connect(self.menu_grupo)
        self.tira.plegar_pedido.connect(self.plegar_grupo)
        self.tira.silenciar_pedido.connect(self.silenciar)
        self.reloj_dormir = QTimer(self, interval=60_000)
        self.reloj_dormir.timeout.connect(self.revisar_dormidas)
        self.reloj_dormir.start()
        QApplication.instance().focusChanged.connect(self._foco_cambiado)

    # ─────────────────────────────── menús
    def menu_pestana(self, chip, pos):
        m = menu_bonito(QMenu(self))
        url = chip.pagina.vista.url().toString()
        m.addAction("Nueva pestaña a la derecha", lambda: self.nueva_pestana_junto(chip))
        m.addAction("Recargar", chip.pagina.vista.reload)
        m.addAction("Duplicar", lambda: self.nueva_pestana_junto(chip, url))
        m.addSeparator()
        m.addAction("Desfijar" if chip.fijada else "Fijar", lambda: self.fijar(chip, not chip.fijada))
        m.addAction("Activar sonido" if chip.silenciada else "Silenciar pestaña", lambda: self.silenciar(chip))
        sub = menu_bonito(m.addMenu("Añadir a un grupo"))
        sub.addAction("＋  Grupo nuevo…", lambda: self.agrupar(chip, None))
        if self.grupos:
            sub.addSeparator()
        for gid, g in self.grupos.items():
            sub.addAction(f"●  {g['nombre'] or 'Sin nombre'}", lambda gid=gid: self.agrupar(chip, gid))
        if chip.grupo:
            m.addAction("Quitar del grupo", lambda: self.quitar_de_grupo(chip))
        m.addSeparator()
        if self.division and chip in self.division[:2]:
            m.addAction("Salir de la pantalla dividida", self.deshacer_division)
        elif chip is not self.chip_activo:
            m.addAction("Ver junto a la pestaña actual (pantalla dividida)",
                        lambda: self.dividir(self.chip_activo, chip))
        else:
            m.addAction("Dividir pantalla con una pestaña nueva", lambda: self.dividir(chip, None))
        if chip is not self.chip_activo and not chip.dormida:
            m.addAction("Dormir pestaña (libera memoria)", lambda: self.dormir(chip))
        m.addSeparator()
        m.addAction("Cerrar\tCtrl+W", lambda: self.cerrar(chip))
        m.addAction("Cerrar las demás", lambda: [self.cerrar(c) for c in list(self.tira.chips)
                                                 if c is not chip and not c.fijada])
        i = self.tira.chips.index(chip)
        m.addAction("Cerrar las de la derecha", lambda: [self.cerrar(c) for c in list(self.tira.chips[i + 1:])])
        m.exec(pos)

    def menu_grupo(self, gid, pos):
        g = self.grupos.get(gid)
        if not g:
            return
        m = menu_bonito(QMenu(self))
        m.addAction("Renombrar…", lambda: self.renombrar_grupo(gid))
        colores = menu_bonito(m.addMenu("Color"))
        for nombre, color in COLORES_GRUPO.items():
            a = colores.addAction(f"●  {nombre}", lambda c=color: self.color_grupo(gid, c))
            a.setCheckable(True)
            a.setChecked(g["color"] == color)
        m.addAction("Desplegar" if g["plegado"] else "Plegar", lambda: self.plegar_grupo(gid))
        m.addAction("Nueva pestaña en el grupo", lambda: self.nueva_en_grupo(gid))
        m.addSeparator()
        m.addAction("Desagrupar", lambda: self.desagrupar(gid))
        m.addAction("Cerrar el grupo", lambda: [self.cerrar(c) for c in list(self.tira.chips) if c.grupo == gid])
        m.exec(pos)

    def nueva_pestana_junto(self, chip, url=""):
        v = self.nueva_pestana(url)
        nuevo = self.chip_activo
        self.tira.chips.remove(nuevo)
        self.tira.chips.insert(self.tira.chips.index(chip) + 1, nuevo)
        nuevo.grupo = chip.grupo
        self.tira.normalizar()
        self.tira.recolocar()
        return v

    # ─────────────────────────────── grupos
    def agrupar(self, chip, gid):
        if gid is None:
            nombre, ok = QInputDialog.getText(self, "Grupo nuevo", "Nombre del grupo:",
                                              text=f"Grupo {len(self.grupos) + 1}")
            if not ok:
                return
            gid = f"g{int(time.time() * 1000)}"
            colores = list(COLORES_GRUPO.values())
            self.grupos[gid] = {"nombre": nombre.strip(), "color": colores[(len(self.grupos) + 1) % len(colores)],
                                "plegado": False}
        chip.fijada = False
        miembros = [c for c in self.tira.chips if c.grupo == gid and c is not chip]
        chip.grupo = gid
        if miembros:
            self.tira.chips.remove(chip)
            self.tira.chips.insert(self.tira.chips.index(miembros[-1]) + 1, chip)
        self._reordenar()

    def quitar_de_grupo(self, chip):
        gid = chip.grupo
        miembros = [c for c in self.tira.chips if c.grupo == gid]
        chip.grupo = None
        self.tira.chips.remove(chip)
        self.tira.chips.insert(self.tira.chips.index(miembros[-1]) + 1 if miembros[-1] is not chip
                               else len(self.tira.chips), chip)
        self._reordenar()

    def desagrupar(self, gid):
        for c in self.tira.chips:
            if c.grupo == gid:
                c.grupo = None
        self._reordenar()

    def renombrar_grupo(self, gid):
        nombre, ok = QInputDialog.getText(self, "Renombrar grupo", "Nombre del grupo:", text=self.grupos[gid]["nombre"])
        if ok:
            self.grupos[gid]["nombre"] = nombre.strip()
            self.tira.recolocar()

    def color_grupo(self, gid, color):
        self.grupos[gid]["color"] = color
        for c in self.tira.chips:
            c.update()
        self.tira.recolocar()

    def plegar_grupo(self, gid):
        g = self.grupos[gid]
        if not g["plegado"] and self.chip_activo and self.chip_activo.grupo == gid:
            fuera = [c for c in self.tira.chips if c.grupo != gid]
            if not fuera:
                self.aviso.mostrar("No puedes plegar el único grupo abierto")
                return
            self.activar(fuera[-1])
        g["plegado"] = not g["plegado"]
        self.tira.recolocar()

    def nueva_en_grupo(self, gid):
        miembros = [c for c in self.tira.chips if c.grupo == gid]
        if self.grupos[gid]["plegado"]:
            self.grupos[gid]["plegado"] = False
        self.nueva_pestana_junto(miembros[-1])

    def _reordenar(self):
        self.tira.normalizar()
        self.tira.limpiar_grupos()
        self.tira.recolocar()
        for c in self.tira.chips:
            c.update()

    # ─────────────────────────────── fijar, sonido, dormir
    def fijar(self, chip, fijada):
        chip.fijada = fijada
        if fijada:
            chip.grupo = None
        self._reordenar()

    def silenciar(self, chip):
        pagina = chip.pagina.vista.page()
        pagina.setAudioMuted(not pagina.isAudioMuted())

    def dormir(self, chip):
        if chip is self.chip_activo or chip.dormida or (self.division and chip in self.division[:2]):
            return
        pagina = chip.pagina.vista.page()
        try:
            E = QWebEnginePage.LifecycleState
            pagina.setLifecycleState(E.Frozen)
            pagina.setLifecycleState(E.Discarded)
            chip.dormida = True
            chip.update()
        except Exception:
            pass

    def despertar(self, chip):
        if chip.dormida:
            chip.pagina.vista.page().setLifecycleState(QWebEnginePage.LifecycleState.Active)
            chip.dormida = False
            chip.update()

    def revisar_dormidas(self):
        minutos = int(self.ajustes.datos.get("dormir_min") or 0)
        if not minutos:
            return
        limite = time.time() - minutos * 60
        for c in self.tira.chips:
            if c is not self.chip_activo and not c.sonando and c.ultimo_uso < limite:
                self.dormir(c)

    # ─────────────────────────────── pantalla dividida
    def dividir(self, izquierda, derecha=None):
        if self.division:
            self.deshacer_division()
        if derecha is None:
            self.nueva_pestana()
            derecha = self.chip_activo
        if izquierda is derecha:
            return
        divisor = QSplitter(Qt.Orientation.Horizontal, objectName="divisor")
        divisor.setHandleWidth(6)
        for chip in (izquierda, derecha):
            self.despertar(chip)
            self.pila.removeWidget(chip.pagina)
            divisor.addWidget(chip.pagina)
            chip.pagina.dividida = True
            chip.dividida = True
            chip.pagina.show()
            chip.pagina.colocar()
        divisor.setSizes([1000, 1000])
        self.pila.addWidget(divisor)
        self.division = (izquierda, derecha, divisor)
        self._ignorar_foco_hasta = time.time() + 0.8  # al mover las páginas llegan eventos de foco tardíos
        self.activar(derecha)
        derecha.pagina.vista.setFocus()
        self.aviso.mostrar("◫  Pantalla dividida · arrastra el centro para cambiar el tamaño")

    def deshacer_division(self):
        if not self.division:
            return
        izquierda, derecha, divisor = self.division
        self.division = None
        for chip in (izquierda, derecha):
            chip.pagina.dividida = chip.pagina.resaltada = False
            chip.dividida = False
            chip.pagina.setParent(None)
            self.pila.addWidget(chip.pagina)
            chip.pagina.colocar()
        self.pila.removeWidget(divisor)
        divisor.deleteLater()
        if self.chip_activo:
            self.pila.setCurrentWidget(self.chip_activo.pagina)

    def _mostrar_pagina(self, chip):
        """Pone en pantalla la página de la pestaña (o la pantalla dividida a la que pertenece)."""
        if self.division and chip in self.division[:2]:
            self.pila.setCurrentWidget(self.division[2])
            for c in self.division[:2]:
                c.pagina.resaltada = c is chip
                c.pagina.update()
        else:
            self.pila.setCurrentWidget(chip.pagina)

    def _foco_cambiado(self, viejo, nuevo):
        if not self.division or nuevo is None or time.time() < self._ignorar_foco_hasta:
            return
        for chip in self.division[:2]:
            if chip is not self.chip_activo and chip.pagina.isAncestorOf(nuevo):
                self.activar(chip, enfocar=False)
                return
