from matplotlib import pyplot as plt
from matplotlib.lines import Line2D
import variable
import numpy as np
import pandas as pd
import sys
import os
import time
import mne
import joblib
import seaborn as sns
from PyQt5.QtWidgets import QInputDialog, QMainWindow, QApplication, QFileDialog

from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from ui import Ui_MainWindow, QTextEditLogger
from my_functions import *
import io
from contextlib import redirect_stdout
import matplotlib.lines

buf = io.StringIO()
redirect_stdout(buf)

PARAMETERS = pd.read_csv("./parameters.csv")
print(PARAMETERS)
P_STAGE_CODE = PARAMETERS[ PARAMETERS["parameter"].isin(["Wake","NREM","REM"]) ]
print(P_STAGE_CODE)
STAGE_CODE = P_STAGE_CODE.set_index("value").to_dict()["parameter"]
STAGE_CODE_REVERSE = P_STAGE_CODE.set_index("parameter").to_dict()["value"]
PARAMETERS = PARAMETERS.set_index("parameter").to_dict()["value"]
PARAMETERS['epoch_length'] = int(PARAMETERS['epoch_length'])

# STAGE_CODE = {
#     1: "Wake",
#     2: "NREM",
#     3: "REM"
# }

# STAGE_CODE_REVERSE = {
#     "Wake": 1,
#     "NREM": 2,
#     "REM": 3
# }

# PARAMETERS = {
#     'Wake': 1,
#     'NREM': 2,
#     'REM': 3,
#     'epoch_length': 4  # 默认值，会被界面上的选择覆盖
# }


class Thread_run_all_files(QThread):
    signal = pyqtSignal('PyQt_PyObject')

    def __init__(self):
        QThread.__init__(self)
        self.filepath_list = []
        self.num_files = 0
        self.model_name = None      

    # 修正WAKE到REM的过渡
    @staticmethod
    def correct_sleep_transitions(df):

        """
        Corrects sleep stage transitions according to the protocol:
        - If REM follows WAKE directly, change REM to NREM
        - Enforces the general order: WAKE -> NREM -> REM
        Returns corrected dataframe with valid transitions
        """

        corrected_data = df.copy()
        stages = corrected_data.iloc[:, 1].values  # Assuming second column is the sleep stage
        stages = stages[::-1]

        for i in range(1, len(stages)):
            prev_stage = stages[i-1]
            current_stage = stages[i]
            
            # Correct WAKE -> REM transitions 
            if prev_stage == 3 and current_stage == 1:
                stages[i] = 2  
                #stages[i - 1] = 2 # Change WAKE to NREM，使用该行会使得标注功能失效
            else:
                continue

        corrected_data.iloc[:, 1] = stages[::-1]
        return corrected_data  

    def run(self):

        progress = 0
        self.signal.emit([progress,f"Selected Model: {self.model_name}.pkl"])

        self.num_files = len(self.filepath_list)
        self.model = joblib.load(f"./models/{self.model_name}.pkl")
        df = pd.DataFrame()
        for index, filepath in enumerate(self.filepath_list):

