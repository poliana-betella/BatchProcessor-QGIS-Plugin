# -*- coding: utf-8 -*-
import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QInputDialog, QMessageBox


class BatchProcessorPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.batch_dialog = None

    def initGui(self):
        icon_path = os.path.join(os.path.dirname(__file__), "icon.png")
        icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()

        action_batch = QAction(icon, "Operações geométricas em lote...", self.iface.mainWindow())
        action_batch.triggered.connect(self.run_batch_geometry)
        self.iface.addPluginToMenu("&BatchProcessor", action_batch)
        self.actions.append(action_batch)

        action_validate = QAction(icon, "Validar camada ativa (preview QC)...", self.iface.mainWindow())
        action_validate.triggered.connect(self.run_validation_demo)
        self.iface.addPluginToMenu("&BatchProcessor", action_validate)
        self.actions.append(action_validate)

        action_bridge = QAction(icon, "Executar ferramenta externa...", self.iface.mainWindow())
        action_bridge.triggered.connect(self.run_external_tool_demo)
        self.iface.addPluginToMenu("&BatchProcessor", action_bridge)
        self.actions.append(action_bridge)

        for action in self.actions:
            self.iface.addVectorToolBarIcon(action)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu("&BatchProcessor", action)
            self.iface.removeVectorToolBarIcon(action)
        self.actions = []

    # ------------------------------------------------------------------

    def run_batch_geometry(self):
        from .batch_dialog import BatchGeometryDialog
        self.batch_dialog = BatchGeometryDialog(self.iface, parent=self.iface.mainWindow())
        self.batch_dialog.show()

    def run_validation_demo(self):
        """
        Abre o dialogo de validacao/QC para a camada ativa, usando um campo
        escolhido pelo usuario para colorir as feicoes por categoria.
        Serve como demonstracao generica do padrao — cada projeto real
        define suas proprias categorias/cores ao chamar ValidationDialog.
        """
        from qgis.PyQt.QtGui import QColor
        from .validation_dialog import ValidationDialog

        layer = self.iface.activeLayer()
        if layer is None or layer.type() != layer.VectorLayer:
            QMessageBox.warning(self.iface.mainWindow(), "BatchProcessor",
                                 "Selecione uma camada vetorial de polígonos no painel de camadas.")
            return

        field_names = [f.name() for f in layer.fields()]
        if not field_names:
            QMessageBox.warning(self.iface.mainWindow(), "BatchProcessor",
                                 "A camada ativa não tem nenhum campo para usar como categoria.")
            return

        field_name, ok = QInputDialog.getItem(
            self.iface.mainWindow(), "BatchProcessor",
            "Campo a usar como categoria:", field_names, 0, False,
        )
        if not ok:
            return

        # categorias genéricas de exemplo — em uso real, o chamador passa
        # as categorias e cores relevantes ao seu próprio fluxo
        example_styles = [
            ("A", QColor(220, 50, 50), "Categoria A"),
            ("B", QColor(240, 180, 40), "Categoria B"),
            ("C", QColor(60, 140, 90), "Categoria C"),
        ]

        dialog = ValidationDialog(
            layer, field_name, example_styles,
            title="Validação — {}".format(layer.name()),
            message="Revise a classificação das feições antes de prosseguir.",
            parent=self.iface.mainWindow(),
        )
        if dialog.exec_():
            QMessageBox.information(self.iface.mainWindow(), "BatchProcessor", "Validação confirmada.")
        else:
            QMessageBox.information(self.iface.mainWindow(), "BatchProcessor", "Validação cancelada.")

    def run_external_tool_demo(self):
        """
        Demonstra a ponte para ferramentas externas: pede um comando ao
        usuário e o executa em segundo plano (ou via WSL, se no Windows).
        """
        from . import external_tool_bridge as bridge

        command, ok = QInputDialog.getText(
            self.iface.mainWindow(), "BatchProcessor",
            "Comando a executar (no shell local, ou via WSL se estiver no Windows):",
        )
        if not ok or not command.strip():
            return

        def _on_finished(success, stdout, stderr):
            pass  # log já registrado pela própria ponte; ganchos extras entram aqui

        bridge.run_background(
            self.iface, process_key="batchprocessor_demo", title="Comando externo",
            shell_command=command.strip(), on_finished=_on_finished,
        )
