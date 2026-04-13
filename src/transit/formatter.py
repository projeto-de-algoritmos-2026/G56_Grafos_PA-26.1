"""
Formatação de rotas para exibição no terminal.

Transforma um PathResult em um itinerário legível,
agrupando trechos consecutivos da mesma linha.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from src.graph.dijkstra import PathResult
from src.graph.graph import Graph


@dataclass
class Leg:
    """Um trecho contínuo da viagem — sequência de paradas na mesma linha."""
    route_label: str
    stops: List[str]        # nomes das paradas
    is_walk: bool = False

    @property
    def n_stops(self) -> int:
        return max(0, len(self.stops) - 1)

    @property
    def mode_label(self) -> str:
        return "A pé" if self.is_walk else self.route_label


def build_legs(result: PathResult, graph: Graph) -> List[Leg]:
    """
    Agrupa os passos do PathResult em trechos (Legs) por linha.
    Troca de linha = novo Leg. A origem (route_label vazio) é
    absorvida como ponto de partida do primeiro leg real.
    """
    if not result.reachable or not result.steps:
        return []

    def _name(sid: str) -> str:
        v = graph.get_vertex(sid)
        return v.label if v else sid

    legs: List[Leg] = []
    pending_origin: str = ""   # nome da parada de origem (antes de ver a 1ª linha)
    current_route: str = ""
    current_stops: List[str] = []
    current_walk: bool = False

    for stop_id, route_label in result.steps:
        name = _name(stop_id)
        is_walk = bool(route_label) and "A pé" in route_label

        # Primeiro passo: sempre tem route_label vazio — só guardamos o nome
        if not current_stops and not pending_origin and not route_label:
            pending_origin = name
            continue

        # Primeiro leg real: incorpora a origem pendente
        if pending_origin and not current_stops:
            current_route = route_label
            current_walk = is_walk
            current_stops = [pending_origin, name]
            pending_origin = ""
            continue

        if route_label == current_route or not route_label:
            current_stops.append(name)
        else:
            if current_stops:
                legs.append(Leg(current_route, current_stops, current_walk))
            current_route = route_label
            current_walk = is_walk
            current_stops = [current_stops[-1], name]

    if current_stops:
        legs.append(Leg(current_route, current_stops, current_walk))

    return legs


def format_itinerary(result: PathResult, graph: Graph) -> str:
    """
    Retorna uma string formatada com o itinerário completo.
    """
    if not result.reachable:
        return "  Nenhuma rota encontrada entre essas paradas."

    origin_v = graph.get_vertex(result.origin_id)
    dest_v   = graph.get_vertex(result.dest_id)
    origin_name = origin_v.label if origin_v else result.origin_id
    dest_name   = dest_v.label   if dest_v   else result.dest_id

    lines = [
        "",
        f"  Origem:        {origin_name}",
        f"  Destino:       {dest_name}",
        f"  Tempo total:   {result.formatted_time}",
        f"  Baldeacoes:    {result.n_transfers}",
        "",
        "  ─────────────────────────────────────────────",
        "  ITINERÁRIO",
        "  ─────────────────────────────────────────────",
    ]

    legs = build_legs(result, graph)

    for i, leg in enumerate(legs, 1):
        lines.append(f"\n  {i}. {leg.mode_label}")
        for j, stop in enumerate(leg.stops):
            if j == 0:
                prefix = "     ├─"
            elif j == len(leg.stops) - 1:
                prefix = "     └─"
            else:
                prefix = "     │ "
            lines.append(f"  {prefix} {stop}")
        if not leg.is_walk and leg.n_stops > 0:
            lines.append(f"        ({leg.n_stops} parada(s))")

    lines += [
        "",
        "  ─────────────────────────────────────────────",
    ]
    return "\n".join(lines)
