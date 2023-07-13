from sklearn import datasets, svm
from sklearn.model_selection import train_test_split

from observer.trackers import Observer
from observer.tracking_type import TrackingType
from observer.track_class import track_class


if __name__ == "__main__":
    digits = datasets.load_digits()

    n_samples = len(digits.images)
    data = digits.images.reshape((n_samples, -1))

    # Create a classifier: a support vector classifier
    clf = svm.SVC(gamma=0.001)
    track_class(clf)    

    # Split data into 50% train and 50% test subsets
    X_train, X_test, y_train, y_test = train_test_split(
        data, digits.target, test_size=0.5, shuffle=False
    )
    Observer.track(TrackingType.Training)
    # Learn the digits on the train subset
    clf.fit(X_train, y_train)
    Observer.track(TrackingType.Inference)
    # Predict the value of the digit on the test subset
    predicted = clf.predict(X_test)
    Observer.stop()
