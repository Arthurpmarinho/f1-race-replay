# Guia do Desenvolvedor: PitWallWindow

## Visão Geral

`PitWallWindow` é uma classe base que simplifica a criação de janelas personalizadas com telemetria no projeto F1 Race Replay. Ela cuida de toda a complexidade da conexão com o stream de telemetria, permitindo que os desenvolvedores se concentrem apenas na funcionalidade da sua janela.

![Template da PitWall Window](../../resources/pit-wall-window-template.png)

## Por Que Usar a PitWallWindow?

Sem a `PitWallWindow`, você precisaria:
- Criar e configurar um `TelemetryStreamClient`
- Conectar os sinais Qt de recebimento de dados, status da conexão e erros
- Tratar a limpeza adequada quando a janela for fechada
- Gerenciar o estado da conexão e a contagem de mensagens

Com a `PitWallWindow`, você simplesmente:
1. Estende a classe
2. Implementa `setup_ui()` para criar sua interface
3. Implementa `on_telemetry_data()` para processar os dados

## Usando o Template

Para começar rapidamente, use o arquivo de template [`pit_wall_window_template.py`](../../src/gui/pit_wall_window_template.py). Ele fornece uma estrutura pré-configurada com todos os imports necessários e os esboços dos métodos, para que você possa se concentrar em implementar a lógica principal do seu insight.


## Início Rápido

```python
from src.gui.pit_wall_window import PitWallWindow
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class MyInsightWindow(PitWallWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Custom Insight")
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        self.info_label = QLabel("Waiting for data...")
        layout.addWidget(self.info_label)
    
    def on_telemetry_data(self, data):
        if 'frame_index' in data:
            self.info_label.setText(f"Frame: {data['frame_index']}")
```

Sua janela se conectará automaticamente ao stream de telemetria e começará a receber dados.

**Exemplo:**

```python
def on_telemetry_data(self, data):
    # Atualiza o contador de frames
    if 'frame_index' in data:
        self.frame_label.setText(f"Frame: {data['frame_index']}")
    
    # Processa os dados dos pilotos
    if 'frame' in data and 'drivers' in data['frame']:
        drivers = data['frame']['drivers']
        for code, driver in drivers.items():
            speed = driver.get('speed', 0)
            if speed > 300:  # Destaca momentos de alta velocidade
                self.highlight_driver(code, speed)
```

### `on_connection_status_changed(status)` (Opcional)

Chamado quando o estado da conexão muda.

**Parâmetros:**
- `status` (str): Um destes valores: "Connected", "Connecting..." ou "Disconnected"

**Exemplo:**

```python
def on_connection_status_changed(self, status):
    if status == "Connected":
        self.enable_controls()
    else:
        self.disable_controls()
```

### `on_stream_error(error_msg)` (Opcional)

Chamado quando ocorre um erro no stream. O erro já é exibido na barra de status, mas você pode adicionar um tratamento personalizado.

**Parâmetros:**
- `error_msg` (str): Descrição do erro

**Exemplo:**

```python
def on_stream_error(self, error_msg):
    self.error_log.append(f"[{datetime.now()}] {error_msg}")
```

## Recursos Embutidos

### Barra de Status

Toda `PitWallWindow` inclui uma barra de status com:
- **Status da Conexão**: Mostra o estado atual da conexão com cores (verde = conectado, laranja = conectando, vermelho = desconectado)
- **Contador de Mensagens**: Exibe o total de mensagens recebidas

Você pode adicionar outros widgets à barra de status:

```python
def setup_ui(self):
    # ... configuração da sua interface ...
    
    # Adiciona um widget de status personalizado
    my_status = QLabel("Custom Info")
    self.status_bar.addPermanentWidget(my_status)
```

### Limpeza Automática

A classe base cuida da limpeza adequada quando a janela é fechada, garantindo que o cliente de telemetria seja parado e os recursos sejam liberados.

## Executando Sua Janela

### De Forma Independente

```python
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyInsightWindow()
    window.show()
    sys.exit(app.exec())
```

### A Partir da Aplicação Principal

Adicione um item de menu ou um botão na aplicação principal:

```python
def launch_my_insight(self):
    self.insight_window = MyInsightWindow()
    self.insight_window.show()
```
