# F1 Race Replay 🏎️ 🏁

Uma aplicação em Python para visualizar a telemetria de corridas de Fórmula 1 e reproduzir os eventos da corrida, com controles interativos e interface gráfica.

![Prévia do Race Replay](../../resources/preview.png)

> **GRANDE NOVIDADE:** O recurso de stream de telemetria agora está em estado utilizável. Veja a [documentação da demo de telemetria](../../telemetry.md) para instruções de acesso, detalhes do formato dos dados e ideias de uso.

## Funcionalidades

- **Visualização do Replay da Corrida:** Acompanhe a corrida com as posições dos pilotos em tempo real em uma pista renderizada.
- **Visualização do Safety Car:** Veja o Safety Car sair do pit lane, liderar o pelotão e voltar aos boxes — com transições animadas e efeitos de brilho pulsante.
- **Menu de Insights:** Menu flutuante com acesso rápido a ferramentas de análise de telemetria (abre automaticamente com o replay).
- **Classificação (Leaderboard):** Veja as posições dos pilotos ao vivo e os compostos de pneu atuais.
- **Exibição de Volta e Tempo:** Acompanhe a volta atual e o tempo total de corrida.
- **Status do Piloto:** Pilotos que abandonam ou saem da corrida são marcados como "OUT" na classificação.
- **Controles Interativos:** Pause, volte, avance e ajuste a velocidade de reprodução usando os botões na tela ou atalhos de teclado.
- **Legenda:** Uma legenda na tela explica todos os controles.
- **Insights de Telemetria do Piloto:** Veja velocidade, marcha, status do DRS e a volta atual dos pilotos selecionados na classificação.

## Controles

- **Pausar/Continuar:** ESPAÇO ou botão Pause
- **Voltar/Avançar:** ← / → ou botões Rewind/Fast Forward
- **Velocidade de Reprodução:** ↑ / ↓ ou botão Speed (alterna entre 0.5x, 1x, 2x, 4x)
- **Definir Velocidade Diretamente:** Teclas 1–4
- **Reiniciar:** **R** para reiniciar o replay
- **Alternar Zona de DRS:** **D** para ocultar/mostrar a zona de DRS
- **Alternar Barra de Progresso:** **B** para ocultar/mostrar a barra de progresso
- **Alternar Nomes dos Pilotos:** **L** para ocultar/mostrar os nomes dos pilotos na pista
- **Selecionar piloto(s):** Clique para selecionar um piloto ou Shift + clique para selecionar vários


## Safety Car

O replay inclui um **Safety Car simulado** que aparece na pista sempre que os dados da F1 indicam o acionamento do Safety Car (código de status da pista `4`). Como a API da F1 não fornece telemetria GPS do Safety Car real, sua posição é simulada com base na posição do líder da corrida.

### Como funciona

- **Fonte dos dados:** O momento de acionamento do Safety Car vem dos dados reais de status da pista da F1, via FastF1 (`session.track_status`).
- **Simulação da posição:** O SC é posicionado ~500 metros à frente do líder da corrida, sobre a polilinha de referência da pista. Isso aproxima onde o SC real estaria em relação ao pelotão.
- **Três fases de animação:**
  - **Deploying (Entrando)** — O SC é animado saindo do pit lane para a pista ao longo de ~3 segundos, com brilho pulsante e o rótulo "SC DEPLOYING".
  - **On Track (Na Pista)** — O SC anda à frente do líder com um brilho âmbar constante e o rótulo "SC".
  - **Returning (Retornando)** — O SC é animado voltando ao pit lane ao longo de ~3 segundos, com um brilho pulsante que vai sumindo e o rótulo "SC IN".
- **Aparência visual:** O SC é desenhado como um círculo laranja/âmbar maior (raio de 8px, contra 6px dos carros normais), com um anel de contorno laranja e o rótulo "SC" sempre visível.

### Detalhes técnicos

O cálculo da posição do SC acontece em `_compute_safety_car_positions()` em `src/f1_data.py`. Cada frame recebe um campo `safety_car`:

```json
{
  "safety_car": {
    "x": 1234.56,
    "y": 7890.12,
    "phase": "on_track",
    "alpha": 1.0
  }
}
```

| Campo | Descrição |
|-------|-----------|
| `x`, `y` | Coordenadas do SC no mundo |
| `phase` | `"deploying"`, `"on_track"` ou `"returning"` |
| `alpha` | Opacidade de `0.0` (invisível) a `1.0` (totalmente visível), usada na animação de fade in/out |

