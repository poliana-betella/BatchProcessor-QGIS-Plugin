# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/) e [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-16

### Adicionado
- Operações geométricas em lote (corrigir geometrias, buffer, dissolver, reprojetar) aplicáveis a várias camadas selecionadas de uma vez, com relatório individual de sucesso/falha por camada.
- Diálogo genérico de validação/QC: preview em memória de feições coloridas por categoria (com legenda), sem alterar a camada original, antes de confirmar ou cancelar.
- Ponte genérica para ferramentas de linha de comando externas, com execução em terminal visível ou em segundo plano (assíncrona), incluindo roteamento automático via WSL no Windows e tradução de caminho entre Windows e WSL.
