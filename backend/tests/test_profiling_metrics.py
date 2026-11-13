import pandas as pd

from app.services.profiling import profile_dataset


def test_profile_counts_iqr_outliers_only_for_sufficient_numeric_samples():
    profile = profile_dataset(
        pd.DataFrame(
            {
                "with_outlier": [1, 2, 3, 100],
                "small_sample": [1, 2, 100],
            }
        )
    )

    assert profile["columns"]["with_outlier"]["potential_outliers"] == 1
    assert profile["columns"]["small_sample"]["potential_outliers"] == 0


def test_profile_reports_missing_percentage_for_each_column():
    profile = profile_dataset(
        pd.DataFrame(
            {
                "partially_missing": [1, None, 3, None],
                "complete": [1, 2, 3, 4],
            }
        )
    )

    assert profile["columns"]["partially_missing"]["missing_values"] == 2
    assert profile["columns"]["partially_missing"]["missing_percentage"] == 50.0
    assert profile["columns"]["complete"]["missing_percentage"] == 0.0
