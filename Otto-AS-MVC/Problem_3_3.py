# Problem_3_3.py  – Air‑standard Diesel‑cycle MVC

from Air import *
from Problem_3_2 import ottoCycleView          # reuse the shared View
from matplotlib import pyplot as plt
from PyQt5 import QtWidgets as qtw
import numpy as np
from copy import deepcopy as dc


# ─────────────────────────────────────────────────────────────────────────────
#  MODEL
# ─────────────────────────────────────────────────────────────────────────────
class dieselCycleModel:
    """
    Pure‑Python **air‑standard Diesel‑cycle** model.

    Processes (per mole of ideal‑gas air)
    -------------------------------------
    1 → 2  Isentropic compression to volume V₂ = V₁ / r
    2 → 3  *Constant‑pressure* heat addition until `T_high` (P₂ = P₃)
    3 → 4  Isentropic expansion back to V₁
    4 → 1  Constant‑volume heat rejection

    Inputs
    ------
    p_initial , t_initial , v_cylinder
        State‑1 conditions.
    compression_ratio  r
        V₁ / V₂.
    t_high
        **Actual temperature T₃** at the end of heat addition
        (prompt revision – earlier versions treated this as a ratio).

    Outputs (molar)
    ---------------
    State1 … State4 : stateProps
    W_Compression , W_Power , W_Cycle
    Q_In , Q_Out
    Eff            – cycle thermal efficiency [%].
    r_c            – cut‑off ratio V₃ / V₂.
    upperCurve , lowerCurve : StateDataForPlotting
    """

    def __init__(self,
                 p_initial: float = 1.01325e5,
                 v_cylinder: float = 1.0,
                 t_initial: float = 300.0,
                 t_high:    float = 1500.0,
                 compression_ratio: float = 18.0,
                 name: str  = 'Air‑Standard Diesel Cycle'):
        """
        Initialise but do **NOT** solve the cycle yet.

        Parameters match the Otto model except `compression_ratio`
        replaces `ratio`, and `t_high` is now a **real temperature**.
        """
        self.units  = units()
        self.air    = air()
        self.name   = name

        # user inputs
        self.p_initial = p_initial
        self.t_initial = t_initial
        self.v_cyl     = v_cylinder
        self.t_high    = t_high
        self.r         = compression_ratio

        # results (place‑holders)
        self.State1 = self.State2 = self.State3 = self.State4 = None
        self.r_c    = None                          # V₃ / V₂
        self.W_Power = self.W_Compression = self.W_Cycle = 0.0
        self.Q_In = self.Q_Out = self.Eff = 0.0

        # plotting data
        self.lowerCurve = StateDataForPlotting()
        self.upperCurve = StateDataForPlotting()

    # ------------------------------------------------------------------
    def solve(self) -> None:
        """
        Compute all state points and energy terms (molar basis),
        then build the plotting curves.
        """
        a = self.air

        # --- state 1 : BDC ----------------------------------------------
        self.State1 = a.set(P=self.p_initial, T=self.t_initial, name='1')

        # --- state 2 : isentropic compression ---------------------------
        self.State2 = a.set(v=self.State1.v / self.r,
                            s=self.State1.s, name='2')

        # --- state 3 : constant‑P heat addition to T_high ---------------
        self.State3 = a.set(P=self.State2.P, T=self.t_high, name='3')
        self.r_c    = self.State3.v / self.State2.v    # cut‑off ratio

        # --- state 4 : isentropic expansion back to V₁ ------------------
        self.State4 = a.set(v=self.State1.v, s=self.State3.s, name='4')

        # --- extensive factors -----------------------------------------
        a.n = self.v_cyl / a.State.v
        a.m = a.n * a.MW

        # --- energy balances (molar) -----------------------------------
        self.W_Compression = self.State2.u - self.State1.u
        W_23 = (self.State3.h - self.State2.h) - (self.State3.u - self.State2.u)  # const‑P work
        W_34 = self.State3.u - self.State4.u                                       # isentropic work
        self.W_Power       = W_23 + W_34
        self.W_Cycle       = self.W_Power + self.W_Compression
        self.Q_In          = self.State3.h - self.State2.h
        self.Q_Out         = self.State4.u - self.State1.u
        self.Eff           = 100.0 * (1.0 - self.Q_Out / self.Q_In)

        self._build_plot_data()

    # ------------------------------------------------------------------
    def _build_plot_data(self) -> None:
        """
        Create smooth StateDataForPlotting curves for GUI plotting:
        lowerCurve = 1→2 ; upperCurve = 2→3→4→1.
        """
        self.lowerCurve.clear(); self.upperCurve.clear()
        a = air()

        # 1→2  isentropic
        for v in np.linspace(self.State1.v, self.State2.v, 30):
            st = a.set(v=v, s=self.State1.s)
            self.lowerCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

        # 2→3  constant‑pressure
        for v in np.linspace(self.State2.v, self.State3.v, 30):
            st = a.set(P=self.State2.P, v=v)
            self.upperCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

        # 3→4  isentropic
        for v in np.linspace(self.State3.v, self.State4.v, 30):
            st = a.set(v=v, s=self.State3.s)
            self.upperCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

        # 4→1  constant‑volume
        for T in np.linspace(self.State4.T, self.State1.T, 30):
            st = a.set(T=T, v=self.State4.v)
            self.upperCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

    # ------------------------------------------------------------------
    def getSI(self) -> bool:
        """Return `True` if current units are SI; else English."""
        return self.units.SI


