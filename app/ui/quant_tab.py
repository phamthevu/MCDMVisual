from __future__ import annotations

import numpy as np
import pandas as pd
import pyqtgraph as pg
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QColor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox, QPushButton,
    QLabel, QFileDialog, QMessageBox, QComboBox, QTabWidget, QToolTip, QColorDialog,
)
from app.core.quant_charts import regression_fit, finite_coefficients, sem_path_layout
from app.ui.exporting import export_plot_widget


class QuantPage(QWidget):
    def __init__(self,state,kind):
        super().__init__();self.state=state;self.kind=kind
        root=QHBoxLayout(self);panel=QGroupBox(f"{kind} chart inputs");controls=QVBoxLayout(panel)
        self.chart_type=QComboBox()
        if kind=="Regression":self.chart_type.addItems(["Observed vs fitted", "Residuals vs fitted", "Coefficient estimates"])
        else:self.chart_type.addItems(["SEM path diagram", "Path coefficient bars", "Measurement / validity metrics"])
        controls.addWidget(QLabel("Chart"));controls.addWidget(self.chart_type)
        self.primary_color=QColor("#2573a4");self.secondary_color=QColor("#dc4646")
        color_row=QHBoxLayout();self.btn_primary_color=QPushButton("Primary");self.btn_secondary_color=QPushButton("Secondary")
        color_row.addWidget(self.btn_primary_color);color_row.addWidget(self.btn_secondary_color);controls.addLayout(color_row)
        self._set_color_button(self.btn_primary_color,self.primary_color);self._set_color_button(self.btn_secondary_color,self.secondary_color)
        self.btn_primary_color.clicked.connect(lambda:self._choose_color("primary"));self.btn_secondary_color.clicked.connect(lambda:self._choose_color("secondary"))
        self.xcol=QComboBox();self.ycol=QComboBox();self.labelcol=QComboBox();self.targetcol=QComboBox()
        form=QFormLayout();form.addRow("Predictor / source",self.xcol);form.addRow("Outcome / estimate",self.ycol);form.addRow("Label / construct",self.labelcol);form.addRow("Target (SEM)",self.targetcol);controls.addLayout(form)
        self.status=QLabel("Import data in the Data tab to activate this chart.");self.status.setWordWrap(True);controls.addWidget(self.status)
        export=QPushButton("Export PNG / SVG…");export.clicked.connect(self.export);controls.addWidget(export);controls.addStretch(1)
        root.addWidget(panel,0);self.plot=pg.PlotWidget(background="w");self.plot.showGrid(x=True,y=True,alpha=.25);root.addWidget(self.plot,1)
        self._hover_nodes=[];self._hover_edges=[]
        self.plot.scene().sigMouseMoved.connect(self._on_plot_mouse_moved)
        self.chart_type.currentIndexChanged.connect(self.refresh);self.xcol.currentIndexChanged.connect(self.refresh);self.ycol.currentIndexChanged.connect(self.refresh);self.labelcol.currentIndexChanged.connect(self.refresh);self.targetcol.currentIndexChanged.connect(self.refresh)

    @staticmethod
    def _set_color_button(button,color):
        color=QColor(color);button.setText(color.name());button.setStyleSheet(f"background:{color.name()};color:{'#fff' if color.lightness()<130 else '#172033'}")

    def _choose_color(self,which):
        attr="primary_color" if which=="primary" else "secondary_color"
        color=QColorDialog.getColor(getattr(self,attr),self,f"Choose {which} chart color")
        if not color.isValid():return
        setattr(self,attr,color);self._set_color_button(self.btn_primary_color if which=="primary" else self.btn_secondary_color,color)
        self.refresh()

    def refresh(self):
        d=self.state.data; frame=d.quant_frame
        allowed=d.method==self.kind and d.quant_type==self.kind and frame is not None and not frame.empty
        for widget in (self.chart_type,self.xcol,self.ycol,self.labelcol,self.targetcol):widget.setEnabled(allowed)
        if not allowed:
            self.status.setText(f"Choose {self.kind} results in the Data tab and import a worksheet.");self.plot.clear();return
        cols=[str(c) for c in frame.columns]
        for cb in (self.xcol,self.ycol,self.labelcol,self.targetcol):
            old=cb.currentText();cb.blockSignals(True)
            if [cb.itemText(i) for i in range(cb.count())]!=cols:
                cb.clear();cb.addItems(cols)
                lower=[c.lower() for c in cols]
                guesses=(["x","predictor","source","from"] if cb is self.xcol else
                         ["y","estimate","coefficient","beta","value"] if cb is self.ycol else
                         ["label","path","construct","term","variable","source"] if cb is self.labelcol else
                         ["target","to","outcome"])
                match=next((i for i,c in enumerate(lower) if any(g in c for g in guesses)),0)
                cb.setCurrentIndex(match)
            elif old in cols:cb.setCurrentText(old)
            cb.blockSignals(False)
        self._draw(frame)

    def _draw(self,frame):
        self.plot.clear();self._hover_nodes=[];self._hover_edges=[];typ=self.chart_type.currentIndex()
        try:
            if self.kind=="Regression":
                x=pd.to_numeric(frame[self.xcol.currentText()],errors="coerce").to_numpy(float)
                y=pd.to_numeric(frame[self.ycol.currentText()],errors="coerce").to_numpy(float)
                data=regression_fit(x,y)
                if typ==0:
                    self.plot.addLegend()
                    self.plot.addItem(pg.ScatterPlotItem(x=data["x"],y=data["y"],size=8,brush=(*self.primary_color.getRgb()[:3],220),pen=pg.mkPen("w")))
                    self._hover_nodes=[{"x":float(xv),"y":float(yv),"tip":f"<b>Observed record {i+1}</b><br>{self.xcol.currentText()}: {xv:.6g}<br>{self.ycol.currentText()}: {yv:.6g}<br>Fitted: {pv:.6g}"} for i,(xv,yv,pv) in enumerate(zip(data["x"],data["y"],data["predicted"]))]
                    order=np.argsort(data["x"]);self.plot.plot(data["x"][order],data["predicted"][order],pen=pg.mkPen(self.secondary_color,width=2),name=f"OLS R²={data['r2']:.3f}")
                    self.plot.setLabel("bottom",self.xcol.currentText());self.plot.setLabel("left",self.ycol.currentText())
                    self.status.setText(f"OLS visualization · n={len(data['x'])} · R²={data['r2']:.4f} · β₁={data['slope']:.5g}")
                elif typ==1:
                    self.plot.addItem(pg.ScatterPlotItem(x=data["predicted"],y=data["residual"],size=8,brush=(*self.primary_color.getRgb()[:3],220),pen=pg.mkPen("w")))
                    self._hover_nodes=[{"x":float(xv),"y":float(rv),"tip":f"<b>Residual record {i+1}</b><br>Fitted: {xv:.6g}<br>Residual: {rv:.6g}"} for i,(xv,rv) in enumerate(zip(data["predicted"],data["residual"]))]
                    self.plot.addItem(pg.InfiniteLine(pos=0,angle=0,pen=pg.mkPen(self.secondary_color,style=Qt.PenStyle.DashLine)))
                    self.plot.setLabel("bottom","Fitted values");self.plot.setLabel("left","Residuals");self.status.setText(f"Residual diagnostic · n={len(data['x'])} · OLS R²={data['r2']:.4f}")
                else:
                    labels=frame[self.labelcol.currentText()].astype(str).tolist();est=pd.to_numeric(frame[self.ycol.currentText()],errors="coerce").to_numpy(float)
                    labs,vals=finite_coefficients(labels,est);self._draw_bars(labs,vals,self.ycol.currentText());self.status.setText("Coefficient chart from imported estimates; add optional CI columns to the input for a later confidence-interval view.")
            else:
                if typ==0:
                    paths=sem_path_layout(frame[self.xcol.currentText()],frame[self.targetcol.currentText()],frame[self.ycol.currentText()])
                    if not paths["nodes"]:raise ValueError("No valid Source → Target paths with numeric estimates were found.")
                    for source,target,beta in paths["edges"]:
                        x1,y1=paths["positions"][source];x2,y2=paths["positions"][target]
                        self.plot.plot([x1,x2],[y1,y2],pen=pg.mkPen(self.primary_color,width=1+min(3,abs(beta)*3)))
                        vb=self.plot.getViewBox();p1=vb.mapViewToScene(pg.Point(x1,y1));p2=vb.mapViewToScene(pg.Point(x2,y2))
                        angle=float(np.degrees(np.arctan2(p2.y()-p1.y(),p2.x()-p1.x()))+180)
                        arrow=pg.ArrowItem(pos=(x2,y2),angle=angle,brush=self.primary_color,pen=pg.mkPen(self.primary_color),tipAngle=35,headLen=14,headWidth=10)
                        self.plot.addItem(arrow)
                        self._hover_edges.append({"x1":x1,"y1":y1,"x2":x2,"y2":y2,"tip":f"<b>{source} → {target}</b><br>Path estimate β: {beta:.6g}"})
                        t=pg.TextItem(f"β={beta:.3g}",color="#334155",anchor=(.5,.5));t.setPos((x1+x2)/2,(y1+y2)/2+.05);self.plot.addItem(t)
                    xs=[paths["positions"][n][0] for n in paths["nodes"]];ys=[paths["positions"][n][1] for n in paths["nodes"]]
                    self.plot.addItem(pg.ScatterPlotItem(x=xs,y=ys,size=24,brush=self.primary_color.lighter(165),pen=pg.mkPen(self.secondary_color,width=1.5)))
                    for n,(x,y) in paths["positions"].items():
                        label=pg.TextItem(n,color="#172033",anchor=(.5,1.4));label.setPos(x,y);self.plot.addItem(label)
                        self._hover_nodes.append({"x":float(x),"y":float(y),"tip":f"<b>{n}</b><br>SEM construct"})
                    self.status.setText(f"{self.kind} path diagram · {len(paths['nodes'])} constructs · {len(paths['edges'])} paths. Data are visualized as imported; the model is not estimated here.")
                    self.plot.setLabel("bottom","Structural paths")
                elif typ==1:
                    labels=frame[self.labelcol.currentText()].astype(str).tolist();values=pd.to_numeric(frame[self.ycol.currentText()],errors="coerce").to_numpy(float)
                    labs,vals=finite_coefficients(labels,values);self._draw_bars(labs,vals,self.ycol.currentText());self.status.setText("Path estimates shown as a signed bar chart.")
                else:
                    labels=frame[self.labelcol.currentText()].astype(str).tolist();values=pd.to_numeric(frame[self.ycol.currentText()],errors="coerce").to_numpy(float)
                    labs,vals=finite_coefficients(labels,values);self._draw_bars(labs,vals,self.ycol.currentText());self.status.setText("Metric chart: use one row per construct/metric (e.g., Alpha, CR, AVE, HTMT) with numeric values. This view does not calculate validity indices.")
        except Exception as exc:self.status.setText(str(exc))
        self.plot.setTitle(f"{self.kind} · {self.chart_type.currentText()}")
        self.plot.autoRange(padding=.08)

    def _on_plot_mouse_moved(self,pos):
        vb=self.plot.getViewBox()
        if not vb.sceneBoundingRect().contains(pos):QToolTip.hideText();return
        nearest=None;distance=1e9
        for row in self._hover_nodes:
            scene=vb.mapViewToScene(pg.Point(row["x"],row["y"]))
            d=math.hypot(pos.x()-scene.x(),pos.y()-scene.y())
            if d<distance:nearest,distance=row,d
        if nearest is not None and distance<=15:
            QToolTip.showText(QCursor.pos(),nearest["tip"],self.plot);return
        closest=None;edge_distance=1e9
        for edge in self._hover_edges:
            a=vb.mapViewToScene(pg.Point(edge["x1"],edge["y1"]));b=vb.mapViewToScene(pg.Point(edge["x2"],edge["y2"]))
            dx,dy=b.x()-a.x(),b.y()-a.y();den=dx*dx+dy*dy
            t=0 if den==0 else max(0,min(1,((pos.x()-a.x())*dx+(pos.y()-a.y())*dy)/den))
            d=math.hypot(pos.x()-(a.x()+t*dx),pos.y()-(a.y()+t*dy))
            if d<edge_distance:closest,edge_distance=edge,d
        if closest is not None and edge_distance<=8:QToolTip.showText(QCursor.pos(),closest["tip"],self.plot)
        else:QToolTip.hideText()

    def _draw_bars(self,labels,values,axis_label):
        if not len(values):raise ValueError("No finite numeric estimates to plot.")
        order=np.argsort(values);values=np.asarray(values)[order];labels=[labels[i] for i in order];y=np.arange(len(values))
        colors=[(*self.primary_color.getRgb()[:3],220) if v>=0 else (*self.secondary_color.getRgb()[:3],220) for v in values]
        self.plot.addItem(pg.BarGraphItem(x0=np.minimum(values,0),x1=np.maximum(values,0),y=y,height=.68,brush=colors,pen=pg.mkPen(None)))
        self._hover_nodes=[{"x":float(value),"y":float(row),"tip":f"<b>{label}</b><br>{axis_label}: {value:.6g}"} for row,(label,value) in enumerate(zip(labels,values))]
        self.plot.getAxis("left").setTicks([[(int(i),str(label)) for i,label in enumerate(labels)]])
        self.plot.addItem(pg.InfiniteLine(pos=0,angle=90,pen=pg.mkPen("#64748b",style=Qt.PenStyle.DashLine)))
        self.plot.setLabel("bottom",axis_label);self.plot.setLabel("left",self.labelcol.currentText())

    def export(self):
        path,selected=QFileDialog.getSaveFileName(self,"Export quantitative chart","quantitative_chart.png","PNG image (*.png);;SVG vector image (*.svg)")
        if not path:return
        try:
            if path.lower().endswith(".svg") or selected.startswith("SVG"):
                if not path.lower().endswith(".svg"):path+=".svg"
                export_plot_widget(self.plot,path,vector=True)
            else:
                if not path.lower().endswith(".png"):path+=".png"
                export_plot_widget(self.plot,path,vector=False)
            QMessageBox.information(self,"Export complete",f"Chart saved to:\n{path}")
        except Exception as exc:QMessageBox.critical(self,"Export failed",str(exc))


class QuantitativeTab(QWidget):
    def __init__(self,state):
        super().__init__();self.state=state;root=QVBoxLayout(self)
        self.pages=QTabWidget();self.regression=QuantPage(state,"Regression");self.cbsem=QuantPage(state,"CB-SEM");self.plssem=QuantPage(state,"PLS-SEM")
        self.pages.addTab(self.regression,"Regression");self.pages.addTab(self.cbsem,"CB-SEM");self.pages.addTab(self.plssem,"PLS-SEM")
        root.addWidget(self.pages);self.refresh_from_state()
    def refresh_from_state(self):
        method=self.state.data.method;frame=self.state.data.quant_frame
        page_index={"Regression":0,"CB-SEM":1,"PLS-SEM":2}.get(method)
        for i,kind in enumerate(("Regression","CB-SEM","PLS-SEM")):
            self.pages.setTabEnabled(i,frame is not None and self.state.data.quant_type==kind and method==kind)
        if page_index is not None and frame is not None and self.state.data.quant_type==method:
            self.pages.setCurrentIndex(page_index)
        self.regression.refresh();self.cbsem.refresh();self.plssem.refresh()
