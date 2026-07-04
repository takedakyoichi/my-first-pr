"""Tests for keiba.model: time_split, train_models, predict, save/load.

Uses a synthetic DataFrame built directly (not via a real DB) that mirrors
the exact column set produced by features.build_dataset: keys
(race_id/date/horse_id/horse_no), labels (y_win/y_top3), the market-signal
columns kept for EV purposes (win_odds/popularity), jockey/trainer id
columns, and the genuine pre-race feature columns (distance, surface,
going, race_class, field_size, draw, sex, age, weight_carried,
days_since_last, horse_prev_finish, horse_avg_finish3, horse_avg_last3f,
jockey_win_rate, trainer_win_rate, horse_runs).
"""

import pickle

import numpy as np
import pandas as pd
import pytest

from keiba import model


def make_synthetic_dataset(n_races=40, horses_per_race=8, seed=0):
    """Build a synthetic per-horse-per-race DataFrame spanning many dates.

    Columns match features.build_dataset's output exactly, so feature_cols
    selection logic can be exercised against the real deny-list.
    """
    rng = np.random.RandomState(seed)
    rows = []
    dates = pd.date_range("2024-01-01", periods=n_races, freq="D")
    surfaces = ["芝", "ダート"]
    goings = ["良", "稍重", "重"]
    classes = ["G1", "G2", "G3", "OP"]
    sexes = ["牡", "牝", "セ"]

    for race_idx, date in enumerate(dates):
        race_id = f"R{race_idx:04d}"
        n_horses = horses_per_race
        # pick a winner and up to 2 more for top3 uniformly at random
        finish_order = rng.permutation(n_horses) + 1  # finish positions 1..n
        for h in range(n_horses):
            horse_no = h + 1
            finish_pos = int(finish_order[h])
            y_win = 1 if finish_pos == 1 else 0
            y_top3 = 1 if finish_pos <= 3 else 0
            rows.append({
                "race_id": race_id,
                "date": date.strftime("%Y-%m-%d"),
                "horse_id": f"H{race_idx}_{horse_no}",
                "horse_no": horse_no,
                "y_win": y_win,
                "y_top3": y_top3,
                "win_odds": float(rng.uniform(1.5, 30.0)),
                "popularity": int(rng.randint(1, n_horses + 1)),
                "distance": int(rng.choice([1200, 1600, 2000, 2400])),
                "surface": rng.choice(surfaces),
                "going": rng.choice(goings),
                "race_class": rng.choice(classes),
                "field_size": n_horses,
                "draw": horse_no,
                "sex": rng.choice(sexes),
                "age": int(rng.randint(2, 8)),
                "weight_carried": float(rng.uniform(52.0, 58.0)),
                "days_since_last": float(rng.randint(14, 60)),
                "horse_prev_finish": float(rng.randint(1, n_horses + 1)),
                "horse_avg_finish3": float(rng.uniform(1, n_horses)),
                "horse_avg_last3f": float(rng.uniform(33.0, 36.0)),
                "jockey_win_rate": float(rng.uniform(0.0, 0.3)),
                "trainer_win_rate": float(rng.uniform(0.0, 0.3)),
                "horse_runs": int(rng.randint(0, 20)),
                "jockey": f"J{rng.randint(0, 10)}",
                "trainer": f"T{rng.randint(0, 10)}",
            })
    return pd.DataFrame(rows)


DENY_LIST = {
    "race_id", "date", "horse_id", "horse_no",
    "y_win", "y_top3",
    "win_odds", "popularity",
    "jockey", "trainer",
}


@pytest.fixture
def dataset():
    return make_synthetic_dataset()


def test_train_models_returns_win_and_top3_with_clean_feature_cols(dataset):
    train_df, _ = model.time_split(dataset, valid_frac=0.2)
    models = model.train_models(train_df)

    assert "win" in models
    assert "top3" in models
    assert "feature_cols" in models
    assert "meta" in models

    feature_cols = models["feature_cols"]
    assert len(feature_cols) > 0
    # Must exclude keys, labels, and market signals (win_odds/popularity),
    # and jockey/trainer id columns (leaving jockey_win_rate/trainer_win_rate
    # -- the aggregate proxies -- untouched).
    excluded_present = DENY_LIST.intersection(feature_cols)
    assert excluded_present == set(), f"feature_cols leaked deny-listed columns: {excluded_present}"

    # Sanity: the legitimate aggregate features ARE present.
    for expected in ["jockey_win_rate", "trainer_win_rate", "distance", "surface"]:
        assert expected in feature_cols


def test_meta_contains_training_window_and_row_count(dataset):
    train_df, _ = model.time_split(dataset, valid_frac=0.2)
    models = model.train_models(train_df)
    meta = models["meta"]
    assert meta["trained_start"] == train_df["date"].min()
    assert meta["trained_end"] == train_df["date"].max()
    assert meta["n_rows"] == len(train_df)


def test_predict_adds_probability_columns_and_normalizes_within_race(dataset):
    train_df, valid_df = model.time_split(dataset, valid_frac=0.2)
    models = model.train_models(train_df)

    pred = model.predict(models, valid_df)

    for col in ["p_win_raw", "p_top3_raw", "p_win", "p_top3"]:
        assert col in pred.columns

    # Original columns preserved (it's a copy of df with new columns added).
    for col in valid_df.columns:
        assert col in pred.columns

    # Per-race normalization: sum of p_win within each race_id ~= 1.0.
    sums = pred.groupby("race_id")["p_win"].sum()
    assert np.allclose(sums.values, 1.0, atol=1e-6)

    # p_top3 should also be a valid probability-like scaled value (0,~).
    assert (pred["p_top3"] >= 0).all()


def test_time_split_has_no_temporal_overlap_and_roughly_matches_valid_frac(dataset):
    train_df, valid_df = model.time_split(dataset, valid_frac=0.2)

    assert train_df["date"].max() <= valid_df["date"].min()
    assert len(train_df) + len(valid_df) == len(dataset)

    total_rows = len(dataset)
    valid_frac_actual = len(valid_df) / total_rows
    # roughly 0.2 -- allow a generous tolerance since split is by date not row count
    assert 0.05 < valid_frac_actual < 0.40


def test_time_split_different_valid_frac(dataset):
    train_df, valid_df = model.time_split(dataset, valid_frac=0.5)
    assert train_df["date"].max() <= valid_df["date"].min()
    valid_frac_actual = len(valid_df) / len(dataset)
    assert 0.3 < valid_frac_actual < 0.7


def test_save_and_load_round_trip_predicts_identically(dataset, tmp_path):
    train_df, valid_df = model.time_split(dataset, valid_frac=0.2)
    models = model.train_models(train_df)

    out_path = tmp_path / "models.pkl"
    model.save(models, str(out_path))

    assert out_path.exists()

    loaded = model.load(str(out_path))
    assert "win" in loaded and "top3" in loaded
    assert loaded["feature_cols"] == models["feature_cols"]
    assert loaded["meta"] == models["meta"]

    pred_before = model.predict(models, valid_df)
    pred_after = model.predict(loaded, valid_df)

    np.testing.assert_allclose(
        pred_before["p_win_raw"].values, pred_after["p_win_raw"].values
    )
    np.testing.assert_allclose(
        pred_before["p_top3_raw"].values, pred_after["p_top3_raw"].values
    )
    np.testing.assert_allclose(
        pred_before["p_win"].values, pred_after["p_win"].values
    )
