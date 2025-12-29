import pandas as pd
from typing import List, Dict, Any

def process_data(df: pd.DataFrame, operations: List[Dict[str, Any]]) -> pd.DataFrame:
    for op in operations:
        op_type = op.get("type")
        params = op.get("params", {})
        
        if op_type == "clean":
            if params.get("deduplicate"):
                df = df.drop_duplicates()
            if params.get("trim"):
                df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
            if params.get("normalize_columns"):
                df.columns = [c.lower().replace(" ", "_").strip() for c in df.columns]
            if params.get("handle_missing"):
                method = params.get("missing_method", "drop")
                if method == "drop":
                    df = df.dropna()
                elif method == "fill":
                    df = df.fillna(params.get("fill_value", ""))
        
        elif op_type == "filter":
            conditions = params.get("conditions", [])
            logic = params.get("logic", "AND")
            
            if not conditions:
                continue
                
            mask = None
            for cond in conditions:
                col = cond.get("column")
                val = cond.get("value")
                op_func = cond.get("operator", "equals")
                
                if col not in df.columns:
                    continue
                
                current_mask = None
                if op_func == "equals":
                    current_mask = df[col].astype(str) == str(val)
                elif op_func == "contains":
                    current_mask = df[col].astype(str).str.contains(str(val), case=False, na=False)
                elif op_func == "greater_than":
                    current_mask = pd.to_numeric(df[col], errors='coerce') > float(val)
                elif op_func == "less_than":
                    current_mask = pd.to_numeric(df[col], errors='coerce') < float(val)
                elif op_func == "is_null":
                    current_mask = df[col].isna()
                
                if mask is None:
                    mask = current_mask
                else:
                    if logic == "AND":
                        mask = mask & current_mask
                    else:
                        mask = mask | current_mask
            
            if mask is not None:
                df = df[mask]
        
        elif op_type == "summarize":
            group_by = params.get("group_by", [])
            aggregations = params.get("aggregations", [])
            
            if aggregations:
                agg_dict = {}
                for agg in aggregations:
                    col = agg.get("column")
                    func = agg.get("func", "count")
                    if col in df.columns:
                        if col not in agg_dict:
                            agg_dict[col] = []
                        agg_dict[col].append(func)
                
                if group_by:
                    df = df.groupby(group_by).agg(agg_dict).reset_index()
                    # Flatten multi-index columns if necessary
                    if isinstance(df.columns, pd.MultiIndex):
                        df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in df.columns.values]
                else:
                    df = df.agg(agg_dict).to_frame().T
                
    return df

def get_column_info(df: pd.DataFrame) -> List[Dict[str, str]]:
    info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        if "int" in dtype or "float" in dtype:
            type_name = "numeric"
        elif "datetime" in dtype:
            type_name = "datetime"
        else:
            type_name = "string"
        info.append({"name": col, "type": type_name})
    return info
