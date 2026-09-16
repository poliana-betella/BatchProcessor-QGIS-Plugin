# -*- coding: utf-8 -*-
from qgis.core import QgsMapLayer, QgsProject
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QProgressBar,
    QVBoxLayout,
)

from .geometry_batch import OPERATIONS, load_results, run_batch


class BatchGeometryDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("BatchProcessor — Operações geométricas em lote")
        self.resize(480, 480)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.operation_combo = QComboBox()
        for key, spec in OPERATIONS.items():
            self.operation_combo.addItem(spec["label"], key)
        form.addRow("Operação:", self.operation_combo)
        layout.addLayout(form)

        layout.addWidget(QLabel("Camadas (selecione uma ou mais):"))
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QListWidget.ExtendedSelection)
        self._populate_layers()
        layout.addWidget(self.layer_list, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        buttons = QDialogButtonBox()
        self.btn_run = buttons.addButton("Executar", QDialogButtonBox.ActionRole)
        self.btn_run.clicked.connect(self._on_run)
        buttons.addButton(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _populate_layers(self):
        for layer in QgsProject.instance().mapLayers().values():
            if layer.type() == QgsMapLayer.VectorLayer:
                item = QListWidgetItem(layer.name())
                item.setData(1000, layer.id())
                self.layer_list.addItem(item)

    def _on_run(self):
        selected_items = self.layer_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "BatchProcessor", "Selecione ao menos uma camada.")
            return

        layer_ids = [item.data(1000) for item in selected_items]
        layers = [QgsProject.instance().mapLayer(lid) for lid in layer_ids]
        layers = [l for l in layers if l is not None]

        operation_key = self.operation_combo.currentData()

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(layers))

        def _on_progress(done, total, layer_name):
            self.progress_bar.setValue(done)
            if layer_name:
                self.status_label.setText("Processando: {}".format(layer_name))

        results = run_batch(layers, operation_key, progress_callback=_on_progress)
        self.progress_bar.setVisible(False)

        loaded = load_results(results)
        failed = [r for r in results if not r["ok"]]

        summary = "{} de {} camada(s) processada(s) com sucesso.".format(loaded, len(results))
        self.status_label.setText(summary)

        if failed:
            details = "\n".join("- {}: {}".format(r["layer"], r["error"]) for r in failed)
            QMessageBox.warning(self, "BatchProcessor",
                                 "{}\n\nFalhas:\n{}".format(summary, details))
        else:
            QMessageBox.information(self, "BatchProcessor", summary)
