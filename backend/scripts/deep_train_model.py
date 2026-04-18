import sys
import os
sys.path.append(os.getcwd())

import pickle
import random
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder

# Import the simulator logic to ensure consistency
from app.services.venue_simulator import get_gravity_config, THEME_SITUATIONS

def generate_training_data(n_samples=50000):
    """
    Generates a massive 'Historical' dataset based on thematic ground truth.
    Features: [theme, situation, zone_type, capacity, crowd_level]
    Target: [wait_time_minutes]
    """
    print(f"--- Generating {n_samples} historical snapshots for Deep Training ---")
    
    themes = list(THEME_SITUATIONS.keys())
    zone_types = ["gate", "seating", "concession", "plaza"]
    data = []

    for _ in range(n_samples):
        theme = random.choice(themes)
        situation = random.choice(THEME_SITUATIONS[theme])
        z_type = random.choice(zone_types)
        
        # Simulated crowd level based on importance
        is_sink = random.random() < 0.3
        if is_sink:
            crowd_level = random.uniform(0.6, 0.95)
        else:
            crowd_level = random.uniform(0.05, 0.4)
            
        # Wait time physics: 
        # Gates have exponential wait times. Seating/Plaza has linear.
        if z_type == "gate":
            wait_time = (crowd_level ** 2) * 45 + random.uniform(0, 5)
        elif z_type == "seating":
            wait_time = crowd_level * 15 + random.uniform(0, 2)
        else:
            wait_time = crowd_level * 10 + random.uniform(0, 1)

        data.append({
            "theme": theme,
            "situation": situation,
            "zone_type": z_type,
            "crowd_level": crowd_level,
            "wait_time": wait_time
        })

    return pd.DataFrame(data)

def train_model():
    df = generate_training_data()
    
    # Preprocessing
    le_theme = LabelEncoder()
    le_situ = LabelEncoder()
    le_type = LabelEncoder()
    
    df['theme_enc'] = le_theme.fit_transform(df['theme'])
    df['situ_enc'] = le_situ.fit_transform(df['situation'])
    df['type_enc'] = le_type.fit_transform(df['zone_type'])
    
    X = df[['theme_enc', 'situ_enc', 'type_enc', 'crowd_level']]
    y = df['wait_time']
    
    print("--- Training Random Forest Regressor ---")
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    
    # Save model and encoders
    resources_dir = "app/resources"
    if not os.path.exists(resources_dir):
        os.makedirs(resources_dir)
        
    artifacts = {
        "model": model,
        "encoders": {
            "theme": le_theme,
            "situation": le_situ,
            "zone_type": le_type
        }
    }
    
    model_path = os.path.join(resources_dir, "wait_time_model.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(artifacts, f)
        
    print(f"DONE: Model saved to {model_path}")
    print(f"R^2 Score: {model.score(X, y):.4f}")

if __name__ == "__main__":
    train_model()
