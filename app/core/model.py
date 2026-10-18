from dataclasses import dataclass, field
import numpy as np
from PySide6.QtCore import QObject, Signal

@dataclass
class VisualParams:
    bins: int = 2
    edges: list[float] = field(default_factory=list)  # ALWAYS computed in Data tab

@dataclass
class AppData:
    method: str = "DEMATEL"
    quant_type: str = ""
    quant_frame: object | None = None
    matrix: np.ndarray | None = None
    labels: list[str] = field(default_factory=list)
    ranking_labels: list[str] = field(default_factory=list)
    ranking_columns: list[str] = field(default_factory=list)
    ranking_values: np.ndarray | None = None
    cooccurrence_frame: object | None = None
    cooccurrence_labels: list[str] = field(default_factory=list)
    cooccurrence_matrix: np.ndarray | None = None
    cooccurrence_excerpt_count: int = 0
    dematel_table: list[dict] = field(default_factory=list)
    label_positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    vis: VisualParams = field(default_factory=VisualParams)

class AppState(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.data = AppData()

    def emit_changed(self):
        self.changed.emit()
