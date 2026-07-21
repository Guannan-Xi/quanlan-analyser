

import pickle
import numpy as np
import matplotlib.pyplot as plt
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, LabelBinarizer, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, precision_score, recall_score, f1_score, confusion_matrix, \
    ConfusionMatrixDisplay


class SVMModel:
    def __init__(self):
        self.pipe_svc_linear = None
        self.RANDOM_STATE = 0
        self.losses = []
        self.lb = LabelBinarizer()
        self.le = LabelEncoder()

    def train(self, X_data, y_data, save_path, epochs=10):
        self.pipe_svc_linear = Pipeline([
            ('scl', StandardScaler()),
            ('clf', SVC(C=100, kernel='rbf', class_weight='balanced', random_state=self.RANDOM_STATE, probability=True))
        ])
        print(self.pipe_svc_linear)

        # Fill missing values in X_data with 0
        X_data = X_data.fillna(0)

        # Encode labels as integers
        y_data = self.le.fit_transform(y_data)

        # Split the data into training and validation sets
        X_train, X_val, y_train, y_val = train_test_split(X_data, y_data, test_size=0.2, random_state=self.RANDOM_STATE)

        # Fit the LabelBinarizer
        self.lb.fit(y_train)

        # Training with epochs
        for epoch in range(epochs):
            self.pipe_svc_linear.fit(X_train, y_train)
            val_accuracy = self.pipe_svc_linear.score(X_val, y_val)
            val_loss = self.compute_loss(X_val, y_val)
            self.losses.append(val_loss)
            print(f'Epoch {epoch + 1}/{epochs} - Validation Accuracy: {val_accuracy:.3f} - Loss: {val_loss:.3f}')

        # Save the trained model to the specified path
        with open(save_path, 'wb') as f:
            pickle.dump(self.pipe_svc_linear, f)
        print(f'Model saved to {save_path}')

        # Evaluate the model on the validation set
        self.val(X_val, y_val)
        # Plot confusion matrix and loss graph
        self.plot_confusion_matrix(X_val, y_val)
        self.plot_loss()

    def compute_loss(self, X_data, y_data):
        y_proba = self.pipe_svc_linear.predict_proba(X_data)
        y_true = self.lb.transform(y_data)
        loss = -np.mean(np.sum(y_true * np.log(y_proba), axis=1))
        return loss

    def eval(self, model_path):
        # Load the model from the specified path
        with open(model_path, 'rb') as f:
            self.pipe_svc_linear = pickle.load(f)
        return self.pipe_svc_linear

    def val(self, X_data, y_data):
        # Fill missing values in X_data with 0
        X_data = X_data.fillna(0)

        # Make predictions
        y_pred = self.pipe_svc_linear.predict(X_data)

        # Print evaluation metrics
        print(f'Validation Accuracy: {self.pipe_svc_linear.score(X_data, y_data):.3f}')
        print(classification_report(y_data, y_pred))

        precision = precision_score(y_data, y_pred, average='weighted')
        recall = recall_score(y_data, y_pred, average='weighted')
        f1 = f1_score(y_data, y_pred, average='weighted')

        print(f'Precision: {precision:.3f}')
        print(f'Recall: {recall:.3f}')
        print(f'F1 Score: {f1:.3f}')

    def plot_confusion_matrix(self, X_data, y_data):
        y_pred = self.pipe_svc_linear.predict(X_data)
        cm = confusion_matrix(y_data, y_pred)
        disp = ConfusionMatrixDisplay(confusion_matrix=cm)
        disp.plot()
        plt.title('Confusion Matrix')
        plt.show()

    def plot_loss(self):
        plt.plot(self.losses)
        plt.title('Loss over epochs')
        plt.xlabel('Epoch')
        plt.ylabel('Loss')
        plt.show()

    def predict(self, X_data):

        # Make predictions
        y_label = self.pipe_svc_linear.predict(X_data)
        return y_label
