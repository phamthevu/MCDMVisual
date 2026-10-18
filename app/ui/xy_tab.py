from __future__ import annotations

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6.QtCore import Qt, QRectF, QPointF, QEvent
from PySide6.QtGui import QBrush, QPen, QFont, QPolygonF, QColor
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFormLayout, QGroupBox, QPushButton,
    QLabel, QFileDialog, QMessageBox, QComboBox, QDoubleSpinBox, QLineEdit,
    QListWidget, QListWidgetItem, QButtonGroup, QInputDialog, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsLineItem, QGraphicsPolygonItem, QGraphicsItem, QGraphicsItemGroup,
    QTabWidget, QColorDialog, QCheckBox, QToolButton, QFrame, QSplitter,
)
from app.core.quant_charts import regression_fit, finite_coefficients, sem_path_layout
from app.ui.exporting import export_plot_widget


class DraggableText(pg.TextItem):
    """Text item that always maps mouse movement back to data coordinates."""
    def __init__(self, text, view_box, color="#172033", font_size=11, background=False, border=False,
                 background_color="#ffffff", border_color="#334155"):
        super().__init__(text=text, color=color, anchor=(.5, .5))
        self.view_box = view_box
        self.label_text = text
        self.text_color = color
        self.background_enabled = background
        self.border_enabled = border
        self.background_color = background_color
        self.border_color = border_color
        self.setFont(QFont("Arial", font_size))
        self.setColor(QColor(color))
        self._apply_frame()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self._drag_origin = None
        self._mouse_origin = None

    def _apply_frame(self):
        self.fill = pg.mkBrush(self.background_color) if self.background_enabled else pg.mkBrush(None)
        self.border = pg.mkPen(self.border_color, width=1.2) if self.border_enabled else pg.mkPen(None)

    def mouseDragEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            event.ignore(); return
        if event.isStart():
            self._drag_origin = QPointF(self.pos())
            self._mouse_origin = self.view_box.mapSceneToView(event.scenePos())
        elif event.isFinish():
            self._drag_origin = None; self._mouse_origin = None
        elif self._drag_origin is not None and self._mouse_origin is not None:
            current = self.view_box.mapSceneToView(event.scenePos())
            self.setPos(self._drag_origin + (current - self._mouse_origin))
        event.accept()


class MovableGroup(QGraphicsItemGroup):
    def __init__(self):
        super().__init__()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setHandlesChildEvents(True)


