import time
import pandas as pd
import matplotlib.pyplot as plt

from Model import SVMModel
from Data import DataLoader, DataFeature


from mlxtend.plotting import plot_decision_regions

if __name__ == '__main__':
    # data
    file_path = r"F:\data\ExamleData_seizure_15412\ExamleData_seizure_15412.edf"
    anno_path = None
    model_path = r"E:\py_code\Seizure-Detection\Pkl\model_bandpower.pkl"

    start = time.time()
    dataloader = DataLoader(filename=file_path, anno_path=anno_path)
    dataloader.get_data()

    # data: n * 1s
    data = dataloader.slice_data()
    sample_rate = dataloader.sample_rate

    # data features
    data_feature = DataFeature(sample_rate)
    X_train = data_feature.get_features(data)

    model = SVMModel()
    model.eval(model_path)
    y_label = model.predict(X_train)

    print("annotation: ", y_label)
    print("time: ", time.time() - start)
