"""Offscreen interaction and app tab gating tests (run with QT_QPA_PLATFORM=offscreen)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import numpy as np
from unittest.mock import patch
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QPushButton, QDialogButtonBox, QTableWidget, QTableWidgetItem, QComboBox
import pyqtgraph as pg
from app.ui.main_window import MainWindow
from app.core.io_excel import load_total_influence_matrix,load_ranking_results
from app.core.dematel import compute_dematel_from_total

APP=QApplication.instance() or QApplication([])

class AppTabGatingTests(unittest.TestCase):
    def test_cooccurrence_import_and_interactive_heatmap(self):
        w=MainWindow();w.resize(1400,850);w.show();APP.processEvents()
        try:
            w.data_tab.cb_mode.setCurrentIndex(5)
            source=str(Path('Demo Data')/'Code_Cooccurrence_Demo.csv')
            with patch('app.ui.data_tab.QFileDialog.getOpenFileName',return_value=(source,'CSV')):
                w.data_tab.on_load()
            APP.processEvents()
            self.assertEqual(w.state.data.method,'Co-occurrence')
            self.assertTrue(w.tabs.isTabEnabled(1))
            self.assertEqual(w.state.data.cooccurrence_excerpt_count,6)
            self.assertEqual(w.state.data.cooccurrence_matrix.shape,(4,4))
            self.assertTrue(np.allclose(w.state.data.cooccurrence_matrix,w.state.data.cooccurrence_matrix.T))
            self.assertEqual(w.data_tab.tbl_res.rowCount(),4)
            w.tabs.setCurrentIndex(1);APP.processEvents()
            visual=w.visual_tab
            self.assertEqual(visual.cb_chart.currentText(),'Code co-occurrence heatmap')
            self.assertEqual(len(visual._hover_nodes),16)
            self.assertTrue(any(isinstance(item,pg.PColorMeshItem) for item in visual.plot.items()))
            chart_x,chart_y=visual.plot.getViewBox().viewRange()
            self.assertLessEqual(chart_x[0],0);self.assertGreaterEqual(chart_x[1],4)
            self.assertLessEqual(chart_y[0],0);self.assertGreaterEqual(chart_y[1],4)
            cell=visual._hover_nodes[0]
            scene=visual.plot.getViewBox().mapViewToScene(pg.Point(cell['x'],cell['y']))
            with patch('app.ui.visual_tab.QToolTip.showText') as show_tip:
                visual._on_plot_mouse_moved(scene)
                self.assertTrue(show_tip.called)
            with patch('app.ui.visual_tab.QColorDialog.getColor',return_value=QColor('#2277aa')):
                visual._choose_chart_color('primary')
            self.assertEqual(visual.primary_chart_color.name(),'#2277aa')
        finally:w.close()

    def test_shared_import_unlocks_only_matching_analysis_page(self):
        w=MainWindow();w.resize(1400,850);w.show();APP.processEvents()
        try:
            self.assertEqual([w.tabs.tabText(i) for i in range(w.tabs.count())],["Data","Visual","Quantitative charts"])
            self.assertTrue(w.tabs.isTabEnabled(1));self.assertFalse(w.tabs.isTabEnabled(2))
            w.data_tab.cb_mode.setCurrentIndex(2)
            regression_path=str(Path('Demo Data')/'Regression_Demo.xlsx')
            with patch('app.ui.data_tab.QFileDialog.getOpenFileName',return_value=(regression_path,'Excel')):w.data_tab.on_load()
            APP.processEvents()
            self.assertTrue(w.tabs.isTabEnabled(2));self.assertTrue(w.quant_tab.pages.isTabEnabled(0))
            self.assertFalse(w.quant_tab.pages.isTabEnabled(1));self.assertIn('OLS visualization',w.quant_tab.regression.status.text())
            self.assertTrue(w.quant_tab.regression._hover_nodes)
            regression=w.quant_tab.regression;node=regression._hover_nodes[0]
            scene=regression.plot.getViewBox().mapViewToScene(pg.Point(node["x"],node["y"]))
            with patch('app.ui.quant_tab.QToolTip.showText') as show_tip:regression._on_plot_mouse_moved(scene);self.assertTrue(show_tip.called)
            w.data_tab.cb_mode.setCurrentIndex(3)
            self.assertFalse(w.tabs.isTabEnabled(2))
            sem_path=str(Path('Demo Data')/'SEM_Path_Estimates_Demo.xlsx')
            with patch('app.ui.data_tab.QFileDialog.getOpenFileName',return_value=(sem_path,'Excel')):w.data_tab.on_load()
            APP.processEvents()
            self.assertTrue(w.tabs.isTabEnabled(2));self.assertTrue(w.quant_tab.pages.isTabEnabled(1))
            self.assertFalse(w.quant_tab.pages.isTabEnabled(0));self.assertIn('path diagram',w.quant_tab.cbsem.status.text().lower())
            self.assertGreaterEqual(len([item for item in w.quant_tab.cbsem.plot.items() if isinstance(item,pg.ArrowItem)]),1)
            self.assertTrue(w.quant_tab.cbsem._hover_edges)
            sem=w.quant_tab.cbsem;edge=sem._hover_edges[0];mid=pg.Point((edge["x1"]+edge["x2"])/2,(edge["y1"]+edge["y2"])/2)
            scene=sem.plot.getViewBox().mapViewToScene(mid)
            with patch('app.ui.quant_tab.QToolTip.showText') as show_tip:sem._on_plot_mouse_moved(scene);self.assertTrue(show_tip.called)
            with patch('app.ui.quant_tab.QColorDialog.getColor',return_value=QColor("#008866")):
                w.quant_tab.cbsem._choose_color("primary")
            self.assertEqual(w.quant_tab.cbsem.primary_color.name(),"#008866")
            w.data_tab.cb_mode.setCurrentIndex(4)
            self.assertFalse(w.tabs.isTabEnabled(2))
            with patch('app.ui.data_tab.QFileDialog.getOpenFileName',return_value=(sem_path,'Excel')):w.data_tab.on_load()
            APP.processEvents()
            self.assertTrue(w.tabs.isTabEnabled(2));self.assertTrue(w.quant_tab.pages.isTabEnabled(2))
            self.assertFalse(w.quant_tab.pages.isTabEnabled(1));self.assertIn('path diagram',w.quant_tab.plssem.status.text().lower())
        finally:w.close()

    def test_visual_reference_lines_legend_and_compact_axis_controls(self):
        w=MainWindow();w.resize(1100,780);w.show();APP.processEvents()
        try:
            v=w.visual_tab
            d=w.state.data;d.method='DEMATEL';d.labels,d.matrix=load_total_influence_matrix(Path('Demo Data')/'DEMATEL_Demo.xlsx')
            d.dematel_table=compute_dematel_from_total(d.matrix,d.labels);w.state.emit_changed();APP.processEvents()
            v.custom_lines=[("horizontal",0,0,"old", "#ff00ff",40,0)]
            def accept_line_dialog():
                dialog=APP.activeModalWidget();table=dialog.findChild(QTableWidget);table.setCurrentCell(0,0)
                next(b for b in dialog.findChildren(QPushButton) if b.text()=="Delete selected line").click()
                with patch('app.ui.visual_tab.QInputDialog.getItem',return_value=("Function (y = ax + b)",True)):
                    next(b for b in dialog.findChildren(QPushButton) if b.text()=="Add line…").click()
                combo=table.cellWidget(0,0);self.assertEqual(combo.currentData(),"function")
                self.assertFalse(table.item(0,1).flags() & Qt.ItemFlag.ItemIsEditable)
                self.assertTrue(table.item(0,2).flags() & Qt.ItemFlag.ItemIsEditable)
                self.assertTrue(table.item(0,3).flags() & Qt.ItemFlag.ItemIsEditable)
                for col,value in ((2,"1"),(3,"-0.8"),(4,"linear function"),(5,"#00aa77"),(6,"25"),(7,"13")):
                    table.item(0,col).setText(value)
                with patch('app.ui.visual_tab.QColorDialog.getColor',return_value=QColor("#00aa77")):
                    v._choose_line_color(table,0,5,dialog)
                self.assertEqual(table.item(0,5).background().color().name(),"#00aa77")
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            QTimer.singleShot(0,accept_line_dialog);v._manage_custom_lines()
            self.assertEqual(v.custom_lines,[("function",1.0,-0.8,"linear function","#00aa77",25,13)])
            self.assertTrue(any("linear function" in edge.get("tip","") for edge in v._hover_edges))
            self.assertEqual(v._normalize_reference_line((0,4,1,4,"old horizontal","#333333",20,0)),
                             ("horizontal",4.0,0.0,"old horizontal","#333333",20,0))
            self.assertEqual(v._normalize_reference_line((3,0,3,1,"old vertical","#333333",20,0)),
                             ("vertical",3.0,0.0,"old vertical","#333333",20,0))
            v.custom_lines=[("horizontal",-.02,0,"Horizontal reference","#aa2233",30,0),
                            ("vertical",.5,0,"Vertical reference","#22aa33",30,0),
                            ("function",.1,-.1,"Linear reference","#2233aa",30,0)]
            v.refresh_from_state();APP.processEvents()
            self.assertEqual(sum(isinstance(entry["item"],pg.InfiniteLine) for entry in v._reference_line_items),2)
            linear=next(entry for entry in v._reference_line_items if entry["kind"]=="function")
            x_range,y_range=v.plot.getViewBox().viewRange()
            self.assertLessEqual(min(linear["item"].getData()[0]),x_range[1])
            self.assertGreaterEqual(max(linear["item"].getData()[0]),x_range[0])
            for equation in ("y = -0.02", "x = 0.5", "y = 0.1x -0.1"):
                self.assertTrue(any(equation in edge.get("tip","") for edge in v._hover_edges),equation)
            self.assertFalse(v.chk_show_legend.isChecked());self.assertIsNone(v._legend)
            v.chk_show_legend.setChecked(True);APP.processEvents()
            self.assertIsNotNone(v._legend)
            # Existing default entries appear in the manager and can be renamed,
            # removed or recolored without converting them into unrelated items.
            def edit_defaults_and_add():
                dialog=APP.activeModalWidget();table=dialog.findChild(QTableWidget)
                self.assertGreaterEqual(table.rowCount(),3)
                self.assertIsInstance(table.cellWidget(0,1),QComboBox)
                self.assertIsInstance(table.cellWidget(0,2),QComboBox)
                table.cellWidget(0,2).setCurrentText("Drivers")
                next(b for b in dialog.findChildren(QPushButton) if b.text()=="Add legend item").click()
                row=table.rowCount()-1
                table.cellWidget(row,1).setCurrentText("Diamond")
                table.cellWidget(row,2).setEditText("External note")
                table.item(row,3).setText("#ff0000")
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            QTimer.singleShot(0,edit_defaults_and_add);v._configure_legend()
            self.assertEqual(v.legend_overrides["base:cause"][1],"Drivers")
            self.assertEqual(len(v.legend_extras),1)
            self.assertTrue(v.btn_cause_color.isEnabled())
            with patch('app.ui.visual_tab.QColorDialog.getColor',return_value=QColor("#00aa55")):
                v._choose_node_color("cause")
            self.assertEqual(v.cause_color.name(),"#00aa55")
            self.assertEqual(v._shape_symbol("Hexagon"),"h")
            def remove_default_and_extra():
                dialog=APP.activeModalWidget();table=dialog.findChild(QTableWidget);table.setCurrentCell(0,0)
                next(b for b in dialog.findChildren(QPushButton) if b.text()=="Delete selected item").click()
                table.setCurrentCell(table.rowCount()-1,0)
                next(b for b in dialog.findChildren(QPushButton) if b.text()=="Delete selected item").click()
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            QTimer.singleShot(0,remove_default_and_extra);v._configure_legend()
            self.assertIn("base:cause",v.legend_suppressed);self.assertEqual(v.legend_extras,[])
            self.assertGreaterEqual(v.settings_tabs.width(),300)
            self.assertGreaterEqual(v.content_splitter.handleWidth(),5)
            self.assertEqual(v.settings_tabs.widget(0).horizontalScrollBar().maximum(),0)
            self.assertEqual(v.sp_head.minimum(),1);self.assertEqual(v.sp_head.maximum(),50)
            v.zoom_lock.setChecked(False);v.cb_chart.setCurrentText("Influence heatmap");APP.processEvents()
            self.assertTrue(v._hover_nodes);self.assertIn("Total influence",v._hover_nodes[0]["tip"])
            hover=v._hover_nodes[0];scene=v.plot.getViewBox().mapViewToScene(pg.Point(hover["x"],hover["y"]))
            with patch('app.ui.visual_tab.QToolTip.showText') as show_tip:v._on_plot_mouse_moved(scene);self.assertTrue(show_tip.called)
            with patch('app.ui.visual_tab.QColorDialog.getColor',return_value=QColor("#224466")):
                v._choose_chart_color("primary")
            self.assertEqual(v.primary_chart_color.name(),"#224466")
        finally:w.close()

    def test_all_mcdm_charts_render_and_zoom_lock_survives_config_change(self):
        w=MainWindow();w.resize(1450,850);w.show();APP.processEvents()
        try:
            d=w.state.data;d.method='DEMATEL'
            d.labels,d.matrix=load_total_influence_matrix(Path('Demo Data')/'DEMATEL_Demo.xlsx')
            d.dematel_table=compute_dematel_from_total(d.matrix,d.labels);w.state.emit_changed();APP.processEvents()
            v=w.visual_tab;self.assertGreater(len(v.plot.listDataItems()),0)
            self.assertEqual(v.tbl_seg.horizontalScrollBar().maximum(),0)
            for shape in ("Circle","Square","Triangle","Diamond","Pentagon","Hexagon","Star","Plus","Cross"):
                v.cb_shape_cause.setCurrentText(shape);APP.processEvents()
                self.assertGreater(len(v.plot.listDataItems()),0,shape)
            if v.tbl_seg.rowCount():
                v.tbl_seg.setItem(0,4,QTableWidgetItem("#ff0000"));APP.processEvents()
                self.assertEqual(v._bin_styles[0]["color"],"#ff0000")
                v.tbl_seg.setItem(0,2,QTableWidgetItem("50"));APP.processEvents();self.assertEqual(v._bin_styles[0]["opacity"],50)
                v.tbl_seg.setItem(0,3,QTableWidgetItem("50"));APP.processEvents();self.assertEqual(v._bin_styles[0]["dash"],50)
            v.plot.setXRange(-.5,1.5,padding=0);v.plot.setYRange(-.5,1.5,padding=0)
            before=v.plot.getViewBox().viewRange();v.sp_nodes.setValue(v.sp_nodes.value()+1);after=v.plot.getViewBox().viewRange()
            for axis in range(2):
                for bound in range(2):self.assertAlmostEqual(before[axis][bound],after[axis][bound],places=5)
            v.plot.setXRange(-.25,1.25,padding=0);v.plot.setYRange(-.25,1.25,padding=0)
            locked_before=v.plot.getViewBox().viewRange()
            for index in range(v.cb_chart.count()):
                v.cb_chart.setCurrentIndex(index);APP.processEvents();locked_after=v.plot.getViewBox().viewRange()
                for axis in range(2):
                    for bound in range(2):self.assertAlmostEqual(locked_before[axis][bound],locked_after[axis][bound],places=5)
            self.assertGreaterEqual(v.settings_tabs.width(),300)
            scroll=v.settings_tabs.widget(0)
            self.assertEqual(scroll.horizontalScrollBar().maximum(),0)
            if v.tbl_seg.rowCount():
                v.tbl_seg.setItem(0,4,QTableWidgetItem("#ff0000"));APP.processEvents()
                self.assertEqual(v._bin_styles[0]["color"],"#ff0000")
            d.method='Ranking';d.ranking_labels,d.ranking_columns,d.ranking_values=load_ranking_results(Path('Demo Data')/'Ranking_Demo.xlsx');w.state.emit_changed();APP.processEvents()
            for index in range(v.cb_chart.count()):
                v.cb_chart.setCurrentIndex(index);APP.processEvents()
                self.assertTrue(v._hover_nodes,f"Missing hover details for {v.cb_chart.currentText()}")
            self.assertTrue(w.tabs.isTabEnabled(1))
        finally:w.close()
