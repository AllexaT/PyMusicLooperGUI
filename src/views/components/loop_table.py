from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal

class NumericTableItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            val1 = float(self.text().replace('%', ''))
            val2 = float(other.text().replace('%', ''))
            return val1 < val2
        except ValueError:
            return self.text() < other.text()

class LoopTableWidget(QTableWidget):
    loopSelected = pyqtSignal(int) # Emits the original index (rank) when a loop is selected

    def __init__(self, translations):
        super().__init__()
        self.tr_lang = translations
        self.init_ui()

    def init_ui(self):
        self.setColumnCount(4)
        columns_labels = self.tr_lang.get("columns", ["Start", "End", "Length", "Score"])
        self.setHorizontalHeaderLabels(columns_labels)
        
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.verticalHeader().setVisible(True)
        self.setSortingEnabled(True)

        self.setColumnWidth(0, 65)
        self.setColumnWidth(1, 65)
        self.setColumnWidth(2, 65)
        self.setColumnWidth(3, 65)
        
        self.verticalHeader().setFixedWidth(33)
        self.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

        self.itemSelectionChanged.connect(self._on_selection_changed)

    def populate(self, sorted_loops, music_looper):
        """Populate the table with loops. sorted_loops is a list of tuples (original_index, loop_pair)"""
        self.setSortingEnabled(False)
        self.setRowCount(len(sorted_loops))
        
        for rank, (original_index, loop) in enumerate(sorted_loops):
            start_time = music_looper.samples_to_seconds(loop.loop_start)
            end_time = music_looper.samples_to_seconds(loop.loop_end)
            duration = end_time - start_time
            
            items = [
                NumericTableItem(f"{start_time:.2f}"),
                NumericTableItem(f"{end_time:.2f}"),
                NumericTableItem(f"{duration:.2f}"),
                NumericTableItem(f"{loop.score:.2%}")
            ]
            
            for col, item in enumerate(items):
                # Store the original index in the first item to retrieve later
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, original_index)
                self.setItem(rank, col, item)
                
            self.setVerticalHeaderItem(rank, QTableWidgetItem(str(rank)))
            
        self.setSortingEnabled(True)

    def _on_selection_changed(self):
        selected_items = self.selectedItems()
        if selected_items:
            # We stored the original index in UserRole of the first column
            row = selected_items[0].row()
            first_col_item = self.item(row, 0)
            original_index = first_col_item.data(Qt.ItemDataRole.UserRole)
            self.loopSelected.emit(original_index)
    
    def clear_table(self):
        self.setRowCount(0)
