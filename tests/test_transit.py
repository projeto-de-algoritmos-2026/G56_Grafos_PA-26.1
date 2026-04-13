"""
Testes unitários e de integração — DF Transit Navigator.

Cobre:
  - Estrutura do grafo (Graph)
  - Corretude do Dijkstra em grafos conhecidos
  - Parser GTFS com dados de exemplo
  - Integração ponta-a-ponta (GTFS → Grafo → Dijkstra → Rota)
"""

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.graph.graph import Arc, Graph, Vertex
from src.graph.dijkstra import PathResult, dijkstra, shortest_path


# ══════════════════════════════════════════════════════════════════════
#  Fixtures de grafos simples para isolar o algoritmo dos dados reais
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def triangle_graph() -> Graph:
    """
    Grafo triangular dirigido:
        A --10--> B --5--> C
        A --------20-----> C
    Menor caminho A→C: via B, custo 15 (não 20 direto).
    """
    g = Graph()
    for vid in ["A", "B", "C"]:
        g.add_vertex(Vertex(vid, vid))
    g.add_arc(Arc("A", "B", 10))
    g.add_arc(Arc("B", "C", 5))
    g.add_arc(Arc("A", "C", 20))
    return g


@pytest.fixture
def chain_graph() -> Graph:
    """Cadeia: 1→2 (60s) →3 (120s) →4 (180s). Soma: 1→4 = 360s."""
    g = Graph()
    for vid in ["1", "2", "3", "4"]:
        g.add_vertex(Vertex(vid, vid))
    g.add_arc(Arc("1", "2", 60))
    g.add_arc(Arc("2", "3", 120))
    g.add_arc(Arc("3", "4", 180))
    return g


@pytest.fixture
def disconnected_graph() -> Graph:
    """Dois componentes isolados: {X→Y} e {P→Q}."""
    g = Graph()
    for vid in ["X", "Y", "P", "Q"]:
        g.add_vertex(Vertex(vid, vid))
    g.add_arc(Arc("X", "Y", 30))
    g.add_arc(Arc("P", "Q", 45))
    return g


# ══════════════════════════════════════════════════════════════════════
#  Testes do Grafo
# ══════════════════════════════════════════════════════════════════════

class TestGraph:
    def test_vertex_insertion(self, triangle_graph):
        assert triangle_graph.vertex_count() == 3

    def test_arc_count(self, triangle_graph):
        assert triangle_graph.arc_count() == 3

    def test_neighbors(self, triangle_graph):
        neighbors = {n for n, *_ in triangle_graph.neighbors("A")}
        assert neighbors == {"B", "C"}

    def test_idempotent_add_vertex(self):
        g = Graph()
        v = Vertex("X", "X")
        g.add_vertex(v)
        g.add_vertex(v)
        assert g.vertex_count() == 1

    def test_missing_origin_raises(self):
        g = Graph()
        g.add_vertex(Vertex("A", "A"))
        with pytest.raises(KeyError):
            g.add_arc(Arc("Z", "A", 10))

    def test_missing_dest_raises(self):
        g = Graph()
        g.add_vertex(Vertex("A", "A"))
        with pytest.raises(KeyError):
            g.add_arc(Arc("A", "Z", 10))

    def test_negative_weight_raises(self):
        g = Graph()
        for v in ["A", "B"]:
            g.add_vertex(Vertex(v, v))
        with pytest.raises(ValueError):
            g.add_arc(Arc("A", "B", -1))

    def test_contains_operator(self, triangle_graph):
        assert "A" in triangle_graph
        assert "Z" not in triangle_graph


# ══════════════════════════════════════════════════════════════════════
#  Testes do Dijkstra
# ══════════════════════════════════════════════════════════════════════

