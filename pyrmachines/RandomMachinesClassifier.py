from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.validation import check_X_y, check_array, check_is_fitted
from sklearn.utils.multiclass import unique_labels
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.metrics.pairwise import laplacian_kernel
import numpy as np
import pandas as pd

# TODO: Implementar argumentos do kernel laplaciano
# TODO: Implementar automatic_tuning
# TODO: Trocar a funcao log pois esta penalizando acc = 1


class RandomMachinesClassifier(BaseEstimator, ClassifierMixin):

    def __init__(self,
                 poly_scale=2,
                 coef0_poly=0,
                 gamma_rbf=1,
                 degree=2,
                 cost=10,
                 boots_size=25, seed_bootstrap=None, automatic_tuning=False):
        """
        Parameters:
            poly_scale: float, default=2
            coef0_poly: float, default=0
            gamma_rbf: float, default=1
            degree: float, default=2
            cost: float, default=10
            boots_size: float, default=25
            automatic_tuning: bool, default=False
        """
        self.poly_scale = poly_scale
        self.coef0_poly = coef0_poly
        self.gamma_rbf = gamma_rbf
        self.degree = degree
        self.cost = cost
        self.boots_size = boots_size
        self.seed_bootstrap = seed_bootstrap
        self.automatic_tuning = automatic_tuning

    def fit(self, X, y):
        # Check that X and y have correct shape
        X, y = check_X_y(X, y)
        # Store the classes seen during fit
        self.classes_ = unique_labels(y)
        self.X_ = X
        self.y_ = y

        # Set seed for bootstrap and kernel selection
        if (self.seed_bootstrap is not None):
            np.random.seed(self.seed_bootstrap)

        # Kernel types
        kernel_type = ["linear", "poly", "rbf", "laplacian"]

        # Training single model and calculating accuracy
        early_models = []
        for kernel in kernel_type:
            model = self.fit_kernel(X, y, kernel)
            predict = model.predict(X)
            accuracy = accuracy_score(y, predict)
            if (accuracy == 1):
                log_acc = 1
            else:
                log_acc = np.log(np.divide(accuracy, np.subtract(1, accuracy)))
            if (np.isinf(log_acc)):
                log_acc = 1
            early_models.append(
                {'kernel': kernel, "model": model, 'accuracy': accuracy, 'metric': log_acc})
            # print(f"Kernel: {kernel} - Accuracy: {accuracy} - Log: {log_acc}")

        # Calculating the probability of each kernel
        prob_weights_sum = sum(item["metric"] for item in early_models)
        lambda_values = {}
        for model in early_models:
            prob_weights = model["metric"] / prob_weights_sum
            if (prob_weights < 0):
                prob_weights = 0
            model["prob_weights"] = prob_weights
            lambda_values[model["kernel"]] = prob_weights
            print(
                f"Kernel: {model['kernel']} - Accuracy: {model['accuracy']} - Prob_weights: {prob_weights}")

        #  sampling a kernel function with probability = lambda_values
        p = [item["prob_weights"] for item in early_models]
        random_kernel = np.random.choice(
            kernel_type, self.boots_size, replace=True, p=p)

        # Creating the bootstrap sample
        boots_samples_index = []
        for i in range(self.boots_size):
            nrow = len(X)
            nclass = len(self.classes_)
            train_index = np.random.choice(
                range(nrow), size=nrow, replace=True)
            table = np.unique(y[train_index], return_counts=True)
            ntable = len(table[0])
            while (ntable != nclass):
                train_index = np.random.choice(
                    range(nrow), size=nrow, replace=True)
                table = np.unique(y[train_index], return_counts=True)
                ntable = len(table[0])
            boots_samples_index.append(train_index)

        # Training the models
        models = []
        for index in range(len(random_kernel)):
            kernel = random_kernel[index]
            boot_sample_index = boots_samples_index[index]
            X_train = X[boot_sample_index]
            y_train = y[boot_sample_index]
            X_test = np.delete(X, boot_sample_index, axis=0)
            y_test = np.delete(y, boot_sample_index, axis=0)
            model = self.fit_kernel(X_train, y_train, kernel)
            # out of bag
            predict_oobg = model.predict(X_test)
            accuracy = accuracy_score(y_test, predict_oobg)
            kernel_weight = 1 / (accuracy ** 2)
            models.append({'model': model, 'kernel': kernel,
                           'accuracy': accuracy, 'kernel_weight': kernel_weight, index: boot_sample_index})
        self.models = models

        return self

    def predict(self, X):
        # Check if fit has been called
        check_is_fitted(self)
        # Input validation
        X = check_array(X)

        nrow = X.shape[0]
        ncol = len(self.classes_)
        models = self.models
        predict_df = pd.DataFrame(
            np.zeros((nrow, ncol)), columns=self.classes_)
        for model in models:
            model_weights = model["kernel_weight"]
            predict = model["model"].predict(X)
            for i in range(len(predict)):
                predict_df.loc[i, predict[i]] += model_weights
        return list(predict_df.idxmax(axis=1))

    def fit_kernel(self, X_train, y_train, kernel):
        if (self.automatic_tuning):
            if (kernel == "laplacian"):
                model = SVC(kernel=laplacian_kernel).fit(X_train, y_train)
            else:
                model = SVC(kernel=kernel).fit(X_train, y_train)
            return model
        else:
            if (kernel == "linear"):
                model = SVC(kernel="linear",
                            C=self.cost,
                            probability=True,
                            verbose=0).fit(X_train, y_train)
            elif (kernel == "poly"):
                model = SVC(kernel="poly",
                            C=self.cost,
                            gamma=self.poly_scale,
                            probability=True,
                            coef0=self.coef0_poly,
                            degree=self.degree,
                            verbose=0).fit(X_train, y_train)
            elif (kernel == "rbf"):
                model = SVC(kernel="rbf",
                            C=self.cost,
                            probability=True,
                            gamma=self.gamma_rbf,
                            verbose=0).fit(X_train, y_train)
            elif (kernel == "laplacian"):
                model = SVC(kernel=laplacian_kernel,
                            C=self.cost,
                            probability=True,
                            verbose=0).fit(X_train, y_train)
            return model