class XYPlotTab(QWidget):
    """Freeform XY canvas. Choose a tool, click to place, drag objects to move."""
    def __init__(self):
        super().__init__()
        self._draw_mode = "select"
        self._pending_arrow_start = None
        self._gesture_start = None
        self._gesture_dragged = False
        self._preview_item = None
        self._objects = []
        self._mode_buttons = {}
        self.arrow_color = QColor("#334155")
        self.shape_color = QColor("#2563eb")
        self.text_color = QColor("#172033")
        self.text_bg_color = QColor("#ffffff")
        self.text_border_color = QColor("#334155")
        root = QVBoxLayout(self); root.setContentsMargins(12,10,12,12); root.setSpacing(9)
        header = QHBoxLayout(); title = QLabel("XY Drawing"); title.setObjectName("xyTitle")
        subtitle = QLabel("Create and arrange shapes, labels and arrows directly on the canvas."); subtitle.setObjectName("xySubtitle")
        title_stack=QVBoxLayout();title_stack.addWidget(title);title_stack.addWidget(subtitle);header.addLayout(title_stack);header.addStretch(1)
        root.addLayout(header)
        tools_frame=QFrame();tools_frame.setObjectName("ribbon");tools_outer=QVBoxLayout(tools_frame);tools_outer.setContentsMargins(10,8,10,8);tools_outer.setSpacing(7)
        row=QHBoxLayout(); self.tool_group=QButtonGroup(self);self.tool_group.setExclusive(True)
        for label,mode in (("Select","select"),("Rectangle","rectangle"),("Ellipse","circle"),("Triangle","triangle"),("Arrow","arrow")):
            b=QToolButton();b.setText(label);b.setCheckable(True);b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly);b.clicked.connect(lambda checked=False,m=mode:self.set_tool(m));self.tool_group.addButton(b);row.addWidget(b)
            self._mode_buttons[mode]=b
            if mode=="select":b.setChecked(True)
        row.addSpacing(10);row.addWidget(QLabel("Text"));self.text_entry=QLineEdit();self.text_entry.setPlaceholderText("Type text, then click the canvas");self.text_entry.setMaximumWidth(240);row.addWidget(self.text_entry)
        self.text_btn=QToolButton();self.text_btn.setText("Add text");self.text_btn.clicked.connect(self.start_text_tool);row.addWidget(self.text_btn)
        row.addSpacing(10)
        self.btn_arrow_color=QToolButton();self.btn_arrow_color.setText("Arrow color");self.btn_arrow_color.clicked.connect(lambda:self._choose_color("arrow"));row.addWidget(self.btn_arrow_color)
        self.btn_shape_color=QToolButton();self.btn_shape_color.setText("Shape color");self.btn_shape_color.clicked.connect(lambda:self._choose_color("shape"));row.addWidget(self.btn_shape_color)
        self.btn_text_color=QToolButton();self.btn_text_color.setText("Text color");self.btn_text_color.clicked.connect(lambda:self._choose_color("text"));row.addWidget(self.btn_text_color)
        row.addStretch(1)
        self.zoom_lock=QToolButton();self.zoom_lock.setText("Lock view");self.zoom_lock.setCheckable(True);self.zoom_lock.setChecked(False);row.addWidget(self.zoom_lock)
        self.zoom_out=QToolButton();self.zoom_out.setText("−");self.zoom_out.setToolTip("Zoom out");row.addWidget(self.zoom_out)
        self.zoom_in=QToolButton();self.zoom_in.setText("+");self.zoom_in.setToolTip("Zoom in");row.addWidget(self.zoom_in)
        self.btn_export=QToolButton();self.btn_export.setText("Export");self.btn_export.clicked.connect(self.export);row.addWidget(self.btn_export)
        tools_outer.addLayout(row)
        row2=QHBoxLayout();row2.addWidget(QLabel("Text style"));self.text_background=QCheckBox("Background");self.text_border=QCheckBox("Border");row2.addWidget(self.text_background);row2.addWidget(self.text_border)
        self.btn_bg_color=QToolButton();self.btn_bg_color.setText("Fill color");self.btn_bg_color.clicked.connect(lambda:self._choose_color("background"));row2.addWidget(self.btn_bg_color)
        self.btn_border_color=QToolButton();self.btn_border_color.setText("Border color");self.btn_border_color.clicked.connect(lambda:self._choose_color("border"));row2.addWidget(self.btn_border_color)
        self.btn_apply_text_style=QToolButton();self.btn_apply_text_style.setText("Apply to selected text");self.btn_apply_text_style.clicked.connect(self.apply_selected_text_style);row2.addWidget(self.btn_apply_text_style)
        row2.addSpacing(16);self.hline_btn=QToolButton();self.hline_btn.setText("Add y = k");self.vline_btn=QToolButton();self.vline_btn.setText("Add x = k")
        self.hline_btn.clicked.connect(lambda:self.add_reference_line("h"));self.vline_btn.clicked.connect(lambda:self.add_reference_line("v"));row2.addWidget(self.hline_btn);row2.addWidget(self.vline_btn)
        row2.addStretch(1);tools_outer.addLayout(row2);root.addWidget(tools_frame)

        splitter=QSplitter(Qt.Orientation.Horizontal)
        panel=QWidget();side=QVBoxLayout(panel);side.setContentsMargins(0,0,0,0);panel.setMinimumWidth(230);panel.setMaximumWidth(310)
        axes = QGroupBox("Canvas and axes"); form = QFormLayout(axes)
        self.xmin=self._spin(-10);self.xmax=self._spin(10);self.ymin=self._spin(-10);self.ymax=self._spin(10)
        self.xtick=self._spin(1,.01,100);self.ytick=self._spin(1,.01,100)
        for label,widget in (("X minimum",self.xmin),("X maximum",self.xmax),("X tick",self.xtick),
                             ("Y minimum",self.ymin),("Y maximum",self.ymax),("Y tick",self.ytick)):
            form.addRow(label,widget)
        self.title=QLineEdit("XY drawing");form.addRow("Title",self.title)
        apply_btn=QPushButton("Apply axes");apply_btn.clicked.connect(self.apply_axes);form.addRow("",apply_btn)
        side.addWidget(axes)
        list_box=QGroupBox("Slide objects");list_lay=QVBoxLayout(list_box)
        self.object_list=QListWidget();list_lay.addWidget(self.object_list)
        self.object_list.setToolTip("Double-click an object's name to rename it. Select a row to delete it.")
        self.object_list.itemChanged.connect(self._rename_object)
        btnrow=QHBoxLayout();self.delete_btn=QPushButton("Delete");self.clear_btn=QPushButton("Clear all")
        btnrow.addWidget(self.delete_btn);btnrow.addWidget(self.clear_btn);list_lay.addLayout(btnrow)
        self.delete_btn.clicked.connect(self.delete_selected);self.clear_btn.clicked.connect(self.clear_objects)
        side.addWidget(list_box,1);splitter.addWidget(panel)
        plot_panel=QWidget();plot_layout=QVBoxLayout(plot_panel);plot_layout.setContentsMargins(0,0,0,0)
        self.help=QLabel("Drag on the canvas to draw a shape or arrow. Click to place a default-size shape. Add text, then drag it to move. Double-click an object name to rename it.")
        self.help.setWordWrap(True);self.help.setObjectName("xyHelp");plot_layout.addWidget(self.help)
        self.plot=pg.PlotWidget(background="w");self.plot.showGrid(x=True,y=True,alpha=.2);self.plot.setMenuEnabled(False)
        plot_layout.addWidget(self.plot,1);splitter.addWidget(plot_panel);splitter.setStretchFactor(1,1);splitter.setSizes([260,980]);root.addWidget(splitter,1)
        self.zoom_in.clicked.connect(lambda:self.plot.getViewBox().scaleBy((.8,.8)))
        self.zoom_out.clicked.connect(lambda:self.plot.getViewBox().scaleBy((1.25,1.25)))
        self.zoom_lock.toggled.connect(lambda locked:self.plot.getViewBox().setMouseEnabled(x=not locked,y=not locked))
        self.plot.viewport().installEventFilter(self)
        self.setStyleSheet("QLabel#xyTitle{font-size:20px;font-weight:700;color:#0f172a} QLabel#xySubtitle{color:#64748b} QFrame#ribbon{background:#f8fafc;border:1px solid #dbe3ee;border-radius:8px} QToolButton{padding:6px 10px;border:1px solid #d5dde8;border-radius:5px;background:white} QToolButton:checked{background:#dbeafe;border-color:#3b82f6;color:#1d4ed8} QLabel#xyHelp{color:#475569;background:#f8fafc;border:1px solid #e2e8f0;border-radius:5px;padding:6px}")
        self.apply_axes()

    @staticmethod
    def _spin(value,step=.1,maximum=1e9):
        s=QDoubleSpinBox();s.setRange(-maximum,maximum);s.setDecimals(5);s.setSingleStep(step);s.setValue(value);return s

    def set_tool(self, mode):
        self._draw_mode=mode;self._pending_arrow_start=None
        if mode in self._mode_buttons:
            for button_mode,button in self._mode_buttons.items():button.setChecked(button_mode==mode)
        mouse_buttons=Qt.MouseButton.LeftButton if mode=="select" else Qt.MouseButton.NoButton
        for _,item,_ in self._objects:
            item.setAcceptedMouseButtons(mouse_buttons)
        self.help.setText({"select":"Select tool: drag objects to reposition; drag empty space to pan. Rename/delete with the object list.",
          "rectangle":"Rectangle tool: drag to size and draw; click once for a default-size shape.",
          "circle":"Ellipse tool: drag to size and draw; click once for a default-size shape.",
          "triangle":"Triangle tool: drag to size and draw; click once for a default-size shape.",
          "arrow":"Arrow tool: drag from the tail to the tip. A two-click arrow also works."}.get(mode,""))

    def start_text_tool(self):
        if not self.text_entry.text().strip():
            self.help.setText("Type the text in the box first, then press Place text and click the chart.");self.text_entry.setFocus();return
        self.set_tool("text")
        self.help.setText("Text placement active: click the canvas to place. Use Background and Border above to style it, then drag to move.")

    def _choose_color(self, which):
        current={"arrow":self.arrow_color,"shape":self.shape_color,"text":self.text_color,"background":self.text_bg_color,"border":self.text_border_color}[which]
        color=QColorDialog.getColor(current,self,f"Choose {which} color")
        if not color.isValid():return
        setattr(self,{"arrow":"arrow_color","shape":"shape_color","text":"text_color","background":"text_bg_color","border":"text_border_color"}[which],color)
        button={"arrow":self.btn_arrow_color,"shape":self.btn_shape_color,"text":self.btn_text_color,"background":self.btn_bg_color,"border":self.btn_border_color}[which]
        button.setStyleSheet(f"background:{color.name()};color:{'#fff' if color.lightness()<130 else '#172033'}")

    def apply_selected_text_style(self):
        row=self.object_list.currentRow()
        if row<0 or not isinstance(self._objects[row][1],DraggableText):
            self.help.setText("Select a text object in the list first, then apply its background or border style.");return
        item=self._objects[row][1];item.background_enabled=self.text_background.isChecked();item.border_enabled=self.text_border.isChecked()
        item.text_color=self.text_color.name();item.background_color=self.text_bg_color.name();item.border_color=self.text_border_color.name()
        item.setColor(QColor(item.text_color));item._apply_frame();self.plot.update()

    def apply_axes(self):
        if self.xmax.value()<=self.xmin.value() or self.ymax.value()<=self.ymin.value():
            QMessageBox.warning(self,"Axis range","Each maximum must be greater than its minimum.");return
        for axis,lo,hi,step in (("bottom",self.xmin.value(),self.xmax.value(),self.xtick.value()),
                                ("left",self.ymin.value(),self.ymax.value(),self.ytick.value())):
            self.plot.setXRange(lo,hi,padding=0) if axis=="bottom" else self.plot.setYRange(lo,hi,padding=0)
            safe_step=max(step,(hi-lo)/79);first=np.ceil(lo/safe_step)*safe_step
            n=min(80,max(1,int((hi-first)/safe_step)+1));ticks=np.linspace(first,hi,n)
            self.plot.getAxis(axis).setTicks([[(float(v),f"{v:g}") for v in ticks]])
        self.plot.setTitle(self.title.text())

    def eventFilter(self,watched,event):
        if watched is self.plot.viewport():
            if event.type()==QEvent.Type.MouseButtonPress and self._draw_mode!="select" and event.button()==Qt.MouseButton.LeftButton:
                self._gesture_start=self.plot.mapToScene(event.position().toPoint());self._gesture_dragged=False;return True
            if event.type()==QEvent.Type.MouseMove and self._gesture_start is not None:
                pos=self.plot.mapToScene(event.position().toPoint())
                if (pos-self._gesture_start).manhattanLength()>7:self._gesture_dragged=True
                if self._gesture_dragged and self._draw_mode in ("rectangle","circle","triangle"):
                    self._show_preview(self._gesture_start,pos)
                return True
            if event.type()==QEvent.Type.MouseButtonRelease and self._gesture_start is not None and event.button()==Qt.MouseButton.LeftButton:
                start=self._gesture_start;end=self.plot.mapToScene(event.position().toPoint());mode=self._draw_mode
                self._gesture_start=None;self._remove_preview()
                if mode=="arrow":self._handle_arrow_gesture(start,end)
                elif mode in ("rectangle","circle","triangle"):
                    if self._gesture_dragged:self._place_shape_drag(mode,start,end)
                    else:self._place_at(start)
                else:self._place_at(start)
                return True
        return super().eventFilter(watched,event)

    def _remove_preview(self):
        if self._preview_item is not None:
            self.plot.getViewBox().removeItem(self._preview_item);self._preview_item=None

    def _show_preview(self,start,end):
        self._remove_preview();vb=self.plot.getViewBox();a=vb.mapSceneToView(start);b=vb.mapSceneToView(end)
        x=min(a.x(),b.x());y=min(a.y(),b.y());w=abs(a.x()-b.x());h=abs(a.y()-b.y())
        if w<1e-8 or h<1e-8:return
        if self._draw_mode=="rectangle":item=QGraphicsRectItem(QRectF(x,y,w,h))
        elif self._draw_mode=="circle":item=QGraphicsEllipseItem(QRectF(x,y,w,h))
        else:item=QGraphicsPolygonItem(QPolygonF([QPointF(x+w/2,y),QPointF(x,y+h),QPointF(x+w,y+h)]))
        item.setPen(QPen(self.shape_color,2,Qt.PenStyle.DashLine));item.setBrush(QBrush(Qt.BrushStyle.NoBrush));self.plot.getViewBox().addItem(item);self._preview_item=item

    def _place_shape_drag(self,kind,start,end):
        vb=self.plot.getViewBox();a=vb.mapSceneToView(start);b=vb.mapSceneToView(end)
        x=min(a.x(),b.x());y=min(a.y(),b.y());w=abs(a.x()-b.x());h=abs(a.y()-b.y())
        if w<1e-8 or h<1e-8:self._place_at(start);return
        item=self._shape_item(kind,QRectF(x,y,w,h));self.plot.getViewBox().addItem(item);self._track(f"{kind.title()} at ({(x+w/2):.3g}, {(y+h/2):.3g})",item,"viewbox");self.set_tool("select")

    def _handle_arrow_gesture(self,start,end):
        vb=self.plot.getViewBox();a=vb.mapSceneToView(start);b=vb.mapSceneToView(end)
        if (end-start).manhattanLength()>7:self._add_arrow((a.x(),a.y()),(b.x(),b.y()));self.set_tool("select")
        else:self._place_at(start)

    def _place_at(self,scene_pos):
        vb=self.plot.getViewBox()
        if not vb.sceneBoundingRect().contains(scene_pos):return
        point=vb.mapSceneToView(scene_pos);x,y=float(point.x()),float(point.y())
        if self._draw_mode=="arrow":
            if self._pending_arrow_start is None:
                self._pending_arrow_start=(x,y);self.help.setText("Arrow start set. Click the end point.")
            else:
                self._add_arrow(self._pending_arrow_start,(x,y));self._pending_arrow_start=None;self.set_tool("select")
            return
        if self._draw_mode=="text":
            text=self.text_entry.text().strip();self._add_text(text,x,y);self.set_tool("select")
        elif self._draw_mode in ("rectangle","circle","triangle"):
            self._add_shape(self._draw_mode,x,y);self.set_tool("select")

    def _size(self):
        xr,yr=self.plot.getViewBox().viewRange();viewport=self.plot.viewport().size()
        diameter=max(18,min(viewport.width(),viewport.height())*.065)
        return max(abs(xr[1]-xr[0])*diameter/max(viewport.width(),1),.01),max(abs(yr[1]-yr[0])*diameter/max(viewport.height(),1),.01)

    def _track(self,label,item,where="plot"):
        self._objects.append((label,item,where));entry=QListWidgetItem(label);entry.setFlags(entry.flags()|Qt.ItemFlag.ItemIsEditable);self.object_list.addItem(entry)

    def _rename_object(self,entry):
        row=self.object_list.row(entry)
        if 0<=row<len(self._objects):
            label,item,_=self._objects[row];self._objects[row]=(entry.text(),item,self._objects[row][2])
            if isinstance(item,DraggableText):item.label_text=entry.text();item.setText(entry.text())

    def _add_text(self,text,x,y):
        item=DraggableText(text,self.plot.getViewBox(),self.text_color.name(),11,self.text_background.isChecked(),self.text_border.isChecked(),self.text_bg_color.name(),self.text_border_color.name());item.setPos(x,y);self.plot.addItem(item);self._track(f"Text: {text[:45]}",item)

    def _shape_item(self,kind,rect):
        if kind=="rectangle":item=QGraphicsRectItem(rect)
        elif kind=="circle":item=QGraphicsEllipseItem(rect)
        else:item=QGraphicsPolygonItem(QPolygonF([QPointF(rect.center().x(),rect.top()),QPointF(rect.left(),rect.bottom()),QPointF(rect.right(),rect.bottom())]))
        item.setPen(QPen(self.shape_color,2));item.setBrush(QBrush(Qt.BrushStyle.NoBrush));item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,True);item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,True);item.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        return item

    def _add_shape(self,kind,x,y):
        w,h=self._size();item=self._shape_item(kind,QRectF(x-w/2,y-h/2,w,h));self.plot.getViewBox().addItem(item);self._track(f"{kind.title()} at ({x:.3g}, {y:.3g})",item,"viewbox")

    def _add_arrow(self,start,end):
        x1,y1=start;x2,y2=end;dx=x2-x1;dy=y2-y1
        if np.hypot(dx,dy)<1e-12:
            self.help.setText("Arrow needs two different points. Select Arrow and try again.");return
        # Build the arrowhead in scene pixels, then map it back to view coordinates.
        # This handles unequal X/Y scale and view transforms without guessing pixels
        # per data unit from the viewport's outer dimensions.
        vb=self.plot.getViewBox()
        scene_start=vb.mapViewToScene(pg.Point(x1,y1));scene_end=vb.mapViewToScene(pg.Point(x2,y2))
        vx,vy=scene_end.x()-scene_start.x(),scene_end.y()-scene_start.y()
        pixel_len=float(np.hypot(vx,vy))
        if pixel_len<2:
            self.help.setText("Arrow is too short to draw. Drag farther between the tail and tip.");return
        ux,uy=vx/pixel_len,vy/pixel_len;head_px=min(16.0,pixel_len*.35);half_px=head_px*.48
        base=QPointF(scene_end.x()-ux*head_px,scene_end.y()-uy*head_px)
        normal=QPointF(-uy*half_px,ux*half_px)
        points=[vb.mapSceneToView(p) for p in (scene_end,base+normal,base-normal)]
        local=[QPointF(float(p.x())-x1,float(p.y())-y1) for p in points]
        group=MovableGroup();line=QGraphicsLineItem(0,0,dx,dy);line.setPen(QPen(self.arrow_color,2.5));group.addToGroup(line)
        head_item=QGraphicsPolygonItem(QPolygonF(local));head_item.setPen(QPen(self.arrow_color,1));head_item.setBrush(QBrush(self.arrow_color));group.addToGroup(head_item)
        group.setPos(x1,y1);self.plot.getViewBox().addItem(group);self._track(f"Arrow ({x1:.3g}, {y1:.3g}) → ({x2:.3g}, {y2:.3g})",group,"viewbox")

    def add_reference_line(self,axis):
        axis_name="y" if axis=="h" else "x"
        low,high=self.plot.getViewBox().viewRange()[1 if axis=="h" else 0]
        value,ok=QInputDialog.getDouble(self,"Reference line",f"{axis_name} = k",0 if low<=0<=high else (low+high)/2,-1e9,1e9,5)
        if not ok:return
        label,ok=QInputDialog.getText(self,"Line label","Optional label")
        if not ok:return
        item=pg.InfiniteLine(pos=value,angle=0 if axis=="h" else 90,movable=True,pen=pg.mkPen("#dc2626",width=1.5,style=Qt.PenStyle.DashLine))
        self.plot.addItem(item);self._track(f"{axis_name} = {value:g}"+(f" · {label}" if label.strip() else ""),item)
        if label.strip():
            xr,yr=self.plot.getViewBox().viewRange();text=DraggableText(label.strip(),self.plot.getViewBox(),"#b91c1c",10)
            text.setPos(xr[0],value) if axis=="h" else text.setPos(value,yr[0])
            self.plot.addItem(text);self._track(f"Line label: {label.strip()}",text)

    def delete_selected(self):
        row=self.object_list.currentRow()
        if row<0:return
        _,item,where=self._objects.pop(row);self.plot.getViewBox().removeItem(item) if where=="viewbox" else self.plot.removeItem(item);self.object_list.takeItem(row)

    def clear_objects(self):
        for _,item,where in self._objects:self.plot.getViewBox().removeItem(item) if where=="viewbox" else self.plot.removeItem(item)
        self._objects.clear();self.object_list.clear()

    def export(self):
        path,selected=QFileDialog.getSaveFileName(self,"Export XY drawing","xy_drawing.png","PNG image (*.png);;SVG vector image (*.svg)")
        if not path:return
        try:
            if path.lower().endswith(".svg") or selected.startswith("SVG"):
                if not path.lower().endswith(".svg"):path+=".svg"
                export_plot_widget(self.plot,path,vector=True)
            else:
                if not path.lower().endswith(".png"):path+=".png"
                export_plot_widget(self.plot,path,vector=False)
            QMessageBox.information(self,"Export complete",f"Drawing saved to:\n{path}")
        except Exception as exc:QMessageBox.critical(self,"Export failed",str(exc))


