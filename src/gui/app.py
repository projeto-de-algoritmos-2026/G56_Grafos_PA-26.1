"""
Interface gráfica do DF Transit Navigator.

Janela principal com seleção de paradas e visualização da rota no mapa.
Requer: tkintermapview  (pip install tkintermapview)
"""

from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from typing import List, Optional

try:
    import tkintermapview
except ImportError:
    raise SystemExit(
        "Dependência não encontrada: tkintermapview\n"
        "Instale com:  pip install tkintermapview"
    )

from src.graph.dijkstra import PathResult
from src.graph.graph import Vertex
from src.transit.formatter import format_itinerary
from src.transit.network import TransitNetwork

# Paleta de cores para os trechos (uma cor por linha de ônibus)
_LEG_COLORS = [
    "#1565C0",  # azul
    "#B71C1C",  # vermelho
    "#1B5E20",  # verde
    "#E65100",  # laranja
    "#4A148C",  # roxo
    "#006064",  # ciano
    "#3E2723",  # marrom
    "#880E4F",  # rosa
]
_WALK_COLOR   = "#78909C"   # cinza para caminhada
_STOP_COLOR   = "#546E7A"   # marcador de parada inativa
_ORIGIN_COLOR = "#2E7D32"   # verde para origem
_DEST_COLOR   = "#C62828"   # vermelho para destino
_XFER_COLOR   = "#F57F17"   # laranja para baldeação


# ──────────────────────────────────────────────────────────────────────────── #
#  Sidebar                                                                     #
# ──────────────────────────────────────────────────────────────────────────── #

class _Sidebar(tk.Frame):
    """Painel lateral: busca de paradas, botão e resultado da rota."""

    def __init__(self, parent: tk.Widget, app: "TransitApp") -> None:
        super().__init__(parent, bg="#1E272C", width=340)
        self.pack_propagate(False)
        self._app = app
        self._build()

    # ── Construção ── #

    def _build(self) -> None:
        # Título
        tk.Label(self, text="DF Transit",
                 bg="#1E272C", fg="#ECEFF1",
                 font=("Arial", 20, "bold")).pack(
            pady=(18, 0), padx=18, anchor="w")
        tk.Label(self, text="Dijkstra + GTFS SEMOB-DF",
                 bg="#1E272C", fg="#607D8B",
                 font=("Arial", 9)).pack(padx=18, anchor="w")

        self._sep()

        # Seletores de parada
        (self._origin_var,
         self._origin_lb,
         self._origin_results) = self._stop_block(
            "Origem", self._on_origin_key, self._on_origin_pick)

        (self._dest_var,
         self._dest_lb,
         self._dest_results) = self._stop_block(
            "Destino", self._on_dest_key, self._on_dest_pick)

        # Botão calcular
        self.calc_btn = tk.Button(
            self, text="Calcular Rota",
            command=self._app._calculate,
            bg="#1565C0", fg="white",
            font=("Arial", 11, "bold"),
            relief="flat", pady=9,
            activebackground="#0D47A1",
            activeforeground="white",
            cursor="hand2",
            state="disabled",
        )
        self.calc_btn.pack(padx=18, pady=14, fill="x")

        self._sep()

        # Status
        self.status_var = tk.StringVar(value="Carregando rede GTFS...")
        tk.Label(self, textvariable=self.status_var,
                 bg="#1E272C", fg="#607D8B",
                 font=("Arial", 8), wraplength=300,
                 justify="left").pack(padx=18, pady=(4, 2), anchor="w")

        # Legenda de cores
        self._legend_frame = tk.Frame(self, bg="#1E272C")
        self._legend_frame.pack(padx=18, pady=(0, 4), fill="x")

        # Texto da rota
        result_wrap = tk.Frame(self, bg="#1E272C")
        result_wrap.pack(padx=10, pady=(4, 8), fill="both", expand=True)

        self.result_txt = tk.Text(
            result_wrap,
            bg="#141D21", fg="#CFD8DC",
            font=("Courier New", 8),
            relief="flat", wrap="word",
            state="disabled",
            insertbackground="white",
            highlightthickness=0,
        )
        sb = tk.Scrollbar(result_wrap, command=self.result_txt.yview,
                          bg="#37474F", troughcolor="#1E272C",
                          relief="flat")
        self.result_txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.result_txt.pack(side="left", fill="both", expand=True)

    def _sep(self) -> None:
        tk.Frame(self, bg="#37474F", height=1).pack(
            fill="x", padx=16, pady=8)

    def _stop_block(
        self,
        label: str,
        on_key,
        on_pick,
    ) -> tuple:
        """Cria bloco de busca de parada; retorna (StringVar, Listbox, list)."""
        tk.Label(self, text=label,
                 bg="#1E272C", fg="#90A4AE",
                 font=("Arial", 9, "bold")).pack(
            padx=18, pady=(8, 2), anchor="w")

        var = tk.StringVar()
        entry = tk.Entry(
            self, textvariable=var,
            font=("Arial", 10),
            bg="#263238", fg="#ECEFF1",
            insertbackground="#ECEFF1",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#455A64",
            highlightcolor="#1565C0",
        )
        entry.pack(padx=18, ipady=5, fill="x")
        entry.bind("<KeyRelease>", on_key)

        results: List[Vertex] = []
        lb = tk.Listbox(
            self, height=4,
            bg="#263238", fg="#CFD8DC",
            selectbackground="#1565C0",
            selectforeground="white",
            relief="flat", bd=0,
            highlightthickness=0,
            font=("Arial", 8),
        )
        lb.pack(padx=18, pady=(1, 0), fill="x")
        lb.bind("<<ListboxSelect>>", on_pick)

        return var, lb, results

    # ── Eventos de busca ── #

    def _on_origin_key(self, _=None) -> None:
        self._search(self._origin_var.get(),
                     self._origin_lb, self._origin_results)

    def _on_dest_key(self, _=None) -> None:
        self._search(self._dest_var.get(),
                     self._dest_lb, self._dest_results)

    def _search(self, q: str, lb: tk.Listbox, results: list) -> None:
        lb.delete(0, "end")
        results.clear()
        if not self._app.network or len(q) < 2:
            return
        found = self._app.network.search_stops(q)
        results.extend(found[:10])
        for v in results:
            lb.insert("end", v.label)

    def _on_origin_pick(self, _=None) -> None:
        sel = self._origin_lb.curselection()
        if sel and self._origin_results:
            v = self._origin_results[sel[0]]
            self._app._origin = v
            self._origin_var.set(v.label)

    def _on_dest_pick(self, _=None) -> None:
        sel = self._dest_lb.curselection()
        if sel and self._dest_results:
            v = self._dest_results[sel[0]]
            self._app._dest = v
            self._dest_var.set(v.label)

    # ── API pública ── #

    def show_result(self, text: str) -> None:
        self.result_txt.configure(state="normal")
        self.result_txt.delete("1.0", "end")
        self.result_txt.insert("end", text)
        self.result_txt.configure(state="disabled")

    def set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def set_ready(self, msg: str) -> None:
        self.set_status(msg)
        self.calc_btn.configure(state="normal", text="Calcular Rota")

    def set_loading(self, msg: str) -> None:
        self.set_status(msg)
        self.calc_btn.configure(state="disabled", text="Carregando...")

    def show_legend(self, color_map: dict[str, str]) -> None:
        """Exibe legenda de cores das linhas abaixo do status."""
        for w in self._legend_frame.winfo_children():
            w.destroy()
        for label, color in color_map.items():
            row = tk.Frame(self._legend_frame, bg="#1E272C")
            row.pack(anchor="w", fill="x")
            tk.Frame(row, bg=color, width=14, height=8).pack(
                side="left", padx=(0, 5))
            name = label.split("|")[0].strip() if "|" in label else label
            tk.Label(row, text=name,
                     bg="#1E272C", fg="#90A4AE",
                     font=("Arial", 7)).pack(side="left")


