"""
Interface de Linha de Comando — DF Transit Navigator.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from src.graph.graph import Vertex
from src.transit.formatter import format_itinerary
from src.transit.network import FGA_STOP_ID, TERMINAL_GAMA_STOP_ID, TransitNetwork

SEP  = "─" * 60
SEP2 = "═" * 60


def _header(title: str) -> None:
    print(f"\n{SEP2}")
    print(f"  {title}")
    print(SEP2)


def _section(title: str) -> None:
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)


# ------------------------------------------------------------------ #
#  Seleção de parada                                                  #
# ------------------------------------------------------------------ #

def _pick_stop(network: TransitNetwork, prompt: str) -> Optional[Vertex]:
    """
    Permite ao usuário buscar uma parada por nome ou selecionar da lista.
    """
    while True:
        query = input(f"\n  {prompt} (nome ou parte do nome): ").strip()
        if not query:
            return None

        found = network.search_stops(query)
        if not found:
            print("  Nenhuma parada encontrada. Tente outro termo.")
            continue
        if len(found) == 1:
            print(f"  Parada encontrada: {found[0].label}")
            return found[0]

        print(f"\n  {len(found)} parada(s) encontrada(s):")
        for i, v in enumerate(found[:20], 1):
            print(f"    {i:2d}. {v.label}  [{v.vertex_id}]")

        try:
            idx = int(input("  Número da parada: ")) - 1
            if 0 <= idx < len(found):
                return found[idx]
            print("  Índice inválido.")
        except (ValueError, KeyboardInterrupt):
            return None


# ------------------------------------------------------------------ #
#  Menus                                                              #
# ------------------------------------------------------------------ #

def _menu_route(network: TransitNetwork) -> None:
    _section("Consultar Rota")

    origin = _pick_stop(network, "Parada de ORIGEM")
    if origin is None:
        print("  Operação cancelada.")
        return

    dest = _pick_stop(network, "Parada de DESTINO")
    if dest is None:
        print("  Operação cancelada.")
        return

    result = network.find_route(origin.vertex_id, dest.vertex_id)
    print(format_itinerary(result, network.graph))


def _menu_route_to_fga(network: TransitNetwork) -> None:
    _section("Rota até a FGA (UnB Gama)")

    fga = network.get_stop(FGA_STOP_ID)
    print(f"\n  Destino fixo: {fga.label if fga else 'FGA'}")

    origin = _pick_stop(network, "Sua parada de origem")
    if origin is None:
        print("  Operação cancelada.")
        return

    result = network.find_route_to_fga(origin.vertex_id)
    print(format_itinerary(result, network.graph))


def _menu_list_stops(network: TransitNetwork) -> None:
    _section("Paradas Disponíveis no Dataset")
    stops = network.all_stops()
    print(f"\n  Total: {len(stops)} paradas\n")
    for v in stops:
        print(f"    [{v.vertex_id:4s}]  {v.label}")
    print()


def _menu_network_info(network: TransitNetwork) -> None:
    _section("Informações da Rede")
    s = network.stats
    print(f"\n  Rede: Transporte Público do DF (SEMOB-DF / GTFS)")
    print(f"  Paradas no grafo:  {s['paradas']}")
    print(f"  Arcos no grafo:    {s['arcos']}")
    print(f"  Linhas carregadas: {s['linhas']}")
    print(f"  Viagens:           {s['viagens']}")
    print(f"\n  Linhas disponíveis:")
    for route in sorted(network.feed.routes.values(), key=lambda r: r.route_short_name):
        print(f"    • {route.route_short_name:8s} {route.route_long_name}")
    print()


# ------------------------------------------------------------------ #
#  Loop principal                                                     #
# ------------------------------------------------------------------ #

def run(network: Optional[TransitNetwork] = None, gtfs_dir: Optional[Path] = None) -> None:
    if network is None:
        data_dir = gtfs_dir or Path(__file__).resolve().parents[2] / "data" / "gtfs"
        print("\n  Carregando rede de transporte (GTFS)... ", end="", flush=True)
        network = TransitNetwork(data_dir)
        print("OK")

    while True:
        _header("DF Transit Navigator — Menor Caminho por Transporte Público")
        print(f"  Dados: SEMOB-DF / GTFS  |  Algoritmo: Dijkstra")
        s = network.stats
        print(f"  Grafo: {s['paradas']} paradas · {s['arcos']} arcos · {s['linhas']} linhas\n")
        print("  1. Consultar rota entre duas paradas quaisquer")
        print("  2. Rota até a FGA (UnB Gama) — destino fixo")
        print("  3. Listar todas as paradas disponíveis")
        print("  4. Informações da rede e linhas carregadas")
        print("  5. Sair\n")

        choice = input("  Opção: ").strip()

        if choice == "1":
            _menu_route(network)
        elif choice == "2":
            _menu_route_to_fga(network)
        elif choice == "3":
            _menu_list_stops(network)
        elif choice == "4":
            _menu_network_info(network)
        elif choice == "5":
            print("\n  Até logo!\n")
            sys.exit(0)
        else:
            print("  Opção inválida.")
