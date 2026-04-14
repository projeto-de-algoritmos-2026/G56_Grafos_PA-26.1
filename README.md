# DF Transit Navigator

**Encontre o menor caminho por transporte público no DF usando Dijkstra + GTFS**

Projeto desenvolvido para a disciplina de **Projeto de Algoritmos** —
Faculdade do Gama (FGA), Universidade de Brasília (UnB).

---


## Apresentação

[![Apresentação em Vídeo](https://img.youtube.com/vi/kuGAh_TVdt0/0.jpg)](https://youtu.be/kuGAh_TVdt0)
## Problema

Um estudante da FGA mora em outra região administrativa do DF

(Plano Piloto, Vicente Pires, Santa Maria, Taguatinga, Samambaia…) e precisa
saber qual combinação de linhas de ônibus minimiza o tempo total de viagem
até o campus — possivelmente com baldeação.

Esse problema não é trivial: existem várias linhas, cada trecho tem duração
diferente, e é possível combinar rotas com uma ou mais baldeações —
inclusive a pé entre paradas próximas.

---

## Solução

Modelamos a rede de transporte público como um **grafo dirigido ponderado**
e aplicamos o **algoritmo de Dijkstra** para encontrar o caminho de
menor custo (tempo) entre qualquer par de paradas.

Os dados vêm do **GTFS publicado pelo SEMOB-DF** — o mesmo formato
usado pelo Google Maps, Moovit e demais apps de mobilidade.

---

## Por que Dijkstra?

| Algoritmo        | Por que não usar aqui?                                              |
|------------------|---------------------------------------------------------------------|
| **BFS**          | Minimiza nº de paradas, não tempo. Linhas rápidas vs. lentas importam. |
| **DFS**          | Não garante caminho ótimo em grafos ponderados.                     |
| **Bellman-Ford** | Funciona, mas O(V·E) — desnecessário pois os pesos são ≥ 0.        |
| **Dijkstra**     | Garante menor custo com pesos não-negativos. O((V+E)·log V).       |

Em redes de transporte real, Dijkstra é a base do algoritmo **OSPF**
(roteamento de redes) e de variantes como o **Dijkstra tempo-expandido**
usado em apps como o Moovit.

---

## Modelagem do Grafo

```
Vértices  →  paradas de ônibus (stop_id do GTFS)
Arcos     →  conexão entre paradas consecutivas de uma linha (dirigido)
Peso      →  tempo de viagem em segundos (departure_time[i+1] - departure_time[i])

Arcos de transferência (caminhada):
  → Adicionados automaticamente entre paradas a ≤ 400 m
  → Peso = distância_Haversine / 1,39 m/s  (≈ 5 km/h)
  → Bidirecionais (pode-se caminhar nos dois sentidos)
```

### Exemplo visual

```
[Terminal Gama] --120s--> [Gama Setor Leste Q.6] --180s--> [FGA (Principal)]
      |                                                           ^
      |              [Gama Setor Norte] ----walk 250m------------/
      \--300s--> [Hospital Gama] --...
```

### Por que grafo dirigido?

Muitas linhas do DF têm trajetos de ida e volta diferentes
(ruas de mão única, retornos, variantes de percurso).
Um grafo dirigido modela isso corretamente;
um grafo não-dirigido forçaria simetria artificial.

---

## Estrutura do Projeto

```
df-transit/
│
├── src/
│   ├── graph/
│   │   ├── graph.py          # Grafo dirigido com lista de adjacência
│   │   └── dijkstra.py       # Dijkstra com min-heap — implementação própria
│   │
│   ├── gtfs/
│   │   ├── models.py         # Dataclasses: Stop, Route, Trip, StopTime
│   │   ├── parser.py         # Lê arquivos CSV do GTFS
│   │   └── builder.py        # Constrói o grafo a partir do GTFSFeed
│   │                           (inclui Haversine para arcos de caminhada)
│   ├── transit/
│   │   ├── network.py        # TransitNetwork — camada de serviço
│   │   └── formatter.py      # Formata PathResult em itinerário legível
│   │
│   ├── cli/
│   │   └── interface.py      # Interface interativa no terminal (--cli)
│   │
│   └── gui/
│       └── app.py            # Interface gráfica com mapa interativo (padrão)
│
├── data/
│   └── gtfs/                 # Arquivos GTFS (stops, routes, trips, stop_times)
│       ├── stops.txt         # ~160 paradas do DF
│       ├── routes.txt        # 14 linhas
│       ├── trips.txt         # Viagens (ida e volta por linha)
│       └── stop_times.txt    # Horários de passagem
│
├── tests/
│   └── test_transit.py       # Testes unitários e de integração
│
├── docs/
│   └── graph_model.md        # Decisões de modelagem detalhadas
│
├── main.py                   # Ponto de entrada
├── requirements.txt
└── README.md
```

**Separação de responsabilidades:**

| Camada     | Responsabilidade                                         |
|------------|----------------------------------------------------------|
| `graph/`   | Estrutura de dados pura — grafo e algoritmo              |
| `gtfs/`    | Parsing e transformação dos dados abertos do SEMOB-DF    |
| `transit/` | Lógica de negócio — consultas e formatação de rotas      |
| `cli/`     | Interface de terminal (modo legado, flag `--cli`)        |
| `gui/`     | Interface gráfica com mapa interativo (modo padrão)      |

O módulo `graph/` não conhece nada sobre GTFS ou ônibus.
O módulo `gtfs/` não conhece nada sobre Dijkstra.
O algoritmo é completamente independente dos dados.

---

## Como Rodar

### Requisitos

- Python 3.10+
- `tkintermapview` — biblioteca de mapa interativo para tkinter
- `pytest` (apenas para testes)

```bash
pip install -r requirements.txt
```

### Interface gráfica (padrão)

```bash
python main.py
```

Abre uma janela com mapa interativo do DF. Basta digitar o nome da parada
de origem, depois de destino, e clicar em **Calcular Rota**.

### Interface de terminal (legado)

```bash
python main.py --cli
```

### Demonstração automática

```bash
python main.py --demo
```

### Rodar os testes

```bash
python -m pytest tests/ -v
```

---

## Interface Gráfica

A interface gráfica foi adicionada para facilitar a visualização das rotas
no mapa real do DF. Ela usa `tkinter` (já incluso no Python) para a janela
e `tkintermapview` para renderizar o mapa OpenStreetMap com os caminhos.

**Como funciona:**

1. Ao abrir, a rede GTFS é carregada em segundo plano (thread separada)
   para não travar a janela
2. Todas as paradas aparecem como pontos cinzas no mapa
3. O usuário digita o nome da parada — a lista filtra ao vivo
4. Ao clicar em **Calcular Rota**, o Dijkstra roda e o resultado é desenhado:
   - Cada linha de ônibus recebe uma cor diferente
   - Transferências entre linhas aparecem com marcador laranja
   - Origem em verde, destino em vermelho
   - Trechos a pé aparecem em cinza
   - O mapa ajusta automaticamente o zoom para enquadrar toda a rota
5. Uma legenda aparece na sidebar mostrando qual cor corresponde a qual linha

---

## Dataset GTFS

O dataset incluído cobre as principais regiões administrativas do DF,
com aproximadamente **160 paradas** e **14 linhas**, incluindo:

| Região             | Cobertura                                        |
|--------------------|--------------------------------------------------|
| Plano Piloto       | Rodoviária, Asa Sul, Asa Norte, Lago Sul, Lago Norte |
| Gama               | Terminal, FGA/UnB, Santa Maria, Recanto das Emas |
| Taguatinga         | Terminal, Ceilândia, Samambaia                   |
| Vicente Pires      | Setor Comercial, diversas ruas internas          |
| Aguas Claras       | Terminal, Av. Castanheiras, Av. Araucárias       |
| Guará              | Guará I e II, ParkShopping                       |
| Outras             | Aeroporto, Lago Sul, Lago Norte, Sobradinho      |

### Linhas disponíveis

| Código | Trajeto                                        |
|--------|------------------------------------------------|
| 0.300  | Plano Piloto — Circular Central                |
| 0.301  | Asa Sul — Circular                             |
| 0.302  | Asa Norte / Lago Norte                         |
| 0.303  | Lago Sul / Aeroporto / Plano Piloto            |
| 0.304  | Santa Maria / Gama                             |
| 0.306  | Aguas Claras / Guará                           |
| 0.307  | Vicente Pires / Taguatinga                     |
| 0.308  | Taguatinga / Guará                             |
| 0.309  | Ceilândia / Taguatinga                         |
| 0.310  | Samambaia / Recanto das Emas                   |
| 0.311  | Recanto das Emas / Gama                        |
| 0.312  | Guará / Gama / UnB FGA                         |
| 0.313  | Plano Piloto / Taguatinga / Ceilândia          |
| 0.314  | Plano Piloto / Samambaia / Recanto das Emas    |

### Exemplo de rota: Vicente Pires → FGA

```
1. Linha 0.307 | VICENTE PIRES / TAGUATINGA
   ├─ Vicente Pires Rua 3
   │  ...
   └─ Taguatinga Centro Praca do Relogio

2. Linha 0.308 | TAGUATINGA / GUARÁ
   ├─ Taguatinga Centro Praca do Relogio
   │  ...
   └─ Guará I Terminal

3. Linha 0.312 | GUARÁ / GAMA / UNB FGA
   ├─ Guará I Terminal
   │  ...
   └─ FGA UnB Gama (Bloco Principal)
```

---

## Usando o GTFS Oficial do SEMOB-DF

Para usar o feed completo com **todas as linhas do DF**:

1. Acesse **https://www.semob.df.gov.br/** → Dados Abertos → GTFS
2. Baixe o arquivo `.zip` mais recente
3. Extraia o conteúdo em `data/gtfs/`
4. Execute normalmente: `python main.py`

O parser foi escrito para ser compatível com o GTFS completo sem nenhuma
alteração de código.

> **Nota sobre escala:** O GTFS completo do DF tem ~10 000 paradas e
> ~500 000 stop_times. O grafo resultante tem ~50 000 arcos.
> O Dijkstra ainda responde em milissegundos graças ao min-heap.

---

## Complexidade

| Operação                  | Complexidade           |
|---------------------------|------------------------|
| Construção do grafo       | O(V + E)               |
| Dijkstra (por consulta)   | O((V + E) · log V)     |
| Arcos de caminhada        | O(V²) — pré-processado |
| Espaço total              | O(V + E)               |

Com o GTFS completo do DF (V ≈ 10 000, E ≈ 50 000):
Dijkstra responde em **< 50ms** por consulta.

---

## Decisões Técnicas

**Por que lista de adjacência e não matriz de adjacência?**
Redes de transporte são grafos esparsos — cada parada tem em média
3–5 vizinhos diretos. Uma matriz V×V desperdiçaria O(V²) de memória
com zeros, enquanto a lista ocupa apenas O(V + E).

**Por que min-heap nativo (`heapq`) e não fila de prioridade própria?**
O `heapq` do Python é implementado em C e faz parte da stdlib —
não é uma "biblioteca de grafos externa". A lógica do Dijkstra,
o relaxamento das arestas e a reconstrução do caminho são todos
implementados do zero neste projeto.

**Por que Haversine para distâncias entre paradas?**
Paradas de ônibus têm coordenadas GPS (lat/lon). A distância euclidiana
em graus não tem significado físico. Haversine dá a distância real
na superfície da Terra, necessária para calcular o tempo de caminhada.

**Por que tkintermapview e não uma solução web?**
O `tkinter` já vem instalado com o Python — sem necessidade de Node,
npm ou servidor local. O `tkintermapview` usa tiles do OpenStreetMap e
permite desenhar marcadores e caminhos com poucas linhas de código.
Ideal para um projeto acadêmico onde o foco é o algoritmo, não o frontend.

---

## Autores

Desenvolvido como projeto da entrega da parte de grafos da disciplina **Projeto de Algoritmos**
— FGA/UnB, 2024/2025.

Dados públicos: **SEMOB-DF** (Secretaria de Mobilidade do Distrito Federal), porém não existe um zip com os dados dos transporte (ou não achamos), com isso fizemos uma captação manual dos dados, mas esse código pode ser reutilizado por outro dado de outros locais, não só no DF
Formato: **GTFS** (General Transit Feed Specification — Google/MobilityData)