#            try:
            progress = (index+0.1)/self.num_files * 100
            starttime = time.time()
            self.signal.emit([progress,f"########\nStarted processing {filepath}"])
            self.signal.emit([progress,f"--{self.model_name}"])
            
            # 获取文件名和文件夹路径
            edfname = filepath.split("/")[-1]
            firstname = edfname.split('.edf')[0]
            folderpath = filepath.split(firstname)[0]
            csv_file = f"{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_features.csv"

            if os.path.exists(f"{folderpath}{csv_file}"):
                self.signal.emit([progress,f"--Feature file exists, skipped extracting features"])
            else:
                self.signal.emit([progress,f"--Started extracting features"])

                if self.model_name == "1_LightGBM-2EEG":
                    message1 = save_single_edf_to_csv_2eeg(edf_filepath=filepath, model_name = self.model_name, epoch_len=PARAMETERS['epoch_length'])
                if self.model_name == "2_LightGBM-1EEG":
                    message1 = save_single_edf_to_csv_1eeg(edf_filepath=filepath, model_name = self.model_name, epoch_len=PARAMETERS['epoch_length'])
                
                progress = (index+0.5)/self.num_files * 100
                if message1 is not None:
                    self.signal.emit([progress,f"--{message1}"])
                else:
                    self.signal.emit([progress,f"--Finished extracting features"])

            df = pd.read_csv(f"{folderpath}{csv_file}")
            features = df.columns[1:-3].tolist()
            print(features)
            df['score'] = df['score'].astype("float")
            X = df[features]   
            progress = (index+0.3)/self.num_files * 100
            self.signal.emit([progress,f"--Started predicting the scores"])

            # 调用模型，预测分期结果
            y_prediction = self.model.predict(X)
            progress = (index+0.5)/self.num_files * 100
            self.signal.emit([progress,f"--Finished prediction"])

            # 保存分期结果
            df_output = pd.DataFrame({
                "Epoch No.": list(range(len(y_prediction))),
                "Stage_Code": y_prediction
            })
            df_output["Stage_Code"] = df_output["Stage_Code"].astype("int")
            # 修正WAKE到REM的过渡
            df_output = self.correct_sleep_transitions(df_output)
            df_output["Stage"] = df_output["Stage_Code"].map(STAGE_CODE)

            # 应用最小持续时间修正，当epoch_length为4秒时
            # if PARAMETERS['epoch_length'] == 4:
            #     # Convert to numpy array for easier manipulation
            #     stages = df_output["Stage_Code"].values
            #     min_epochs = 2  # 8 seconds / 4 seconds per epoch = 2 epochs minimum
                
            #     # Forward pass to merge short segments
            #     i = 0
            #     while i < len(stages) - 1:
            #         # Find length of current stage
            #         current_stage = stages[i]
            #         segment_length = 1
            #         j = i + 1
            #         while j < len(stages) and stages[j] == current_stage:
            #             segment_length += 1
            #             j += 1
                    
            #         # If segment is too short, merge with neighboring stages
            #         if segment_length < min_epochs:
            #             # Get previous and next stages if they exist
            #             prev_stage = stages[i-1] if i > 0 else None
            #             next_stage = stages[j] if j < len(stages) else None
                        
            #             # Choose which stage to merge with
            #             if prev_stage is None:
            #                 merge_stage = next_stage
            #             elif next_stage is None:
            #                 merge_stage = prev_stage
            #             else:
            #                 # Merge with the most similar stage
            #                 merge_stage = prev_stage if abs(current_stage - prev_stage) <= abs(current_stage - next_stage) else next_stage
                        
            #             # Apply the merge
            #             stages[i:j] = merge_stage
                    
            #         i = j if j > i else i + 1
                
            #     # Update the DataFrame with corrected stages
            #     df_output["Stage_Code"] = stages
            #     # 修正WAKE到REM的过渡
            #     df_output = self.correct_sleep_transitions(df_output)
            #     df_output["Stage"] = df_output["Stage_Code"].map(STAGE_CODE)
            
            df_output.to_csv( f"{folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_scores.csv", index=False)

            progress = (index+0.6)/self.num_files * 100
            self.signal.emit([progress,f"--Saved the score file at {folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_scores.csv"])

            if variable.run_SHAP:
            ##
                if self.model_name == "1_LightGBM-2EEG":
                    self.signal.emit([progress,f"--Calculating SHAP values"])
                    explainer, shap_values_500samples, indices_500samples = get_shap(df, features, model = self.model)
                    progress = (index+0.9)/self.num_files * 100
                    self.signal.emit([progress,f"--Finished calculating SHAP values"])
                    with open(f"{folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_explainer.pickle", 'wb') as handle:
                        pickle.dump(explainer, handle, protocol=pickle.HIGHEST_PROTOCOL)
                    
                    with open(f"{folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_shap_500samples.pickle", 'wb') as handle:
                        pickle.dump(shap_values_500samples, handle, protocol=pickle.HIGHEST_PROTOCOL)

                    np.save(f"{folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_indicies_500samples.npy", indices_500samples)

                    self.signal.emit([progress,f"--Saved SHAP values at {folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_shap_500samples.pickle"])

                if self.model_name == "2_LightGBM-1EEG":
                    self.signal.emit([progress,f"--Calculating SHAP values"])
                    explainer, shap_values_500samples, indices_500samples = get_shap(df, features, model = self.model)
                    progress = (index+0.9)/self.num_files * 100
                    self.signal.emit([progress,f"--Finished calculating SHAP values"])
                    with open(f"{folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_explainer.pickle", 'wb') as handle:
                        pickle.dump(explainer, handle, protocol=pickle.HIGHEST_PROTOCOL)
                    
                    with open(f"{folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_shap_500samples.pickle", 'wb') as handle:
                        pickle.dump(shap_values_500samples, handle, protocol=pickle.HIGHEST_PROTOCOL)

                    np.save(f"{folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_indicies_500samples.npy", indices_500samples)

                    self.signal.emit([progress,f"--Saved SHAP values at {folderpath}{firstname}_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_shap_500samples.pickle"])
            

            progress = (index+1)/self.num_files * 100
            elapsed_time = time.time() - starttime
            print("elapsed_time: ", elapsed_time)
            self.signal.emit([progress,f"elapsed_time: {elapsed_time}"])

        progress = 100
        self.signal.emit([progress, "Done!"])



