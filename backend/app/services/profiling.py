
import pandas as pd


def profile_dataset(df: pd.DataFrame):
    total_rows = len(df)
    total_columns = len(df.columns)

    columns = {}

    for column in df.columns:
        series = df[column]

        missing = int(series.isna().sum())

        column_info = {
            "data_type": str(series.dtype),
            "missing_values": missing,
            "missing_percentage": round(
                (missing / total_rows) * 100, 2
            ) if total_rows else 0,
            "unique_values": int(series.nunique()),
            "duplicate_values": int(series.duplicated().sum())
        }

        if pd.api.types.is_numeric_dtype(series):
            non_finite = int(series.isin([float("inf"), float("-inf")]).sum())
            numeric = series[
                ~series.isin([float("inf"), float("-inf")])
            ].dropna()

            column_info["statistics"] = {
                "mean": float(numeric.mean()) if not numeric.empty else None,
                "median": float(numeric.median()) if not numeric.empty else None,
                "minimum": float(numeric.min()) if not numeric.empty else None,
                "maximum": float(numeric.max()) if not numeric.empty else None
            }

            column_info["non_finite_values"] = non_finite

            if len(numeric) >= 4:
                q1 = numeric.quantile(0.25)
                q3 = numeric.quantile(0.75)
                iqr = q3 - q1

                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr

                column_info["potential_outliers"] = int(
                    ((numeric < lower) | (numeric > upper)).sum()
                )
            else:
                column_info["potential_outliers"] = 0

        columns[str(column)] = column_info

    return {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "duplicate_rows": int(df.duplicated().sum()),
        "total_missing_values": int(df.isna().sum().sum()),
        "columns": columns
    }
