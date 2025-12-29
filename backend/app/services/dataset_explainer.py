import pandas as pd
import numpy as np
from typing import Dict, List, Any
import re


def analyze_dataset(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analyze the dataset structure and content.
    
    Returns comprehensive analysis including:
    - Dataset overview (rows, columns)
    - Column metadata with inferred types
    - Numeric column statistics
    - Categorical column statistics
    """
    analysis = {
        "overview": {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "memory_usage_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "completeness_percentage": round((1 - df.isna().sum().sum() / (len(df) * len(df.columns))) * 100, 2)
        },
        "columns": {},
        "numeric_insights": {},
        "categorical_insights": {}
    }
    
    for col in df.columns:
        col_dtype = str(df[col].dtype)
        is_numeric = df[col].dtype in ['int64', 'float64']
        
        # Basic column info
        column_info = {
            "name": col,
            "dtype": col_dtype,
            "type": "numeric" if is_numeric else "categorical",
            "non_null_count": int(df[col].notna().sum()),
            "null_count": int(df[col].isna().sum()),
            "null_percentage": round((df[col].isna().sum() / len(df)) * 100, 2)
        }
        
        analysis["columns"][col] = column_info
        
        # Detailed insights for numeric columns
        if is_numeric:
            values = df[col].dropna()
            if len(values) > 0:
                analysis["numeric_insights"][col] = {
                    "min": float(values.min()),
                    "max": float(values.max()),
                    "mean": float(values.mean()),
                    "median": float(values.median()),
                    "std": float(values.std()) if len(values) > 1 else 0.0,
                    "unique_count": int(values.nunique())
                }
        
        # Detailed insights for categorical columns
        else:
            values = df[col].dropna().astype(str)
            if len(values) > 0:
                value_counts = values.value_counts()
                top_values = value_counts.head(5)
                
                analysis["categorical_insights"][col] = {
                    "unique_count": int(values.nunique()),
                    "most_common": str(value_counts.index[0]) if len(value_counts) > 0 else None,
                    "most_common_count": int(value_counts.iloc[0]) if len(value_counts) > 0 else 0,
                    "top_5_values": [
                        {"value": str(val), "count": int(count), "percentage": round((count / len(values)) * 100, 2)}
                        for val, count in top_values.items()
                    ]
                }
    
    return analysis


def generate_explanation(df: pd.DataFrame, analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a plain English explanation of the dataset.
    
    Infers:
    - What the dataset is about
    - What each major column represents
    - Potential use cases
    """
    columns = list(df.columns)
    num_rows = len(df)
    num_cols = len(columns)
    
    # Infer dataset purpose based on column names
    purpose = _infer_dataset_purpose(columns)
    
    # Describe column meanings
    column_descriptions = _describe_columns(columns, analysis)
    
    # Suggest use cases
    use_cases = _suggest_use_cases(columns, analysis)
    
    # Build explanation text
    explanation_text = _build_explanation_text(
        purpose, num_rows, num_cols, column_descriptions, use_cases
    )
    
    return {
        "inferred_purpose": purpose,
        "column_descriptions": column_descriptions,
        "suggested_use_cases": use_cases,
        "explanation": explanation_text
    }


def _infer_dataset_purpose(columns: List[str]) -> str:
    """Infer what the dataset is about based on column names."""
    columns_lower = [col.lower() for col in columns]
    columns_text = ' '.join(columns_lower)
    
    # Common patterns for different dataset types
    patterns = {
        "sales": ["sale", "price", "revenue", "product", "customer", "order", "purchase", "transaction"],
        "buildings": ["building", "address", "city", "country", "location", "floor", "height", "area"],
        "people": ["name", "age", "gender", "email", "phone", "person", "employee", "student"],
        "products": ["product", "category", "brand", "sku", "inventory", "stock", "item"],
        "financial": ["amount", "balance", "account", "payment", "credit", "debit", "transaction"],
        "geographic": ["country", "city", "state", "region", "latitude", "longitude", "location"],
        "temporal": ["date", "time", "year", "month", "day", "timestamp", "created", "updated"],
        "vehicles": ["car", "vehicle", "model", "make", "year", "engine", "fuel"],
        "healthcare": ["patient", "diagnosis", "treatment", "doctor", "hospital", "medical"],
        "academic": ["student", "course", "grade", "school", "teacher", "subject", "exam"],
        "real_estate": ["property", "house", "apartment", "rent", "price", "bedroom", "bathroom"]
    }
    
    # Count matches for each category
    matches = {}
    for category, keywords in patterns.items():
        count = sum(1 for keyword in keywords if keyword in columns_text)
        if count > 0:
            matches[category] = count
    
    if matches:
        # Return the category with most matches
        best_match = max(matches, key=matches.get)
        return best_match.title()
    
    return "General Data"


def _describe_columns(columns: List[str], analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    """Describe what each column likely represents."""
    descriptions = []
    
    for col in columns:
        col_info = analysis["columns"][col]
        col_type = col_info["type"]
        
        # Generate description based on column name and type
        description = _infer_column_meaning(col, col_type, analysis)
        
        descriptions.append({
            "column": col,
            "description": description,
            "type": col_type
        })
    
    return descriptions


def _infer_column_meaning(col_name: str, col_type: str, analysis: Dict[str, Any]) -> str:
    """Infer what a column represents based on its name and type."""
    col_lower = col_name.lower()
    
    # Common column name patterns
    if any(x in col_lower for x in ["id", "key", "code"]):
        return "Unique identifier or code"
    elif any(x in col_lower for x in ["name", "title"]):
        return "Name or title"
    elif any(x in col_lower for x in ["date", "time", "created", "updated"]):
        return "Date or timestamp"
    elif any(x in col_lower for x in ["price", "cost", "amount", "value", "revenue", "salary"]):
        return "Monetary value or price"
    elif any(x in col_lower for x in ["count", "quantity", "number", "total"]):
        return "Count or quantity"
    elif any(x in col_lower for x in ["email", "mail"]):
        return "Email address"
    elif any(x in col_lower for x in ["phone", "tel", "mobile"]):
        return "Phone number"
    elif any(x in col_lower for x in ["address", "street", "location"]):
        return "Address or location"
    elif any(x in col_lower for x in ["city", "town"]):
        return "City name"
    elif any(x in col_lower for x in ["country", "nation"]):
        return "Country name"
    elif any(x in col_lower for x in ["state", "province", "region"]):
        return "State or region"
    elif any(x in col_lower for x in ["category", "type", "class"]):
        return "Category or classification"
    elif any(x in col_lower for x in ["status", "state"]):
        return "Status indicator"
    elif any(x in col_lower for x in ["description", "notes", "comment"]):
        return "Descriptive text or notes"
    elif col_type == "numeric":
        return "Numeric measurement or value"
    else:
        return "Text or categorical data"


def _suggest_use_cases(columns: List[str], analysis: Dict[str, Any]) -> List[str]:
    """Suggest potential use cases for this dataset."""
    columns_lower = [col.lower() for col in columns]
    columns_text = ' '.join(columns_lower)
    use_cases = []
    
    # Determine use cases based on column patterns
    if any(x in columns_text for x in ["price", "sale", "revenue"]):
        use_cases.append("Sales analysis and revenue forecasting")
    
    if any(x in columns_text for x in ["date", "time", "year", "month"]):
        use_cases.append("Time-series analysis and trend identification")
    
    if any(x in columns_text for x in ["customer", "user", "client"]):
        use_cases.append("Customer behavior analysis and segmentation")
    
    if any(x in columns_text for x in ["location", "city", "country", "latitude", "longitude"]):
        use_cases.append("Geographic analysis and mapping")
    
    if any(x in columns_text for x in ["category", "type", "class"]):
        use_cases.append("Classification and categorization studies")
    
    if len(analysis["numeric_insights"]) >= 2:
        use_cases.append("Statistical analysis and correlation studies")
    
    if any(x in columns_text for x in ["product", "item", "inventory"]):
        use_cases.append("Inventory management and product analysis")
    
    # Default use case if none found
    if not use_cases:
        use_cases.append("Data exploration and general analysis")
    
    return use_cases


def _build_explanation_text(
    purpose: str,
    num_rows: int,
    num_cols: int,
    column_descriptions: List[Dict[str, str]],
    use_cases: List[str]
) -> str:
    """Build a comprehensive plain English explanation."""
    
    # Introduction
    text = f"This dataset appears to be related to **{purpose}**. "
    text += f"It contains **{num_rows:,} rows** and **{num_cols} columns** of data.\n\n"
    
    # Column descriptions
    text += "### Column Overview\n\n"
    for desc in column_descriptions[:10]:  # Limit to first 10 columns
        text += f"- **{desc['column']}**: {desc['description']} ({desc['type']})\n"
    
    if len(column_descriptions) > 10:
        text += f"\n...and {len(column_descriptions) - 10} more columns.\n"
    
    # Use cases
    text += "\n### Potential Use Cases\n\n"
    text += "This dataset could be valuable for:\n\n"
    for i, use_case in enumerate(use_cases, 1):
        text += f"{i}. {use_case}\n"
    
    return text
