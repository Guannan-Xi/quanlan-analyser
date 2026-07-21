import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from Model import SVMModel
from Data import DataLoader, DataFeature

# from sklearn.preprocessing import OneHotEncoder
# from mlxtend.plotting import plot_decision_regions

if __name__ == '__main__':
    # data
    file_path = r"F:\data\ExamleData_seizure_15412\ExamleData_seizure_15412.edf"
    anno_path = r"F:\data\ExamleData_seizure_15412\Labels_eizures_15412.csv"
    # anno_path = None
    model_path = r"E:\py_code\Seizure-Detection\Pkl\model_bandpower.pkl"


    dataloader = DataLoader(filename=file_path, anno_path=anno_path)
    dataloader.get_data()
    data = dataloader.slice_data()
    anno = dataloader.get_annoadation()
    sample_rate = dataloader.sample_rate    

    # data features
    data_feature = DataFeature(sample_rate)
    X_train = data_feature.get_features(data)
    
    # model
    model = SVMModel()
    svm_model = model.eval(model_path)
    model.val(X_train, anno)