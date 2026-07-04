"""学習実行CLI: race.db から build_dataset -> time_split -> train -> save。

読み取り専用（build_dataset は SELECT のみ）。収集ジョブが同じ race.db に
書き込み中でも基本問題ないが、まれに "database is locked" になったら
再実行してください。
"""
import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from keiba import features, model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="race.db へのパス（読み取り専用）")
    ap.add_argument("--out", required=True, help="学習済みモデルの保存先(pickle)")
    ap.add_argument("--valid-frac", type=float, default=0.2,
                     help="時系列検証に使う直近区間の割合")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        df = features.build_dataset(conn)
    finally:
        conn.close()

    print(f"build_dataset: {len(df)} rows, "
          f"date range {df['date'].min()} .. {df['date'].max()}")

    if len(df) == 0:
        print("no rows available yet -- nothing to train on.")
        return

    train_df, valid_df = model.time_split(df, valid_frac=args.valid_frac)
    print(f"time_split: train={len(train_df)} rows "
          f"({train_df['date'].min()}..{train_df['date'].max()}), "
          f"valid={len(valid_df)} rows "
          f"({valid_df['date'].min() if len(valid_df) else 'NA'}"
          f"..{valid_df['date'].max() if len(valid_df) else 'NA'})")

    if len(train_df) == 0:
        print("train split is empty -- not enough data yet to train.")
        return

    models = model.train_models(train_df)
    print(f"trained: feature_cols={models['feature_cols']}")
    print(f"meta={models['meta']}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    model.save(models, args.out)
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
