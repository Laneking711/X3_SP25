from PyQt5.QtWidgets import QApplication, QWidget, QGraphicsScene, QGraphicsView, QVBoxLayout, QPushButton, QLineEdit, QLabel, QFileDialog, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsTextItem, QGraphicsPathItem
from PyQt5.QtGui import QPen, QBrush, QColor, QFont, QPainterPath
from PyQt5.QtCore import Qt, QPointF
import sys

class CircuitViewer(QWidget):
    """
    Uses example Circuit to produce desired output 
    Main GUI class for visualizing RLC circuits based on a structured text file.
    Uses PyQt5's Graphics View Framework to render schematic elements.
    """

    def __init__(self):
        """
        Initializes the GUI window, layouts, widgets, and data containers.
        """
        super().__init__()
        self.setWindowTitle("Circuit Viewer")
        self.setGeometry(100, 100, 1000, 700)

        layout = QVBoxLayout(self)
        self.btn_open = QPushButton("Open Circuit File")
        self.file_display = QLineEdit()
        self.label = QLabel("Circuit Artist 9000")
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)

        layout.addWidget(self.btn_open)
        layout.addWidget(self.file_display)
        layout.addWidget(self.label)
        layout.addWidget(self.view)

        self.btn_open.clicked.connect(self.open_file)

        self.view.resetTransform()
        self.view.scale(5.0, 5.0)

        self.nodes = {}      # Dictionary of node names and their attributes
        self.elements = []   # List of circuit elements (resistors, wires, etc.)

    def open_file(self):
        """
        Opens a file dialog to load the circuit text file, reads its content,
        and passes the data to the parser.
        """
        fname, _ = QFileDialog.getOpenFileName(self, "Open Circuit File")
        if fname:
            self.file_display.setText(fname)
            with open(fname, 'r') as f:
                lines = f.readlines()
            self.parse_and_draw(lines)

    def parse_and_draw(self, lines):
        """
        Parses the circuit file line-by-line, building internal dictionaries
        of nodes and elements, and then triggers rendering.
        """
        self.scene.clear()
        self.nodes.clear()
        self.elements.clear()

        i = 0
        while i < len(lines):
            line = lines[i].strip().lower()

            # Parse node definition block
            if '<node>' in line:
                node = {}
                i += 1
                while '</node>' not in lines[i].strip().lower():
                    l = lines[i].strip()
                    if l.startswith('name:'):
                        node['name'] = l.split(':')[1].strip().strip("'")
                    elif l.startswith('position:'):
                        x, y = map(float, l.split(':')[1].split(','))
                        node['pos'] = QPointF(x, -y)  # Invert Y for display
                    elif l.startswith('draw:'):
                        node['draw'] = 'true' in l.split(':')[1].strip().lower()
                    i += 1
                self.nodes[node['name']] = node

            # Parse circuit element block
            elif any(tag in line for tag in ('<resistor>', '<inductor>', '<capacitor>', '<voltage source>', '<wire>')):
                elem = {'type': line.replace('<', '').replace('>', '')}
                i += 1
                while not lines[i].strip().lower().startswith('</'):
                    l = lines[i].strip()
                    if l.startswith('name:'):
                        elem['name'] = l.split(':')[1].strip().strip("'")
                    elif l.startswith('node1:'):
                        elem['node1'] = l.split(':')[1].strip().strip("'")
                    elif l.startswith('node2:'):
                        elem['node2'] = l.split(':')[1].strip().strip("'")
                    i += 1
                self.elements.append(elem)
            i += 1

        self.draw_circuit()

    def draw_circuit(self):
        """
        Draws all nodes and circuit elements in the graphics scene.
        Each element type is handled by a corresponding draw_* function.
        """
        node_radius = 4
        font = QFont("Arial", 10)
        pen = QPen(Qt.black, 2)

        # Draw all nodes that are flagged for display
        for name, node in self.nodes.items():
            if node.get('draw', False):
                dot = QGraphicsEllipseItem(
                    node['pos'].x() - node_radius,
                    node['pos'].y() - node_radius,
                    2 * node_radius,
                    2 * node_radius
                )
                dot.setBrush(Qt.black)
                self.scene.addItem(dot)

        # Draw all circuit elements between their respective nodes
        for elem in self.elements:
            node1 = self.nodes.get(elem['node1'])
            node2 = self.nodes.get(elem['node2'])
            if not node1 or not node2:
                continue

            p1 = node1['pos']
            p2 = node2['pos']

            if elem['type'] == 'wire':
                self.scene.addItem(QGraphicsLineItem(p1.x(), p1.y(), p2.x(), p2.y()))
            elif elem['type'] == 'resistor':
                self.draw_resistor(p1, p2, elem['name'])
            elif elem['type'] == 'inductor':
                self.draw_inductor(p1, p2, elem['name'])
            elif elem['type'] == 'capacitor':
                self.draw_capacitor(p1, p2, elem['name'])
            elif elem['type'] == 'voltage source':
                self.draw_voltage(p1, p2, elem['name'])

    def draw_resistor(self, p1, p2, label):
        """
        Draws a zig-zag resistor symbol between two points.
        """
        zigzag = QPainterPath(p1)
        steps = 4
        direction = (p2 - p1) / (steps * 2)
        perp = QPointF(-direction.y(), direction.x()) * 2
        for i in range(1, steps * 2):
            offset = perp if i % 2 == 1 else -perp
            zigzag.lineTo(p1 + i * direction + offset)
        zigzag.lineTo(p2)
        item = QGraphicsPathItem(zigzag)
        item.setPen(QPen(Qt.black, 2))
        self.scene.addItem(item)

        label_item = QGraphicsTextItem(label)
        label_item.setFont(QFont("Arial", 3))
        label_item.setPos((p1 + p2) / 2 + QPointF(-25, -10))
        self.scene.addItem(label_item)

    def draw_inductor(self, p1, p2, label):
        """
        Draws an inductor between two points using four arcs without a base line.
        Arcs are drawn to simulate the coiled wire of an inductor.
        """
        from math import atan2, cos, sin, pi

        # Vector from p1 to p2
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = 5+(dx ** 2 + dy ** 2) ** 0.5
        angle = atan2(dy, dx)

        arc_radius = length / 10
        arc_count = 5
        arc_spacing = length / (arc_count + 1)

        for i in range(arc_count):
            center_x = p1.x() + (i + 1) * arc_spacing * cos(angle)
            center_y = p1.y() + (i + 1) * arc_spacing * sin(angle)

            arc = QGraphicsEllipseItem(center_x-2- arc_radius,
                                       center_y - arc_radius,
                                       2 * arc_radius,
                                       2 * arc_radius)
            arc.setStartAngle(0)
            arc.setSpanAngle(180 * 16)
            arc.setPen(QPen(Qt.darkGreen, 2))
            self.scene.addItem(arc)

        label_item = QGraphicsTextItem(label)
        label_item.setFont(QFont("Arial", 3))
        label_item.setPos((p1 + p2) / 2 + QPointF(0, -25))
        self.scene.addItem(label_item)

    def draw_capacitor(self, p1, p2, label):
        """
        Draws a capacitor using two vertical plates and connecting wires.
        has some manual inputs to shift and move things where it is better placed
        """
        mid = (p1 + p2) / 2
        mid_x = (p1.x() + p2.x()) / 2
        top_y = min(p1.y(), p2.y())
        bottom_y = max(p1.y(), p2.y())
        gap = 5

        plate1 = QGraphicsLineItem(mid_x - 10, top_y + 3 * gap, mid_x + 10, top_y + 3 * gap)
        plate2 = QGraphicsLineItem(mid_x - 10, bottom_y - 3 * gap, mid_x + 10, bottom_y - 3 * gap)
        wire1 = QGraphicsLineItem(p1.x(), p1.y(), mid_x, plate1.line().y1() + 2 * gap)
        wire2 = QGraphicsLineItem(mid_x, bottom_y - 5 * gap, p2.x(), p2.y())

        for item in [plate1, plate2, wire1, wire2]:
            item.setPen(QPen(Qt.black, 2))
            self.scene.addItem(item)

        label_item = QGraphicsTextItem(label)
        label_item.setFont(QFont("Arial", 3))
        label_item.setPos(mid_x + 10, mid.y() - 10)
        self.scene.addItem(label_item)

    def draw_voltage(self, p1, p2, label):
        """
        Draws a voltage source as a vertical circle between two wire stubs with '+' above and '-' below.
        """
        from PyQt5.QtWidgets import QGraphicsSimpleTextItem

        # Midpoint and offset for leads
        mid = (p1 + p2) / 2
        lead_len = 10
        radius = 8

        # Wires from node to circle
        self.scene.addItem(QGraphicsLineItem(p1.x(), p1.y(), mid.x(), mid.y() - radius))
        self.scene.addItem(QGraphicsLineItem(mid.x(), mid.y() + radius, p2.x(), p2.y()))

        # Circle for the voltage source
        circle = QGraphicsEllipseItem(mid.x() - radius, mid.y() - radius, 2 * radius, 2 * radius)
        circle.setPen(QPen(Qt.black, 2))
        self.scene.addItem(circle)

        # Plus sign above
        plus = QGraphicsSimpleTextItem("+")
        plus.setFont(QFont("Arial", 3))
        plus.setPos(mid.x() -2, mid.y() - radius -1)
        self.scene.addItem(plus)

        # Minus sign below
        minus = QGraphicsSimpleTextItem("−")
        minus.setFont(QFont("Arial", 3))
        minus.setPos(mid.x() -2, mid.y() + radius-9)
        self.scene.addItem(minus)

        # Voltage label beside the circle
        label_item = QGraphicsTextItem(label)
        label_item.setFont(QFont("Arial", 3))
        label_item.setPos(mid.x() - 30, mid.y() - 9)
        self.scene.addItem(label_item)


if __name__ == '__main__':
    # Entry point for running the PyQt application
    app = QApplication(sys.argv)
    viewer = CircuitViewer()
    viewer.show()
    sys.exit(app.exec_())
