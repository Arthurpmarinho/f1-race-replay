# Menu de Insights

## Visão Geral

O Menu de Insights é uma janela PySide6 que abre automaticamente quando o replay da corrida começa. Ele oferece acesso rápido a ferramentas de análise de telemetria e janelas de insights. O menu permanece aberto junto com o replay e permite abrir várias janelas de insights.

![Menu de Insights](../../resources/insights-menu.png)

### Insights Ativos
- **Example Insight Window** - Um exemplo funcional que demonstra o padrão PitWallWindow
- **Telemetry Stream Viewer** - Visualize os dados brutos de telemetria em tempo real

## Uso

O menu abre automaticamente quando você inicia um replay e abre uma sessão do tipo "Race" (corrida).

## Adicionando Novos Botões ao Menu

Para adicionar um novo botão de insight ao menu, siga estes passos:

### Passo 1: Crie Sua Janela de Insight

Primeiro, crie sua janela de insight usando a classe base `PitWallWindow`:

```python
# src/gui/my_custom_insight.py
from src.gui.pit_wall_window import PitWallWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyCustomInsight(PitWallWindow):
    """Meu insight de telemetria personalizado."""
    
    def setup_ui(self):
        """Cria a interface personalizada."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        self.data_label = QLabel("Waiting for data...")
        layout.addWidget(self.data_label)
    
    def on_telemetry_data(self, data):
        """Processa os dados de telemetria recebidos."""
        # Sua lógica de processamento de dados
        self.data_label.setText(f"Latest data: {data}")
    
    def on_stream_error(self, error_msg):
        """Trata erros."""
        self.data_label.setText(f"Error: {error_msg}")
```

### Passo 2: Adicione um Método de Abertura

Em `src/gui/insights_menu.py`, adicione um método para abrir seu insight:

```python
def launch_my_custom_insight(self):
    """Abre a janela do meu insight personalizado."""
    print("🚀 Launching: My Custom Insight")
    from src.gui.my_custom_insight import MyCustomInsight
    window = MyCustomInsight()
    window.show()
    self.opened_windows.append(window)
```

### Passo 3: Adicione o Botão a uma Categoria

No método `setup_ui()` da classe `InsightsMenu`, adicione seu botão a uma categoria existente ou crie uma nova:

**Adicionando a uma categoria existente:**

```python
content_layout.addWidget(self.create_category_section(
    "Live Telemetry",
    [
        ("Telemetry Stream Viewer", "View raw telemetry data", self.launch_telemetry_viewer),
        ("My Custom Insight", "Description of what it does", self.launch_my_custom_insight),  # Adicione aqui
    ]
))
```

**Criando uma nova categoria:**

```python
content_layout.addWidget(self.create_category_section(
    "Custom Analysis",
    [
        ("My Custom Insight", "Description of what it does", self.launch_my_custom_insight),
    ]
))
```

### Passo 4: Teste Seu Botão

Execute o menu de forma independente para testar seu novo botão:

```bash
python -m src.gui.insights_menu
```

Isso abrirá o Menu de Insights sem iniciar um replay. A janela não estará conectada à telemetria a menos que você inicie um replay, mas você pode verificar se o botão abre sua janela de insight corretamente.

## Arquitetura

### Estrutura do Menu
```
InsightsMenu (QMainWindow)
├── Cabeçalho
│   ├── Título: "🏎️ F1 Insights"
│   └── Subtítulo: "Launch telemetry insights and analysis tools"
├── Conteúdo Rolável (QScrollArea)
│   ├── Seção de Categoria 1
│   │   ├── Rótulo da Categoria (ex.: "EXAMPLE INSIGHTS")
│   │   ├── Linha Separadora
│   │   ├── Botão de Insight 1 (nome + descrição)
│   │   ├── Botão de Insight 2
│   │   └── ...
│   ├── Seção de Categoria 2
│   │   └── ...
│   └── Stretch (empurra o rodapé para baixo)
└── Rodapé
    ├── Rótulo Informativo: "Requires telemetry stream enabled"
    └── Botão Close Menu
```

### Componentes Principais

**`create_category_section(category_name, insights)`**
- Cria uma seção de categoria com vários botões de insight
- `insights`: Lista de tuplas `(name, description, callback)`
- Cada tupla se torna um botão clicável

**`create_insight_button(name, description, callback)`**
- Cria um botão estilizado com o nome em negrito e uma descrição menor
- Altura mínima: 50px
- Conecta o botão ao callback de abertura

**Lista `opened_windows`**
- Mantém referências a todas as janelas de insight abertas
- Impede que o Python remova as janelas ativas pelo coletor de lixo (garbage collector)
- As janelas continuam abertas mesmo se o menu for fechado

### Processo de Abertura

1. O usuário inicia o replay com `python main.py --viewer`
2. `main.py` chama `launch_insights_menu()` de `src.run_session`
3. A janela do menu é criada e exibida
4. O usuário clica nos botões de insight para abrir janelas de análise
5. Cada insight abre em sua própria janela, com uma conexão de telemetria independente

## Personalização

### Estilo

O menu usa folhas de estilo inline (sem CSS externo). O tema padrão é escuro, com estilo mínimo:

- **Fundo**: Escuro (herda do tema do sistema)
- **Fonte**: Arial em vários tamanhos (24pt no título, 12pt nos botões, 10pt nas descrições)
- **Botões**: Altura mínima de 50px, com nome e descrição
- **Cursor**: Cursor de mão (pointing hand) sobre os botões

Para personalizar a aparência, edite o método `setup_ui()` e adicione uma folha de estilo:

```python
self.setStyleSheet("""
    QMainWindow {
        background-color: #1e1e1e;
    }
    QPushButton {
        background-color: #2d2d2d;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        padding: 8px;
    }
    QPushButton:hover {
        border: 1px solid #e10600;  /* Vermelho Ferrari */
        background-color: #3d3d3d;
    }
""")
```

### Tamanho e Posição da Janela

Ajuste em `__init__()`:

```python
self.setGeometry(50, 50, 300, 600)  # x, y, largura, altura
```

### Layout e Aparência dos Botões

Modifique `create_insight_button()` para personalizar os botões:

```python
def create_insight_button(self, name, description, callback):
    button = QPushButton()
    
    # Layout personalizado
    btn_layout = QVBoxLayout()
    name_label = QLabel(name)
    name_label.setFont(QFont("Arial", 14, QFont.Bold))  # Fonte maior
    
    desc_label = QLabel(description)
    desc_label.setFont(QFont("Arial", 9, QFont.Italic))  # Descrição em itálico
    
    btn_layout.addWidget(name_label)
    btn_layout.addWidget(desc_label)
    
    button.setLayout(btn_layout)
    button.setMinimumHeight(60)  # Botões mais altos
    button.clicked.connect(callback)
    
    return button
```

## Veja Também

- [PitWallWindow.md](./PitWallWindow.md) - Classe base para criar insights
- [../../src/gui/insights_menu.py](../../src/gui/insights_menu.py) - Implementação do menu
- [../../src/gui/example_pit_wall_window.py](../../src/gui/example_pit_wall_window.py) - Insight de exemplo
