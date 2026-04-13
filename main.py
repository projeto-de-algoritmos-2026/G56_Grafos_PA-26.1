#!/usr/bin/env python3
"""
DF Transit Navigator
Menor Caminho por Transporte Público no DF usando Dijkstra + GTFS

Uso:
    python main.py              Interface gráfica (padrão)
    python main.py --cli        Interface de linha de comando
    python main.py --demo       Demonstração automática (sem interação)
    python main.py --test       Executa suite de testes rápidos
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.transit.formatter import format_itinerary
from src.transit.network import FGA_STOP_ID, TERMINAL_GAMA_STOP_ID, TransitNetwork


def _load_network() -> TransitNetwork:
    gtfs_dir = Path(__file__).parent / "data" / "gtfs"
    return TransitNetwork(gtfs_dir)


def demo_mode() -> None:
    print("\n" + "═" * 60)
    print("  DF Transit Navigator — DEMONSTRAÇÃO")
    print("  Algoritmo: Dijkstra | Fonte: GTFS SEMOB-DF")
    print("═" * 60)

    net = _load_network()

    demo_cases = [
        ("S025", "S004",  "Rodoviária do Plano Piloto → FGA"),
        ("S033", "S004",  "Santa Maria → FGA"),
        ("S018", "S004",  "Terminal Taguatinga → FGA"),
        ("S023", "S004",  "Samambaia Norte → FGA"),
        ("S001", "S004",  "Terminal Gama → FGA (local)"),
    ]

    for origin_id, dest_id, label in demo_cases:
        print(f"\n  {'─'*56}")
        print(f"  {label}")
        result = net.find_route(origin_id, dest_id)
        print(format_itinerary(result, net.graph))


def test_mode() -> None:
    print("\n  Carregando rede...", end=" ", flush=True)
    net = _load_network()
    print("OK\n")

    passed = failed = 0

    def check(desc: str, condition: bool) -> None:
        nonlocal passed, failed
        icon = "OK  " if condition else "FALHOU"
        print(f"  {icon}  {desc}")
        if condition:
            passed += 1
        else:
            failed += 1

    # Estrutura do grafo
    check("Grafo tem vértices",            net.graph.vertex_count() > 0)
    check("Grafo tem arcos",               net.graph.arc_count() > 0)
    check("Parada FGA existe",             net.graph.has_vertex(FGA_STOP_ID))
    check("Terminal Gama existe",          net.graph.has_vertex(TERMINAL_GAMA_STOP_ID))

    # Rotas
    r1 = net.find_route("S025", "S004")
    check("Rodoviária → FGA: alcançável",  r1.reachable)
    check("Rodoviária → FGA: tempo > 0",   r1.total_seconds > 0)

    r2 = net.find_route("S001", "S004")
    check("Terminal Gama → FGA: alcançável", r2.reachable)
    check("Terminal Gama → FGA < Rodoviária → FGA",
          r2.total_seconds < r1.total_seconds)

    r3 = net.find_route("S004", "S004")
    check("FGA → FGA: tempo zero",         r3.total_seconds == 0.0)

    # Busca de paradas
    found = net.search_stops("gama")
    check("Busca 'gama' retorna resultados", len(found) > 0)

    found_fga = net.search_stops("FGA")
    check("Busca 'FGA' encontra a parada",  len(found_fga) > 0)

    print(f"\n  Resultado: {passed} OK  {failed} FALHOU\n")
    if failed:
        sys.exit(1)


def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(
        description="DF Transit Navigator — Dijkstra + GTFS SEMOB-DF",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cli",     action="store_true", help="Interface de terminal")
    parser.add_argument("--demo",    action="store_true", help="Modo demonstração")
    parser.add_argument("--test",    action="store_true", help="Testa a implementação")
    parser.add_argument("--verbose", action="store_true", help="Log detalhado")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, force=True)

    if args.demo:
        demo_mode()
    elif args.test:
        test_mode()
    elif args.cli:
        from src.cli.interface import run
        run()
    else:
        from src.gui.app import run_gui
        run_gui()


if __name__ == "__main__":
    main()
