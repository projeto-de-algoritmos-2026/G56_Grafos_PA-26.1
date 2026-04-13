"""
Modelos de dados do padrão GTFS (General Transit Feed Specification).

O GTFS é o formato aberto adotado pelo SEMOB-DF (e pela maioria dos
sistemas de transporte do mundo) para publicar dados de linhas e horários.

Referência: https://gtfs.org/reference/static/
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Stop:
    """
    Representa uma parada de ônibus (stops.txt).
    Campos obrigatórios do GTFS usados neste projeto.
    """
    stop_id: str
    stop_name: str
    stop_lat: float
    stop_lon: float

    def __repr__(self) -> str:
        return f"Stop({self.stop_id!r}, {self.stop_name!r})"


@dataclass
class Route:
    """Representa uma linha de ônibus (routes.txt)."""
    route_id: str
    route_short_name: str   # ex: "0.117"
    route_long_name: str    # ex: "GAMA / PLANO PILOTO"
    route_type: int = 3     # 3 = ônibus (GTFS padrão)

    @property
    def label(self) -> str:
        return f"{self.route_short_name} | {self.route_long_name}"

    def __repr__(self) -> str:
        return f"Route({self.route_id!r}, {self.label!r})"


@dataclass
class Trip:
    """Representa uma viagem específica de uma linha (trips.txt)."""
    trip_id: str
    route_id: str
    direction_id: int = 0   # 0 = ida, 1 = volta


@dataclass
class StopTime:
    """
    Representa o horário de passagem em uma parada (stop_times.txt).
    O GTFS usa formato HH:MM:SS, inclusive com horas > 23 (ex: 25:30:00).
    """
    trip_id: str
    stop_id: str
    stop_sequence: int
    arrival_seconds: int    # segundos desde meia-noite
    departure_seconds: int

    @staticmethod
    def parse_time(hhmmss: str) -> int:
        """Converte 'HH:MM:SS' (inclusive >23h) para segundos desde meia-noite."""
        parts = hhmmss.strip().split(":")
        if len(parts) != 3:
            raise ValueError(f"Formato de tempo inválido: {hhmmss!r}")
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return h * 3600 + m * 60 + s


@dataclass
class GTFSFeed:
    """Agrega todos os dados carregados de um feed GTFS."""
    stops: Dict[str, Stop] = field(default_factory=dict)
    routes: Dict[str, Route] = field(default_factory=dict)
    trips: Dict[str, Trip] = field(default_factory=dict)
    # stop_times: trip_id → lista ordenada por stop_sequence
    stop_times: Dict[str, List[StopTime]] = field(default_factory=dict)

    def add_stop(self, s: Stop) -> None:
        self.stops[s.stop_id] = s

    def add_route(self, r: Route) -> None:
        self.routes[r.route_id] = r

    def add_trip(self, t: Trip) -> None:
        self.trips[t.trip_id] = t

    def add_stop_time(self, st: StopTime) -> None:
        self.stop_times.setdefault(st.trip_id, []).append(st)

    def sort_stop_times(self) -> None:
        """Ordena cada viagem por stop_sequence. Chamar após carregar tudo."""
        for tid in self.stop_times:
            self.stop_times[tid].sort(key=lambda x: x.stop_sequence)

    def __repr__(self) -> str:
        return (
            f"GTFSFeed("
            f"paradas={len(self.stops)}, "
            f"linhas={len(self.routes)}, "
            f"viagens={len(self.trips)})"
        )
