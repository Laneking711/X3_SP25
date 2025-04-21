# Problem3.py  – Air‑standard Otto‑cycle MVC
# ---------------------------------------------------------------------------
# 20‑Apr‑2025
# This module is imported by:
#   • Problem_3_1.py  – the Qt front‑end that lets users pick “Otto” or “Diesel”
#   • Problem_3_3.py     – re‑uses ottoCycleView for consistency
# and can also be run stand‑alone for a quick CLI smoke test.
# ---------------------------------------------------------------------------

from Air import *
from matplotlib import pyplot as plt
from PyQt5 import QtWidgets as qtw
import numpy as np
from copy import deepcopy as dc
import sys


# ─────────────────────────────────────────────────────────────────────────────
#  MODEL
# ─────────────────────────────────────────────────────────────────────────────
class ottoCycleModel:
    """
    Pure‑Python **air‑standard Otto‑cycle** model.

    The cycle consists of four idealized processes on one mole of air
    (ratio‑of‑specific‑heats varies with T via `Air.py` correlations):

        1 → 2  Isentropic compression (V₁ → V₂ = V₁ / CR)
        2 → 3  Constant‑volume heat addition (T₂ → T₃ = `T_high`)
        3 → 4  Isentropic expansion (V₃ → V₄ = V₁)
        4 → 1  Constant‑volume heat rejection (T₄ → T₁)

    After `solve()` the object provides:

    Attributes
    ----------
    State1 … State4 : stateProps
        Thermodynamic states (molar basis).
    W_Compression , W_Power , W_Cycle : float
        Work of compression, expansion, and net (kJ / kmol).
    Q_In , Q_Out : float
        Heat supplied / rejected (kJ / kmol).
    Eff : float
        Cycle thermal efficiency in percent.
    upperCurve , lowerCurve : StateDataForPlotting
        30‑point paths for smooth P‑v / T‑s plotting.
    """

    def __init__(self,
                 p_initial: float = 1.01325e5,
                 v_cylinder: float = 1.0,
                 t_initial: float = 300.0,
                 t_high:    float = 1500.0,
                 ratio:     float = 8.0,
                 name: str  = 'Air‑Standard Otto Cycle'):
        """
        Initialise the model with input parameters but **do not solve** yet.

        All arguments are accepted as SI; the controller converts English
        inputs before calling `solve()`.

        Parameters
        ----------
        p_initial : float
            Initial cylinder pressure P₁ [Pa].
        v_cylinder : float
            Cylinder volume at BDC, V₁ [m³].
        t_initial : float
            Initial temperature T₁ [K].
        t_high : float
            Peak cycle temperature T₃ [K] reached at 2 → 3.
        ratio : float
            Compression ratio CR = V₁ / V₂.
        name : str
            Name used on the plot and summaries.
        """
        self.units = units()
        self.air   = air()
        self.name  = name

        # user inputs
        self.p_initial = p_initial
        self.t_initial = t_initial
        self.t_high    = t_high
        self.v_cyl     = v_cylinder
        self.Ratio     = ratio

        # outputs (placeholders)
        self.State1 = self.State2 = self.State3 = self.State4 = None
        self.W_Power = self.W_Compression = self.W_Cycle = 0.0
        self.Q_In = self.Q_Out = self.Eff = 0.0

        # plotting data containers
        self.upperCurve = StateDataForPlotting()
        self.lowerCurve = StateDataForPlotting()

    # ------------------------------------------------------------------
    def solve(self) -> None:
        """
        Calculate all four states and the molar energy terms.

        Calls the helper `_build_plot_data()` to fill curve objects for
        subsequent plotting.
        """
        a = self.air

        # --- state 1 : BDC -------------------------------------------------
        self.State1 = a.set(P=self.p_initial, T=self.t_initial, name='1')

        # --- state 2 : isentropic compression ------------------------------
        self.State2 = a.set(v=self.State1.v / self.Ratio,
                            s=self.State1.s, name='2')

        # --- state 3 : constant‑volume heat addition -----------------------
        self.State3 = a.set(T=self.t_high, v=self.State2.v, name='3')

        # --- state 4 : isentropic expansion back to V₁ ---------------------
        self.State4 = a.set(v=self.State1.v, s=self.State3.s, name='4')

        # --- extensive scaling factors ------------------------------------
        a.n = self.v_cyl / a.State.v   # kmol
        a.m = a.n * a.MW               # kg

        # --- molar energy balances ----------------------------------------
        self.W_Compression = self.State2.u - self.State1.u
        self.W_Power       = self.State3.u - self.State4.u
        self.W_Cycle       = self.W_Power - self.W_Compression
        self.Q_In          = self.State3.u - self.State2.u
        self.Q_Out         = self.State4.u - self.State1.u
        self.Eff           = 100.0 * self.W_Cycle / self.Q_In

        self._build_plot_data()

    # ------------------------------------------------------------------
    def _build_plot_data(self) -> None:
        """
        Generate smooth P‑v/T‑s/etc. paths for plotting:

        * lowerCurve : 1 → 2 (isentropic compression)
        * upperCurve : 2 → 3 (const‑V) + 3 → 4 (isentropic) + 4 → 1 (const‑V)
        """
        self.upperCurve.clear(); self.lowerCurve.clear()
        a = air()   # scratch working‑fluid

        # 1 → 2
        for v in np.linspace(self.State1.v, self.State2.v, 30):
            st = a.set(v=v, s=self.State1.s)
            self.lowerCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

        # 2 → 3
        for T in np.linspace(self.State2.T, self.State3.T, 30):
            st = a.set(T=T, v=self.State2.v)
            self.upperCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

        # 3 → 4
        for v in np.linspace(self.State3.v, self.State4.v, 30):
            st = a.set(v=v, s=self.State3.s)
            self.upperCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

        # 4 → 1
        for T in np.linspace(self.State4.T, self.State1.T, 30):
            st = a.set(T=T, v=self.State4.v)
            self.upperCurve.add((st.T, st.P, st.u, st.h, st.s, st.v))

    # ------------------------------------------------------------------
    def getSI(self) -> bool:
        """Return `True` if units are currently SI; `False` if English."""
        return self.units.SI