class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MyMainWindow, self).__init__(parent)
        self.setupUi(self)

        self.input_base_dir = './'
        self.filepath_list = []
        self.filename_list = [0]
        self.num_files = 0
        
        # 设置默认模型
        self.model_name = "2_LightGBM-1EEG"

        self.thread_run = Thread_run_all_files()
        self.thread_run.signal.connect(self.update_progress)

        self.button_input_files.clicked.connect(self.update_file_list)
        self.button_clear_input.clicked.connect(self.clear)
        self.button_run.clicked.connect(self.run_all_files)
        self.button_plot.clicked.connect(self.plot_edf)
        
        print(STAGE_CODE_REVERSE['Wake'])
        self.label_wake_code.setText(f"Wake: {STAGE_CODE_REVERSE['Wake']}")
        self.label_nrem_code.setText(f"NREM: {STAGE_CODE_REVERSE['NREM']}")
        self.label_rem_code.setText(f"REM: {STAGE_CODE_REVERSE['REM']}")
        print("epoch length: ", str(PARAMETERS['epoch_length']))
        self.combobox_epoch_length.setCurrentText(str(PARAMETERS['epoch_length']))

        self.combobox_select_n_epochs.currentIndexChanged.connect(self.update_display_n_epochs)
        self.button_goto_epoch.clicked.connect(self.update_display_goto_epoch)
        self.button_previous.clicked.connect(self.update_display_previous)
        self.button_previous_more.clicked.connect(self.update_display_previous_more)
        self.button_next.clicked.connect(self.update_display_next)
        self.button_next_more.clicked.connect(self.update_display_next_more)
        self.combobox_epoch_length.currentIndexChanged.connect(self.update_epoch_length)
        self.combobox_selected_epoch_stage.currentIndexChanged.connect(self.user_edit_stage)
        self.listWidget_input.itemSelectionChanged.connect(self.selectionChanged)

        self.map_colors = {1: "orange", 2: "blue", 3: "red"}
        self.map_stages = {1:"Wake", 2:"NREM", 3:"REM"}

        self.edf_path = None
        self.feature_file_path = None
        self.eeg_100zh_path = None
        self.score_file_path = None
        
        self.eeg_100hz = None
        self.n_channels = None
        self.df_score = None
        self.scores = None
        self.stages = None
        self.color_epochs = None
        self.score_file_user_edit_path = None
        self.df_score_user_edit = None
        self.n_epochs = None
        self.ch_names = None
        self.epochlabels = []  # 初始化标签列表

        # 添加一个列表来跟踪所有的高亮对象
        self.highlight_lines = []
        self.current_selected_epoch = None  # 添加这行来跟踪当前选中的epoch

    def update_file_list(self):
        added_filepath_list = QFileDialog.getOpenFileNames(
            self, 'open file', self.input_base_dir, "EDF/EDF+ Files (*.edf)"
        )[0]
        if len(added_filepath_list) > 0:
            self.filepath_list += added_filepath_list
            self.num_files = len(self.filepath_list)
            self.filename_list = self.filename_list * self.num_files

            self.listWidget_input.clear()
            for i in range(self.num_files):
                last_slash_index = self.filepath_list[i].rfind('/')
                self.input_base_dir = self.filepath_list[i][:last_slash_index]
                self.filename_list[i] = self.filepath_list[i][last_slash_index + 1:]
                self.listWidget_input.addItem(self.filepath_list[i])

        if self.num_files > 0:
            self.button_run.setEnabled(True)
    

    def clear(self):
        self.progressBar.setProperty("value", 0)
        self.label_status.setText("")
        self.filepath_list = []
        self.filename_list = [0]
        self.num_files = 0
        self.listWidget_input.clear()
        self.button_run.setEnabled(False)


    @pyqtSlot("PyQt_PyObject")
    def update_progress(self, emitted_signal):
        progress = emitted_signal[0]
        message = emitted_signal[1]
        self.progressBar.setProperty('value', '{:.0f}'.format(progress))
        self.textbox.appendPlainText(f"{message}\n")
        if progress == 100:
            self.button_run.setEnabled(True)
            self.button_input_files.setEnabled(True)
            self.button_clear_input.setEnabled(True)
            self.label_status.setText("Done")


    def run_all_files(self):
        self.button_run.setEnabled(False)
        self.button_input_files.setEnabled(False)
        self.button_clear_input.setEnabled(False)
        self.label_status.setText("Processing...")

        self.thread_run.filepath_list = []
        for index in range(self.listWidget_input.count()):
            self.thread_run.filepath_list.append(self.listWidget_input.item(index).text())
        
        self.thread_run.model_name = "2_LightGBM-1EEG"
        self.thread_run.start()


    def plot_edf(self):
        print("start plottinng lightgbm")

        print(self.listWidget_input.selectedItems())
        print(self.model_name)
        self.edf_path = self.listWidget_input.selectedItems()[0].text()
        self.feature_file_path = self.edf_path.replace(".edf", f"_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_features.csv")
        self.eeg_100zh_path = self.edf_path.replace(".edf", f"_{self.model_name}_rs_100hz.npy")
        self.score_file_path = self.edf_path.replace(".edf", f"_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_scores.csv")
        self.ch_names_path = self.edf_path.replace(".edf", f"_ch_names.pickle")
        
        self.ListWidget_warning.setText("")

        if os.path.exists(self.eeg_100zh_path):
            self.eeg_100hz = np.load(self.eeg_100zh_path)
            self.n_channels = self.eeg_100hz.shape[0]
            print("n_channels: ", self.n_channels)
        else:
            self.ListWidget_warning.setText(f"{self.eeg_100zh_path} doesn't exist, cannot visualize")
            return 
        
        if os.path.exists(self.ch_names_path):
            with open (self.ch_names_path, 'rb') as fp:
                self.ch_names = pickle.load(fp)
        else:
            self.ListWidget_warning.setText(f"{self.ch_names_path} doesn't exist, cannot visualize")
            return 

        if os.path.exists(self.score_file_path):
            self.df_score = pd.read_csv(self.score_file_path)
            self.scores = self.df_score["Stage_Code"].values
            self.stages = self.df_score["Stage"].values
            self.n_epochs = len(self.scores)
            self.color_epochs = [self.map_colors[e] for e in self.scores]
        else:  
            # self.button_plot.setEnabled(True)
            self.ListWidget_warning.setText(f"{self.score_file_path} doesn't exist, cannot visualize")
            return 

        self.score_file_user_edit_path = self.edf_path.replace(".edf", f"_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_scores_user_edit.csv")
        self.df_score_user_edit = None
        if os.path.exists(self.score_file_user_edit_path):
            self.df_score_user_edit = pd.read_csv(self.score_file_user_edit_path)

        self.figure.clf()
        self.canvas.draw()
        # self.figure_shap_global.clf()
        # self.canvas_shap_global.draw()
        # self.figure_shap_epoch.clf()
        # self.canvas_shap_epoch.draw()
        
        n_epochs_display = self.get_n_epochs_display()


        
        self.max_time = int(len(self.eeg_100hz[0])/100)   # 100hz sampling frequency
        time_sec = np.arange(0, self.max_time, 0.01)
        time_epochs_start = np.arange(len(self.scores)) * PARAMETERS['epoch_length']
        time_epochs_end = time_epochs_start + PARAMETERS['epoch_length']
        
        df = pd.read_csv(self.feature_file_path)

        self.features = df.columns[1:-3].tolist()
        df['score'] = self.df_score['Stage_Code'].astype("float")
        X = df[self.features]
        
        self.n_axes = self.n_channels + 1
        # 使用的EEG和EMG通道编号
        eeg_no = 2
        emg_no = 1
        # ax1 plots first channel in eeg file
        self.ax1 = self.figure.add_subplot(self.n_axes,1,2)
        self.ax1.plot(time_sec, self.eeg_100hz[eeg_no])
        self.ax1.get_xaxis().set_visible(False)
        self.ax1.spines['top'].set_visible(False)
        self.ax1.spines['right'].set_visible(False)
        self.ax1.spines['bottom'].set_visible(False)
        self.epoch_start = 0
        self.ax1.set_xlim(self.epoch_start,PARAMETERS['epoch_length']*n_epochs_display)
        self.ax1.set_ylim(-0.0004, 0.0004)
        # 将V转换为µV (1V = 1,000,000 µV)
        self.ax1.yaxis.set_major_formatter(lambda x, pos: f'{x*1e6:.0f}')
        self.ax1.set_ylabel(f"{self.ch_names[eeg_no]}\n(µV)",rotation=0,fontsize=8,ha="right")
        self.ax1.yaxis.set_label_coords(-0.1, 0.5)

        # ax2 plots 2nd channel in eeg file
        ax2 = self.figure.add_subplot(self.n_axes,1,3, sharex=self.ax1)
        ax2.plot(time_sec, self.eeg_100hz[emg_no])
        ax2.get_xaxis().set_visible(False)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['bottom'].set_visible(False)
        ax2.set_ylim(-0.0002, 0.0002)
        ax2.yaxis.set_major_formatter(lambda x, pos: f'{x*1e6:.0f}')
        ax2.set_ylabel(f"{self.ch_names[emg_no]}\n(µV)",rotation=0,fontsize=8,ha="right")
        ax2.yaxis.set_label_coords(-0.1, 0.5)

        ax3 = self.figure.add_subplot(self.n_axes,1,4, sharex=self.ax1)
        ax3.plot(time_sec, self.eeg_100hz[0])
        ax3.get_xaxis().set_visible(False)
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        ax3.spines['bottom'].set_visible(False)
        ax3.set_ylim(-0.0001, 0.0001)
        ax3.yaxis.set_major_formatter(lambda x, pos: f'{x*1e6:.0f}')
        ax3.set_ylabel(f"{self.ch_names[0]}\n(µV)",rotation=0,fontsize=8,ha="right")
        ax3.yaxis.set_label_coords(-0.1, 0.5)

        ax4 = self.figure.add_subplot(self.n_axes,1,5, sharex=self.ax1)
        ax4.plot(time_sec, self.eeg_100hz[3])
        ax4.get_xaxis().set_visible(False)
        ax4.spines['top'].set_visible(False)
        ax4.spines['right'].set_visible(False)
        ax4.spines['bottom'].set_visible(False)
        ax4.set_ylim(-0.0004, 0.0004)
        ax4.yaxis.set_major_formatter(lambda x, pos: f'{x*1e6:.0f}')
        ax4.set_ylabel(f"{self.ch_names[3]}\n(µV)",rotation=0,fontsize=8,ha="right")
        ax4.yaxis.set_label_coords(-0.1, 0.5)

        # 加速度计通道保持原样
        ax5 = self.figure.add_subplot(self.n_axes,1,6, sharex=self.ax1)
        ax5.plot(time_sec, self.eeg_100hz[4])
        ax5.get_xaxis().set_visible(False)
        ax5.spines['top'].set_visible(False)
        ax5.spines['right'].set_visible(False)
        ax5.spines['bottom'].set_visible(False)
        ax5.set_ylim(-1500, 1500)
        ax5.set_ylabel(f"{self.ch_names[4]}\n(mG)",rotation=0,fontsize=8,ha="right")
        ax5.yaxis.set_label_coords(-0.1, 0.5)

        ax6 = self.figure.add_subplot(self.n_axes,1,7, sharex=self.ax1)
        ax6.plot(time_sec, self.eeg_100hz[5])
        ax6.get_xaxis().set_visible(False)
        ax6.spines['top'].set_visible(False)
        ax6.spines['right'].set_visible(False)
        ax6.spines['bottom'].set_visible(False)
        ax6.set_ylim(-1500, 1500)
        ax6.set_ylabel(f"{self.ch_names[5]}\n(mG)",rotation=0,fontsize=8,ha="right")
        ax6.yaxis.set_label_coords(-0.1, 0.5)

        if self.n_channels == 7:
            ax7 = self.figure.add_subplot(self.n_axes,1,8, sharex=self.ax1)
            ax7.plot(time_sec, self.eeg_100hz[6])
            ax7.set_xlabel("Time (sec)")
            ax7.spines['top'].set_visible(False)
            ax7.spines['right'].set_visible(False)
            ax7.spines['bottom'].set_visible(False)
            ax7.set_ylim(-1500, 1500)
            ax7.set_ylabel(f"{self.ch_names[6]}\n(mG)",rotation=0,fontsize=8,ha="right")
            ax7.yaxis.set_label_coords(-0.1, 0.5)

       

        # ax_hypnogram
        ax_hypnogram = self.figure.add_subplot(self.n_axes,1,1, sharex=self.ax1)
        ax_hypnogram.plot(time_epochs_start, self.scores, "|", markersize=7, color="black")
        ax_hypnogram.hlines(self.scores, time_epochs_start, time_epochs_end, colors=self.color_epochs, linewidths=3)
        ax_hypnogram.set_yticks([1,2,3])
        ax_hypnogram.set_yticklabels(["Wake", "NREM", "REM"])
        ax_hypnogram.get_xaxis().set_visible(False)
        ax_hypnogram.spines['top'].set_visible(False)
        ax_hypnogram.spines['right'].set_visible(False)
        ax_hypnogram.spines['bottom'].set_visible(False)

        if self.df_score_user_edit is not None:

            difference_locations = np.where(self.df_score["Stage_Code"] != self.df_score_user_edit["Stage_Code"])
            scores_changed_to = self.df_score_user_edit["Stage_Code"].values[difference_locations]
            
            for i_epoch, i_score in zip(difference_locations[0], scores_changed_to):

                time_epoch_start = PARAMETERS['epoch_length'] * i_epoch
                time_epoch_end = time_epoch_start + PARAMETERS['epoch_length']

                ax_hypnogram.hlines(i_score, time_epoch_start, time_epoch_end, 
                                        colors=self.map_colors[i_score], linewidths=3,
                                        linestyles="dotted")

        def onclick_lightgbm(event):
            print('%s click: button=%d, x=%d, y=%d, xdata=%f, ydata=%f' %
                ('double' if event.dblclick else 'single', event.button,
                event.x, event.y, event.xdata, event.ydata))
                
            new_epoch = int(event.xdata//PARAMETERS['epoch_length'])
            print("clicked epoch: ", new_epoch)

            # 清除所有现有的高亮
            for line in self.highlight_lines:
                try:
                    line.remove()
                except:
                    pass
            self.highlight_lines.clear()

            # 如果点击的是当前已选中的epoch，则取消选中
            if new_epoch == self.current_selected_epoch:
                self.current_selected_epoch = None
                self.combobox_selected_epoch_stage.setEnabled(False)
                self.canvas.draw()
                return

            # 如果是新的epoch，则高亮显示
            self.current_selected_epoch = new_epoch
            self.epoch_index_shap = new_epoch
            x = X.loc[[self.epoch_index_shap],:]
            
            # 添加新的高亮
            for ax in self.figure.axes:
                line = ax.hlines(
                    0,
                    self.epoch_index_shap*PARAMETERS['epoch_length'],
                    (self.epoch_index_shap+1)*PARAMETERS['epoch_length'],
                    colors="pink", linewidths=100, alpha=0.4
                )
                self.highlight_lines.append(line)

            if event.button==3:
                if variable.run_SHAP:
                    self.figure_shap_epoch.clf()
                    shap_values_x = explainer.shap_values(x)
                    self.plot_shap_epoch(shap_values_x)

            self.canvas.draw()

            # update combobox_selected_epoch_stage
            self.combobox_selected_epoch_stage.setEnabled(True)
            self.combobox_selected_epoch_stage.setCurrentText(self.stages[self.epoch_index_shap])
        
        cid = self.canvas.mpl_connect('button_press_event', onclick_lightgbm)
        self.canvas.draw()
        print("finished plotting traces")

        # Enable the buttons
        self.combobox_select_n_epochs.setEnabled(True)
        self.button_goto_epoch.setEnabled(True)
        self.button_previous.setEnabled(True)
        self.button_previous_more.setEnabled(True)
        self.button_next.setEnabled(True)
        self.button_next_more.setEnabled(True)

        if variable.run_SHAP:

            explaner_path = self.edf_path.replace(".edf", f"_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_explainer.pickle")
            shap_500samples_path = self.edf_path.replace(".edf", f"_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_shap_500samples.pickle")
            indicies_500samples_path = self.edf_path.replace(".edf", f"_{self.model_name}_epoch_length_{PARAMETERS['epoch_length']}_sec_indicies_500samples.npy")

            ## Plot global SHAP values

            with open(explaner_path, 'rb') as handle:
                explainer = pickle.load(handle)

            with open(shap_500samples_path, 'rb') as handle:
                shap_values_500samples = pickle.load(handle)

            indicies_500samples = np.load(indicies_500samples_path).tolist()

            df_500samples = df.loc[indicies_500samples,]
            # self.plot_shap_global(shap_values_500samples, df_500samples, indicies_500samples)


    def get_n_epochs_display(self):
        n_epochs_display = 10
        selected_n_epochs = self.combobox_select_n_epochs.currentText()
        if selected_n_epochs == "All":
            n_epochs_display = self.n_epochs
        else:
            n_epochs_display = int(selected_n_epochs)
        return n_epochs_display


    def update_display_goto_epoch(self):
        n_epochs_display = self.get_n_epochs_display()

        self.epoch_start, done = QInputDialog.getInt(
           self, 'Input Dialog', 'Enter the Epoch You Want to View:')

        self.figure.axes[0].set_xlim(PARAMETERS['epoch_length']*self.epoch_start, PARAMETERS['epoch_length']*(self.epoch_start + n_epochs_display))
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()


    def update_display_n_epochs(self):
        try:
            n_epochs_display = self.get_n_epochs_display()
            
            # 确保epoch_start不会导致显示超出数据范围
            if self.epoch_start + n_epochs_display > len(self.scores):
                self.epoch_start = max(0, len(self.scores) - n_epochs_display)
            
            # 更新x轴范围
            for ax in self.figure.axes:
                ax.set_xlim(
                    PARAMETERS['epoch_length'] * self.epoch_start,
                    PARAMETERS['epoch_length'] * (self.epoch_start + n_epochs_display)
                )
            
            self.update_epoch_labels(n_epochs_display)
            self.canvas.draw()
        except Exception as e:
            print(f"Error in update_display_n_epochs: {str(e)}")
            self.ListWidget_warning.setText(f"Error updating display: {str(e)}")


    def update_epoch_labels(self, n_epochs_display):
        # 确保有效的轴索引
        if not hasattr(self, 'epochlabels'):
            self.epochlabels = []
        
        # 清除有的标签
        for label in self.epochlabels:
            try:
                label.remove()
            except:
                pass
        self.epochlabels = []

        # # 只在显示少于100个epoch时添加标签
        # if n_epochs_display < 100:
        #     # 获取最后一个轴（通常是底部的轴）
        #     bottom_ax = self.figure.axes[-1]
            
        #     # 确保epoch_start不会导致标签超出数据范围
        #     max_epochs = len(self.scores)
        #     for i in range(min(10, n_epochs_display)):
        #         epoch_num = self.epoch_start + i
        #         if epoch_num < max_epochs:  # 确保不超出数据范围
        #             self.epochlabels.append(
        #                 bottom_ax.annotate(
        #                     str(epoch_num), 
        #                     ((epoch_num + 0.5) * PARAMETERS['epoch_length'], 1),
        #                     ha="center",
        #                     va="bottom"
        #                 )
        #             )
        # 只在显示少于100个epoch时添加标签
        if n_epochs_display <= 50:  # 修改这里以包含20和50的情况
            # 获取最后一个轴（通常是底部的轴）
            bottom_ax = self.figure.axes[-1]
            
            # 确保epoch_start不会导致标签超出数据范围
            max_epochs = len(self.scores)
            
            # 根据显示的epoch数量调整标签间隔
            if n_epochs_display <= 20:
                label_interval = 1  # 每个epoch都显示标签
            else:  # 50个epochs的情况
                label_interval = 5  # 每5个epoch显示一个标签
            
            for i in range(0, n_epochs_display, label_interval):
                epoch_num = self.epoch_start + i
                if epoch_num < max_epochs:  # 确保不超出数据范围
                    self.epochlabels.append(
                        bottom_ax.annotate(
                            str(epoch_num), 
                            ((epoch_num + 0.5) * PARAMETERS['epoch_length'], 1),
                            ha="center",
                            va="bottom"
                        )
                    )
        
        # 重绘画布
        self.canvas.draw()


    def update_display_previous(self):
        n_epochs_display = self.get_n_epochs_display()
        self.epoch_start -= 1
        self.figure.axes[0].set_xlim(PARAMETERS['epoch_length']*self.epoch_start, PARAMETERS['epoch_length']*(self.epoch_start + n_epochs_display) )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()


    def update_display_previous_more(self):
        n_epochs_display = self.get_n_epochs_display()
        self.epoch_start -= n_epochs_display
        self.figure.axes[0].set_xlim(PARAMETERS['epoch_length']*self.epoch_start, PARAMETERS['epoch_length']*(self.epoch_start + n_epochs_display) )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()


    def update_display_next(self):
        n_epochs_display = self.get_n_epochs_display()
        self.epoch_start += 1
        self.figure.axes[0].set_xlim(PARAMETERS['epoch_length']*self.epoch_start, PARAMETERS['epoch_length']*(self.epoch_start + n_epochs_display) )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()


    def update_display_next_more(self):
        n_epochs_display = self.get_n_epochs_display()
        self.epoch_start += n_epochs_display
        self.figure.axes[0].set_xlim(PARAMETERS['epoch_length']*self.epoch_start, PARAMETERS['epoch_length']*(self.epoch_start + n_epochs_display) )
        self.update_epoch_labels(n_epochs_display)
        self.canvas.draw()


    def update_epoch_length(self):
        PARAMETERS['epoch_length'] = int(self.combobox_epoch_length.currentText())
        pd.DataFrame(PARAMETERS, index=[0]).T\
            .reset_index(drop=False)\
            .rename(columns={"index":"parameter", 0:"value"})\
            .to_csv("parameters.csv", index=False)


    def selectionChanged(self):
        if self.listWidget_input.count() > 0:
        #if int(self.combobox_epoch_length.currentText()) == 
            self.button_plot.setEnabled(True)        
            
        
    def user_edit_stage(self):
        ## write to csv file
        if self.df_score_user_edit is None:
            self.df_score_user_edit = self.df_score

        stage_user_edit = self.combobox_selected_epoch_stage.currentText()
        score_user_edit = STAGE_CODE_REVERSE[stage_user_edit]
        self.df_score_user_edit.loc[self.df_score_user_edit["Epoch No."]==self.epoch_index_shap, "Stage"] =  stage_user_edit
        self.df_score_user_edit.loc[self.df_score_user_edit["Epoch No."]==self.epoch_index_shap, "Stage_Code"] = score_user_edit
        
        self.df_score_user_edit.to_csv(self.score_file_user_edit_path, index=False)

        ## update plot

        ax_hypnogram_edit = self.figure.get_axes()[self.n_axes-1]
        print(ax_hypnogram_edit)

        time_epoch_start = PARAMETERS['epoch_length'] * self.epoch_index_shap
        print(time_epoch_start)
        time_epoch_end = time_epoch_start + PARAMETERS['epoch_length']

        ax_hypnogram_edit.hlines(score_user_edit, time_epoch_start, time_epoch_end, 
                                 colors=self.map_colors[score_user_edit], linewidths=3,
                                 linestyles="dotted")
        
        self.canvas.draw()

        # time_epochs_start = np.arange(0, self.max_time, PARAMETERS['epoch_length'])
        # time_epochs_end = time_epochs_start + PARAMETERS['epoch_length']
        # ax_hypnogram.hlines(scores, time_epochs_start, time_epochs_end, colors=color_epochs, linewidths=3)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWin = MyMainWindow()
#    sys.stdout=myWin

    # 重定向标准输出到UI的文本框
    # logger = QTextEditLogger(myWin.textbox)
    # sys.stdout = logger
    # sys.stderr = logger  # 同时重定向错误输出
    myWin.show()
    sys.exit(app.exec_())

print('Done')
