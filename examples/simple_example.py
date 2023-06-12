from sklearn import datasets, svm
from sklearn.model_selection import train_test_split

from observe_dag.trackers import Observer
from observe_dag.tracking_type import TrackingType


if __name__ == "__main__":
    digits = datasets.load_digits()

    n_samples = len(digits.images)
    data = digits.images.reshape((n_samples, -1))

    # Create a classifier: a support vector classifier
    clf = svm.SVC(gamma=0.001)

    # Split data into 50% train and 50% test subsets
    X_train, X_test, y_train, y_test = train_test_split(
        data, digits.target, test_size=0.5, shuffle=False
    )
    Observer.track(TrackingType.Training)
    # Learn the digits on the train subset
    clf.fit(X_train, y_train)
    Observer.stop()
    Observer.track(TrackingType.Inference)
    # Predict the value of the digit on the test subset
    predicted = clf.predict(X_test)
    Observer.stop()