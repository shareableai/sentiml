from xgboost import XGBClassifier
# read data
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

from sentiml.trackers import Observer
from sentiml.tracking_type import TrackingType
from sentiml.track_class import track_class


if __name__ == "__main__":
    Observer.track(TrackingType.Processing)
    data = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(data['data'], data['target'], test_size=.2)
    # create model instance
    bst = XGBClassifier(n_estimators=2, max_depth=2, learning_rate=1, objective='binary:logistic')
    track_class(bst)
    # fit model
    Observer.track(TrackingType.Training)
    bst.fit(X_train, y_train)
    # make predictions
    Observer.track(TrackingType.Inference)
    preds = bst.predict(X_test)
    Observer.stop()