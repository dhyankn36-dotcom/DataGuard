import pandas as pd

from app.services.profiling import profile_dataset


def test_profile_identifies_empty_and_constant_columns():
    dataframe = pd.DataFrame(
        {
            "empty": pd.Series([None, None], dtype="float64"),
            "constant": [7, 7],
            "varying": [1, 2],
        }
    )

    profile = profile_dataset(dataframe)

    assert profile["columns"]["empty"]["is_empty"] is True
    assert profile["columns"]["empty"]["is_constant"] is False
    assert profile["columns"]["empty"]["statistics"] == {
        "mean": None,
        "median": None,
        "minimum": None,
        "maximum": None,
    }
    assert profile["columns"]["constant"]["is_empty"] is False
    assert profile["columns"]["constant"]["is_constant"] is True
    assert profile["columns"]["varying"]["is_constant"] is False


def test_profile_excludes_infinite_values_from_numeric_statistics():
    dataframe = pd.DataFrame({"measurement": [1.0, float("inf"), 3.0, float("-inf")]})

    profile = profile_dataset(dataframe)
    column = profile["columns"]["measurement"]

    assert column["non_finite_values"] == 2
    assert column["statistics"] == {
        "mean": 2.0,
        "median": 2.0,
        "minimum": 1.0,
        "maximum": 3.0,
    }


def test_quality_score_accounts_for_missing_and_duplicate_rows():
    dataframe = pd.DataFrame(
        {
            "name": ["Ada", "Ada", None],
            "score": [10, 10, 30],
        }
    )

    profile = profile_dataset(dataframe)

    assert profile["total_missing_values"] == 1
    assert profile["duplicate_rows"] == 1
    assert profile["quality_score"] == 56


def test_profile_handles_a_dataframe_without_rows_or_columns():
    profile = profile_dataset(pd.DataFrame())

    assert profile["total_rows"] == 0
    assert profile["total_columns"] == 0
    assert profile["duplicate_rows"] == 0
    assert profile["total_missing_values"] == 0
    assert profile["quality_score"] == 100
    assert profile["columns"] == {}



def test_profile_reports_unique_percentage_using_non_missing_values():
    dataframe = pd.DataFrame(
        {
            "categories": ["A", "A", "B", None],
            "all_unique": [1, 2, 3, 4],
            "all_missing": [None, None, None, None],
        }
    )

    profile = profile_dataset(dataframe)

    assert profile["columns"]["categories"]["unique_percentage"] == 66.67
    assert profile["columns"]["all_unique"]["unique_percentage"] == 100.0
    assert profile["columns"]["all_missing"]["unique_percentage"] == 0
