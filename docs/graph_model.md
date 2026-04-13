# Modelagem do Grafo — DF Transit Navigator

## Decisões de Modelagem

### 1. Tipo de Grafo: Dirigido e Ponderado

**Dirigido** porque linhas de ônibus do DF frequentemente têm percursos
diferentes nos dois sentidos (ruas de mão única, retornos obrigatórios,
variantes por ponto final). Forçar simetria introduziria rotas inexistentes.

**Ponderado** porque o tempo entre paradas varia significativamente:
uma parada num corredor expresso pode ser 30 segundos; uma parada
em via local congestionada pode ser 4 minutos.

### 2. Vértice por Parada Física

Cada `stop_id` do GTFS vira exatamente um vértice.
Alternativas consideradas e descartadas:

- **Grafo tempo-expandido** (vértice = parada × horário): modela
  com precisão o tempo de espera pelo próximo ônibus, mas explode
  para O(V × T) vértices — inviável sem dados de frequência detalhados.
- **Vértice por linha-parada**: permite modelar baldeações como arcos
  de custo zero, mas duplica vértices e complica a interface.

A escolha simples (um vértice por parada) é adequada porque
estamos minimizando **tempo de viagem em movimento**,
não tempo de espera (que depende do horário do dia).

### 3. Peso das Arestas de Trânsito

```
peso(A → B) = stop_times[B].arrival_seconds - stop_times[A].departure_seconds
```

Usa a **primeira viagem registrada** de cada par de paradas na mesma linha.
Justificativa: o tempo entre paradas consecutivas é estável entre viagens
da mesma linha no mesmo sentido; o horário absoluto varia, mas a diferença
entre paradas consecutivas é determinada pela distância e velocidade da via.

### 4. Arcos de Transferência (Caminhada)

Paradas dentro de `WALK_THRESHOLD = 400m` recebem arcos bidirecionais:

```
peso_caminhada = distância_Haversine(A, B) / 1.39 m/s
```

400m foi escolhido como limiar porque:
- É a distância máxima que a maioria das pessoas aceita caminhar
  para fazer uma baldeação (referência: ITDP Brasil)
- Evita conectar paradas de bairros diferentes que são próximas
  em linha reta mas separadas por obstáculos (rios, vias expressas)

### 5. Por que não modelar tempo de espera?

Modelar a espera pelo próximo ônibus exigiria saber o horário de partida
do usuário — o que tornaria o grafo dinâmico (muda a cada consulta).
O modelo atual calcula o **tempo mínimo possível** dado que o usuário
embarca no próximo ônibus disponível — uma simplificação honesta
e explicitamente documentada.

---

## Estrutura GTFS → Grafo

```
stops.txt       → Vertex(stop_id, stop_name, lat, lon)
routes.txt      → rótulo das arestas (route_short_name | route_long_name)
trips.txt       → associa viagens a linhas
stop_times.txt  → Arc(from_stop, to_stop, Δt_segundos, route_label)
Haversine       → Arc(stop_A, stop_B, walk_seconds, "🚶 A pé")
```

## Exemplo de Execução do Dijkstra

Consulta: Terminal Gama → FGA

```
Inicialização:
  dist[Terminal Gama] = 0
  dist[todos os outros] = ∞

Iteração 1 — extrai Terminal Gama (custo 0):
  Relaxa vizinhos: Setor Central (240s), Setor Norte (360s), …

Iteração 2 — extrai Setor Central (custo 240s):
  Relaxa vizinhos: Setor Leste Q.6 (420s), Hospital (540s), …

Iteração 3 — extrai Setor Norte (custo 360s):
  Descobre arco a pé para Setor Leste Q.12 (360 + 180 = 540s)

...

Iteração N — extrai FGA/Principal:
  PARADA ANTECIPADA — destino encontrado.

Reconstrução: FGA ← Setor Leste Q.6 ← Setor Central ← Terminal Gama
Custo total: 19min
```
