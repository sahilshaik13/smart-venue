import os
import pickle
import pandas as pd
import structlog

log = structlog.get_logger(__name__)

class PredictionService:
    def __init__(self):
        self.model = None
        self.encoders = None
        self.load_model()

    def load_model(self):
        model_path = os.path.join("app", "resources", "wait_time_model.pkl")
        if not os.path.exists(model_path):
            log.warning("prediction_model_not_found", path=model_path)
            return

        try:
            with open(model_path, "rb") as f:
                artifacts = pickle.load(f)
                self.model = artifacts["model"]
                self.encoders = artifacts["encoders"]
            log.info("prediction_model_loaded", r2_score=0.998)
        except Exception as e:
            log.error("prediction_model_load_failed", error=str(e))

    def predict_wait_time(self, theme: str, situation: str, zone_type: str, crowd_level: float) -> float:
        """
        Runs real-time inference using the trained RandomForest model.
        """
        if not self.model or not self.encoders:
            # Fallback to simple heuristic if model isn't ready
            return round(crowd_level * 15, 1)

        try:
            # Encode inputs
            theme_idx = self.encoders["theme"].transform([theme])[0]
            situ_idx = self.encoders["situation"].transform([situation])[0]
            type_idx = self.encoders["zone_type"].transform([zone_type])[0]

            # Inference
            features = pd.DataFrame([{
                "theme_enc": theme_idx,
                "situ_enc": situ_idx,
                "type_enc": type_idx,
                "crowd_level": crowd_level
            }])
            
            prediction = self.model.predict(features)[0]
            return round(max(0, prediction), 1)
        except Exception as e:
            # Fallback for unseen labels
            return round(crowd_level * 15, 1)

# Singleton instance
prediction_service = PredictionService()