# ──────────────────────────────────────────────────────────────────────────── #
#  Aplicação principal                                                         #
# ──────────────────────────────────────────────────────────────────────────── #

class TransitApp:
    """Janela principal do DF Transit Navigator."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("DF Transit Navigator")
        self.root.geometry("1300x740")
        self.root.configure(bg="#263238")

        self.network: Optional[TransitNetwork] = None
        self._origin: Optional[Vertex] = None
        self._dest:   Optional[Vertex] = None

        self._stop_markers:  list = []
        self._route_paths:   list = []
        self._route_markers: list = []

        self._build_ui()
        self._load_network()

    # ── UI ── #

    def _build_ui(self) -> None:
        self._sidebar = _Sidebar(self.root, self)
        self._sidebar.pack(side="left", fill="y")

        map_frame = tk.Frame(self.root, bg="#263238")
        map_frame.pack(side="right", fill="both", expand=True)

        self.map_widget = tkintermapview.TkinterMapView(
            map_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(-15.83, -48.00)
        self.map_widget.set_zoom(11)

    # ── Carregamento da rede ── #

    def _load_network(self) -> None:
        def _worker() -> None:
            data_dir = Path(__file__).resolve().parents[2] / "data" / "gtfs"
            net = TransitNetwork(data_dir)
            self.root.after(0, lambda: self._on_loaded(net))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_loaded(self, net: TransitNetwork) -> None:
        self.network = net
        s = net.stats
        self._sidebar.set_ready(
            f"Rede: {s['paradas']} paradas  |  "
            f"{s['arcos']} arcos  |  {s['linhas']} linhas"
        )
        self._draw_all_stops()

    # ── Marcadores de todas as paradas ── #

    def _draw_all_stops(self) -> None:
        for v in self.network.all_stops():
            if v.lat == 0.0 and v.lon == 0.0:
                continue
            m = self.map_widget.set_marker(
                v.lat, v.lon,
                text="",
                marker_color_circle=_STOP_COLOR,
                marker_color_outside=_STOP_COLOR,
            )
            self._stop_markers.append(m)

    # ── Cálculo da rota ── #

    def _calculate(self) -> None:
        if not self.network:
            return
        if not self._origin or not self._dest:
            self._sidebar.set_status(
                "Selecione a origem e o destino antes de calcular.")
            return

        result = self.network.find_route(
            self._origin.vertex_id, self._dest.vertex_id)

        self._sidebar.show_result(
            format_itinerary(result, self.network.graph))
        self._draw_route(result)

        if result.reachable:
            self._sidebar.set_status(
                f"Rota encontrada:  {result.formatted_time}"
                f"  |  {result.n_transfers} baldeacao(s)")
        else:
            self._sidebar.set_status("Nenhuma rota encontrada.")

    # ── Desenho da rota no mapa ── #

    def _clear_route(self) -> None:
        for p in self._route_paths:
            p.delete()
        self._route_paths.clear()
        for m in self._route_markers:
            m.delete()
        self._route_markers.clear()

    def _draw_route(self, result: PathResult) -> None:
        self._clear_route()
        if not result.reachable or not result.steps:
            return

        steps = result.steps
        graph = self.network.graph

        # ── Agrupar passos em segmentos por linha ── #
        # steps[i] = (stop_id, route_label_usado_para_chegar_aqui)
        # steps[0] tem route_label == "" (ponto de origem)
        segments: list[tuple[str, list[tuple[float, float]]]] = []
        seg_coords: list[tuple[float, float]] = []
        seg_label: Optional[str] = None

        for i, (stop_id, route_label) in enumerate(steps):
            v = graph.get_vertex(stop_id)
            if not v or (v.lat == 0.0 and v.lon == 0.0):
                continue
            coord = (v.lat, v.lon)

            if i == 0:
                # Origem: só grava coordenada, aguarda próximo passo p/ saber a linha
                seg_coords = [coord]
                continue

            if route_label != seg_label:
                # Mudança de linha: salva segmento anterior
                if seg_label is not None and len(seg_coords) >= 2:
                    segments.append((seg_label, seg_coords[:]))
                seg_coords = seg_coords[-1:] if seg_coords else []
                seg_label = route_label

            seg_coords.append(coord)

        if seg_label is not None and len(seg_coords) >= 2:
            segments.append((seg_label, seg_coords))

        # ── Desenhar segmentos com cores por linha ── #
        color_map: dict[str, str] = {}
        color_idx = 0

        for label, coords in segments:
            is_walk = "A pé" in (label or "")
            if is_walk:
                color = _WALK_COLOR
            else:
                if label not in color_map:
                    color_map[label] = _LEG_COLORS[color_idx % len(_LEG_COLORS)]
                    color_idx += 1
                color = color_map[label]

            p = self.map_widget.set_path(coords, color=color, width=5)
            self._route_paths.append(p)

        # ── Marcadores de baldeação ── #
        prev_label: Optional[str] = None
        for stop_id, route_label in steps[1:-1]:
            if route_label and prev_label and route_label != prev_label:
                v = graph.get_vertex(stop_id)
                if v and not (v.lat == 0.0 and v.lon == 0.0):
                    m = self.map_widget.set_marker(
                        v.lat, v.lon,
                        text=v.label,
                        marker_color_circle=_XFER_COLOR,
                        marker_color_outside=_XFER_COLOR,
                    )
                    self._route_markers.append(m)
            if route_label:
                prev_label = route_label

        # ── Marcadores de origem e destino ── #
        origin_v = graph.get_vertex(result.origin_id)
        if origin_v:
            m = self.map_widget.set_marker(
                origin_v.lat, origin_v.lon,
                text=f"Origem: {origin_v.label}",
                marker_color_circle=_ORIGIN_COLOR,
                marker_color_outside=_ORIGIN_COLOR,
            )
            self._route_markers.append(m)

        dest_v = graph.get_vertex(result.dest_id)
        if dest_v:
            m = self.map_widget.set_marker(
                dest_v.lat, dest_v.lon,
                text=f"Destino: {dest_v.label}",
                marker_color_circle=_DEST_COLOR,
                marker_color_outside=_DEST_COLOR,
            )
            self._route_markers.append(m)

        # ── Legenda de linhas ── #
        self._sidebar.show_legend(color_map)

        # ── Ajustar zoom e centro do mapa ── #
        all_coords = [c for _, cs in segments for c in cs]
        if all_coords:
            lats = [c[0] for c in all_coords]
            lons = [c[1] for c in all_coords]
            center_lat = (max(lats) + min(lats)) / 2
            center_lon = (max(lons) + min(lons)) / 2
            extent = max(max(lats) - min(lats), max(lons) - min(lons))
            zoom = (14 if extent < 0.04
                    else 13 if extent < 0.10
                    else 12 if extent < 0.20
                    else 11 if extent < 0.45
                    else 10)
            self.map_widget.set_position(center_lat, center_lon)
            self.map_widget.set_zoom(zoom)

    def run(self) -> None:
        self.root.mainloop()


# ──────────────────────────────────────────────────────────────────────────── #
#  Ponto de entrada                                                            #
# ──────────────────────────────────────────────────────────────────────────── #

def run_gui() -> None:
    TransitApp().run()
