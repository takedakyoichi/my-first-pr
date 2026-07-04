"""Win/top3 LightGBM models for the netkeiba value-betting pipeline.

Trains two independent binary classifiers -- one for "finishes 1st"
(y_win) and one for "finishes in the top 3" (y_top3) -- on the
leakage-safe feature frame produced by keiba.features.build_dataset.

Feature selection follows an explicit DENY-LIST built from the Task 1
handoff notes: the model must never see race/entity keys, the labels
themselves, or market signals (win_odds/popularity), nor the raw
jockey/trainer identity columns (only their pre-aggregated win-rate
features -- jockey_win_rate/trainer_win_rate -- are legitimate
pre-race signals; the raw IDs are high-cardinality and not intended
as model inputs per the plan).

    DENY_COLUMNS = {
        # keys
        "race_id", "date", "horse_id", "horse_no",
        # labels
        "y_win", "y_top3",
        # market signals (would leak market consensus / cause the model to
        # just chase the odds instead of predicting independently)
        "win_odds", "popularity",
        # raw identity columns (kept in features.py for convenience/debug,
        # but not meant to be fed directly into the model -- their
        # aggregated win-rate proxies are used instead)
        "jockey", "trainer",
    }

Everything else in the DataFrame is treated as a feature. Known
categorical columns (surface, going, race_class, sex) are cast to
pandas "category" dtype and passed to LightGBM via categorical_feature
so it treats them as categorical rather than ordinal-encoded numbers.
"""

import pickle

import lightgbm as lgb
import numpy as np
import pandas as pd

DENY_COLUMNS = {
    "race_id", "date", "horse_id", "horse_no",
    "y_win", "y_top3",
    "win_odds", "popularity",
    "jockey", "trainer",
}

CATEGORICAL_COLUMNS = ["surface", "going", "race_class", "sex"]

_LGBM_PARAMS = {
    "objective": "binary",
    "verbose": -1,
    "min_child_samples": 5,
}


def _feature_cols(df: pd.DataFrame):
    return [c for c in df.columns if c not in DENY_COLUMNS]


def time_split(df: pd.DataFrame, valid_frac: float = 0.2):
    """Split df chronologically by `date`; the latest valid_frac of the
    timeline (by distinct date, not row count) becomes the validation set.

    Guarantees max(train.date) <= min(valid.date) -- no temporal overlap.
    """
    dates = pd.to_datetime(df["date"])
    sorted_unique_dates = np.sort(dates.unique())
    n_dates = len(sorted_unique_dates)
    n_valid_dates = max(1, int(round(n_dates * valid_frac)))
    n_valid_dates = min(n_valid_dates, n_dates - 1) if n_dates > 1 else n_dates
    cutoff_date = sorted_unique_dates[n_dates - n_valid_dates]

    train_mask = dates < cutoff_date
    valid_mask = ~train_mask

    train_df = df.loc[train_mask].reset_index(drop=True)
    valid_df = df.loc[valid_mask].reset_index(drop=True)
    return train_df, valid_df


def _prep_features(df: pd.DataFrame, feature_cols):
    X = df[feature_cols].copy()
    for col in CATEGORICAL_COLUMNS:
        if col in X.columns:
            X[col] = X[col].astype("category")
    return X


def train_models(train_df: pd.DataFrame) -> dict:
    """Train win/top3 LightGBM binary classifiers on train_df.

    Returns a dict: {"win": model, "top3": model, "feature_cols": [...],
    "meta": {"trained_start", "trained_end", "n_rows"}}.
    """
    feature_cols = _feature_cols(train_df)
    cat_cols = [c for c in CATEGORICAL_COLUMNS if c in feature_cols]

    X = _prep_features(train_df, feature_cols)

    win_model = lgb.LGBMClassifier(**_LGBM_PARAMS)
    win_model.fit(X, train_df["y_win"], categorical_feature=cat_cols)

    top3_model = lgb.LGBMClassifier(**_LGBM_PARAMS)
    top3_model.fit(X, train_df["y_top3"], categorical_feature=cat_cols)

    meta = {
        "trained_start": train_df["date"].min(),
        "trained_end": train_df["date"].max(),
        "n_rows": len(train_df),
    }

    return {
        "win": win_model,
        "top3": top3_model,
        "feature_cols": feature_cols,
        "meta": meta,
    }


def predict(models: dict, df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with raw model probabilities plus in-race
    normalized probabilities.

    p_win_raw / p_top3_raw: raw LightGBM predict_proba outputs.
    p_win: p_win_raw rescaled so sum(p_win) == 1 within each race_id.
    p_top3: p_top3_raw rescaled the same way (so the "expected number of
    top-3 finishers" implied by the field stays internally consistent).
    """
    feature_cols = models["feature_cols"]
    X = _prep_features(df, feature_cols)
    # Align categorical dtype categories aren't required to match training
    # exactly for LightGBM's sklearn API predict, since it uses the
    # underlying Booster's raw feature handling; category codes are
    # recomputed consistently as long as values are known at train time.

    out = df.copy()
    out["p_win_raw"] = models["win"].predict_proba(X)[:, 1]
    out["p_top3_raw"] = models["top3"].predict_proba(X)[:, 1]

    win_sum = out.groupby("race_id")["p_win_raw"].transform("sum")
    top3_sum = out.groupby("race_id")["p_top3_raw"].transform("sum")

    with np.errstate(invalid="ignore", divide="ignore"):
        out["p_win"] = out["p_win_raw"] / win_sum
        out["p_top3"] = out["p_top3_raw"] / top3_sum * 3.0

    return out


def save(models: dict, path: str) -> None:
    with open(path, "wb") as f:
        pickle.dump(models, f)


def load(path: str) -> dict:
    with open(path, "rb") as f:
        return pickle.load(f)
