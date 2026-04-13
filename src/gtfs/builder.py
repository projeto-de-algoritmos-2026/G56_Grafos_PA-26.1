"""
Construção do Grafo a partir de um GTFSFeed.

Este módulo é a ponte entre os dados GTFS e o algoritmo de Dijkstra.
Cada decisão de modelagem tem impacto direto na qualidade das rotas.

Decisões de modelagem:
─────────────────────
1. Um vértice por parada (stop_id único).
   Simples, direto, sem explosão de estados.

2. Arco dirigido entre paradas consecutivas de cada viagem.
   Peso = diferença de departure_time entre paradas.
   Uma viagem com 20 paradas gera 19 arcos.

3. Por que usar a primeira viagem de cada par (parada_A → parada_B)?
   Para simplificar sem perder utilidade: usamos o tempo médio entre
   paradas consecutivas de uma linha como proxy do tempo de viagem.
   Isso é razoável porque o tempo entre paradas varia pouco entre
   viagens diferentes da mesma linha no mesmo sentido.

4. Arcos de transferência (caminhada).
   Paradas a ≤ WALK_THRESHOLD_M metros recebem arcos bidirecionais
   com peso = distância / velocidade_média_pedestre.
   Isso permite que o Dijkstra descubra baldeações realistas.

5. Grafo DIRIGIDO para modelar linhas de mão única
   (ônibus não necessariamente faz o mesmo trajeto nos dois sentidos).
"""

from __future__ import annotations

import math
import logging
from typing import Dict, Set, Tuple

from src.graph.graph import Arc, Graph, Vertex
from src.gtfs.models import GTFSFeed, Stop

log = logging.getLogger(__name__)

# Raio máximo (metros) para considerar duas paradas como conectadas a pé
WALK_THRESHOLD_M: float = 400.0

# Velocidade média de caminhada (m/s) — ~5 km/h
WALK_SPEED_MS: float = 5000 / 3600


def build_graph(feed: GTFSFeed, add_walk_transfers: bool = True) -> Graph:
    """
    Constrói o grafo de transporte público a partir de um GTFSFeed.

    Args:
        feed:               Feed GTFS já carregado e ordenado.
        add_walk_transfers: Se True, adiciona arcos de caminhada entre
                            paradas próximas (habilita descoberta de baldeações).

    Returns:
        Graph pronto para ser passado ao Dijkstra.
    """
    graph = Graph()

    # 1. Adiciona todas as paradas como vértices
    for stop in feed.stops.values():
        graph.add_vertex(Vertex(
            vertex_id=stop.stop_id,
            label=stop.stop_name,
            lat=stop.stop_lat,
            lon=stop.stop_lon,
        ))

    # 2. Para cada viagem, adiciona arcos entre paradas consecutivas
    transit_arcs: int = 0
    # Rastreia pares já adicionados para evitar duplicatas de mesma linha/peso
    seen_arcs: Set[Tuple[str, str, str]] = set()

    for trip_id, stop_times in feed.stop_times.items():
        trip = feed.trips.get(trip_id)
        if trip is None:
            continue
        route = feed.routes.get(trip.route_id)
        route_label = route.label if route else trip.route_id

        for i in range(len(stop_times) - 1):
            a = stop_times[i]
            b = stop_times[i + 1]

            # Peso = tempo entre saída de A e chegada em B (segundos)
            weight = float(b.arrival_seconds - a.departure_seconds)

            if weight <= 0:
                # Dado GTFS inconsistente (horários iguais ou invertidos): usa 60s
                weight = 60.0

            key = (a.stop_id, b.stop_id, trip.route_id)
            if key in seen_arcs:
                continue
            seen_arcs.add(key)

            # Verifica se ambos os vértices existem (parada pode não estar em stops.txt)
            if not graph.has_vertex(a.stop_id) or not graph.has_vertex(b.stop_id):
                continue

            graph.add_arc(Arc(
                from_id=a.stop_id,
                to_id=b.stop_id,
                weight=weight,
                route_label=route_label,
                is_walk=False,
            ))
            transit_arcs += 1

    log.info("Arcos de trânsito adicionados: %d", transit_arcs)

    # 3. Arcos de caminhada entre paradas próximas
    if add_walk_transfers:
        walk_arcs = _add_walk_transfers(graph, feed)
        log.info("Arcos de caminhada adicionados: %d", walk_arcs)

    return graph


def _add_walk_transfers(graph: Graph, feed: GTFSFeed) -> int:
    """
    Adiciona arcos bidirecionais de caminhada entre paradas
    que estejam a no máximo WALK_THRESHOLD_M metros uma da outra.

    Usa fórmula de Haversine para distância precisa entre coordenadas.
    """
    stops = list(feed.stops.values())
    added = 0

    for i in range(len(stops)):
        for j in range(i + 1, len(stops)):
            a, b = stops[i], stops[j]
            dist_m = _haversine_meters(a.stop_lat, a.stop_lon, b.stop_lat, b.stop_lon)
            if dist_m <= WALK_THRESHOLD_M:
                walk_time = dist_m / WALK_SPEED_MS  # segundos
                label = f"A pé ({dist_m:.0f}m)"

                graph.add_arc(Arc(a.stop_id, b.stop_id, walk_time, label, is_walk=True))
                graph.add_arc(Arc(b.stop_id, a.stop_id, walk_time, label, is_walk=True))
                added += 2

    return added


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Distância em metros entre dois pontos geográficos (fórmula de Haversine).

    Usa o raio médio da Terra (6 371 000 m). Preciso para distâncias
    curtas (< 100 km), que é sempre o caso entre paradas de ônibus.
    """
    R = 6_371_000  # metros
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ / 2) ** 2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
