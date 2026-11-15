"""Hoja de estilo de la interfaz."""
from .comun import *  # noqa: F401,F403


# ═════════════════════════════ estilo

def hoja_estilo():
    c = C
    marca = DATOS / "marca.svg"
    if not marca.exists():
        marca.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 18 18"><path d="M4.5 9.5l3 3 6-7" '
                         'fill="none" stroke="white" stroke-width="2.2" stroke-linecap="round" '
                         'stroke-linejoin="round"/></svg>', encoding="utf-8")
    ruta_marca = marca.as_posix()
    return f"""
* {{ color: {c['texto']}; outline: none; }}
QMainWindow, #central, #cabecera, #barra {{ background: {c['fondo']}; }}
QToolTip {{ background: #1b1f29; color: {c['texto']}; border: 1px solid {c['borde']}; border-radius: 6px; padding: 5px 8px; }}
QMenu {{ background: #161a22; border: 1px solid {c['borde']}; border-radius: 12px; padding: 6px; }}
QMenu::item {{ padding: 7px 28px 7px 14px; border-radius: 7px; }}
QMenu::item:selected {{ background: rgba({rgb(T.a1)},0.25); }}
QMenu::separator {{ height: 1px; background: {c['borde']}; margin: 5px 8px; }}
#omniEntrada {{ background: transparent; border: none; font-size: 10.5pt; selection-background-color: {T.a1}; }}
#popupOmni {{ background: #161a22; border: 1px solid {c['borde']}; padding: 4px; }}
#popupOmni::item {{ padding: 7px 10px; border-radius: 6px; }}
#popupOmni::item:selected {{ background: rgba({rgb(T.a1)},0.28); }}
#panel {{ background: {c['barra']}; }}
#tituloPanel {{ font-weight: 600; font-size: 10.5pt; padding: 8px 2px; }}
#tenue {{ color: {c['tenue']}; }}
QTabWidget::pane {{ border: none; }}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{ background: transparent; color: {c['tenue']}; padding: 7px 13px; margin: 0 3px 8px 0; border-radius: 8px; border: none; }}
QTabBar::tab:selected {{ background: {c['chip_activo']}; color: {c['texto']}; }}
QTabBar::tab:hover:!selected {{ background: {c['chip']}; color: {c['texto']}; }}
QLineEdit, QPlainTextEdit, QComboBox {{ background: {c['chip']}; border: 1px solid {c['borde']}; border-radius: 8px; padding: 6px 9px; selection-background-color: {T.a1}; }}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{ border-color: {T.a1}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: #161a22; border: 1px solid {c['borde']}; selection-background-color: rgba({rgb(T.a1)},0.3); padding: 4px; }}
QPushButton {{ background: {c['chip']}; border: 1px solid {c['borde']}; border-radius: 8px; padding: 7px 12px; text-align: left; }}
QPushButton:hover {{ background: {c['chip_hover']}; border-color: #3b4254; }}
QPushButton:pressed {{ background: {c['chip_activo']}; }}
#seccion {{ color: {c['tenue']}; font-size: 8pt; font-weight: 700; padding-top: 14px; }}
QTableWidget {{ background: {c['chip']}; border: 1px solid {c['borde']}; border-radius: 8px; gridline-color: transparent; }}
QHeaderView::section {{ background: {c['barra']}; color: {c['tenue']}; border: none; padding: 5px 8px; }}
QTableWidget::item {{ padding: 0 6px; }}
QTableWidget::item:selected {{ background: rgba({rgb(T.a1)},0.25); }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: #2c3241; border-radius: 3px; min-height: 30px; min-width: 30px; }}
QScrollBar::handle:hover {{ background: #3c4459; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
#tarjeta {{ background: #141821; border: 1px solid #2d3343; border-radius: 18px; }}
#paletaEntrada {{ background: transparent; border: none; font-size: 13pt; padding: 10px 8px; }}
#paletaLista {{ background: transparent; border: none; }}
#aviso {{ background: #1c2130; border: 1px solid #353c50; border-radius: 12px; padding: 10px 18px; }}
#buscador {{ background: #161a23; border: 1px solid {c['borde']}; border-radius: 12px; }}
#buscador QLineEdit {{ border: none; background: transparent; padding: 4px; }}
#pregunta {{ background: #161a23; border: 1px solid {c['borde']}; border-radius: 14px; }}
#tituloPregunta {{ font-weight: 600; font-size: 10.5pt; }}
#hoja {{ background: #10131a; border: 1px solid #2a3040; border-radius: 20px; }}
#navAjustes {{ background: transparent; border-right: 1px solid {c['borde']}; }}
#tituloAjustes {{ font-size: 17pt; font-weight: 600; padding: 0 6px 14px 6px; }}
#listaAjustes {{ background: transparent; border: none; }}
#tituloSeccion {{ font-size: 15pt; font-weight: 600; padding: 22px 28px 12px 28px; }}
#tarjetaAjuste {{ background: #161a23; border: 1px solid {c['borde']}; border-radius: 14px; }}
#separador {{ background: {c['borde']}; margin: 0 16px; border: none; }}
#filaTitulo {{ font-size: 10pt; }}
#tecla {{ background: {c['chip']}; border: 1px solid {c['borde']}; border-radius: 6px; padding: 2px 8px; color: {c['tenue']}; }}
QPushButton#primario {{ background: {T.a1}; border-color: {T.a1}; color: white; font-weight: 600; }}
QPushButton#primario:hover {{ background: {QColor(T.a1).lighter(115).name()}; }}
QPushButton#peligro {{ background: rgba(255,107,129,0.10); border-color: rgba(255,107,129,0.45); color: #ff8b9c; }}
QPushButton#peligro:hover {{ background: rgba(255,107,129,0.2); }}
QCheckBox {{ spacing: 10px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1px solid #3a4152; background: {c['chip']}; }}
QCheckBox::indicator:checked {{ background: {T.a1}; border-color: {T.a1}; image: url({ruta_marca}); }}
QDialog, QMessageBox {{ background: #12151c; }}
#insignia {{ background: rgba(139,92,246,0.18); color: #c4b5fd; border: 1px solid rgba(139,92,246,0.35); border-radius: 13px; padding: 4px 12px; font-weight: 600; }}
#panelDescargas {{ background: #141821; border: 1px solid #2d3343; border-radius: 16px; }}
#itemDescarga {{ background: {c['chip']}; border: 1px solid {c['borde']}; border-radius: 12px; }}
QPushButton#chipIA {{ border-radius: 14px; padding: 6px 12px; text-align: center; }}
QPushButton#chipIA:hover {{ border-color: {T.a1}; }}
#chatIA {{ background: {c['chip']}; border: 1px solid {c['borde']}; border-radius: 12px; padding: 8px; }}
#flotante {{ background: #000; border: 1px solid #2d3343; }}
#barraFlotante {{ background: #12151c; }}
QSplitter#divisor::handle {{ background: {c['fondo']}; }}
QSplitter#divisor::handle:hover {{ background: {T.a1}; }}
#error {{ color: #ff8b9c; }}
#listaAuditoria {{ background: {c['chip']}; border: 1px solid {c['borde']}; border-radius: 10px; padding: 4px; }}
#listaAuditoria::item {{ padding: 7px 6px; border-bottom: 1px solid {c['borde']}; }}
#listaAuditoria::item:selected {{ background: rgba({rgb(T.a1)},0.2); }}
"""
