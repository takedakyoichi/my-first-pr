"""Leakage-safe feature engineering for the netkeiba value-betting pipeline.

build_dataset(conn) turns the races/entries tables into a per-horse-per-race
training DataFrame. Every aggregate feature (jockey/trainer win rate, horse
history, days since last race) is computed using ONLY rows whose race date is
strictly BEFORE the current row's race date -- never the current race itself
or any future race. win_odds/popularity are never used as model features
(win_odds is kept only for later expected-value calculations).
"""

import re

import numpy as np
import pandas as pd

_SEX_AGE_RE = re.compile(r"^([^\d]+)(\d+)$")


def _parse_sex_age(sex_age):
    if not isinstance(sex_age, str):
        return None, np.nan
    m = _SEX_AGE_RE.match(sex_age.strip())
    if not m:
        return None, np.nan
    return m.group(1), int(m.group(2))


def build_dataset(conn) -> pd.DataFrame:
    races = pd.read_sql_query(
        "SELECT race_id, date, course, distance, surface, going, "
        "race_class, num_runners, weather FROM races",
        conn,
    )
    entries = pd.read_sql_query(
        "SELECT race_id, horse_id, horse_no, draw, jockey, trainer, sex_age, "
        "weight_carried, win_odds, popularity, finish_pos, time_sec, "
        "last_3f, margin FROM entries",
        conn,
    )

    df = entries.merge(races, on="race_id", how="left")

    # Sort by date ascending (tie-broken by race_id, horse_no) so all
    # "past-only" computations below only ever see strictly earlier races
    # for ties on the same date we still exclude same-row/-group values via
    # cumcount/cumsum, but different races on the same date could otherwise
    # leak into each other. Use date as the grouping key for the "prior date"
    # cutoff so races run on the same date never see each other's results.
    df["date"] = df["date"].astype(str)
    df = df.sort_values(["date", "race_id", "horse_no"]).reset_index(drop=True)

    # --- Labels ---
    df["y_win"] = (df["finish_pos"] == 1).astype(int)
    df["y_top3"] = df["finish_pos"].isin([1, 2, 3]).astype(int)

    # --- sex/age parsed from sex_age ---
    sex_age_parsed = df["sex_age"].apply(_parse_sex_age)
    df["sex"] = sex_age_parsed.apply(lambda t: t[0])
    df["age"] = sex_age_parsed.apply(lambda t: t[1])

    # --- field_size ---
    df["field_size"] = df["num_runners"]

    # --- Past-only aggregate features ---
    # To guarantee no leakage even when multiple races share the same date,
    # we compute stats per (group, date) first, aggregate to one row per
    # date, then do a "strictly before this date" cumulative computation on
    # that per-date table, and finally map back onto the original rows. This
    # way two horses/jockeys racing on the same date never see each other's
    # same-day results, and a given row never sees its own race's result.

    def past_only_rate_by_date(entity_col, win_col):
        """Win-rate of entity_col using only rows with date < this row's date."""
        per_date = (
            df.groupby([entity_col, "date"])[win_col]
            .agg(["sum", "count"])
            .reset_index()
            .sort_values("date")
        )
        per_date["cum_sum_before"] = (
            per_date.groupby(entity_col)["sum"].cumsum() - per_date["sum"]
        )
        per_date["cum_count_before"] = (
            per_date.groupby(entity_col)["count"].cumsum() - per_date["count"]
        )
        with np.errstate(invalid="ignore", divide="ignore"):
            per_date["rate"] = per_date["cum_sum_before"] / per_date["cum_count_before"]
        per_date.loc[per_date["cum_count_before"] == 0, "rate"] = np.nan
        lookup = per_date.set_index([entity_col, "date"])["rate"]
        return df.set_index([entity_col, "date"]).index.map(lookup)

    df["jockey_win_rate"] = past_only_rate_by_date("jockey", "y_win")
    df["trainer_win_rate"] = past_only_rate_by_date("trainer", "y_win")

    # --- Horse history features (per horse_id, strictly before this date) ---
    horse_hist = df[["horse_id", "date", "race_id", "finish_pos", "last_3f"]].copy()
    horse_hist = horse_hist.sort_values(["horse_id", "date", "race_id"]).reset_index(drop=True)

    def _horse_past_features(group):
        group = group.sort_values("date")
        n = len(group)
        runs = np.arange(n)  # number of strictly-prior races (0-indexed position)
        prev_finish = group["finish_pos"].shift(1)
        avg_finish3 = (
            group["finish_pos"].shift(1).rolling(window=3, min_periods=1).mean()
        )
        avg_last3f = group["last_3f"].shift(1).expanding(min_periods=1).mean()
        dates = pd.to_datetime(group["date"])
        days_since_last = dates.diff().dt.days
        return pd.DataFrame({
            "race_id": group["race_id"].values,
            "horse_id": group["horse_id"].values,
            "horse_runs": runs,
            "horse_prev_finish": prev_finish.values,
            "horse_avg_finish3": avg_finish3.values,
            "horse_avg_last3f": avg_last3f.values,
            "days_since_last": days_since_last.values,
        })

    horse_feats = pd.concat(
        [_horse_past_features(g) for _, g in horse_hist.groupby("horse_id")],
        ignore_index=True,
    )

    df = df.merge(horse_feats, on=["race_id", "horse_id"], how="left")

    columns = [
        "race_id", "date", "horse_id", "horse_no",
        "y_win", "y_top3", "win_odds",
        "distance", "surface", "going", "race_class", "field_size", "draw",
        "sex", "age", "weight_carried", "days_since_last",
        "horse_prev_finish", "horse_avg_finish3", "horse_avg_last3f",
        "jockey_win_rate", "trainer_win_rate", "horse_runs",
        "jockey", "trainer",
    ]
    return df[columns]
