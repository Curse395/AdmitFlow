from __future__ import annotations

import math

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


def aggregate_time_series(df: pd.DataFrame) -> pd.DataFrame:
    aggregate = df.groupby("cycle_year", as_index=False).agg(
        applications=("applicant_id", "count"),
        admissions=("admitted", "sum"),
        enrolments=("enrolled", "sum"),
    )
    aggregate = aggregate.sort_values("cycle_year").reset_index(drop=True)
    return aggregate


def evaluate_forecast(df: pd.DataFrame) -> dict:
    series = aggregate_time_series(df)
    series["year_index"] = np.arange(len(series))
    X = series["year_index"].to_numpy().reshape(-1, 1)
    y = series["enrolments"].to_numpy()

    split = max(1, len(series) - 2)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = LinearRegression()
    model.fit(X_train, y_train)
    predicted = model.predict(X_test)

    mae = mean_absolute_error(y_test, predicted)
    rmse = math.sqrt(mean_squared_error(y_test, predicted))
    nonzero_actual = y_test != 0
    mape = (
        np.mean(np.abs((y_test[nonzero_actual] - predicted[nonzero_actual]) / y_test[nonzero_actual]))
        if nonzero_actual.any()
        else 0.0
    )

    future_years = np.arange(series["cycle_year"].max() + 1, series["cycle_year"].max() + 7)
    future_index = np.arange(len(series), len(series) + 6)
    future_forecast = model.predict(future_index.reshape(-1, 1))

    horizons = {
        "H1": round(float(future_forecast[0]), 2),
        "H2": round(float(future_forecast[1]), 2),
        "H4": round(float(future_forecast[3]), 2),
        "H6": round(float(future_forecast[5]), 2),
    }

    return {
        "training_years": int(len(series)),
        "holdout_years": int(len(y_test)),
        "metrics": {
            "mae": round(float(mae), 4),
            "rmse": round(float(rmse), 4),
            "mape": round(float(mape), 4),
        },
        "horizons": horizons,
        "forecast_years": [int(year) for year in future_years],
        "series": series.to_dict(orient="records"),
    }


def forecast_horizons(df: pd.DataFrame) -> dict:
    return evaluate_forecast(df)
