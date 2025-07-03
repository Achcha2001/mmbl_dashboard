import os
import joblib
import pandas as pd

# Path to your pickle file (adjust if your structure is different)
MODEL_PATH = os.path.join(
    os.path.dirname(__file__),   # points to utils/
    'models',
    'holtwinters_model.pkl'
)

def get_forecast(periods=6):
    """
    Load the pre-trained Holt-Winters model and forecast for the given number of periods (months).
    Returns: dict of { "YYYY-MM": value, ... }
    """
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)

    # Try to forecast; handle both pandas Series and arrays
    preds = model.forecast(periods)
    # Try to produce YYYY-MM keys if possible (monthly forecast is recommended)
    if hasattr(preds, 'index'):
        # Index should be DatetimeIndex
        result = {}
        for i, val in enumerate(preds):
            idx = preds.index[i]
            # Use "YYYY-MM" for monthly, or "YYYY-MM-DD" for daily
            key = idx.strftime('%Y-%m') if len(str(idx)) >= 7 else str(idx)
            result[key] = float(val)
        return result
    else:
        # Fallback: just enumerate if no DatetimeIndex
        return {str(i+1): float(val) for i, val in enumerate(preds)}

# For local testing:
if __name__ == "__main__":
    result = get_forecast(6)
    print(result)
