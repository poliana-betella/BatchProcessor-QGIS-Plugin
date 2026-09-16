# BatchProcessor

Conjunto de ferramentas de produtividade para QGIS, nascidas de rotinas repetitivas do dia a dia em geoprocessamento: rodar a mesma operação em várias camadas, revisar uma classificação antes de confiar nela, e disparar ferramentas de linha de comando externas sem sair do QGIS.

## O que tem aqui

### 1. Operações geométricas em lote

Aplica a mesma operação (corrigir geometrias, buffer, dissolver, reprojetar) a várias camadas vetoriais selecionadas de uma vez, usando os algoritmos nativos de processamento do QGIS por baixo dos panos. Cada camada é processada de forma independente — se uma falhar (geometria corrompida, campo ausente, etc.), as demais continuam normalmente, e o relatório final mostra exatamente quais falharam e por quê.

### 2. Validação / QC com preview categorizado

Um diálogo genérico de revisão: mostra uma cópia em memória das feições de uma camada, coloridas por categoria (com legenda), antes de o usuário decidir se prossegue ou cancela. Pensado para qualquer fluxo onde uma classificação automática (de uso do solo, de qualidade de dado, de status de revisão etc.) precisa de uma checagem visual humana antes de virar resultado final — a camada original nunca é alterada, só o preview.

### 3. Ponte para ferramentas externas (com suporte a WSL)

Um padrão genérico para chamar uma ferramenta de linha de comando a partir do QGIS, com duas formas de execução: em terminal visível (para comandos interativos ou demorados, onde faz sentido acompanhar a saída ao vivo) ou em segundo plano, de forma assíncrona, sem travar a interface. No Windows, se a ferramenta só existir no Linux, a chamada pode ser roteada automaticamente pelo WSL, com tradução de caminho entre os dois sistemas de arquivos (`C:\pasta\arquivo` ↔ `/mnt/c/pasta/arquivo`).

## Uso

Menu **BatchProcessor**, com três entradas: *Operações geométricas em lote...*, *Validar camada ativa (preview QC)...* e *Executar ferramenta externa...*.

## Instalação

Copie a pasta do plugin para o diretório de plugins do QGIS (`Configurações → Perfis de usuário → Abrir pasta de perfil ativo → python/plugins`) e ative em **Complementos → Gerenciar e Instalar Complementos**.

## Stack

Python + API do QGIS (PyQt/qgis.core/qgis.gui), `processing` nativo do QGIS para as operações geométricas, `QProcess` para a ponte de ferramentas externas. Sem dependências externas além do que o próprio QGIS já fornece.
