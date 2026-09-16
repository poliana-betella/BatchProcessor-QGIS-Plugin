# -*- coding: utf-8 -*-
"""
BatchProcessor
Operacoes geometricas em lote, dialogo de validacao/QC e ponte para
ferramentas de linha de comando externas (com suporte a WSL).
"""


def classFactory(iface):
    from .batch_processor import BatchProcessorPlugin
    return BatchProcessorPlugin(iface)