> **Observação:** Se você tem arquivos `.pkl` em cache de execuções anteriores, precisa executar novamente com `--refresh-data` para gerar os dados de posição do SC. Arquivos em cache antigos simplesmente não mostrarão o Safety Car.

## Suporte a Sessões de Classificação (em desenvolvimento)

Foi adicionado recentemente o suporte a replays de sessões de Classificação (Qualifying), com visualização de telemetria incluindo velocidade, marcha, acelerador e freio ao longo da distância da volta. Esse recurso ainda está sendo aprimorado.

## Requisitos

- Python 3.11+
- [FastF1](https://github.com/theOehrly/Fast-F1)
- [Arcade](https://api.arcade.academy/en/latest/)
- numpy

Instale as dependências:
```bash
pip install -r requirements.txt
```

A pasta de cache do FastF1 será criada automaticamente na primeira execução. Se ela não for criada, você pode criar manualmente uma pasta chamada `.fastf1-cache` na raiz do projeto.
> **Aviso da Primeira Execução:** Carregar uma sessão pela primeira vez pode demorar bem mais, porque os dados de telemetria precisam ser baixados, processados e armazenados em cache localmente. As próximas aberturas da mesma sessão são significativamente mais rápidas.

## Configuração do Ambiente

Para começar a usar este projeto localmente, siga estes passos:

1. **Clone o Repositório:**
   ```bash
   git clone https://github.com/IAmTomShaw/f1-race-replay
   cd f1-race-replay
   ```
2. **Crie um Ambiente Virtual:**
    O processo varia de acordo com o seu sistema operacional.
    - No macOS/Linux:
      ```bash
      python3 -m venv venv
      source venv/bin/activate
      ```
    - No Windows:
      ```bash
      python -m venv venv
      .\venv\Scripts\activate
      ```
3. **Instale as Dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Execute a Aplicação:**
    Agora você pode executar a aplicação seguindo as instruções da seção Uso abaixo.

## Solução de Problemas
Se o processo de obtenção dos dados falhar, execute:
```bash
pip install --upgrade fastf1
```

## Uso

**MENU GRÁFICO PADRÃO:** Para usar o novo sistema de menu gráfico, basta executar:
```bash
python main.py
```

![Prévia do Menu Gráfico](../../resources/gui-menu.png)

Isso abrirá uma interface gráfica onde você pode selecionar o ano e a etapa do fim de semana de corrida que deseja assistir. Esse recurso ainda é novo, então, por favor, relate qualquer problema que encontrar.

**MENU CLI OPCIONAL:** Para usar o sistema de menu em linha de comando, basta executar:
```bash
python main.py --cli
```

![Prévia do Menu CLI](../../resources/cli-menu.gif)

Isso mostrará uma série de perguntas e uma lista de opções para você escolher usando as setas do teclado e a tecla Enter.

Se você já sabe o ano e o número da etapa da sessão que deseja assistir, pode executar os comandos diretamente, assim:

Execute o script principal especificando o ano e a etapa:
```bash
python main.py --viewer --year 2025 --round 12
```

Para executar sem o HUD:
```bash
python main.py --viewer --year 2025 --round 12 --no-hud
```

Para executar uma sessão Sprint (se o evento tiver uma), adicione `--sprint`:
```bash
python main.py --viewer --year 2025 --round 12 --sprint
```

A aplicação carregará um conjunto de dados de telemetria pré-calculado se você já o tiver executado antes para o mesmo evento. Para forçar o recálculo dos dados de telemetria, use a flag `--refresh-data`:
```bash
python main.py --viewer --year 2025 --round 12 --refresh-data
```

### Replay de Sessão de Classificação

Para executar o replay de uma sessão de Classificação, use a flag `--qualifying`:
```bash
python main.py --viewer --year 2025 --round 12 --qualifying
```

Para executar uma sessão de Classificação Sprint (se o evento tiver uma), adicione `--sprint`:
```bash
python main.py --viewer --year 2025 --round 12 --qualifying --sprint
```

## Estrutura de Arquivos

```
f1-race-replay/
├── main.py                    # Ponto de entrada, carrega a sessão e inicia o replay
├── requirements.txt           # Dependências Python
├── README.md                  # Documentação do projeto
├── roadmap.md                 # Funcionalidades planejadas e visão do projeto
├── resources/
│   └── preview.png           # Imagem de prévia do replay
├── src/
│   ├── f1_data.py            # Carregamento e processamento de telemetria, geração de frames e simulação da posição do SC
│   ├── arcade_replay.py      # Visualização e lógica da interface
│   └── ui_components.py      # Componentes de interface, como botões e classificação
│   ├── interfaces/
│   │   └── qualifying.py     # Interface da sessão de classificação e visualização de telemetria
│   │   └── race_replay.py    # Interface do replay da corrida, renderização do SC e visualização de telemetria
│   └── lib/
│       └── tyres.py          # Definições de tipos para as estruturas de dados de telemetria
│       └── time.py           # Utilitários de formatação de tempo
└── .fastf1-cache/            # Pasta de cache do FastF1 (criada automaticamente na primeira execução)
└── computed_data/            # Dados de telemetria calculados (criados automaticamente na primeira execução)
```

## Criando Janelas de Telemetria Personalizadas

Quando você inicia o replay de uma corrida, um **Menu de Insights** aparece automaticamente, oferecendo acesso rápido a várias ferramentas de análise de telemetria. Você pode criar facilmente janelas de insight personalizadas que recebem dados de telemetria ao vivo usando a classe base `PitWallWindow`:

```python
from src.gui.pit_wall_window import PitWallWindow

class MyInsightWindow(PitWallWindow):
    def setup_ui(self):
        # Crie sua interface personalizada
        pass
    
    def on_telemetry_data(self, data):
        # Processe os dados de telemetria
        pass
```

A classe base `PitWallWindow` cuida automaticamente de toda a lógica de conexão com o stream de telemetria, permitindo que você se concentre apenas na funcionalidade da sua janela.

**Principais Recursos:**
- Conexão automática com o stream de telemetria
- Barra de status embutida com o estado da conexão
- Limpeza adequada ao fechar a janela
- API simples - basta implementar `setup_ui()` e `on_telemetry_data()`

**Documentação e Exemplos:**
- Veja [PitWallWindow.md](./PitWallWindow.md) para o guia completo
- Veja [InsightsMenu.md](./InsightsMenu.md) para adicionar insights ao menu
- Execute o exemplo: `python -m src.gui.example_pit_wall_window`
- Teste o menu: `python -m src.gui.insights_menu`

## Personalização

- Altere a largura da pista, as cores e o layout da interface em `src/arcade_replay.py`.
- Ajuste o processamento de telemetria em `src/f1_data.py`.
- Crie janelas de telemetria personalizadas usando a classe base `PitWallWindow` (veja acima).

## Contribuindo

Várias contribuições da comunidade ajudaram a melhorar este projeto. Há um arquivo [contributors.md](../../contributors.md) para reconhecer quem contribuiu com funcionalidades e melhorias.

Se quiser contribuir, fique à vontade para:

- Abrir pull requests com melhorias de interface ou novas funcionalidades.
- Relatar problemas (issues) no GitHub.

Veja o [roadmap.md](../../roadmap.md) para as funcionalidades planejadas e a visão do projeto.

# Problemas Conhecidos

- Se você estiver usando um ambiente `conda`, talvez precise instalar alguns pacotes extras caso receba este erro:
```
arcade.application.NoOpenGLException: Unable to create an OpenGL 3.3+ context. Check to make sure your system supports OpenGL 3.3 or higher
```
Você pode resolver isso facilmente executando este comando:
```bash
$ conda install -c conda-forge libstdcxx-ng
```
Agradecimentos a @el-mandaloriano por mostrar como resolver esse problema: #12
- A classificação parece imprecisa nas primeiras curvas da corrida. Ela também é afetada temporariamente quando um piloto entra nos boxes. No fim da corrida, a classificação às vezes é afetada pelas posições x,y finais de alguns pilotos estarem mais à frente que as de outros. Esses são problemas conhecidos, causados por imprecisões na telemetria, e estão sendo trabalhados para versões futuras. É provável que sejam corrigidos em etapas, já que melhorar a precisão da classificação é uma tarefa complexa.

## 📝 Licença

Este projeto está licenciado sob a Licença MIT.

## ⚠️ Aviso Legal

Não há intenção de violar direitos autorais. Fórmula 1 e marcas relacionadas são propriedade de seus respectivos donos. Todos os dados utilizados vêm de APIs publicamente disponíveis e são usados apenas para fins educacionais e não comerciais.

---

Feito com ❤️ por [Tom Shaw](https://tomshaw.dev)