# ─────────────────────────────────────────────────────────────────────────────
#  CONTROLLER
# ─────────────────────────────────────────────────────────────────────────────
class dieselCycleController:
    """
    MVC controller for the Diesel cycle.

    • Re‑uses `ottoCycleView` so plotting & widget handling are identical.
    • `calc()` reads GUI values, converts to floats, calls `set()`.
    • `set()` updates the model, executes `solve()`, then refreshes view.
    """

    def __init__(self, model: dieselCycleModel = None, ax=None):
        self.model = dieselCycleModel() if model is None else model
        self.view  = ottoCycleView()
        self.view.ax = ax

    # ---------- widget plumbing --------------------------------------
    def setWidgets(self, w) -> None:
        """
        Store widget references and relabel “T High” to highlight that it
        is a **temperature input** (not a ratio) for the Diesel cycle.
        """
        [self.view.lbl_THigh, self.view.lbl_TLow, self.view.lbl_P0, self.view.lbl_V0, self.view.lbl_CR,
         self.view.le_THigh, self.view.le_TLow, self.view.le_P0, self.view.le_V0, self.view.le_CR,
         self.view.le_T1, self.view.le_T2, self.view.le_T3, self.view.le_T4,
         self.view.lbl_T1Units, self.view.lbl_T2Units, self.view.lbl_T3Units, self.view.lbl_T4Units,
         self.view.le_PowerStroke, self.view.le_CompressionStroke, self.view.le_HeatAdded, self.view.le_Efficiency,
         self.view.lbl_PowerStrokeUnits, self.view.lbl_CompressionStrokeUnits, self.view.lbl_HeatInUnits,
         self.view.rdo_Metric, self.view.cmb_Abcissa, self.view.cmb_Ordinate,
         self.view.chk_LogAbcissa, self.view.chk_LogOrdinate, self.view.ax, self.view.canvas] = w

        # update static label
        self.view.lbl_THigh.setText(f"T High ({self.view.lbl_T1Units.text()})")

    # ---------- GUI slot ---------------------------------------------
    def calc(self) -> None:
        """
        Slot connected to the **Calculate** button in Cycle_App.
        """
        m = self.view
        self.set(T_0=float(m.le_TLow.text()),
                 P_0=float(m.le_P0.text()),
                 V_0=float(m.le_V0.text()),
                 T_High=float(m.le_THigh.text()),          # real temperature
                 compression_ratio=float(m.le_CR.text()),
                 SI=m.rdo_Metric.isChecked())

    # ---------- public API -------------------------------------------
    def set(self, T_0=300.0, P_0=1.0, V_0=0.001,
            T_High=1500.0, compression_ratio=18.0,
            SI: bool = True) -> None:
        """
        Update inputs, solve the Diesel model, and refresh the view.
        """
        U = self.model.units; U.set(SI=SI)
        m = self.model
        m.t_initial = T_0 if SI else T_0 / U.CF_T
        m.p_initial = P_0 if SI else P_0 / U.CF_P
        m.v_cyl     = V_0 if SI else V_0 / U.CF_V
        m.t_high    = T_High if SI else T_High / U.CF_T
        m.r         = compression_ratio
        m.solve()
        self.updateView()

    # helper ----------------------------------------------------------
    def updateView(self) -> None: self.view.updateView(cycle=self.model)

    def plot_cycle_XY(self, *a, **kw): self.view.plot_cycle_XY(self.model, *a, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI smoke test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    app = qtw.QApplication(sys.argv)
    dc = dieselCycleController()
    # English units demo: 540 R → 2700 R, r = 18
    dc.set(T_0=540.0, P_0=1.0, V_0=0.02,
           T_High=2700.0, compression_ratio=18.0, SI=False)
    dc.plot_cycle_XY(X="v", Y="P", total=True)
