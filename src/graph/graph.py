"""
Grafo dirigido e ponderado com lista de adjacência.

Modela a rede de transporte público do DF:
  - Vértices  → paradas de ônibus
  - Arestas   → conexões entre paradas consecutivas de uma linha
  - Peso      → tempo de viagem em segundos
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple


@dataclass(frozen=True)
class Vertex:
    """Representa uma parada de ônibus no grafo."""
    vertex_id: str          # stop_id do GTFS
    label: str              # stop_name do GTFS
    lat: float = 0.0
    lon: float = 0.0

    def __hash__(self) -> int:
        return hash(self.vertex_id)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Vertex) and self.vertex_id == other.vertex_id

    def __repr__(self) -> str:
        return f"Vertex({self.vertex_id!r}, {self.label!r})"


@dataclass
class Arc:
    """
    Arco (aresta dirigida) entre duas paradas.

    route_label é apenas informativo — o mesmo par de paradas
    pode ser conectado por linhas diferentes com pesos distintos.
    """
    from_id: str
    to_id: str
    weight: float           # tempo em segundos
    route_label: str = ""   # ex: "0.117 | Gama – Plano Piloto"
    is_walk: bool = False   # True = conexão a pé (transferência)


class Graph:
    """
    Grafo dirigido ponderado com lista de adjacência.

    Projetado para ser esparso — redes de transporte têm muitos
    vértices e cada parada tem poucos vizinhos diretos.

    Complexidade:
        Espaço:             O(V + E)
        add_vertex:         O(1)
        add_arc:            O(1)
        neighbors(v):       O(grau_saída(v))
        has_vertex:         O(1)  [hash]
    """

    def __init__(self) -> None:
        self._vertices: Dict[str, Vertex] = {}
        # Lista de adjacência: vid → [(vizinho_id, peso, route_label, is_walk)]
        self._adj: Dict[str, List[Tuple[str, float, str, bool]]] = {}

    # ------------------------------------------------------------------ #
    #  Inserção                                                            #
    # ------------------------------------------------------------------ #

    def add_vertex(self, v: Vertex) -> None:
        """Adiciona vértice; ignora se já existir (idempotente)."""
        if v.vertex_id not in self._vertices:
            self._vertices[v.vertex_id] = v
            self._adj[v.vertex_id] = []

    def add_arc(self, arc: Arc) -> None:
        """
        Adiciona arco dirigido from→to.

        Raises:
            KeyError: se algum dos vértices não existir.
            ValueError: se o peso for negativo.
        """
        if arc.from_id not in self._vertices:
            raise KeyError(f"Vértice de origem não existe: {arc.from_id!r}")
        if arc.to_id not in self._vertices:
            raise KeyError(f"Vértice de destino não existe: {arc.to_id!r}")
        if arc.weight < 0:
            raise ValueError(f"Peso negativo não permitido: {arc.weight}")

        self._adj[arc.from_id].append(
            (arc.to_id, arc.weight, arc.route_label, arc.is_walk)
        )

    # ------------------------------------------------------------------ #
    #  Consultas                                                           #
    # ------------------------------------------------------------------ #

    def neighbors(self, vid: str) -> List[Tuple[str, float, str, bool]]:
        """Retorna [(vizinho_id, peso, route_label, is_walk)] para vid."""
        return self._adj.get(vid, [])

    def get_vertex(self, vid: str) -> Optional[Vertex]:
        return self._vertices.get(vid)

    def has_vertex(self, vid: str) -> bool:
        return vid in self._vertices

    def all_vertices(self) -> Iterator[Vertex]:
        return iter(self._vertices.values())

    def vertex_count(self) -> int:
        return len(self._vertices)

    def arc_count(self) -> int:
        return sum(len(adj) for adj in self._adj.values())

    def __contains__(self, vid: str) -> bool:
        return vid in self._vertices

    def __repr__(self) -> str:
        return f"Graph(V={self.vertex_count()}, E={self.arc_count()})"
