# -*- coding: utf-8 -*-
"""
Ponte genérica para executar uma ferramenta de linha de comando externa a
partir do QGIS. No Windows, se a ferramenta só existir no Linux, a chamada
pode ser roteada através do WSL — com tradução automática de caminho entre
os dois sistemas de arquivos e duas formas de execução:

  - "visível": abre um terminal (útil para comandos interativos/demorados,
    onde o usuário quer acompanhar a saída ao vivo);
  - "em segundo plano": roda de forma assíncrona (QProcess), sem travar a
    interface do QGIS, e dispara um callback quando termina.

Isto é um padrão de integração genérico — o nome e o caminho da ferramenta
externa são configuráveis pelo chamador, não fixos neste módulo.
"""
import os
import platform
import tempfile
from datetime import datetime

from qgis.PyQt.QtCore import QProcess
from qgis.core import Qgis, QgsMessageLog

LOG_TAG = "BatchProcessor"

# processos assíncronos ativos, para não perder a referência e para evitar
# disparar o mesmo comando duas vezes em paralelo
_ACTIVE_PROCESSES = {}


def _log(message, level=Qgis.Info):
    QgsMessageLog.logMessage(str(message), LOG_TAG, level)


def is_windows():
    return platform.system() == "Windows"


def windows_path_to_wsl(windows_path):
    """Converte um caminho Windows (C:\\pasta\\arquivo) para o equivalente
    dentro do WSL (/mnt/c/pasta/arquivo)."""
    drive, rest = os.path.splitdrive(windows_path)
    drive_letter = drive.rstrip(":").lower()
    rest_posix = rest.replace("\\", "/")
    return "/mnt/{}{}".format(drive_letter, rest_posix)


def wsl_path_to_windows(wsl_path, distro="Ubuntu"):
    """Converte um caminho dentro do WSL para o equivalente acessível a
    partir do Windows via \\\\wsl.localhost\\<distro>\\..."""
    return r"\\wsl.localhost\{}{}".format(distro, wsl_path.replace("/", "\\"))


def build_shell_command(tool_command, activate_env_command=None):
    """
    Monta a linha de comando final a ser executada dentro do shell de
    destino (bash). `activate_env_command`, se fornecido, é encadeado antes
    da ferramenta (ex.: ativar um ambiente virtual/conda específico).
    """
    parts = []
    if activate_env_command:
        parts.append(activate_env_command)
    parts.append(tool_command)
    return " && ".join(parts)


def run_visible_terminal(iface, title, shell_command, use_wsl=None):
    """
    Abre um terminal visível rodando `shell_command`. No Windows, gera um
    .bat temporário que invoca `wsl bash -l -i -c "..."`; em outros
    sistemas, roda diretamente no shell local.
    """
    use_wsl = is_windows() if use_wsl is None else use_wsl

    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if use_wsl:
            script_name = "batchprocessor_{}.bat".format(timestamp)
            script_path = os.path.join(tempfile.gettempdir(), script_name)
            escaped_cmd = shell_command.replace('"', r"\"")

            content = (
                "@echo off\r\n"
                "chcp 65001 >nul\r\n"
                "title {title}\r\n"
                "echo ============================================================\r\n"
                "echo {title}\r\n"
                "echo ============================================================\r\n"
                "wsl bash -l -i -c \"{cmd}\"\r\n"
                "echo.\r\n"
                "echo Processo finalizado.\r\n"
                "pause\r\n"
            ).format(title=title, cmd=escaped_cmd)

            with open(script_path, "w", encoding="utf-8", newline="\r\n") as f:
                f.write(content)
            os.startfile(script_path)
        else:
            script_name = "batchprocessor_{}.sh".format(timestamp)
            script_path = os.path.join(tempfile.gettempdir(), script_name)
            with open(script_path, "w", encoding="utf-8") as f:
                f.write("#!/bin/bash\n{}\n".format(shell_command))
            os.chmod(script_path, 0o755)
            QProcess.startDetached("x-terminal-emulator", ["-e", script_path])

        if iface:
            iface.messageBar().pushMessage("Processando", "{} iniciado em terminal externo.".format(title),
                                            level=Qgis.Info, duration=5)
        _log("Terminal externo iniciado: {}".format(script_path))
        return {"ok": True, "title": title}

    except Exception as exc:
        _log("Falha ao abrir terminal externo: {}".format(exc), Qgis.Critical)
        if iface:
            iface.messageBar().pushMessage("Erro", "Não foi possível abrir o terminal externo.",
                                            level=Qgis.Critical, duration=7)
        return {"ok": False, "title": title, "error": str(exc)}


def run_background(iface, process_key, title, shell_command, on_finished=None, use_wsl=None):
    """
    Roda `shell_command` de forma assíncrona (sem bloquear o QGIS). No
    Windows com use_wsl=True, o programa executado é `wsl`; caso contrário,
    roda em `bash` local. `on_finished(ok: bool, stdout: str, stderr: str)`
    é chamado ao término, se fornecido.
    """
    use_wsl = is_windows() if use_wsl is None else use_wsl

    existing = _ACTIVE_PROCESSES.get(process_key)
    if existing and existing.state() != QProcess.NotRunning:
        message = "Já existe um processo em andamento para '{}'.".format(process_key)
        if iface:
            iface.messageBar().pushMessage("Aviso", message, level=Qgis.Warning, duration=6)
        return {"ok": False, "title": title, "error": message}

    process = QProcess()
    if use_wsl:
        process.setProgram("wsl")
        process.setArguments(["bash", "-l", "-i", "-c", shell_command])
    else:
        process.setProgram("bash")
        process.setArguments(["-l", "-c", shell_command])
    process.setProcessChannelMode(QProcess.SeparateChannels)

    def _finished(exit_code, exit_status):
        stdout = bytes(process.readAllStandardOutput()).decode("utf-8", errors="ignore")
        stderr = bytes(process.readAllStandardError()).decode("utf-8", errors="ignore")
        _ACTIVE_PROCESSES.pop(process_key, None)

        ok = exit_status == QProcess.NormalExit and exit_code == 0
        if stdout.strip():
            _log("STDOUT ({}):\n{}".format(title, stdout))
        if stderr.strip():
            _log("STDERR ({}):\n{}".format(title, stderr), Qgis.Warning if ok else Qgis.Critical)

        if iface:
            level = Qgis.Success if ok else Qgis.Critical
            msg = "{} concluído.".format(title) if ok else "{} falhou. Veja o log.".format(title)
            iface.messageBar().pushMessage("BatchProcessor", msg, level=level, duration=6)

        if on_finished:
            on_finished(ok, stdout, stderr)

    def _errored(_error):
        _ACTIVE_PROCESSES.pop(process_key, None)
        _log("Erro ao iniciar processo '{}': {}".format(title, process.errorString()), Qgis.Critical)
        if iface:
            iface.messageBar().pushMessage("Erro", "Falha ao iniciar {}.".format(title),
                                            level=Qgis.Critical, duration=7)
        if on_finished:
            on_finished(False, "", process.errorString())

    process.finished.connect(_finished)
    process.errorOccurred.connect(_errored)

    _ACTIVE_PROCESSES[process_key] = process
    process.start()

    if iface:
        iface.messageBar().pushMessage("Processando", "{} iniciado em segundo plano.".format(title),
                                        level=Qgis.Info, duration=5)
    _log("Iniciando processo em segundo plano: {}".format(shell_command))

    return {"ok": True, "title": title}
