# -*- coding: utf-8 -*-
"""
Dialogo generico de validacao/QC: mostra um preview em memoria das feicoes
de uma camada, coloridas por categoria (com legenda), antes de o usuario
decidir se prossegue (ex.: exportar) ou cancela. As categorias e cores sao
configuraveis pelo chamador — nao ha nenhuma taxonomia fixa embutida aqui,
propositalmente, para que o dialogo sirva a qualquer fluxo de classificacao
(uso do solo, qualidade de dado, status de revisao, etc.).
"""
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFillSymbol,
    QgsRendererCategory,
    QgsVectorLayer,
)
from qgis.gui import QgsMapCanvas


class ValidationDialog(QDialog):
    """
    layer: camada de origem (poligonos) a validar.
    field_name: campo cujos valores definem a categoria de cada feição.
    category_styles: lista de (valor_do_campo, cor QColor, rótulo) — define
        a legenda e as cores; se um valor não estiver na lista, cai na
        categoria "Não classificado".
    context_layers: camadas extras exibidas como contexto (ex.: perímetro),
        sem participar da validação em si.
    """

    def __init__(self, layer, field_name, category_styles, context_layers=None,
                 title="Validação", message="Revise as feições antes de prosseguir.",
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(880, 680)

        self.layer = layer
        self.field_name = field_name
        self.category_styles = category_styles
        self.context_layers = context_layers or []

        self.preview_layer = self._build_preview_layer()

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(message))

        self.canvas = QgsMapCanvas()
        self.canvas.setCanvasColor(Qt.white)
        layout.addWidget(self.canvas, 1)

        legend_row = QHBoxLayout()
        for _value, color, label in self.category_styles:
            swatch = QLabel("  ")
            swatch.setStyleSheet(
                "background-color: rgb({},{},{}); border: 1px solid #333;".format(
                    color.red(), color.green(), color.blue()
                )
            )
            swatch.setFixedSize(14, 14)
            legend_row.addWidget(swatch)
            legend_row.addWidget(QLabel(label))
            legend_row.addSpacing(12)
        legend_row.addStretch()
        layout.addLayout(legend_row)

        buttons = QHBoxLayout()
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_proceed = QPushButton("Prosseguir")
        self.btn_proceed.clicked.connect(self.accept)
        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_proceed)
        layout.addLayout(buttons)

        self._apply_categorized_renderer()

        layers_to_show = [self.preview_layer] + list(self.context_layers)
        self.canvas.setLayers(layers_to_show)
        self.canvas.setExtent(self.layer.extent())
        self.canvas.refresh()

    def _build_preview_layer(self):
        """Copia as feições para uma camada em memória — a validação nunca
        toca a camada original, só o preview."""
        preview = QgsVectorLayer(
            "{}?crs={}".format(self._geometry_type_name(), self.layer.crs().authid()),
            self.layer.name() + " (preview)",
            "memory",
        )
        provider = preview.dataProvider()
        provider.addAttributes(self.layer.fields())
        preview.updateFields()
        provider.addFeatures([f for f in self.layer.getFeatures()])
        return preview

    def _geometry_type_name(self):
        from qgis.core import QgsWkbTypes
        geom_type = QgsWkbTypes.geometryType(self.layer.wkbType())
        if geom_type == QgsWkbTypes.PointGeometry:
            return "Point"
        if geom_type == QgsWkbTypes.LineGeometry:
            return "LineString"
        return "Polygon"

    def _apply_categorized_renderer(self):
        props = {"style": "solid", "outline_width": "0.26", "outline_color": "black"}
        categories = []

        for value, color, label in self.category_styles:
            symbol = QgsFillSymbol.createSimple({
                **props,
                "color": "{},{},{}".format(color.red(), color.green(), color.blue()),
            })
            categories.append(QgsRendererCategory(value, symbol, label))

        # categoria "coringa" para qualquer valor fora da lista configurada
        fallback_symbol = QgsFillSymbol.createSimple({**props, "color": "0,0,0"})
        categories.append(QgsRendererCategory(None, fallback_symbol, "Não classificado"))

        renderer = QgsCategorizedSymbolRenderer(self.field_name, categories)
        self.preview_layer.setRenderer(renderer)
