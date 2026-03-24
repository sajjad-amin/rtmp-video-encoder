import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QComboBox, QLineEdit)
from PyQt6.QtCore import Qt
from converter import ConverterThread

class RTMPVideoEncoderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RTMP Video Encoder")
        self.setMinimumWidth(850)
        self.setMinimumHeight(450)
        
        self.thread = None
        self._is_cancelling_all = False
        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # --- Row 1: Source & Dest ---
        row1_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Browse Sources (Multiple)")
        self.browse_btn.clicked.connect(self.browse_sources)
        
        self.dest_folder_input = QLineEdit()
        self.dest_folder_input.setReadOnly(True)
        self.dest_folder_input.setPlaceholderText("Destination Folder (Default: Same as Source Directory)")
        self.dest_folder_btn = QPushButton("Select Destination")
        self.dest_folder_btn.clicked.connect(self.select_destination_folder)
        
        row1_layout.addWidget(self.browse_btn)
        row1_layout.addWidget(self.dest_folder_input)
        row1_layout.addWidget(self.dest_folder_btn)
        
        # --- Row 2: Engine & Remove ---
        row2_layout = QHBoxLayout()
        encoder_label = QLabel("Encoding Engine:")
        self.encoder_combo = QComboBox()
        self.encoder_combo.addItems([
            "Auto-Detect (Best Available)",
            "CPU (libx264)",
            "Apple VideoToolbox (h264_videotoolbox)",
            "NVIDIA NVENC (h264_nvenc)",
            "Intel QSV (h264_qsv)",
            "AMD AMF (h264_amf)"
        ])
        
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        
        row2_layout.addWidget(encoder_label)
        row2_layout.addWidget(self.encoder_combo)
        row2_layout.addStretch()
        row2_layout.addWidget(self.remove_btn)
        
        # --- Batch Process Table ---
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Source File", "Destination Output", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(2, 250)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        # --- Footer Controls ---
        control_layout = QHBoxLayout()
        
        self.time_label = QLabel("Elapsed: 00:00:00 | Estimated: 00:00:00")
        self.time_label.setStyleSheet("color: #666; font-weight: bold;")
        
        self.convert_btn = QPushButton("Start")
        self.convert_btn.setMinimumHeight(35)
        self.convert_btn.setFixedWidth(120)
        self.convert_btn.clicked.connect(self.start_batch_processing)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setMinimumHeight(35)
        self.pause_btn.setFixedWidth(120)
        self.pause_btn.clicked.connect(self.toggle_pause)
        self.pause_btn.setEnabled(False)
        
        self.cancel_btn = QPushButton("Cancel All")
        self.cancel_btn.setMinimumHeight(35)
        self.cancel_btn.setFixedWidth(120)
        self.cancel_btn.clicked.connect(self.cancel_all)
        self.cancel_btn.setEnabled(False) 
        
        control_layout.addWidget(self.time_label)
        control_layout.addStretch()
        control_layout.addWidget(self.convert_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.cancel_btn)
        
        # --- Assemble Layout ---
        layout.addLayout(row1_layout)
        layout.addLayout(row2_layout)
        layout.addWidget(self.table)
        layout.addLayout(control_layout)

    def select_destination_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder_path:
            self.dest_folder_input.setText(folder_path)
            # Update currently pending rows
            for row in range(self.table.rowCount()):
                if self.table.item(row, 2).text() == "Pending":
                    source_path = self.table.item(row, 0).text()
                    _, filename = os.path.split(source_path)
                    name, _ = os.path.splitext(filename)
                    new_dest = os.path.join(folder_path, f"{name}_converted.mp4")
                    self.table.item(row, 1).setText(new_dest)

    def browse_sources(self):
        file_filter = "Video Files (*.mp4 *.mkv *.avi *.mov *.flv *.ts);;All Files (*)"
        file_paths, _ = QFileDialog.getOpenFileNames(self, "Select Source Videos", "", file_filter)
        
        dest_dir = self.dest_folder_input.text()
        
        for file_path in file_paths:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            directory, filename = os.path.split(file_path)
            name, _ = os.path.splitext(filename)
            
            out_dir = dest_dir if dest_dir else directory
            default_dest = os.path.join(out_dir, f"{name}_converted.mp4")
            
            self.table.setItem(row, 0, QTableWidgetItem(file_path))
            self.table.setItem(row, 1, QTableWidgetItem(default_dest))
            self.table.setItem(row, 2, QTableWidgetItem("Pending"))

    def remove_selected(self):
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
            
        for row in sorted(rows, reverse=True):
            status = self.table.item(row, 2).text()
            if "Pending" in status or "Done" in status or "Error" in status or "Cancelled" in status:
                self.table.removeRow(row)
            else:
                QMessageBox.warning(self, "Warning", "Cannot remove an actively processing queue item.")

    def start_batch_processing(self):
        pending_row = -1
        for row in range(self.table.rowCount()):
            text = self.table.item(row, 2).text()
            if "Pending" in text or "Cancelled/Error" in text:
                pending_row = row
                break
                
        if pending_row == -1:
            QMessageBox.information(self, "Batch Complete", "All files in the queue have been processed!")
            self.reset_ui()
            return

        self._is_cancelling_all = False
        
        self.convert_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("Pause")
        self.cancel_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self.dest_folder_btn.setEnabled(False)
        self.encoder_combo.setEnabled(False) 
        
        source = self.table.item(pending_row, 0).text()
        dest = self.table.item(pending_row, 1).text()
        encoder_selection = self.encoder_combo.currentText()
        
        self.table.item(pending_row, 2).setText("Starting...")
        
        self.thread = ConverterThread(pending_row, source, dest, encoder_selection, parent=self)
        self.thread.progress_updated.connect(self.update_progress)
        self.thread.conversion_finished.connect(self.conversion_done)
        self.thread.encoder_detected.connect(self.update_encoder_combo)
        self.thread.start()

    def update_encoder_combo(self, row, encoder_name):
        index = self.encoder_combo.findText(encoder_name)
        if index >= 0:
            self.encoder_combo.setCurrentIndex(index)

    def update_progress(self, row, progress, elapsed_str, est_str):
        self.table.item(row, 2).setText(f"Processing {progress}%")
        self.time_label.setText(f"Elapsed: {elapsed_str} | Estimated: {est_str}")

    def conversion_done(self, row, success, message):
        if self.thread:
            # Tell Qt to free it safely and remove Python reference
            self.thread.deleteLater()
            self.thread = None
            
        if success:
            self.table.item(row, 2).setText("Done")
        else:
            self.table.item(row, 2).setText(f"Cancelled/Error")
            
        self.time_label.setText("Elapsed: 00:00:00 | Estimated: 00:00:00")
            
        if self._is_cancelling_all:
            self.reset_ui()
            return

        self.start_batch_processing()

    def toggle_pause(self):
        try:
            if self.thread and self.thread.isRunning():
                is_paused = self.thread.toggle_pause()
                if is_paused:
                    self.pause_btn.setText("Resume")
                else:
                    self.pause_btn.setText("Pause")
        except RuntimeError:
            pass

    def cancel_all(self):
        reply = QMessageBox.question(
            self, 'Cancel Batch Processing', 
            'Are you sure you want to abort the entire batch? The currently active file will fail.',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._is_cancelling_all = True
            self.cancel_btn.setEnabled(False)
            self.pause_btn.setEnabled(False)
            try:
                if self.thread and self.thread.isRunning():
                    self.table.item(self.thread.row, 2).setText("Cancelling...")
                    self.thread.cancel()
                else:
                    self.reset_ui()
            except RuntimeError:
                self.reset_ui()

    def reset_ui(self):
        self.convert_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("Pause")
        self.cancel_btn.setEnabled(False)
        self.encoder_combo.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.remove_btn.setEnabled(True)
        self.dest_folder_btn.setEnabled(True)
        self.time_label.setText("Elapsed: 00:00:00 | Estimated: 00:00:00")

    def closeEvent(self, event):
        try:
            if self.thread and self.thread.isRunning():
                reply = QMessageBox.question(
                    self, 'Quit Application', 
                    'A batch conversion is currently running. Are you sure you want to quit and abort all operations?',
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._is_cancelling_all = True
                    self.thread.cancel()
                    self.thread.wait()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()
        except RuntimeError:
            # Reached if C++ Object was safely GC'd earlier
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = RTMPVideoEncoderApp()
    window.show()
    sys.exit(app.exec())
