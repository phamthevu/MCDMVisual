"""Offscreen interaction and app tab gating tests (run with QT_QPA_PLATFORM=offscreen)."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import tempfile
from unittest.mock import patch
from pathlib import Path
import pandas as pd
from PySide6.QtCore import Qt, QPoint, QPointF, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QToolButton, QAbstractButton, QDialogButtonBox, QTableWidget, QTableWidgetItem
from app.ui.exporting import export_plot_widget
from app.ui.xy_tab import XYPlotTab
from app.ui.main_window import MainWindow
from app.core.io_excel import load_total_influence_matrix,load_ranking_results
from app.core.dematel import compute_dematel_from_total

APP=QApplication.instance() or QApplication([])

class DrawingInteractionTests(unittest.TestCase):
    def test_place_drag_and_delete_canvas_objects(self):
        w=XYPlotTab();w.resize(1200,800);w.show();APP.processEvents()
        try:
            def click_data(x,y):
                scene=w.plot.getViewBox().mapViewToScene(QPointF(x,y))
                QTest.mouseClick(w.plot.viewport(),Qt.MouseButton.LeftButton,pos=w.plot.mapFromScene(scene))
                APP.processEvents()
            buttons={button.text():button for button in w.findChildren(QAbstractButton)}
            for name,point in (("Rectangle",(0,0)),("Ellipse",(1,1)),("Triangle",(-1,1))):
                QTest.mouseClick(buttons[name],Qt.MouseButton.LeftButton);click_data(*point)
            self.assertEqual(w.object_list.count(),3)
            # PowerPoint-style drag gesture sets a custom shape size.
            QTest.mouseClick(buttons["Rectangle"],Qt.MouseButton.LeftButton)
            start=w.plot.mapFromScene(w.plot.getViewBox().mapViewToScene(QPointF(-4,-3)))
            end=w.plot.mapFromScene(w.plot.getViewBox().mapViewToScene(QPointF(-2,-1)))
            QTest.mousePress(w.plot.viewport(),Qt.MouseButton.LeftButton,pos=start)
            QTest.mouseMove(w.plot.viewport(),end,100)
            QTest.mouseRelease(w.plot.viewport(),Qt.MouseButton.LeftButton,pos=end);APP.processEvents()
            self.assertEqual(w.object_list.count(),4)
            w.text_entry.setText("Move this label")
            QTest.mouseClick(buttons["Add text"],Qt.MouseButton.LeftButton);click_data(-1,-1)
            self.assertEqual(w.object_list.count(),5)
            item=w._objects[-1][1];before=QPointF(item.pos());scene=item.mapToScene(QPointF(0,0));start=w.plot.mapFromScene(scene);end=start+QPoint(45,-25)
            QTest.mousePress(w.plot.viewport(),Qt.MouseButton.LeftButton,pos=start)
            QTest.mouseMove(w.plot.viewport(),end,80)
            QTest.mouseRelease(w.plot.viewport(),Qt.MouseButton.LeftButton,pos=end);APP.processEvents()
            self.assertGreater((item.pos()-before).manhattanLength(),.05)
            w.object_list.item(4).setText("Renamed text")
            self.assertEqual(item.label_text,"Renamed text")
            w.text_background.setChecked(True);w.text_border.setChecked(True);w.object_list.setCurrentRow(4);w.apply_selected_text_style()
            self.assertTrue(item.background_enabled);self.assertTrue(item.border_enabled)
            with patch('app.ui.xy_tab.QColorDialog.getColor',return_value=QColor("#ff00ff")):
                w._choose_color("arrow")
            self.assertEqual(w.arrow_color.name(),"#ff00ff")
            QTest.mouseClick(buttons["Arrow"],Qt.MouseButton.LeftButton);click_data(-2,2);click_data(2,-2)
            self.assertEqual(w.object_list.count(),6)
            # Drag gesture creates an arrow whose head is defined in screen space,
            # so its size remains usable on charts with unequal axis scales.
            QTest.mouseClick(buttons["Arrow"],Qt.MouseButton.LeftButton)
            start=w.plot.mapFromScene(w.plot.getViewBox().mapViewToScene(QPointF(3,3)))
            end=w.plot.mapFromScene(w.plot.getViewBox().mapViewToScene(QPointF(-3,-2)))
            QTest.mousePress(w.plot.viewport(),Qt.MouseButton.LeftButton,pos=start)
            QTest.mouseMove(w.plot.viewport(),end,120)
            QTest.mouseRelease(w.plot.viewport(),Qt.MouseButton.LeftButton,pos=end);APP.processEvents()
            self.assertEqual(w.object_list.count(),7)
            arrow=w._objects[-1][1]
            self.assertEqual(arrow.childItems()[0].pen().color().name(),"#ff00ff")
            self.assertGreater(arrow.childItems()[1].polygon().count(),2)
            with tempfile.TemporaryDirectory() as temp:
                output=Path(temp)/'draw.svg';export_plot_widget(w.plot,str(output),vector=True,width=1200)
                svg=output.read_text(encoding='utf-8')
                self.assertIn('<svg',svg);self.assertIn('Renamed text',svg)
                png=Path(temp)/'draw.png';export_plot_widget(w.plot,str(png),vector=False,width=900)
                self.assertEqual(png.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
            w.object_list.setCurrentRow(0);QTest.mouseClick(buttons["Delete"],Qt.MouseButton.LeftButton)
            self.assertEqual(w.object_list.count(),6)
        finally:w.close()

class AppTabGatingTests(unittest.TestCase):
    def test_shared_import_unlocks_only_matching_analysis_page(self):
        w=MainWindow();w.resize(1400,850);w.show();APP.processEvents()
        try:
            self.assertTrue(w.tabs.isTabEnabled(2));self.assertFalse(w.tabs.isTabEnabled(3))
            w.data_tab.cb_mode.setCurrentIndex(2)
            regression_path=str(Path('Demo Data')/'Regression_Demo.xlsx')
            with patch('app.ui.data_tab.QFileDialog.getOpenFileName',return_value=(regression_path,'Excel')):w.data_tab.on_load()
            APP.processEvents()
            self.assertTrue(w.tabs.isTabEnabled(3));self.assertTrue(w.quant_tab.pages.isTabEnabled(0))
            self.assertFalse(w.quant_tab.pages.isTabEnabled(1));self.assertIn('OLS visualization',w.quant_tab.regression.status.text())
            w.data_tab.cb_mode.setCurrentIndex(3)
            self.assertFalse(w.tabs.isTabEnabled(3))
            sem_path=str(Path('Demo Data')/'SEM_Path_Estimates_Demo.xlsx')
            with patch('app.ui.data_tab.QFileDialog.getOpenFileName',return_value=(sem_path,'Excel')):w.data_tab.on_load()
            APP.processEvents()
            self.assertTrue(w.tabs.isTabEnabled(3));self.assertTrue(w.quant_tab.pages.isTabEnabled(1))
            self.assertFalse(w.quant_tab.pages.isTabEnabled(0));self.assertIn('path diagram',w.quant_tab.cbsem.status.text().lower())
            w.data_tab.cb_mode.setCurrentIndex(4)
            self.assertFalse(w.tabs.isTabEnabled(3))
            with patch('app.ui.data_tab.QFileDialog.getOpenFileName',return_value=(sem_path,'Excel')):w.data_tab.on_load()
            APP.processEvents()
            self.assertTrue(w.tabs.isTabEnabled(3));self.assertTrue(w.quant_tab.pages.isTabEnabled(2))
            self.assertFalse(w.quant_tab.pages.isTabEnabled(1));self.assertIn('path diagram',w.quant_tab.plssem.status.text().lower())
        finally:w.close()

    def test_visual_reference_lines_legend_and_compact_axis_controls(self):
        w=MainWindow();w.resize(1100,780);w.show();APP.processEvents()
        try:
            v=w.visual_tab
            d=w.state.data;d.method='DEMATEL';d.labels,d.matrix=load_total_influence_matrix(Path('Demo Data')/'DEMATEL_Demo.xlsx')
            d.dematel_table=compute_dematel_from_total(d.matrix,d.labels);w.state.emit_changed();APP.processEvents()
            v.custom_lines=[("h",0.0,"zero","#ff00ff")]
            def accept_line_dialog():
                dialog=APP.activeModalWidget();table=dialog.findChild(QTableWidget);table.setCurrentCell(0,0)
                next(b for b in dialog.findChildren(QPushButton) if b.text()=="Delete selected line").click()
                dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            QTimer.singleShot(0,accept_line_dialog);v._manage_custom_lines();self.assertEqual(v.custom_lines,[])
            self.assertFalse(v.chk_show_legend.isChecked());self.assertIsNone(v._legend)
            v.chk_show_legend.setChecked(True);APP.processEvents()
            self.assertIsNotNone(v._legend)
            # Existing default entries appear in the manager and can be renamed,
            # removed or recolored without converting them into unrelated items.
            def edit_defaults_and_add():
                dialog=APP.activeModalWidget();table=dialog.findChild(QTableWidget)
                self.assertGreaterEqual(table.rowCount(),3)
                table.setItem(0,2,QTableWidgetItem("Drivers"))
                next(b for b in dialog.findChildren(QPushButton) if b.text()=="Add legend item").click()
                row=table.rowCount()-1
                for col,value in enumerate(("","Diamond","External note","#ff0000")):table.setItem(row,col,QTableWidgetItem(value))
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
            self.assertLessEqual(v.settings_tabs.width(),320)
            self.assertEqual(v.settings_tabs.widget(0).horizontalScrollBar().maximum(),0)
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
            self.assertLessEqual(v.settings_tabs.width(),320)
            scroll=v.settings_tabs.widget(0)
            self.assertEqual(scroll.horizontalScrollBar().maximum(),0)
            if v.tbl_seg.rowCount():
                v.tbl_seg.setItem(0,4,QTableWidgetItem("#ff0000"));APP.processEvents()
                self.assertEqual(v._bin_styles[0]["color"],"#ff0000")
            d.method='Ranking';d.ranking_labels,d.ranking_columns,d.ranking_values=load_ranking_results(Path('Demo Data')/'Ranking_Demo.xlsx');w.state.emit_changed();APP.processEvents()
            for index in range(v.cb_chart.count()):v.cb_chart.setCurrentIndex(index);APP.processEvents()
            self.assertTrue(w.tabs.isTabEnabled(1))
        finally:w.close()
