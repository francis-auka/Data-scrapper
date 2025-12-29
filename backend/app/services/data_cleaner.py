import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple


def detect_issues(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Detect data quality issues in the dataframe.
    
    Returns a comprehensive report of:
    - Missing values per column
    - Number of duplicate rows
    - Columns with inconsistent data types
    - Outliers detected using IQR method
    """
    report = {
        "missing_values": {},
        "duplicates": 0,
        "inconsistent_types": [],
        "outliers": {},
        "total_rows": len(df),
        "total_columns": len(df.columns)
    }
    
    # Detect missing values
    for col in df.columns:
        missing_count = df[col].isna().sum()
        if missing_count > 0:
            report["missing_values"][col] = {
                "count": int(missing_count),
                "percentage": round((missing_count / len(df)) * 100, 2)
            }
    
    # Detect duplicates
    report["duplicates"] = int(df.duplicated().sum())
    
    # Detect inconsistent data types (mixed numeric/string in same column)
    for col in df.columns:
        if df[col].dtype == 'object':
            # Check if column contains mix of numbers and strings
            non_null_values = df[col].dropna()
            if len(non_null_values) > 0:
                numeric_count = pd.to_numeric(non_null_values, errors='coerce').notna().sum()
                total_count = len(non_null_values)
                # If some but not all values are numeric, it's inconsistent
                if 0 < numeric_count < total_count:
                    report["inconsistent_types"].append({
                        "column": col,
                        "numeric_count": int(numeric_count),
                        "non_numeric_count": int(total_count - numeric_count)
                    })
    
    # Detect outliers using IQR method for numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        values = df[col].dropna()
        if len(values) > 0:
            Q1 = values.quantile(0.25)
            Q3 = values.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            outliers = values[(values < lower_bound) | (values > upper_bound)]
            
            if len(outliers) > 0:
                report["outliers"][col] = {
                    "count": int(len(outliers)),
                    "percentage": round((len(outliers) / len(values)) * 100, 2),
                    "lower_bound": float(lower_bound),
                    "upper_bound": float(upper_bound),
                    "examples": outliers.head(5).tolist()
                }
    
    return report


def auto_clean(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Automatically clean the dataframe and generate a detailed report.
    
    Cleaning operations:
    1. Remove duplicate rows
    2. Handle missing values (median for numeric, mode for categorical)
    3. Normalize column names (lowercase, snake_case)
    4. Convert columns to appropriate data types where possible
    
    Returns:
    - Cleaned dataframe
    - Detailed cleaning report
    """
    original_df = df.copy()
    cleaned_df = df.copy()
    
    report = {
        "original_rows": len(df),
        "original_columns": len(df.columns),
        "changes": {
            "duplicates_removed": 0,
            "missing_values_filled": {},
            "columns_renamed": {},
            "data_types_converted": {},
            "outliers_detected": 0  # Detected but NOT removed
        },
        "final_rows": 0,
        "final_columns": 0,
        "summary": []
    }
    
    # 1. Remove duplicate rows
    duplicates_count = cleaned_df.duplicated().sum()
    if duplicates_count > 0:
        cleaned_df = cleaned_df.drop_duplicates()
        report["changes"]["duplicates_removed"] = int(duplicates_count)
        report["summary"].append(f"Removed {duplicates_count} duplicate row(s)")
    
    # 2. Handle missing values
    for col in cleaned_df.columns:
        missing_count = cleaned_df[col].isna().sum()
        if missing_count > 0:
            if cleaned_df[col].dtype in ['int64', 'float64']:
                # Use median for numeric columns (more robust to outliers)
                fill_value = cleaned_df[col].median()
                cleaned_df[col].fillna(fill_value, inplace=True)
                report["changes"]["missing_values_filled"][col] = {
                    "count": int(missing_count),
                    "method": "median",
                    "fill_value": float(fill_value) if pd.notna(fill_value) else None
                }
                report["summary"].append(f"Filled {missing_count} missing value(s) in '{col}' with median ({fill_value:.2f})")
            else:
                # Use mode for categorical columns
                mode_values = cleaned_df[col].mode()
                if len(mode_values) > 0:
                    fill_value = mode_values[0]
                    cleaned_df[col].fillna(fill_value, inplace=True)
                    report["changes"]["missing_values_filled"][col] = {
                        "count": int(missing_count),
                        "method": "mode",
                        "fill_value": str(fill_value)
                    }
                    report["summary"].append(f"Filled {missing_count} missing value(s) in '{col}' with mode ('{fill_value}')")
    
    # 3. Normalize column names
    original_columns = cleaned_df.columns.tolist()
    normalized_columns = [
        col.lower().strip().replace(' ', '_').replace('-', '_').replace('.', '_')
        for col in original_columns
    ]
    
    # Only rename if there are changes
    column_renames = {}
    for orig, norm in zip(original_columns, normalized_columns):
        if orig != norm:
            column_renames[orig] = norm
    
    if column_renames:
        cleaned_df.columns = normalized_columns
        report["changes"]["columns_renamed"] = column_renames
        report["summary"].append(f"Normalized {len(column_renames)} column name(s) to snake_case")
    
    # 4. Convert data types where possible
    for col in cleaned_df.columns:
        if cleaned_df[col].dtype == 'object':
            # Try to convert to numeric
            converted = pd.to_numeric(cleaned_df[col], errors='coerce')
            # If most values are numeric, convert the column
            if converted.notna().sum() / len(cleaned_df) > 0.8:  # 80% threshold
                original_type = str(cleaned_df[col].dtype)
                cleaned_df[col] = converted
                new_type = str(cleaned_df[col].dtype)
                report["changes"]["data_types_converted"][col] = {
                    "from": original_type,
                    "to": new_type
                }
                report["summary"].append(f"Converted '{col}' from {original_type} to {new_type}")
    
    # Detect outliers (but don't remove them)
    outlier_report = detect_issues(cleaned_df)
    if outlier_report["outliers"]:
        total_outliers = sum(info["count"] for info in outlier_report["outliers"].values())
        report["changes"]["outliers_detected"] = total_outliers
        report["summary"].append(f"Detected {total_outliers} outlier(s) in {len(outlier_report['outliers'])} column(s) (not removed)")
    
    report["final_rows"] = len(cleaned_df)
    report["final_columns"] = len(cleaned_df.columns)
    
    # Add summary message
    if not report["summary"]:
        report["summary"].append("No data quality issues detected - dataset is already clean!")
    
    return cleaned_df, report