class TestDijkstra:
    def test_prefers_indirect_cheaper_path(self, triangle_graph):
        """A→C via B (custo 15) deve vencer a aresta direta A→C (custo 20)."""
        r = shortest_path(triangle_graph, "A", "C")
        assert r.reachable
        assert r.total_seconds == 15.0
        assert r.stop_ids == ["A", "B", "C"]

    def test_same_origin_and_dest(self, triangle_graph):
        r = shortest_path(triangle_graph, "A", "A")
        assert r.total_seconds == 0.0
        assert r.stop_ids == ["A"]

    def test_chain_total_cost(self, chain_graph):
        r = shortest_path(chain_graph, "1", "4")
        assert r.reachable
        assert r.total_seconds == 360.0

    def test_chain_path_order(self, chain_graph):
        r = shortest_path(chain_graph, "1", "4")
        assert r.stop_ids == ["1", "2", "3", "4"]

    def test_unreachable_returns_not_reachable(self, disconnected_graph):
        r = shortest_path(disconnected_graph, "X", "P")
        assert not r.reachable
        assert r.stop_ids == []

    def test_invalid_origin_raises(self, triangle_graph):
        with pytest.raises(KeyError):
            dijkstra(triangle_graph, "INEXISTENTE")

    def test_dijkstra_all_targets(self, chain_graph):
        results = dijkstra(chain_graph, "1")
        assert "1" in results
        assert "4" in results
        assert results["4"].total_seconds == 360.0

    def test_early_stop_on_destination(self, chain_graph):
        """Dijkstra com destination_id deve terminar cedo e ainda dar resultado correto."""
        results = dijkstra(chain_graph, "1", destination_id="3")
        assert "3" in results
        assert results["3"].total_seconds == 180.0  # 60+120

    def test_formatted_time_seconds_only(self):
        g = Graph()
        for v in ["A", "B"]:
            g.add_vertex(Vertex(v, v))
        g.add_arc(Arc("A", "B", 45))
        r = shortest_path(g, "A", "B")
        assert r.formatted_time == "45s"

    def test_formatted_time_minutes(self):
        g = Graph()
        for v in ["A", "B"]:
            g.add_vertex(Vertex(v, v))
        g.add_arc(Arc("A", "B", 600))
        r = shortest_path(g, "A", "B")
        assert r.formatted_time == "10min"

    def test_formatted_time_hours(self):
        g = Graph()
        for v in ["A", "B"]:
            g.add_vertex(Vertex(v, v))
        g.add_arc(Arc("A", "B", 3660))
        r = shortest_path(g, "A", "B")
        assert r.formatted_time == "1h 01min"

    def test_n_transfers_no_change(self, chain_graph):
        """Viagem toda na mesma linha = 0 baldeações."""
        r = shortest_path(chain_graph, "1", "4")
        # Todos os steps têm route_label vazio → 0 trocas
        assert r.n_transfers == 0


# ══════════════════════════════════════════════════════════════════════
#  Testes de Integração com dados GTFS reais
# ══════════════════════════════════════════════════════════════════════

class TestIntegration:
    @pytest.fixture(autouse=True)
    def network(self):
        from src.transit.network import TransitNetwork
        gtfs_dir = Path(__file__).parents[1] / "data" / "gtfs"
        self.net = TransitNetwork(gtfs_dir)

    def test_network_loads(self):
        assert self.net.graph.vertex_count() > 0
        assert self.net.graph.arc_count() > 0

    def test_fga_stop_exists(self):
        from src.transit.network import FGA_STOP_ID
        assert self.net.graph.has_vertex(FGA_STOP_ID)

    def test_route_terminal_to_fga(self):
        from src.transit.network import FGA_STOP_ID, TERMINAL_GAMA_STOP_ID
        r = self.net.find_route(TERMINAL_GAMA_STOP_ID, FGA_STOP_ID)
        assert r.reachable
        assert r.total_seconds > 0
        assert r.stop_ids[-1] == FGA_STOP_ID

    def test_rodoviaria_to_fga_reachable(self):
        r = self.net.find_route("S025", "S004")
        assert r.reachable

    def test_closer_origin_is_faster(self):
        """Terminal Gama (próximo) deve ser mais rápido que Rodoviária (distante)."""
        r_local  = self.net.find_route("S001", "S004")
        r_remote = self.net.find_route("S025", "S004")
        assert r_local.total_seconds < r_remote.total_seconds

    def test_search_stops(self):
        found = self.net.search_stops("gama")
        assert len(found) > 0

    def test_search_fga(self):
        found = self.net.search_stops("FGA")
        assert any("FGA" in v.label for v in found)

    def test_route_to_itself_zero(self):
        r = self.net.find_route("S004", "S004")
        assert r.total_seconds == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
