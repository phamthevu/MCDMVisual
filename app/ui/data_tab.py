from __future__ import annotations
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QGroupBox, QFormLayout, QLabel,
    QAbstractItemView, QComboBox, QMessageBox, QHeaderView, QInputDialog)
from PySide6.QtCore import Qt
from app.core.io_excel import load_total_influence_matrix, load_ranking_results
from app.core.dematel import compute_dematel_from_total
from app.core.visual_scale import min_mid_max, compute_edges
from app.core.cooccurrence import compute_code_cooccurrence


class DataTab(QWidget):
    """Input and validated results for DEMATEL T matrices or final rankings."""
    def __init__(self, state):
        super().__init__()
        self.state = state
        root = QVBoxLayout(self)
        bar = QHBoxLayout()
        bar.addWidget(QLabel("Analysis"))
        self.cb_mode = QComboBox()
        self.cb_mode.addItems(["DEMATEL INRM (total influence T)", "Ranking results (TOPSIS / other methods)",
                               "Regression results", "CB-SEM results", "PLS-SEM results",
                               "Code co-occurrence (excerpt coding)"])
        self.cb_mode.currentIndexChanged.connect(self.on_mode_changed)
        bar.addWidget(self.cb_mode)
        self.btn_load = QPushButton("Import Excel / CSV")
        self.btn_load.clicked.connect(self.on_load)
        bar.addWidget(self.btn_load)
        bar.addStretch(1)
        root.addLayout(bar)

        body = QHBoxLayout()
        root.addLayout(body, 1)
        input_box = QGroupBox("Input & preview")
        input_layout = QVBoxLayout(input_box)
        self.lbl_input = QLabel("DEMATEL input: final total influence matrix T (numeric values).")
        input_layout.addWidget(self.lbl_input)
        self.tbl_input = QTableWidget()
        self.tbl_input.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.tbl_input.itemChanged.connect(self.on_cell_changed)
        input_layout.addWidget(self.tbl_input)
        body.addWidget(input_box, 3)

        side = QVBoxLayout()
        body.addLayout(side, 2)
        result_box = QGroupBox("Calculated / imported results")
        result_layout = QVBoxLayout(result_box)
        self.tbl_res = QTableWidget()
        self.tbl_res.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tbl_res.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        result_layout.addWidget(self.tbl_res)
        side.addWidget(result_box, 3)

        vis_box = QGroupBox("DEMATEL scale")
        form = QFormLayout(vis_box)
        self.lbl_min, self.lbl_mid, self.lbl_max, self.lbl_edges = [QLabel("—") for _ in range(4)]
        from PySide6.QtWidgets import QSpinBox
        self.spin_bins = QSpinBox()
        self.spin_bins.setRange(2, 20)
        self.spin_bins.setValue(self.state.data.vis.bins)
        self.spin_bins.valueChanged.connect(self.on_bins_changed)
        form.addRow("Minimum T", self.lbl_min)
        form.addRow("Midpoint", self.lbl_mid)
        form.addRow("Maximum T", self.lbl_max)
        form.addRow("Influence bins", self.spin_bins)
        form.addRow("Bin edges", self.lbl_edges)
        side.addWidget(vis_box, 1)
        self.scale_box = vis_box
        self._busy = False

    def on_mode_changed(self, index):
        self.state.data.method = ["DEMATEL", "Ranking", "Regression", "CB-SEM", "PLS-SEM", "Co-occurrence"][index]
        is_dematel = index == 0
        prompts = ["DEMATEL input: final total influence matrix T (numeric values).",
                   "Ranking input: alternative in column 1; one or more final numeric result columns after it.",
                   "Regression: import a sheet with observed X/Y columns; predicted/residual columns are optional.",
                   "CB-SEM: import path estimates; use Source, Target, Estimate columns. Fit indices may be in the same sheet.",
                   "PLS-SEM: import path estimates; use Source, Target, Estimate columns. Loadings/validity metrics can be in the sheet.",
                   "Co-occurrence: import Excerpt ID plus 0/1 code columns, or a long Excerpt ID / Code assignment list."]
        self.lbl_input.setText(prompts[index])
        self.scale_box.setEnabled(is_dematel)
        if self.state.data.method not in ("Regression", "CB-SEM", "PLS-SEM"):
            self.state.data.quant_type = ""
        self._render_input()
        self._recompute()
        self.state.emit_changed()

    def on_load(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open analysis results", "",
                                               "Excel / CSV (*.xlsx *.xls *.csv)")
        if not path:
            return
        try:
            sheet = 0
            if not path.lower().endswith(".csv"):
                with pd.ExcelFile(path) as workbook:
                    names = workbook.sheet_names
                if len(names) > 1:
                    selected, ok = QInputDialog.getItem(self, "Select worksheet", "Worksheet", names, 0, False)
                    if not ok: return
                    sheet = selected
            if self.state.data.method == "DEMATEL":
                labels, matrix = load_total_influence_matrix(path, sheet=sheet)
                self.state.data.labels = labels
                self.state.data.matrix = matrix
            elif self.state.data.method == "Ranking":
                names, columns, values = load_ranking_results(path, sheet=sheet)
                self.state.data.ranking_labels = names
                self.state.data.ranking_columns = columns
                self.state.data.ranking_values = values
            elif self.state.data.method == "Co-occurrence":
                frame=(pd.read_csv(path) if path.lower().endswith(".csv") else
                       pd.read_excel(path,sheet_name=sheet))
                labels,matrix,excerpt_count=compute_code_cooccurrence(frame)
                self.state.data.cooccurrence_frame=frame
                self.state.data.cooccurrence_labels=labels
                self.state.data.cooccurrence_matrix=matrix
                self.state.data.cooccurrence_excerpt_count=excerpt_count
            else:
                if path.lower().endswith(".csv"):
                    self.state.data.quant_frame=pd.read_csv(path)
                else:
                    with pd.ExcelFile(path) as workbook:
                        self.state.data.quant_frame=pd.read_excel(workbook,sheet_name=sheet)
                self.state.data.quant_type = self.state.data.method
            self._render_input()
            self._recompute()
            self.state.emit_changed()
        except Exception as exc:
            QMessageBox.critical(self, "Could not import results", str(exc))

    def _render_input(self):
        d = self.state.data
        self._busy = True
        self.tbl_input.blockSignals(True)
        if d.method == "DEMATEL" and d.matrix is not None:
            a = np.asarray(d.matrix, dtype=float)
            self.tbl_input.setRowCount(a.shape[0]); self.tbl_input.setColumnCount(a.shape[1])
            self.tbl_input.setHorizontalHeaderLabels(d.labels)
            self.tbl_input.setVerticalHeaderLabels(d.labels)
            for r in range(a.shape[0]):
                for c in range(a.shape[1]):
                    item = QTableWidgetItem(f"{a[r,c]:.7g}"); item.setTextAlignment(Qt.AlignCenter)
                    self.tbl_input.setItem(r, c, item)
        elif d.method == "Ranking" and d.ranking_values is not None:
            a = np.asarray(d.ranking_values, dtype=float)
            self.tbl_input.setRowCount(a.shape[0]); self.tbl_input.setColumnCount(a.shape[1])
            self.tbl_input.setHorizontalHeaderLabels(d.ranking_columns)
            self.tbl_input.setVerticalHeaderLabels(d.ranking_labels)
            for r in range(a.shape[0]):
                for c in range(a.shape[1]):
                    item = QTableWidgetItem(f"{a[r,c]:.7g}"); item.setTextAlignment(Qt.AlignCenter)
                    self.tbl_input.setItem(r, c, item)
        elif d.method == "Co-occurrence" and d.cooccurrence_frame is not None:
            frame=d.cooccurrence_frame
            self.tbl_input.setRowCount(len(frame));self.tbl_input.setColumnCount(len(frame.columns))
            self.tbl_input.setHorizontalHeaderLabels([str(c) for c in frame.columns])
            self.tbl_input.setVerticalHeaderLabels([str(i+1) for i in range(len(frame))])
            for r in range(len(frame)):
                for c in range(len(frame.columns)):
                    value=frame.iat[r,c]
                    self.tbl_input.setItem(r,c,QTableWidgetItem("" if pd.isna(value) else str(value)))
            self.tbl_input.setEditTriggers(QAbstractItemView.NoEditTriggers)
        elif d.method in ("Regression", "CB-SEM", "PLS-SEM") and d.quant_frame is not None:
            frame=d.quant_frame
            self.tbl_input.setRowCount(len(frame)); self.tbl_input.setColumnCount(len(frame.columns))
            self.tbl_input.setHorizontalHeaderLabels([str(c) for c in frame.columns])
            self.tbl_input.setVerticalHeaderLabels([str(i+1) for i in range(len(frame))])
            for r in range(len(frame)):
                for c in range(len(frame.columns)):
                    value=frame.iat[r,c]
                    text="" if pd.isna(value) else str(value)
                    self.tbl_input.setItem(r,c,QTableWidgetItem(text))
            self.tbl_input.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            self.tbl_input.clear(); self.tbl_input.setRowCount(0); self.tbl_input.setColumnCount(0)
        self.tbl_input.blockSignals(False)
        if d.method not in ("Regression", "CB-SEM", "PLS-SEM", "Co-occurrence"):
            self.tbl_input.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self._busy = False

    def on_cell_changed(self, item):
        if self._busy: return
        d = self.state.data
        try:
            value = float(item.text())
            if not np.isfinite(value): raise ValueError()
            if d.method == "DEMATEL":
                if value < 0: raise ValueError("DEMATEL influence values must be non-negative.")
                d.matrix[item.row(), item.column()] = value
            else:
                d.ranking_values[item.row(), item.column()] = value
            self._recompute(); self.state.emit_changed()
        except Exception as exc:
            QMessageBox.warning(self, "Invalid value", str(exc) or "Enter a finite numeric value.")
            self._render_input()

    def on_bins_changed(self, value):
        self.state.data.vis.bins = int(value)
        self._update_scale(); self.state.emit_changed()

    def _recompute(self):
        d = self.state.data
        if d.method == "DEMATEL" and d.matrix is not None:
            try:
                d.dematel_table = compute_dematel_from_total(d.matrix, d.labels)
                self._render_dematel(d.dematel_table)
                self._update_scale()
            except Exception as exc:
                QMessageBox.warning(self, "Invalid DEMATEL matrix", str(exc))
        elif d.method == "Ranking" and d.ranking_values is not None:
            self._render_ranking()
        elif d.method == "Co-occurrence" and d.cooccurrence_matrix is not None:
            self._render_cooccurrence()
        elif d.method == "Ranking":
            self.tbl_res.clear(); self.tbl_res.setRowCount(0); self.tbl_res.setColumnCount(0)
        else:
            self.tbl_res.clear(); self.tbl_res.setRowCount(0); self.tbl_res.setColumnCount(0)

    def _render_dematel(self, table):
        headers = ["Factor", "R", "C", "R+C", "R-C", "Weight", "Rank", "Group"]
        self.tbl_res.setColumnCount(len(headers)); self.tbl_res.setHorizontalHeaderLabels(headers)
        self.tbl_res.setRowCount(len(table))
        for r, row in enumerate(table):
            for c, key in enumerate(headers):
                v = row[key]; text = f"{v:.6g}" if isinstance(v, float) else str(v)
                self.tbl_res.setItem(r, c, QTableWidgetItem(text))

    def _render_ranking(self):
        d = self.state.data
        headers = ["Alternative", *d.ranking_columns]
        self.tbl_res.setColumnCount(len(headers)); self.tbl_res.setHorizontalHeaderLabels(headers)
        self.tbl_res.setRowCount(len(d.ranking_labels))
        for r, name in enumerate(d.ranking_labels):
            self.tbl_res.setItem(r, 0, QTableWidgetItem(name))
            for c, val in enumerate(d.ranking_values[r]):
                self.tbl_res.setItem(r, c+1, QTableWidgetItem(f"{val:.7g}"))

    def _render_cooccurrence(self):
        d=self.state.data;labels=d.cooccurrence_labels;matrix=np.asarray(d.cooccurrence_matrix,float)
        self.tbl_res.setColumnCount(len(labels)+1);self.tbl_res.setRowCount(len(labels))
        self.tbl_res.setHorizontalHeaderLabels(["Code",*labels])
        self.tbl_res.setVerticalHeaderLabels([str(i+1) for i in range(len(labels))])
        for row,label in enumerate(labels):
            self.tbl_res.setItem(row,0,QTableWidgetItem(label))
            for col in range(len(labels)):
                self.tbl_res.setItem(row,col+1,QTableWidgetItem(f"{matrix[row,col]:.0f}"))

    def _update_scale(self):
        a = self.state.data.matrix
        if a is None: return
        vmin, vmid, vmax = min_mid_max(a)
        edges = compute_edges(vmin, vmax, self.state.data.vis.bins)
        self.state.data.vis.edges = edges
        self.lbl_min.setText(f"{vmin:.6g}"); self.lbl_mid.setText(f"{vmid:.6g}"); self.lbl_max.setText(f"{vmax:.6g}")
        self.lbl_edges.setText(" | ".join(f"{e:.4g}" for e in edges))
