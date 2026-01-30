import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

def train_model():
    data_path = Path("ml/training_data.csv")
    if not data_path.exists():
        print(f"Błąd: Nie znaleziono pliku {data_path}")
        print("Uruchom najpierw backtest, aby wygenerować dane treningowe:")
        print("python -m app.backtest_runner")
        return

    print(f"Wczytywanie danych z {data_path}...")
    try:
        df = pd.read_csv(data_path)
    except Exception as e:
        print(f"Błąd podczas wczytywania CSV: {e}")
        return
    
    print(f"Liczba próbek: {len(df)}")
    if len(df) < 50:
        print("Ostrzeżenie: Mała liczba danych. Model może być niedouczony.")

    # Target
    if "target" not in df.columns:
        print("Błąd: Brak kolumny 'target' w danych.")
        return
        
    y = df["target"]
    X = df.drop(columns=["target"])

    # Identify categorical and numeric columns automatically if possible, or define them
    # Based on our backtest_runner logic:
    categorical_features = ["session", "strategy_type", "regime"]
    
    # Check if these columns exist in X
    existing_cat = [col for col in categorical_features if col in X.columns]
    existing_num = [col for col in X.columns if col not in existing_cat]
    
    print(f"Cechy numeryczne: {existing_num}")
    print(f"Cechy kategoryczne: {existing_cat}")

    # Preprocessing Pipeline
    numeric_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ])

    categorical_transformer = Pipeline(steps=[
        ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
        ('onehot', OneHotEncoder(handle_unknown='ignore'))
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', numeric_transformer, existing_num),
            ('cat', categorical_transformer, existing_cat)
        ])

    # Model Pipeline
    # Using GradientBoosting as default "Professional" choice
    clf = Pipeline(steps=[('preprocessor', preprocessor),
                          ('classifier', GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42))])

    # Split
    if len(df) > 10:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    else:
        print("Za mało danych na podział train/test. Trenowanie na całości.")
        X_train, y_train = X, y
        X_test, y_test = X, y

    print("Trenowanie modelu...")
    clf.fit(X_train, y_train)

    print("Ewaluacja modelu (na zbiorze testowym):")
    y_pred = clf.predict(X_test)
    print(classification_report(y_test, y_pred))
    print("Macierz pomyłek:")
    print(confusion_matrix(y_test, y_pred))

    # Feature Importance (if possible)
    try:
        model = clf.named_steps['classifier']
        # Getting feature names after one-hot encoding is tricky in pipeline, skip for now or simplify
        print("\nWażność cech (Feature Importance) - surowe indeksy:")
        print(model.feature_importances_)
    except:
        pass

    # Save
    model_path = Path("ml/model.pkl")
    joblib.dump(clf, model_path)
    print(f"\nModel zapisano do {model_path}")
    print("Gotowy do użycia w ml/server.py")

if __name__ == "__main__":
    train_model()
