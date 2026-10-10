from PySide6.QtWidgets import QMainWindow, QTabWidget
from app.ui.data_tab import DataTab
from app.ui.visual_tab import VisualTab
from app.core.model import AppState

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MCDM Results Visualizer")

        self.state = AppState()

        self.tabs = QTabWidget()
        self.data_tab = DataTab(self.state)
        self.visual_tab = VisualTab(self.state)

        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.visual_tab, "Visual")
        self.setCentralWidget(self.tabs)

        self.state.changed.connect(self.visual_tab.refresh_from_state)
