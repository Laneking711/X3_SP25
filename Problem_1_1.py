"""
ChatGpt and Ex2 P2 code were used to help produce this code
RLC_GUI.py  – Transient response of a driven RLC circuit
---------------------------------------------------------------------------
Created 20‑Apr‑2025

This file fulfils the specification shown in the prompt:

1.  Display a picture of the series‑RLC circuit together with editable
    line‑edit widgets for **R, L, C** and the sinusoidal source parameters
    *(magnitude A, frequency ω, phase φ)*.
    Defaults: R = 10 Ω, L = 20 H, C = 0.05 F, v(t)=20 sin(20 t + 0).

2.  Simulate the transient response (current in the inductor i₁, current
    through the resistor/capacitor i₂, and capacitor voltage v_C) after the
    source is switched on, using `scipy.integrate.solve_ivp`.

3.  Plot i₁(t), i₂(t) and v_C(t) in a Matplotlib canvas embedded in the GUI,
    complete with the interactive navigation toolbar.
"""

# ---------------------------------------------------------------------------
# region imports
# ---------------------------------------------------------------------------
import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QGroupBox,
                             QGridLayout)
from PyQt5.QtGui import QPixmap
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from scipy.integrate import solve_ivp


# ---------------------------------------------------------------------------
# region numerical model
# ---------------------------------------------------------------------------
def simulate_rlc(R: float, L: float, C: float,
                 A: float, w: float, p: float,
                 t_end: float = 10.0, pts: int = 500):
    """
    Simulate the *transient* response of the driven series RLC circuit.

    Differential model
    ------------------
    Using mesh‑currents **i₁** (through L) and **i₂** (through C, returning
    through R), the state vector is X = [i₁, i₂]ᵀ.

    v(t) = A sin(ω t + φ)

    i₁̇ = ( v(t) – R·(i₁ – i₂) ) / L
    i₂̇ = i₁̇ – (1 / R C)·i₂

    Parameters
    ----------
    R, L, C : float
        Resistance (Ω), inductance (H) and capacitance (F).
    A, w, p : float
        Source amplitude [V], angular frequency [rad s⁻¹] and phase [rad].
    t_end : float, optional
        End time for the simulation [s].
    pts : int, optional
        Number of evaluation points.

    Returns
    -------
    t   : ndarray
        Time vector.
    i1  : ndarray
        Inductor current i₁(t) [A].
    i2  : ndarray
        Resistor/capacitor mesh current i₂(t) [A].
    vC  : ndarray
        Capacitor voltage v_C(t) [V].
    """
    def ode_system(t, X):
        i1, i2 = X
        vt = A * np.sin(w * t + p)
        i1dot = (vt - R * (i1 - i2)) / L
        i2dot = i1dot - (1.0 / (R * C)) * i2
        return [i1dot, i2dot]

    t_span = (0.0, t_end)
    t_eval = np.linspace(*t_span, pts)
    sol = solve_ivp(ode_system, t_span, [0.0, 0.0], t_eval=t_eval)

    t  = sol.t
    i1 = sol.y[0]
    i2 = sol.y[1]
    vC = (i2 - i1) * R
    return t, i1, i2, vC


# ---------------------------------------------------------------------------
# region GUI
# ---------------------------------------------------------------------------
class RLCGui(QWidget):
    """
    PyQt5 GUI that realises the three requirements of the prompt.

    Widgets
    -------
    * **QGroupBox “Circuit Inputs”** – six `QLineEdit`s for R, L, C, A, ω, φ.
    * Circuit diagram (static `QPixmap`) alongside a **Simulate** button.
    * Matplotlib `FigureCanvasQTAgg` + `NavigationToolbar2QT` for plotting.

    Workflow
    --------
    1.  User edits values and presses *Simulate*.
    2.  `run_simulation()` reads text, calls `simulate_rlc()`.
    3.  The three waveforms are plotted with dual y‑axes:
        currents on `ax1`, capacitor voltage on `ax2`.
    """
    # ------------------------------------------------------------------
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RLC Circuit Simulator")
        self._init_ui()

    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        """Build all widgets and layouts; connect Simulate button."""
        layout = QVBoxLayout()

        # ----- input group -------------------------------------------------
        input_box = QGroupBox("Circuit Inputs")
        grid = QGridLayout()
        self.inputs = {}

        labels   = ["R (Ohms)", "L (H)", "C (F)",
                    "Amplitude (V)", "Frequency (rad/s)", "Phase (rad)"]
        defaults = [10, 20, 0.05, 20, 20, 0]

        for i, (label, default) in enumerate(zip(labels, defaults)):
            grid.addWidget(QLabel(label), i, 0)
            line_edit = QLineEdit(str(default))
            self.inputs[label] = line_edit
            grid.addWidget(line_edit, i, 1)

        input_box.setLayout(grid)
        layout.addWidget(input_box)

        # ----- circuit image + simulate button -----------------------------
        image_layout = QHBoxLayout()
        pixmap = QPixmap("Circuit1.png")   # local schematic
        image_label = QLabel(); image_label.setPixmap(pixmap)
        image_layout.addWidget(image_label)

        self.sim_btn = QPushButton("Simulate")
        self.sim_btn.clicked.connect(self.run_simulation)
        image_layout.addWidget(self.sim_btn)
        layout.addLayout(image_layout)

        # ----- matplotlib canvas & toolbar ---------------------------------
        self.canvas = FigureCanvasQTAgg(Figure(figsize=(8, 5)))
        self.ax1 = self.canvas.figure.add_subplot(111)
        self.ax2 = self.ax1.twinx()
        self.toolbar = NavigationToolbar2QT(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    # ------------------------------------------------------------------
    def run_simulation(self) -> None:
        """
        Retrieve user inputs, call the ODE solver, and update the plot.

        Errors in conversion raise `ValueError`, handled with a simple
        console message (GUI remains responsive).
        """
        try:
            R = float(self.inputs["R (Ohms)"].text())
            L = float(self.inputs["L (H)"].text())
            C = float(self.inputs["C (F)"].text())
            A = float(self.inputs["Amplitude (V)"].text())
            w = float(self.inputs["Frequency (rad/s)"].text())
            p = float(self.inputs["Phase (rad)"].text())

            t, i1, i2, vC = simulate_rlc(R, L, C, A, w, p)

            # ----- redraw plot -------------------------------------------
            self.ax1.clear(); self.ax2.clear()

            self.ax1.plot(t, i1, label='i₁(t)', linestyle='-')
            self.ax1.plot(t, i2, label='i₂(t)', linestyle='--')
            self.ax2.plot(t, vC, label='v_C(t)', linestyle=':')

            self.ax1.set_xlabel("Time (s)")
            self.ax1.set_ylabel("Current (A)")
            self.ax2.set_ylabel("Capacitor Voltage (V)")
            self.ax1.legend(loc='upper right')
            self.ax2.legend(loc='lower right')

            self.canvas.draw()

        except ValueError:
            print("Invalid input – please enter numeric values.")


# ---------------------------------------------------------------------------
# region main
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = RLCGui()
    win.show()
    sys.exit(app.exec_())
