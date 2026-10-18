from PySide6.QtWidgets import QMainWindow, QTabWidget
from app.ui.data_tab import DataTab
from app.ui.visual_tab import VisualTab
from app.ui.xy_tab import XYPlotTab, QuantitativeTab
from app.core.model import AppState

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCDMVisualStudio")

        self.state = AppState()

        self.tabs = QTabWidget()
        self.data_tab = DataTab(self.state)
        self.visual_tab = VisualTab(self.state)
        self.xy_tab = XYPlotTab()
        self.quant_tab = QuantitativeTab(self.state)

        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.visual_tab, "Visual")
        self.tabs.addTab(self.xy_tab, "XY drawing")
        self.tabs.addTab(self.quant_tab, "Quantitative charts")
        self.setCentralWidget(self.tabs)

        self.state.changed.connect(self.visual_tab.refresh_from_state)
        self.state.changed.connect(self.quant_tab.refresh_from_state)
        self.state.changed.connect(self._update_tab_access)
        self._update_tab_access()

    def _update_tab_access(self):
        data=self.state.data
        is_mcdm=data.method in ("DEMATEL","Ranking")
        is_quant=data.method in ("Regression","CB-SEM","PLS-SEM") and data.quant_type==data.method and data.quant_frame is not None
        self.tabs.setTabEnabled(1,is_mcdm)
        self.tabs.setTabEnabled(3,is_quant)
