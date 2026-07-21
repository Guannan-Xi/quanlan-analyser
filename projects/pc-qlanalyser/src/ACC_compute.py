from PyQt5 import QtCore, QtGui, QtWidgets
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pandas as pd
from PyQt5.QtWidgets import QFileDialog
import os

class Ui_ACC_compute(object):
    def setupUi(self, ACC_compute):
        ACC_compute.setObjectName("ACC_compute")
        ACC_compute.setWindowTitle("ACC Compute")
        ACC_compute.resize(800, 600)
        
        # Create main layout
        self.main_layout = QtWidgets.QVBoxLayout(ACC_compute)
        
        # Add title label
        self.title = QtWidgets.QLabel("Total ACC Time Series")
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.title.setFont(font)
        self.title.setAlignment(QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(self.title)
        
        # Create figure for plotting
        self.figure = Figure(figsize=(8, 6))
        self.canvas = FigureCanvas(self.figure)
        self.main_layout.addWidget(self.canvas)
        
        # Add compute button
        self.compute_button = QtWidgets.QPushButton("Compute Total ACC")
        self.compute_button.clicked.connect(self.compute_acc_rms)
        self.main_layout.addWidget(self.compute_button)
        
        # Add save button
        # self.save_button = QtWidgets.QPushButton("Save and Exit")
        # self.save_button.clicked.connect(self.save_data)
        # self.main_layout.addWidget(self.save_button)
        
        # Add result label
        self.result_label = QtWidgets.QLabel()
        self.result_label.setAlignment(QtCore.Qt.AlignCenter)
        self.main_layout.addWidget(self.result_label)

    def import_raw(self, raw):
        self.raw = raw

    def compute_acc_rms(self):
        # Get ACC channel names (assuming they contain 'ACC' in their names)
        acc_channels = [ch for ch in self.raw.ch_names if 'ACC' in ch.upper()]
        
        if len(acc_channels) != 3:
            self.result_label.setText("Error: Expected 3 ACC channels, found " + str(len(acc_channels)))
            return
        
        # Get data from ACC channels
        data, times = self.raw[acc_channels, :]
        data = data * 1e-6
        # Compute RMS for each time point across channels
        # self.rms_values = np.sqrt(np.mean(np.square(data * 1e-6), axis=0))
        self.total_acc_values = np.sqrt(np.sum(np.square(data), axis=0))
        self.times = times
        self.acc_data = data
        
        # Plot results
        self.figure.clear()
        
        # Create subplots
        gs = self.figure.add_gridspec(2, 1, height_ratios=[2, 1])
        
        # Plot individual ACC channels
        ax1 = self.figure.add_subplot(gs[0])
        for i, channel in enumerate(acc_channels):
            ax1.plot(times, data[i], label=channel)
        ax1.set_ylabel('Acceleration')
        ax1.set_title('ACC Channels')
        ax1.legend()
        
        # Plot RMS values
        ax2 = self.figure.add_subplot(gs[1])
        ax2.plot(times, self.total_acc_values, 'r-', label='Total ACC')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Total ACC Value')
        ax2.set_title('Total ACC Time Series')
        ax2.legend()
        
        self.figure.tight_layout()
        self.canvas.draw()
        
        # Auto save results
        try:
            # Create ACC_Compute folder
            result_path = os.path.join(self.raw.info['description'], 'ACC_Compute')
            os.makedirs(result_path, exist_ok=True)
            
            # Save figure
            fig_path = os.path.join(result_path, 'ACC_plot.png')
            self.figure.savefig(fig_path, dpi=300, bbox_inches='tight')
            
            # Save data to CSV
            df = pd.DataFrame({
                'Time': self.times,
                'Total ACC': self.total_acc_values
            })
            csv_path = os.path.join(result_path, 'ACC_data.csv')
            df.to_csv(csv_path, index=False)
            
            self.result_label.setText("Results saved successfully")
        except Exception as e:
            self.result_label.setText(f"Error saving results: {str(e)}")

    def save_data(self):
        if not hasattr(self, 'total_acc_values'):
            self.result_label.setText("Please compute Total ACC values first")
            return
            
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(None, "Save Data", "",
                                                 "Excel Files (*.xlsx);;CSV Files (*.csv);;All Files (*)",
                                                 options=options)
        
        if file_name:
            # Create DataFrame
            df = pd.DataFrame({
                'Time': self.times,
                'Total ACC': self.total_acc_values
            })
            
            # Save based on file extension
            if file_name.endswith('.xlsx'):
                df.to_excel(file_name, index=False)
            else:
                if not file_name.endswith('.csv'):
                    file_name += '.csv'
                df.to_csv(file_name, index=False)
                
            # self.result_label.setText(f"Data saved to {file_name}")
            
            # Close the ACC module window
            self.result_label.parent().close() 
            