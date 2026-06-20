"""Fold-safe preprocessing pipelines (brief sections 7, 8).

Every transformer is fit on training data only; imputation/scaling statistics never
leak from validation or test because the whole thing lives inside an sklearn Pipeline
that is fit per fold / on dev only.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import RobustScaler, OneHotEncoder


class Winsorizer(BaseEstimator, TransformerMixin):
    """Clip each column to [p_low, p_high] learned on TRAIN only (brief section 9)."""

    def __init__(self, lower=0.01, upper=0.99):
        self.lower = lower
        self.upper = upper

    def fit(self, X, y=None):
        X = np.asarray(X, dtype=float)
        self.lo_ = np.nanpercentile(X, self.lower * 100, axis=0)
        self.hi_ = np.nanpercentile(X, self.upper * 100, axis=0)
        return self

    def transform(self, X):
        X = np.asarray(X, dtype=float)
        return np.clip(X, self.lo_, self.hi_)


def build_preprocessor(numeric_features, categorical_features, *, scale: bool,
                       winsor: tuple | None = None):
    """ColumnTransformer: (optional winsorize) + median impute + missing indicator
    for numerics (+RobustScaler when scale=True), constant 'Unknown' impute +
    one-hot for cats. Winsor/impute/scale are all fit on training data only."""
    num_steps = []
    if winsor is not None:
        num_steps.append(("winsor", Winsorizer(winsor[0], winsor[1])))
    num_steps.append(("impute", SimpleImputer(strategy="median", add_indicator=True)))
    if scale:
        num_steps.append(("scale", RobustScaler()))
    num_pipe = Pipeline(num_steps)

    cat_pipe = Pipeline([
        ("impute", SimpleImputer(strategy="constant", fill_value="Unknown")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    transformers = []
    if numeric_features:
        transformers.append(("num", num_pipe, list(numeric_features)))
    if categorical_features:
        transformers.append(("cat", cat_pipe, list(categorical_features)))
    ct = ColumnTransformer(transformers, remainder="drop",
                           verbose_feature_names_out=True)
    return ct


def coerce_frame(df: pd.DataFrame, numeric_features, categorical_features) -> pd.DataFrame:
    """Return a frame with numeric features as float and categoricals as string."""
    out = pd.DataFrame(index=df.index)
    for c in numeric_features:
        out[c] = pd.to_numeric(df[c], errors="coerce").astype(float)
    for c in categorical_features:
        s = df[c].astype(str)
        s = s.where(~s.isin(["", "nan", "None", "NaN"]), other=np.nan)
        out[c] = s
    return out
