"""
Parser de arquivos GTFS no formato CSV.

Lê os arquivos do diretório GTFS e popula um GTFSFeed.
Compatível com o feed do SEMOB-DF e com qualquer feed GTFS estático padrão.

Uso:
    feed = parse_gtfs_directory(Path("data/gtfs/"))
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Optional

from src.gtfs.models import GTFSFeed, Route, Stop, StopTime, Trip

log = logging.getLogger(__name__)


def parse_gtfs_directory(
    gtfs_dir: Path,
    route_filter: Optional[set] = None,
) -> GTFSFeed:
    """
    Carrega e retorna um GTFSFeed a partir de um diretório GTFS.

    Args:
        gtfs_dir:     Caminho para o diretório contendo os .txt do GTFS.
        route_filter: Conjunto de route_ids a incluir. Se None, carrega tudo.
                      Use para trabalhar apenas com linhas que servem o Gama.

    Returns:
        GTFSFeed populado e com stop_times ordenados.

    Raises:
        FileNotFoundError: se algum arquivo obrigatório não existir.
    """
    feed = GTFSFeed()

    _parse_stops(gtfs_dir / "stops.txt", feed)
    _parse_routes(gtfs_dir / "routes.txt", feed, route_filter)
    _parse_trips(gtfs_dir / "trips.txt", feed)
    _parse_stop_times(gtfs_dir / "stop_times.txt", feed)
    feed.sort_stop_times()

    log.info("GTFS carregado: %s", feed)
    return feed


# ------------------------------------------------------------------ #
#  Parsers individuais (privados)                                     #
# ------------------------------------------------------------------ #

def _parse_stops(path: Path, feed: GTFSFeed) -> None:
    _require(path)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            try:
                feed.add_stop(Stop(
                    stop_id=row["stop_id"].strip(),
                    stop_name=row["stop_name"].strip(),
                    stop_lat=float(row["stop_lat"]),
                    stop_lon=float(row["stop_lon"]),
                ))
            except (KeyError, ValueError) as e:
                log.warning("Linha inválida em stops.txt: %s — %s", row, e)


def _parse_routes(path: Path, feed: GTFSFeed, route_filter: Optional[set]) -> None:
    _require(path)
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rid = row["route_id"].strip()
            if route_filter and rid not in route_filter:
                continue
            try:
                feed.add_route(Route(
                    route_id=rid,
                    route_short_name=row.get("route_short_name", "").strip(),
                    route_long_name=row.get("route_long_name", "").strip(),
                    route_type=int(row.get("route_type", 3)),
                ))
            except (KeyError, ValueError) as e:
                log.warning("Linha inválida em routes.txt: %s — %s", row, e)


def _parse_trips(path: Path, feed: GTFSFeed) -> None:
    _require(path)
    # Conjunto de route_ids carregados para filtrar trips
    loaded_routes = set(feed.routes.keys())
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            rid = row["route_id"].strip()
            if rid not in loaded_routes:
                continue
            try:
                feed.add_trip(Trip(
                    trip_id=row["trip_id"].strip(),
                    route_id=rid,
                    direction_id=int(row.get("direction_id", 0)),
                ))
            except (KeyError, ValueError) as e:
                log.warning("Linha inválida em trips.txt: %s — %s", row, e)


def _parse_stop_times(path: Path, feed: GTFSFeed) -> None:
    _require(path)
    loaded_trips = set(feed.trips.keys())
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            tid = row["trip_id"].strip()
            if tid not in loaded_trips:
                continue
            try:
                arr = StopTime.parse_time(row["arrival_time"])
                dep = StopTime.parse_time(row["departure_time"])
                feed.add_stop_time(StopTime(
                    trip_id=tid,
                    stop_id=row["stop_id"].strip(),
                    stop_sequence=int(row["stop_sequence"]),
                    arrival_seconds=arr,
                    departure_seconds=dep,
                ))
            except (KeyError, ValueError) as e:
                log.warning("Linha inválida em stop_times.txt: %s — %s", row, e)


def _require(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo GTFS obrigatório não encontrado: {path}\n"
            "Baixe o feed do SEMOB-DF em:\n"
            "  https://www.semob.df.gov.br/  (seção 'Dados Abertos / GTFS')\n"
            "e extraia o conteúdo em data/gtfs/"
        )
