# Cycle_App.py – robust GUI for Otto & Diesel cycles
#ChatGPT was used to help produce this code
import sys
from PyQt5 import QtWidgets as qtw
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from Problem_3_2 import ottoCycleController
from Problem_3_3  import dieselCycleController
from Otto_GUI import Ui_Form


class MainWindow(qtw.QWidget, Ui_Form):
    """
    
    Top‑level Qt window hosting the **Otto / Diesel Cycle Calculator**.

    Features
    --------
    • Two exclusive radio‑button groups:
        * Cycle  : `rdo_Otto`, `rdo_Diesel`
        * Units  : `rdo_Metric`, `rdo_English`
      (Only one button per group can be selected at any time.)

    • Single shared `ottoCycleView` reused by both controllers to avoid
      duplicating widget logic.

    • Matplotlib canvas embedded in the “Plot” `QGroupBox`.

    Crash guards
    ------------
    * `_setUnits()` early‑exits until all widgets are wired.
    * Controller swap (`_switchController`) disconnects & reconnects the
      **Calculate** button to the new controller before any calculation
      occurs, preventing stale signal emissions.
    """

    def __init__(self):
        """Build GUI, create controllers, and wire all signals."""
        super().__init__()
        self.setupUi(self)

        # ── Ensure four radio buttons exist even if UI file lacked them ─
        def add_radio(name: str, text: str, row: int) -> qtw.QRadioButton:
            rb = qtw.QRadioButton(text); setattr(self, name, rb)
            self.gridLayout.addWidget(rb, row, 4, 1, 1)
            return rb

        if not hasattr(self, "rdo_Otto"):    self.rdo_Otto    = add_radio("rdo_Otto",    "Otto",    0)
        if not hasattr(self, "rdo_Diesel"):  self.rdo_Diesel  = add_radio("rdo_Diesel",  "Diesel",  1)
        if not hasattr(self, "rdo_Metric"):  self.rdo_Metric  = add_radio("rdo_Metric",  "Metric",  2)
        if not hasattr(self, "rdo_English"): self.rdo_English = add_radio("rdo_English", "English", 3)

        # default selections
        self.rdo_Otto.setChecked(True)
        self.rdo_English.setChecked(True)

        # ── Exclusive button groups so only one per set is active ───────
        self.grpCycle = qtw.QButtonGroup(self);  self.grpCycle.setExclusive(True)
        self.grpCycle.addButton(self.rdo_Otto);  self.grpCycle.addButton(self.rdo_Diesel)

        self.grpUnits = qtw.QButtonGroup(self);  self.grpUnits.setExclusive(True)
        self.grpUnits.addButton(self.rdo_Metric); self.grpUnits.addButton(self.rdo_English)

        # ── Matplotlib canvas inside Plot group box ─────────────────────
        self.fig = Figure(figsize=(5, 4), tight_layout=True)
        self.ax  = self.fig.add_subplot()
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.grid_Plot.addWidget(self.canvas, 2, 0, 1, 5)

        # ── Instantiate both controllers; default to Otto ──────────────
        self.otto   = ottoCycleController()
        self.diesel = dieselCycleController()
        self.controller = self.otto
        self.controller.setWidgets(self._widgets())

        # ── Connect signals *after* widgets are wired to avoid race ────
        self.btn_Calculate.clicked.connect(self.controller.calc)
        self.rdo_Otto.toggled.connect(self._switchController)
        self.rdo_Diesel.toggled.connect(self._switchController)
        self.rdo_Metric.toggled.connect(self._setUnits)
        self.rdo_English.toggled.connect(self._setUnits)

        self.show()

    # ------------------------------------------------------------------
    def _widgets(self) -> list:
        """
        Return widgets in the exact order expected by
        `ottoCycleController.setWidgets()` / `dieselCycleController.setWidgets()`.
        """
        return [self.lbl_THigh, self.lbl_TLow, self.lbl_P0, self.lbl_V0, self.lbl_CR,
                self.le_THigh, self.le_TLow, self.le_P0, self.le_V0, self.le_CR,
                self.le_T1, self.le_T2, self.le_T3, self.le_T4,
                self.lbl_T1Units, self.lbl_T2Units, self.lbl_T3Units, self.lbl_T4Units,
                self.le_PowerStroke, self.le_CompressionStroke, self.le_HeatAdded, self.le_Efficiency,
                self.lbl_PowerStrokeUnits, self.lbl_CompressionStrokeUnits, self.lbl_HeatInUnits,
                self.rdo_Metric, self.cmb_Abcissa, self.cmb_Ordinate,
                self.chk_LogAbcissa, self.chk_LogOrdinate,
                self.ax, self.canvas]

    # ------------------------------------------------------------------
    def _switchController(self) -> None:
        """
        Swap between Otto and Diesel controllers when cycle radio buttons
        toggle.  Re‑wires the **Calculate** button to the new controller
        and immediately updates unit labels.
        """
        self.controller = self.otto if self.rdo_Otto.isChecked() else self.diesel
        self.controller.setWidgets(self._widgets())

        # reconnect Calculate button
        try:
            self.btn_Calculate.clicked.disconnect()
        except TypeError:   # no connections yet
            pass
        self.btn_Calculate.clicked.connect(self.controller.calc)

        self._setUnits()    # refresh labels instantly

    # ------------------------------------------------------------------
    def _setUnits(self) -> None:
        """
        Update unit labels (°C vs °F etc.) without forcing a calculation.

        Guard clause skips execution until widgets are wired – prevents
        attribute errors during startup.
        """
        if not hasattr(self.controller.view, "lbl_P0"):
            return
        self.controller.model.units.SI = self.rdo_Metric.isChecked()
        self.controller.view.updateDisplayWidgets(Model=self.controller.model)

    # ------------------------------------------------------------------
    def closeEvent(self, event):
        """
        Clear the Matplotlib figure to avoid backend segmentation faults
        on some platforms, then pass the close event to Qt base‑class.
        """
        self.fig.clear()
        super().closeEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
#  Stand‑alone launcher
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    mw = MainWindow()
    mw.setWindowTitle("Otto / Diesel Cycle Calculator")
    mw.resize(1200, 900)
    sys.exit(app.exec())
