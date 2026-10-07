# Testes

Este projeto usa o `pytest` para testes automatizados.

## Instale as dependências de teste

Para desenvolvimento local, primeiro crie e ative um ambiente virtual:

    python3 -m venv .venv
    source .venv/bin/activate

No Windows, ative com:

    .venv\Scripts\activate

Depois, instale as dependências de desenvolvimento:

    python -m pip install --upgrade pip
    python -m pip install -r requirements-dev.txt

## Execute a suíte de testes

Execute todos os testes com:

    python -m pytest

Execute apenas os testes unitários leves com:

    python -m pytest tests/lib

## Estratégia de testes

A suíte de testes inicial foca em módulos leves que não exigem:

- download de dados do FastF1 ao vivo
- abertura de janelas gráficas
- um contexto OpenGL
- uma sessão de replay de corrida em execução

A suíte atual inclui:

- testes unitários de formatação e parsing de tempo
- testes unitários do mapeamento de compostos de pneus
- testes unitários de detecção de temporada
- testes unitários de persistência de configurações com arquivos temporários
- testes de fumaça (smoke tests) de importação dos módulos do projeto

Alguns testes de fumaça de importação podem ser ignorados (skipped) localmente quando dependências opcionais de execução não estão instaladas.
