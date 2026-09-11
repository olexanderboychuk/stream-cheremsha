#!/usr/bin/env python3
"""Demo PySide6 application with PyQtAuto server enabled.

This application demonstrates a typical PySide6 app that can be automated
using PyQtAuto. The server starts automatically based on environment variables
or can be force-started.

Usage:
    # Start with automation enabled
    PYQTAUTO_ENABLED=1 python tests/qtappdemo.py

    # Or with a custom port
    PYQTAUTO_ENABLED=1 PYQTAUTO_PORT=9999 python tests/qtappdemo.py
"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DemoWindow(QMainWindow):
    """Demo application window with various widgets for testing automation."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyQtAuto Demo Application")
        self.setObjectName("main_window")
        self.resize(600, 500)

        # Central widget with tabs
        central = QWidget()
        central.setObjectName("central_widget")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)

        # Tab widget
        tabs = QTabWidget()
        tabs.setObjectName("main_tabs")

        # Tab 1: Form controls
        tabs.addTab(self._create_form_tab(), "Form")

        # Tab 2: Actions
        tabs.addTab(self._create_actions_tab(), "Actions")

        # Tab 3: Lists
        tabs.addTab(self._create_lists_tab(), "Lists")

        layout.addWidget(tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setObjectName("status_bar")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _create_form_tab(self) -> QWidget:
        """Create the form controls tab."""
        widget = QWidget()
        widget.setObjectName("form_tab")
        layout = QVBoxLayout(widget)

        # Name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Name:")
        name_label.setObjectName("name_label")
        self.name_input = QLineEdit()
        self.name_input.setObjectName("name_input")
        self.name_input.setPlaceholderText("Enter your name")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)

        # Email input
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setObjectName("email_label")
        self.email_input = QLineEdit()
        self.email_input.setObjectName("email_input")
        self.email_input.setPlaceholderText("Enter your email")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)
        layout.addLayout(email_layout)

        # Country combo
        country_layout = QHBoxLayout()
        country_label = QLabel("Country:")
        country_label.setObjectName("country_label")
        self.country_combo = QComboBox()
        self.country_combo.setObjectName("country_combo")
        self.country_combo.addItems(
            ["Select...", "USA", "UK", "France", "Germany", "Japan"]
        )
        country_layout.addWidget(country_label)
        country_layout.addWidget(self.country_combo)
        layout.addLayout(country_layout)

        # Age spinner
        age_layout = QHBoxLayout()
        age_label = QLabel("Age:")
        age_label.setObjectName("age_label")
        self.age_spinner = QSpinBox()
        self.age_spinner.setObjectName("age_spinner")
        self.age_spinner.setRange(1, 120)
        self.age_spinner.setValue(25)
        age_layout.addWidget(age_label)
        age_layout.addWidget(self.age_spinner)
        age_layout.addStretch()
        layout.addLayout(age_layout)

        # Gender radio buttons
        gender_group = QGroupBox("Gender")
        gender_group.setObjectName("gender_group")
        gender_layout = QHBoxLayout(gender_group)
        self.radio_male = QRadioButton("Male")
        self.radio_male.setObjectName("radio_male")
        self.radio_female = QRadioButton("Female")
        self.radio_female.setObjectName("radio_female")
        self.radio_other = QRadioButton("Other")
        self.radio_other.setObjectName("radio_other")
        self.radio_male.setChecked(True)
        gender_layout.addWidget(self.radio_male)
        gender_layout.addWidget(self.radio_female)
        gender_layout.addWidget(self.radio_other)
        layout.addWidget(gender_group)

        # Newsletter checkbox
        self.newsletter_check = QCheckBox("Subscribe to newsletter")
        self.newsletter_check.setObjectName("newsletter_check")
        layout.addWidget(self.newsletter_check)

        # Submit button
        self.submit_btn = QPushButton("Submit")
        self.submit_btn.setObjectName("submit_btn")
        self.submit_btn.clicked.connect(self._on_submit)
        layout.addWidget(self.submit_btn)

        # Result label
        self.result_label = QLabel("")
        self.result_label.setObjectName("result_label")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        layout.addStretch()
        return widget

    def _create_actions_tab(self) -> QWidget:
        """Create the actions tab."""
        widget = QWidget()
        widget.setObjectName("actions_tab")
        layout = QVBoxLayout(widget)

        # Counter section
        counter_group = QGroupBox("Counter")
        counter_group.setObjectName("counter_group")
        counter_layout = QHBoxLayout(counter_group)

        self.counter_label = QLabel("0")
        self.counter_label.setObjectName("counter_label")
        self.counter_label.setStyleSheet("font-size: 24px; font-weight: bold;")

        self.inc_btn = QPushButton("+")
        self.inc_btn.setObjectName("inc_btn")
        self.inc_btn.clicked.connect(self._increment)

        self.dec_btn = QPushButton("-")
        self.dec_btn.setObjectName("dec_btn")
        self.dec_btn.clicked.connect(self._decrement)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("reset_btn")
        self.reset_btn.clicked.connect(self._reset_counter)

        counter_layout.addWidget(self.dec_btn)
        counter_layout.addWidget(self.counter_label)
        counter_layout.addWidget(self.inc_btn)
        counter_layout.addWidget(self.reset_btn)
        layout.addWidget(counter_group)

        # Slider section
        slider_group = QGroupBox("Volume")
        slider_group.setObjectName("slider_group")
        slider_layout = QHBoxLayout(slider_group)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setObjectName("volume_slider")
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.valueChanged.connect(self._on_volume_change)

        self.volume_label = QLabel("50")
        self.volume_label.setObjectName("volume_label")
        self.volume_label.setMinimumWidth(30)

        slider_layout.addWidget(self.volume_slider)
        slider_layout.addWidget(self.volume_label)
        layout.addWidget(slider_group)

        # Progress section
        progress_group = QGroupBox("Progress")
        progress_group.setObjectName("progress_group")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("progress_bar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        progress_btn_layout = QHBoxLayout()
        self.start_progress_btn = QPushButton("Start")
        self.start_progress_btn.setObjectName("start_progress_btn")
        self.start_progress_btn.clicked.connect(self._start_progress)

        self.stop_progress_btn = QPushButton("Stop")
        self.stop_progress_btn.setObjectName("stop_progress_btn")
        self.stop_progress_btn.clicked.connect(self._stop_progress)
        self.stop_progress_btn.setEnabled(False)

        progress_btn_layout.addWidget(self.start_progress_btn)
        progress_btn_layout.addWidget(self.stop_progress_btn)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addLayout(progress_btn_layout)
        layout.addWidget(progress_group)

        # Dialog buttons
        dialog_group = QGroupBox("Dialogs")
        dialog_group.setObjectName("dialog_group")
        dialog_layout = QHBoxLayout(dialog_group)

        self.info_btn = QPushButton("Info")
        self.info_btn.setObjectName("info_btn")
        self.info_btn.clicked.connect(
            lambda: QMessageBox.information(self, "Info", "This is an info message")
        )

        self.warn_btn = QPushButton("Warning")
        self.warn_btn.setObjectName("warn_btn")
        self.warn_btn.clicked.connect(
            lambda: QMessageBox.warning(self, "Warning", "This is a warning message")
        )

        dialog_layout.addWidget(self.info_btn)
        dialog_layout.addWidget(self.warn_btn)
        layout.addWidget(dialog_group)

        layout.addStretch()
        return widget

    def _create_lists_tab(self) -> QWidget:
        """Create the lists tab."""
        widget = QWidget()
        widget.setObjectName("lists_tab")
        layout = QVBoxLayout(widget)

        # List widget
        list_group = QGroupBox("Items")
        list_group.setObjectName("list_group")
        list_layout = QVBoxLayout(list_group)

        self.item_list = QListWidget()
        self.item_list.setObjectName("item_list")
        self.item_list.addItems(["Item 1", "Item 2", "Item 3", "Item 4", "Item 5"])

        # Add item controls
        add_layout = QHBoxLayout()
        self.new_item_input = QLineEdit()
        self.new_item_input.setObjectName("new_item_input")
        self.new_item_input.setPlaceholderText("New item...")

        self.add_item_btn = QPushButton("Add")
        self.add_item_btn.setObjectName("add_item_btn")
        self.add_item_btn.clicked.connect(self._add_item)

        self.remove_item_btn = QPushButton("Remove")
        self.remove_item_btn.setObjectName("remove_item_btn")
        self.remove_item_btn.clicked.connect(self._remove_item)

        add_layout.addWidget(self.new_item_input)
        add_layout.addWidget(self.add_item_btn)
        add_layout.addWidget(self.remove_item_btn)

        list_layout.addWidget(self.item_list)
        list_layout.addLayout(add_layout)
        layout.addWidget(list_group)

        # Notes text area
        notes_group = QGroupBox("Notes")
        notes_group.setObjectName("notes_group")
        notes_layout = QVBoxLayout(notes_group)

        self.notes_text = QTextEdit()
        self.notes_text.setObjectName("notes_text")
        self.notes_text.setPlaceholderText("Enter notes here...")

        notes_layout.addWidget(self.notes_text)
        layout.addWidget(notes_group)

        return widget

    def _on_submit(self):
        """Handle form submission."""
        name = self.name_input.text()
        email = self.email_input.text()
        country = self.country_combo.currentText()
        age = self.age_spinner.value()

        gender = "Unknown"
        if self.radio_male.isChecked():
            gender = "Male"
        elif self.radio_female.isChecked():
            gender = "Female"
        elif self.radio_other.isChecked():
            gender = "Other"

        newsletter = "Yes" if self.newsletter_check.isChecked() else "No"

        result = (
            f"Submitted: {name}, {email}, {country}, Age: {age}, "
            f"Gender: {gender}, Newsletter: {newsletter}"
        )
        self.result_label.setText(result)
        self.status_bar.showMessage("Form submitted!")

    def _increment(self):
        """Increment counter."""
        current = int(self.counter_label.text())
        self.counter_label.setText(str(current + 1))

    def _decrement(self):
        """Decrement counter."""
        current = int(self.counter_label.text())
        self.counter_label.setText(str(current - 1))

    def _reset_counter(self):
        """Reset counter."""
        self.counter_label.setText("0")

    def _on_volume_change(self, value: int):
        """Handle volume slider change."""
        self.volume_label.setText(str(value))

    def _start_progress(self):
        """Start progress bar animation."""
        from PySide6.QtCore import QTimer

        self.progress_bar.setValue(0)
        self.start_progress_btn.setEnabled(False)
        self.stop_progress_btn.setEnabled(True)

        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._update_progress)
        self._progress_timer.start(50)

    def _stop_progress(self):
        """Stop progress bar animation."""
        if hasattr(self, "_progress_timer"):
            self._progress_timer.stop()
        self.start_progress_btn.setEnabled(True)
        self.stop_progress_btn.setEnabled(False)

    def _update_progress(self):
        """Update progress bar."""
        value = self.progress_bar.value()
        if value >= 100:
            self._stop_progress()
        else:
            self.progress_bar.setValue(value + 1)

    def _add_item(self):
        """Add item to list."""
        text = self.new_item_input.text().strip()
        if text:
            self.item_list.addItem(text)
            self.new_item_input.clear()

    def _remove_item(self):
        """Remove selected item from list."""
        current = self.item_list.currentRow()
        if current >= 0:
            self.item_list.takeItem(current)


def main():
    """Run the demo application."""
    app = QApplication(sys.argv)

    # Start the PyQtAuto server
    # This will check PYQTAUTO_ENABLED env var, or you can force=True
    from pyqtauto.server import start_server

    server = start_server(force=True)  # Force start for demo
    if server:
        print(f"PyQtAuto server started on port {server.port}")

    window = DemoWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
