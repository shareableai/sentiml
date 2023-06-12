import warnings

import lightning.pytorch as pl
from lightning.pytorch.callbacks import EarlyStopping, LearningRateMonitor
import pandas as pd
import torch
from pandas.errors import SettingWithCopyWarning

from pytorch_forecasting import GroupNormalizer, TimeSeriesDataSet
from pytorch_forecasting.data import NaNLabelEncoder
from pytorch_forecasting.data.examples import generate_ar_data
from pytorch_forecasting.metrics import NormalDistributionLoss
from pytorch_forecasting.models.deepar import DeepAR

from observe_dag.trackers import Observer
from observe_dag.tracking_type import TrackingType

warnings.simplefilter("error", category=SettingWithCopyWarning)
Observer.track(TrackingType.Processing)
data = generate_ar_data(seasonality=10.0, timesteps=400, n_series=10)
data["static"] = "2"
data["date"] = pd.Timestamp("2020-01-01") + pd.to_timedelta(data.time_idx, "D")
validation = data.series.sample(5)

max_encoder_length = 60
max_prediction_length = 20

training_cutoff = data["time_idx"].max() - max_prediction_length

training = TimeSeriesDataSet(
    data[lambda x: x.series.isin(validation)],
    time_idx="time_idx",
    target="value",
    categorical_encoders={"series": NaNLabelEncoder().fit(data.series)},
    group_ids=["series"],
    static_categoricals=["static"],
    min_encoder_length=max_encoder_length,
    max_encoder_length=max_encoder_length,
    min_prediction_length=max_prediction_length,
    max_prediction_length=max_prediction_length,
    time_varying_unknown_reals=["value"],
    time_varying_known_reals=["time_idx"],
    target_normalizer=GroupNormalizer(groups=["series"]),
    add_relative_time_idx=False,
    add_target_scales=True,
    randomize_length=None,
)

validation = TimeSeriesDataSet.from_dataset(
    training,
    data[lambda x: x.series.isin(validation)],
    # predict=True,
    stop_randomization=True,
)
batch_size = 64
train_dataloader = training.to_dataloader(
    train=True, batch_size=batch_size, num_workers=0
)
val_dataloader = validation.to_dataloader(
    train=False, batch_size=batch_size, num_workers=0
)

# save datasets
training.save("training.pkl")
validation.save("validation.pkl")

early_stop_callback = EarlyStopping(
    monitor="val_loss", min_delta=1e-4, patience=5, verbose=False, mode="min"
)
lr_logger = LearningRateMonitor()

trainer = pl.Trainer(
    max_epochs=10,
    accelerator="cpu",
    devices="auto",
    gradient_clip_val=0.1,
    limit_train_batches=30,
    limit_val_batches=3,
    callbacks=[lr_logger, early_stop_callback],
)
deepar = DeepAR.from_dataset(
    training,
    learning_rate=0.1,
    hidden_size=32,
    dropout=0.1,
    loss=NormalDistributionLoss(),
    log_interval=10,
    log_val_interval=3,
)
Observer.track(TrackingType.Training)
trainer.fit(
    deepar,
    train_dataloaders=train_dataloader,
    val_dataloaders=val_dataloader,
)
Observer.track(TrackingType.Inference)
# calcualte mean absolute error on validation set
actuals = torch.cat([y for x, (y, weight) in iter(val_dataloader)])
predictions = deepar.predict(val_dataloader)
print(f"Mean absolute error of model: {(actuals - predictions).abs().mean()}")
Observer.stop()