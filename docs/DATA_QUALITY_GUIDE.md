# Dataset Quality Review Guide

DataGuard helps inspect tabular datasets before they are used for analysis or machine-learning workflows. This guide explains how to interpret the main quality signals and choose cleaning actions carefully.

## 1. Start with the dataset overview

After uploading a CSV or XLSX file, review:

- Row and column counts
- Column names and inferred data types
- Missing-value counts
- Duplicate-row count
- Numeric summaries and potential outlier indicators

Confirm that the file loaded as expected before applying any transformation.

## 2. Interpret missing values

A missing value can mean different things depending on the column.

- A missing optional comment may be acceptable.
- A missing target label may make a training example unusable.
- A missing numeric measurement may require domain-specific treatment.

Do not automatically fill every missing value. First determine why the value is absent and whether the chosen strategy makes sense for the column.

## 3. Review duplicate rows

Duplicate records can inflate counts and bias downstream analysis. Check whether repeated rows are genuinely duplicate observations or valid repeated events before removing them.

## 4. Understand numeric summaries

Minimum, maximum, mean, median, and spread help reveal unusual values. An outlier is not necessarily an error: investigate the source and domain meaning before removing or changing it.

## 5. Choose a cleaning strategy

| Strategy | Effect | When to consider it |
|---|---|---|
| Keep missing values | Preserves blanks | When downstream processing can handle them |
| Drop rows | Removes rows with missing values | When the number of affected rows is small and removal is justified |
| Fill median/mode | Fills numeric columns with median and other columns with most frequent value | When a simple baseline imputation is appropriate |
| Remove duplicates | Removes repeated rows | When records are confirmed duplicates |

DataGuard's cleaned export operates on a copy. The uploaded original dataset is not overwritten.

## 6. Validate the exported dataset

Before using a cleaned export:

1. Compare original and exported row counts.
2. Review the number of missing values and duplicates remaining.
3. Check important columns and representative records.
4. Confirm that data types and category values remain sensible.
5. Record the selected cleaning options so the process can be reproduced.

## Important limitations

A quality score is a quick indicator, not a guarantee that a dataset is correct, unbiased, representative, or suitable for a particular model. Domain knowledge and validation rules are still necessary. Avoid uploading confidential data unless your environment is approved to handle it.
