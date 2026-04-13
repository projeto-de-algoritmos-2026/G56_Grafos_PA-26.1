"""
Algoritmo de Dijkstra para redes de transporte público.

Por que Dijkstra e não BFS?
    BFS minimiza número de arestas (= número de paradas), não o tempo.
    Com pesos diferentes por aresta (linhas rápidas vs. lentas,
    baldeação a pé vs. ônibus direto), apenas Dijkstra garante
    o menor tempo total de viagem.

Por que não Bellman-Ford?
    Todos os pesos são não-negativos (tempo não pode ser negativo),
    então Dijkstra é suficiente e mais eficiente: O((V+E)·log V)
    contra O(V·E) do Bellman-Ford.

Referência:
    Dijkstra, E. W. (1959). "A note on two problems in connexion
    with graphs." Numerische Mathematik, 1(1), 269–271.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from src.graph.graph import Graph


@dataclass
class PathResult:
    """Resultado do menor caminho entre dois vértices."""

    origin_id: str
    dest_id: str
    total_seconds: float
    # Sequência de (stop_id, route_label_do_trecho_anterior)
    # O primeiro elemento sempre tem route_label == ""
    steps: List[Tuple[str, str]]
    reachable: bool = True

    # ------------------------------------------------------------------ #
    #  Propriedades derivadas                                             #
    # ------------------------------------------------------------------ #

    @property
    def stop_ids(self) -> List[str]:
        return [sid for sid, _ in self.steps]

    @property
    def n_transfers(self) -> int:
        """
        Número de baldeações = quantas vezes a linha muda ao longo do caminho.
        Trechos a pé também contam como uma 'mudança'.
        """
        routes = [r for _, r in self.steps if r]
        if not routes:
            return 0
        changes = sum(1 for a, b in zip(routes, routes[1:]) if a != b)
        return changes

    @property
    def total_minutes(self) -> float:
        return self.total_seconds / 60.0

    @property
    def formatted_time(self) -> str:
        m = int(self.total_seconds // 60)
        s = int(self.total_seconds % 60)
        if m >= 60:
            h = m // 60
            m = m % 60
            return f"{h}h {m:02d}min"
        if m == 0:
            return f"{s}s"
        if s == 0:
            return f"{m}min"
        return f"{m}min {s:02d}s"

    def __repr__(self) -> str:
        if not self.reachable:
            return f"PathResult(inacessível: {self.origin_id!r} → {self.dest_id!r})"
        return (
            f"PathResult({self.origin_id!r} → {self.dest_id!r}, "
            f"tempo={self.formatted_time}, baldeações={self.n_transfers})"
        )


def dijkstra(
    graph: Graph,
    origin_id: str,
    destination_id: Optional[str] = None,
) -> Dict[str, PathResult]:
    """
    Dijkstra com min-heap a partir de um vértice de origem.

    Implementação do zero, sem bibliotecas externas de grafo.

    Args:
        graph:          Grafo do sistema de transporte.
        origin_id:      ID da parada de origem.
        destination_id: ID da parada de destino. Se fornecido, a busca
                        termina antecipadamente ao finalizar esse vértice
                        (otimização: evita explorar todo o grafo).

    Returns:
        Dict { stop_id → PathResult } com o menor caminho da origem
        até cada parada alcançável.

    Raises:
        KeyError: se origin_id não existir no grafo.
    """
    if origin_id not in graph:
        raise KeyError(f"Parada de origem não existe no grafo: {origin_id!r}")

    INF = float("inf")

    # dist[v]  = menor tempo acumulado de origin até v
    dist: Dict[str, float] = {v.vertex_id: INF for v in graph.all_vertices()}
    dist[origin_id] = 0.0

    # prev[v] = (predecessor_id, route_label_do_trecho) para reconstrução
    prev: Dict[str, Optional[Tuple[str, str]]] = {
        v.vertex_id: None for v in graph.all_vertices()
    }

    # Min-heap: (custo_acumulado, stop_id)
    heap: List[Tuple[float, str]] = []
    heapq.heappush(heap, (0.0, origin_id))

    visited: set = set()

    # ------------------------------------------------------------------ #
    #  Loop principal                                                     #
    # ------------------------------------------------------------------ #
    while heap:
        cost, uid = heapq.heappop(heap)

        if uid in visited:
            # Entrada desatualizada na heap — descarta
            continue
        visited.add(uid)

        # Parada antecipada: destino já finalizado
        if destination_id is not None and uid == destination_id:
            break

        # Relaxamento de arcos saindo de uid
        for (vid, weight, route_label, is_walk) in graph.neighbors(uid):
            if vid in visited:
                continue
            new_cost = cost + weight
            if new_cost < dist[vid]:
                dist[vid] = new_cost
                prev[vid] = (uid, route_label)
                heapq.heappush(heap, (new_cost, vid))

    # ------------------------------------------------------------------ #
    #  Reconstrução dos caminhos                                          #
    # ------------------------------------------------------------------ #
    targets = [destination_id] if destination_id else list(dist.keys())
    results: Dict[str, PathResult] = {}

    for tid in targets:
        if tid is None or tid not in dist:
            continue
        total = dist[tid]
        if total == INF:
            results[tid] = PathResult(
                origin_id=origin_id,
                dest_id=tid,
                total_seconds=INF,
                steps=[],
                reachable=False,
            )
        else:
            steps = _reconstruct(prev, origin_id, tid)
            results[tid] = PathResult(
                origin_id=origin_id,
                dest_id=tid,
                total_seconds=total,
                steps=steps,
                reachable=True,
            )

    return results


def shortest_path(graph: Graph, origin_id: str, dest_id: str) -> PathResult:
    """Atalho: retorna o PathResult para um único par origem→destino."""
    res = dijkstra(graph, origin_id, dest_id)
    if dest_id not in res:
        return PathResult(origin_id, dest_id, float("inf"), [], reachable=False)
    return res[dest_id]


# ------------------------------------------------------------------ #
#  Auxiliar privado                                                   #
# ------------------------------------------------------------------ #

def _reconstruct(
    prev: Dict[str, Optional[Tuple[str, str]]],
    origin_id: str,
    target_id: str,
) -> List[Tuple[str, str]]:
    """
    Reconstrói o caminho de origin até target seguindo os ponteiros prev.

    Retorna lista de (stop_id, route_label_usado_para_chegar_aqui).
    O primeiro elemento (origem) tem route_label == "".
    """
    path: List[Tuple[str, str]] = []
    current = target_id

    while current is not None:
        info = prev.get(current)
        if info is None:
            path.append((current, ""))
            break
        predecessor, route_label = info
        path.append((current, route_label))
        current = predecessor

    path.reverse()

    if not path or path[0][0] != origin_id:
        return []
    return path