class QuantPage(QWidget):
    def __init__(self,state,kind):
        super().__init__();self.state=state;self.kind=kind
        root=QHBoxLayout(self);panel=QGroupBox(f"{kind} chart inputs");controls=QVBoxLayout(panel)
        self.chart_type=QComboBox()
        if kind=="Regression":self.chart_type.addItems(["Observed vs fitted", "Residuals vs fitted", "Coefficient estimates"])
        else:self.chart_type.addItems(["SEM path diagram", "Path coefficient bars", "Measurement / validity metrics"])
        controls.addWidget(QLabel("Chart"));controls.addWidget(self.chart_type)
        self.xcol=QComboBox();self.ycol=QComboBox();self.labelcol=QComboBox();self.targetcol=QComboBox()
        form=QFormLayout();form.addRow("Predictor / source",self.xcol);form.addRow("Outcome / estimate",self.ycol);form.addRow("Label / construct",self.labelcol);form.addRow("Target (SEM)",self.targetcol);controls.addLayout(form)
        self.status=QLabel("Import data in the Data tab to activate this chart.");self.status.setWordWrap(True);controls.addWidget(self.status)
        export=QPushButton("Export PNG / SVG…");export.clicked.connect(self.export);controls.addWidget(export);controls.addStretch(1)
        root.addWidget(panel,0);self.plot=pg.PlotWidget(background="w");self.plot.showGrid(x=True,y=True,alpha=.25);root.addWidget(self.plot,1)
        self.chart_type.currentIndexChanged.connect(self.refresh);self.xcol.currentIndexChanged.connect(self.refresh);self.ycol.currentIndexChanged.connect(self.refresh);self.labelcol.currentIndexChanged.connect(self.refresh);self.targetcol.currentIndexChanged.connect(self.refresh)

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
        self.plot.clear();typ=self.chart_type.currentIndex()
        try:
            if self.kind=="Regression":
                x=pd.to_numeric(frame[self.xcol.currentText()],errors="coerce").to_numpy(float)
                y=pd.to_numeric(frame[self.ycol.currentText()],errors="coerce").to_numpy(float)
                data=regression_fit(x,y)
                if typ==0:
                    self.plot.addLegend()
                    self.plot.addItem(pg.ScatterPlotItem(x=data["x"],y=data["y"],size=8,brush=(37,115,164,220),pen=pg.mkPen("w")))
                    order=np.argsort(data["x"]);self.plot.plot(data["x"][order],data["predicted"][order],pen=pg.mkPen("#dc2626",width=2),name=f"OLS R²={data['r2']:.3f}")
                    self.plot.setLabel("bottom",self.xcol.currentText());self.plot.setLabel("left",self.ycol.currentText())
                    self.status.setText(f"OLS visualization · n={len(data['x'])} · R²={data['r2']:.4f} · β₁={data['slope']:.5g}")
                elif typ==1:
                    self.plot.addItem(pg.ScatterPlotItem(x=data["predicted"],y=data["residual"],size=8,brush=(37,115,164,220),pen=pg.mkPen("w")))
                    self.plot.addItem(pg.InfiniteLine(pos=0,angle=0,pen=pg.mkPen("#dc2626",style=Qt.PenStyle.DashLine)))
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
                        self.plot.plot([x1,x2],[y1,y2],pen=pg.mkPen("#64748b",width=1+min(3,abs(beta)*3)))
                        angle=np.degrees(np.arctan2(y2-y1,x2-x1));self.plot.addItem(pg.ArrowItem(pos=(x2,y2),angle=angle,brush="#475569",tipAngle=35,headLen=12))
                        t=pg.TextItem(f"β={beta:.3g}",color="#334155",anchor=(.5,.5));t.setPos((x1+x2)/2,(y1+y2)/2+.05);self.plot.addItem(t)
                    xs=[paths["positions"][n][0] for n in paths["nodes"]];ys=[paths["positions"][n][1] for n in paths["nodes"]]
                    self.plot.addItem(pg.ScatterPlotItem(x=xs,y=ys,size=24,brush=(219,234,254,255),pen=pg.mkPen("#2563eb",width=1.5)))
                    for n,(x,y) in paths["positions"].items():
                        label=pg.TextItem(n,color="#172033",anchor=(.5,1.4));label.setPos(x,y);self.plot.addItem(label)
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

    def _draw_bars(self,labels,values,axis_label):
        if not len(values):raise ValueError("No finite numeric estimates to plot.")
        order=np.argsort(values);values=np.asarray(values)[order];labels=[labels[i] for i in order];y=np.arange(len(values))
        colors=[(37,115,164,220) if v>=0 else (220,70,60,220) for v in values]
        self.plot.addItem(pg.BarGraphItem(x0=np.minimum(values,0),x1=np.maximum(values,0),y=y,height=.68,brush=colors,pen=pg.mkPen(None)))
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