# ─────────────────────────────────────────────────────────────────────────────
#  CONTROLLER
# ─────────────────────────────────────────────────────────────────────────────
class ottoCycleController:
    """
    Glue between Qt widgets (`ottoCycleView`) and the numerical model
    (`ottoCycleModel`).  Also usable from the command line.
    """

    def __init__(self, model: ottoCycleModel = None, ax=None):
        self.model = ottoCycleModel() if model is None else model
        self.view  = ottoCycleView()
        self.view.ax = ax

    # ---------- public GUI slots --------------------------------------
    def calc(self) -> None:
        """
        Slot for **Calculate** button – reads line‑edits, converts to
        floats, then delegates to `set()`.
        """
        m = self.view
        self.set(T_0=float(m.le_TLow.text()),
                 P_0=float(m.le_P0.text()),
                 V_0=float(m.le_V0.text()),
                 T_High=float(m.le_THigh.text()),
                 ratio=float(m.le_CR.text()),
                 SI=m.rdo_Metric.isChecked())

    # ---------- public API --------------------------------------------
    def set(self,
            T_0: float = 300.0,
            P_0: float = 1.0,
            V_0: float = 0.001,
            T_High: float = 1500.0,
            ratio: float = 8.0,
            SI: bool = True) -> None:
        """
        Update inputs, solve, and refresh view.

        Allows scripted/unit‑test use without a GUI.
        """
        U = self.model.units
        U.set(SI=SI)
        mo = self.model
        mo.t_initial = T_0 if SI else T_0 / U.CF_T
        mo.p_initial = P_0 if SI else P_0 / U.CF_P
        mo.v_cyl     = V_0 if SI else V_0 / U.CF_V
        mo.t_high    = T_High if SI else T_High / U.CF_T
        mo.Ratio     = ratio
        mo.solve()
        self.updateView()

    # ---------- widget plumbing ---------------------------------------
    def setWidgets(self, w) -> None:
        """
        Store references to all GUI widgets in the view.

        The order is dictated by `Problem_3_1.py` and mirrors the auto‑
        generated *Otto_GUI.ui* layout.
        """
        [self.view.lbl_THigh, self.view.lbl_TLow, self.view.lbl_P0, self.view.lbl_V0, self.view.lbl_CR,
         self.view.le_THigh, self.view.le_TLow, self.view.le_P0, self.view.le_V0, self.view.le_CR,
         self.view.le_T1, self.view.le_T2, self.view.le_T3, self.view.le_T4,
         self.view.lbl_T1Units, self.view.lbl_T2Units, self.view.lbl_T3Units, self.view.lbl_T4Units,
         self.view.le_PowerStroke, self.view.le_CompressionStroke, self.view.le_HeatAdded, self.view.le_Efficiency,
         self.view.lbl_PowerStrokeUnits, self.view.lbl_CompressionStrokeUnits, self.view.lbl_HeatInUnits,
         self.view.rdo_Metric, self.view.cmb_Abcissa, self.view.cmb_Ordinate,
         self.view.chk_LogAbcissa, self.view.chk_LogOrdinate, self.view.ax, self.view.canvas] = w

    # ---------- helper ------------------------------------------------
    def updateView(self) -> None:
        """Tell the view to redraw plot and numeric fields."""
        self.view.updateView(cycle=self.model)

    def plot_cycle_XY(self, *a, **kw) -> None:
        """CLI shortcut to view.plot_cycle_XY()."""
        self.view.plot_cycle_XY(self.model, *a, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  VIEW
# ─────────────────────────────────────────────────────────────────────────────
class ottoCycleView:
    """
    Handles all user‑visible updates:

    • Embedded Matplotlib plot
    • Numeric outputs to QLineEdit widgets
    • Unit‑label relabeling when Metric / English toggles

    Prompt‑driven safety: `updateDisplayWidgets()` returns immediately
    if the model hasn’t solved yet, preventing the crash you experienced
    when switching controllers pre‑calculation.
    """

    def __init__(self):
        # widget placeholders (populated by controller.setWidgets)
        self.lbl_THigh = qtw.QLabel(); self.lbl_TLow = qtw.QLabel()
        self.lbl_P0 = qtw.QLabel();    self.lbl_V0  = qtw.QLabel(); self.lbl_CR = qtw.QLabel()
        self.le_THigh = qtw.QLineEdit(); self.le_TLow = qtw.QLineEdit()
        self.le_P0 = qtw.QLineEdit();    self.le_V0  = qtw.QLineEdit(); self.le_CR = qtw.QLineEdit()
        self.le_T1 = qtw.QLineEdit(); self.le_T2 = qtw.QLineEdit(); self.le_T3 = qtw.QLineEdit(); self.le_T4 = qtw.QLineEdit()
        self.lbl_T1Units = qtw.QLabel(); self.lbl_T2Units = qtw.QLabel(); self.lbl_T3Units = qtw.QLabel(); self.lbl_T4Units = qtw.QLabel()
        self.le_Efficiency = qtw.QLineEdit()
        self.le_PowerStroke = qtw.QLineEdit(); self.le_CompressionStroke = qtw.QLineEdit(); self.le_HeatAdded = qtw.QLineEdit()
        self.lbl_PowerStrokeUnits = qtw.QLabel(); self.lbl_CompressionStrokeUnits = qtw.QLabel(); self.lbl_HeatInUnits = qtw.QLabel()
        self.rdo_Metric = qtw.QRadioButton()
        self.cmb_Abcissa = qtw.QComboBox(); self.cmb_Ordinate = qtw.QComboBox()
        self.chk_LogAbcissa = qtw.QCheckBox(); self.chk_LogOrdinate = qtw.QCheckBox()
        self.canvas = None; self.ax = None

    # --------------------------------------------------------------
    def updateView(self, cycle: ottoCycleModel) -> None:
        """
        Redraw plot (if ready) and update numeric QLineEdits.

        Called every time inputs change or units toggle.
        """
        # no plot until curves exist
        if not cycle.upperCurve.T or not cycle.lowerCurve.T:
            self.updateDisplayWidgets(Model=cycle)
            return

        cycle.units.SI = self.rdo_Metric.isChecked()
        self.plot_cycle_XY(cycle,
                           X=self.cmb_Abcissa.currentText(),
                           Y=self.cmb_Ordinate.currentText(),
                           logx=self.chk_LogAbcissa.isChecked(),
                           logy=self.chk_LogOrdinate.isChecked(),
                           mass=False, total=True)
        self.updateDisplayWidgets(Model=cycle)

    # --------------------------------------------------------------
    def plot_cycle_XY(self, cycle: ottoCycleModel,
                      X: str = 's', Y: str = 'T',
                      logx: bool = False, logy: bool = False,
                      mass: bool = False, total: bool = False) -> None:
        """
        Plot the cycle for any pair of thermodynamic properties.

        Parameters
        ----------
        cycle : ottoCycleModel
        X, Y  : {'P','T','u','h','s','v'}
            Properties for the abscissa / ordinate.
        logx, logy : bool
            Use logarithmic axis scale.
        mass : bool
            Convert per‑mole values to per‑kg.
        total : bool
            Convert per‑mole values to total (multiplying by `n`).
        """
        if X == Y or not cycle.upperCurve.T or not cycle.lowerCurve.T:
            return

        QT = True
        if self.ax is None:              # CLI mode
            self.ax = plt.subplot(); QT = False
        ax = self.ax; ax.clear()
        ax.set_xscale('log' if logx else 'linear')
        ax.set_yscale('log' if logy else 'linear')

        # convert & plot lower and upper branches
        X_LC = self.convertDataCol(cycle, cycle.lowerCurve.getDataCol(X), X, mass, total)
        Y_LC = self.convertDataCol(cycle, cycle.lowerCurve.getDataCol(Y), Y, mass, total)
        X_UC = self.convertDataCol(cycle, cycle.upperCurve.getDataCol(X), X, mass, total)
        Y_UC = self.convertDataCol(cycle, cycle.upperCurve.getDataCol(Y), Y, mass, total)
        ax.plot(X_LC, Y_LC, color='k'); ax.plot(X_UC, Y_UC, color='g')

        # labels & title
        cycle.units.setPlotUnits(SI=cycle.units.SI, mass=mass, total=total)
        ax.set_xlabel(cycle.lowerCurve.getAxisLabel(X, Units=cycle.units))
        ax.set_ylabel(cycle.lowerCurve.getAxisLabel(Y, Units=cycle.units))
        ax.set_title(cycle.name)
        ax.tick_params(axis='both', which='both', direction='in', top=True, right=True)

        # state markers
        for st in map(lambda s: self._conv(s, cycle, mass, total),
                      (cycle.State1, cycle.State2, cycle.State3, cycle.State4)):
            ax.plot(st.getVal(X), st.getVal(Y), marker='o',
                    markerfacecolor='w', markeredgecolor='k')

        ax.relim(); ax.autoscale_view()
        self.canvas.draw() if QT else plt.show()

    # helper
    def _conv(self, st, cycle, mass, total):
        tmp = dc(st)
        tmp.ConvertStateData(SI=cycle.getSI(), Units=cycle.units,
                             n=cycle.air.n, MW=cycle.air.MW,
                             mass=mass, total=total)
        return tmp

    # --------------------------------------------------------------
    def convertDataCol(self, cycle: ottoCycleModel,
                       data: list, colName: str = 'T',
                       mass: bool = False, total: bool = False) -> list:
        """
        Convert a list of molar‑SI values (`data`) into the currently
        selected unit system and basis.
        """
        UC = cycle.units; n = cycle.air.n; MW = cycle.air.MW
        TCF = 1 if UC.SI else UC.CF_T; PCF = 1 if UC.SI else UC.CF_P
        eCF = 1 if UC.SI else UC.CF_e; sCF = 1 if UC.SI else UC.CF_s
        vCF = 1 if UC.SI else UC.CF_v; nCF = 1 if UC.SI else UC.CF_n
        if mass: eCF /= MW; sCF /= MW; vCF /= MW
        elif total: eCF *= n * nCF; sCF *= n * nCF; vCF *= n * nCF
        w = colName.lower()
        if w == 't': return [T * TCF for T in data]
        if w == 'u': return [u * eCF for u in data]
        if w == 'h': return [h * eCF for h in data]
        if w == 's': return [s * sCF for s in data]
        if w == 'v': return [v * vCF for v in data]
        if w == 'p': return [P * PCF for P in data]

    # --------------------------------------------------------------
    def updateDisplayWidgets(self, Model: ottoCycleModel) -> None:
        """
        Populate all QLineEdits and unit labels with the latest results.

        Guard clause exits immediately if `Model.State1 is None`; this
        satisfies the prompt’s requirement to prevent a GUI crash when
        switching controllers before calculation.
        """
        if Model.State1 is None:
            return

        U = Model.units; SI = U.SI; CFT = 1 if SI else U.CF_T; CFE = 1 if SI else U.CF_E

        # label prefixes with units
        self.lbl_THigh.setText(f"T High ({U.TUnits})")
        self.lbl_TLow .setText(f"T Low ({U.TUnits})")
        self.lbl_P0   .setText(f"P0 ({U.PUnits})")
        self.lbl_V0   .setText(f"V0 ({U.VUnits})")

        # temperatures
        self.le_T1.setText(f"{Model.State1.T * CFT:.2f}")
        self.le_T2.setText(f"{Model.State2.T * CFT:.2f}")
        self.le_T3.setText(f"{Model.State3.T * CFT:.2f}")
        self.le_T4.setText(f"{Model.State4.T * CFT:.2f}")
        for lbl in (self.lbl_T1Units, self.lbl_T2Units,
                    self.lbl_T3Units, self.lbl_T4Units):
            lbl.setText(U.TUnits)

        # energies & efficiency
        self.le_Efficiency.setText(f"{Model.Eff:.3f}")
        self.le_PowerStroke.setText(f"{Model.air.n * Model.W_Power * CFE:.3f}")
        self.le_CompressionStroke.setText(f"{Model.air.n * Model.W_Compression * CFE:.3f}")
        self.le_HeatAdded.setText(f"{Model.air.n * Model.Q_In * CFE:.3f}")
        for lbl in (self.lbl_PowerStrokeUnits, self.lbl_CompressionStrokeUnits,
                    self.lbl_HeatInUnits):
            lbl.setText(U.EUnits)


# ─────────────────────────────────────────────────────────────────────────────
#  CLI smoke test
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = qtw.QApplication(sys.argv)
    oc = ottoCycleController()
    oc.set(T_0=540.0, P_0=1.0, V_0=0.02,   # English units example
           T_High=3600.0, ratio=8.0, SI=False)
    oc.plot_cycle_XY(X="v", Y="P", total=True)
