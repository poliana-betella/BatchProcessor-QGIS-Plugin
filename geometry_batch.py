# -*- coding: utf-8 -*-
"""
Aplica a mesma operacao geometrica a varias camadas vetoriais de uma vez,
usando o pipeline nativo de processamento do QGIS (qgis:processing), e
carrega os resultados no projeto com um sufixo indicando a operacao.
"""
import processing
from qgis.core import QgsProject, QgsVectorLayer

OPERATIONS = {
    "fix_geometries": {
        "label": "Corrigir geometrias inválidas",
        "algorithm": "native:fixgeometries",
        "params_extra": {},
    },
    "buffer": {
        "label": "Buffer",
        "algorithm": "native:buffer",
        "params_extra": {"DISTANCE": 10, "SEGMENTS": 8, "DISSOLVE": False},
    },
    "dissolve": {
        "label": "Dissolver",
        "algorithm": "native:dissolve",
        "params_extra": {},
    },
    "reproject": {
        "label": "Reprojetar",
        "algorithm": "native:reprojectlayer",
        "params_extra": {"TARGET_CRS": "EPSG:4674"},
    },
}


class BatchOperationError(Exception):
    pass


def run_batch(layers, operation_key, extra_params=None, progress_callback=None):
    """
    Executa `operation_key` (uma chave de OPERATIONS) em cada camada de
    `layers`, sequencialmente. Falhas em uma camada nao interrompem as
    demais — cada resultado (sucesso ou erro) e reportado individualmente
    para que o usuario veja exatamente quais camadas precisam de atencao.

    Retorna uma lista de dicts: {"layer": nome, "ok": bool, "result_layer": QgsVectorLayer|None, "error": str|None}
    """
    if operation_key not in OPERATIONS:
        raise BatchOperationError("Operação desconhecida: {}".format(operation_key))

    spec = OPERATIONS[operation_key]
    params_extra = dict(spec["params_extra"])
    if extra_params:
        params_extra.update(extra_params)

    results = []
    total = len(layers)

    for index, layer in enumerate(layers):
        if progress_callback:
            progress_callback(index, total, layer.name())

        try:
            params = {"INPUT": layer, "OUTPUT": "memory:{}_{}".format(layer.name(), operation_key)}
            params.update(params_extra)

            output = processing.run(spec["algorithm"], params)
            result_layer = output.get("OUTPUT")

            if isinstance(result_layer, str):
                result_layer = QgsVectorLayer(result_layer, "{}_{}".format(layer.name(), operation_key), "ogr")

            if result_layer is None or not result_layer.isValid():
                results.append({
                    "layer": layer.name(), "ok": False, "result_layer": None,
                    "error": "Resultado inválido retornado pelo algoritmo.",
                })
                continue

            result_layer.setName("{}_{}".format(layer.name(), operation_key))
            results.append({"layer": layer.name(), "ok": True, "result_layer": result_layer, "error": None})

        except Exception as exc:
            results.append({"layer": layer.name(), "ok": False, "result_layer": None, "error": str(exc)})

    if progress_callback:
        progress_callback(total, total, None)

    return results


def load_results(results):
    """Adiciona ao projeto todas as camadas resultantes que tiveram sucesso."""
    project = QgsProject.instance()
    loaded = 0
    for result in results:
        if result["ok"] and result["result_layer"] is not None:
            project.addMapLayer(result["result_layer"])
            loaded += 1
    return loaded
