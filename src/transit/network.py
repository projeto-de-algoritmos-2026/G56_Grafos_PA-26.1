"""
Rede de Transporte Público do DF.

Camada de serviço que une o grafo (Dijkstra) com os dados GTFS,
expondo uma interface de alto nível para consultas de rota.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from src.graph.dijkstra import PathResult, shortest_path
from src.graph.graph import Graph, Vertex
from src.gtfs.builder import build_graph
from src.gtfs.models import GTFSFeed
from src.gtfs.parser import parse_gtfs_directory

log = logging.getLogger(__name__)

# Parada da FGA no dataset de exemplo
FGA_STOP_ID = "S065"
TERMINAL_GAMA_STOP_ID = "S001"


class TransitNetwork:
    """
    Representa a rede de transporte público carregada do GTFS.

    Pré-compila o grafo na construção; consultas posteriores são baratas.
    """

    def __init__(self, gtfs_dir: Path, route_filter: Optional[set] = None):
        log.info("Carregando feed GTFS de %s …", gtfs_dir)
        self.feed: GTFSFeed = parse_gtfs_directory(gtfs_dir, route_filter)
        log.info("Construindo grafo de transporte …")
        self.graph: Graph = build_graph(self.feed, add_walk_transfers=True)
        log.info("Rede pronta: %s", self.graph)

    # ------------------------------------------------------------------ #
    #  Consultas principais                                               #
    # ------------------------------------------------------------------ #

    def find_route(self, origin_id: str, dest_id: str) -> PathResult:
        """
        Encontra o trajeto de menor tempo entre duas paradas.

        Usa Dijkstra com o grafo pré-construído.
        Complexidade: O((V + E) · log V).
        """
        if origin_id not in self.graph:
            raise ValueError(f"Parada de origem não existe: {origin_id!r}")
        if dest_id not in self.graph:
            raise ValueError(f"Parada de destino não existe: {dest_id!r}")
        return shortest_path(self.graph, origin_id, dest_id)

    def find_route_to_fga(self, origin_id: str) -> PathResult:
        """Atalho: rota de qualquer parada até a FGA."""
        return self.find_route(origin_id, FGA_STOP_ID)

    def search_stops(self, query: str) -> List[Vertex]:
        """Busca paradas cujo nome contenha a query (case-insensitive)."""
        q = query.lower()
        return [
            v for v in self.graph.all_vertices()
            if q in v.label.lower()
        ]

    def get_stop(self, stop_id: str) -> Optional[Vertex]:
        return self.graph.get_vertex(stop_id)

    def all_stops(self) -> List[Vertex]:
        return sorted(self.graph.all_vertices(), key=lambda v: v.label)

    # ------------------------------------------------------------------ #
    #  Metadados                                                          #
    # ------------------------------------------------------------------ #

    @property
    def stats(self) -> dict:
        return {
            "paradas": self.graph.vertex_count(),
            "arcos":   self.graph.arc_count(),
            "linhas":  len(self.feed.routes),
            "viagens": len(self.feed.trips),
        }

    def __repr__(self) -> str:
        return f"TransitNetwork(DF, {self.graph})"
