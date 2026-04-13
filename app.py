from flask import Flask, render_template, request
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC

from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, roc_curve, auc
from sklearn.preprocessing import StandardScaler

app = Flask(__name__)


def evaluate_model(model, X_train, X_test, y_train, y_test):
    model.fit(X_train, y_train)
    pred = model.predict(X_test)

    return {
        "acc": round(accuracy_score(y_test, pred), 3),
        "precision": round(precision_score(y_test, pred, average='weighted', zero_division=0), 3),
        "recall": round(recall_score(y_test, pred, average='weighted', zero_division=0), 3),
        "f1": round(f1_score(y_test, pred, average='weighted', zero_division=0), 3),
        "pred": pred.tolist()
    }


@app.route("/", methods=["GET", "POST"])
def home():
    result = None

    if request.method == "POST":
        file = request.files.get("file")

        try:
            df = pd.read_csv(file, encoding="latin1")

            rows, cols = df.shape
            missing = int(df.isnull().sum().sum())

            X = df.iloc[:, :-1]
            y = df.iloc[:, -1]

            class_counts = y.value_counts()
            imbalance_ratio = class_counts.min() / class_counts.max()

            if imbalance_ratio < 0.3:
                imbalance_status = "⚠️ Highly Imbalanced Dataset"
            elif imbalance_ratio < 0.7:
                imbalance_status = "🟡 Moderately Balanced"
            else:
                imbalance_status = "🟢 Well Balanced"

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.3, random_state=42
            )

            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)
            X_scaled = scaler.transform(X)

            # 🔥 Hyperparameter tuning (NEW)
            param_grid = {"C": [0.1, 1, 10]}
            grid = GridSearchCV(LogisticRegression(max_iter=1000), param_grid, cv=5)
            grid.fit(X_train, y_train)
            tuned_lr = grid.best_estimator_

            models = {
                "🌳 Decision Tree": DecisionTreeClassifier(),
                "🌲 Random Forest": RandomForestClassifier(),
                "📈 Logistic Regression (Tuned)": tuned_lr,
                "📊 SVM": SVC(probability=True)
            }

            results = {}

            for name, model in models.items():
                results[name] = evaluate_model(model, X_train, X_test, y_train, y_test)

            best_model = max(results, key=lambda x: results[x]["acc"])
            confidence = results[best_model]["acc"] * 100

            # 🔥 Feature importance
            rf = RandomForestClassifier()
            rf.fit(X_train, y_train)
            importance = rf.feature_importances_.round(4).tolist()

            # 🔥 Confusion Matrix (NEW)
            best_model_obj = models[best_model]
            best_model_obj.fit(X_train, y_train)
            pred = best_model_obj.predict(X_test)
            cm = confusion_matrix(y_test, pred).tolist()

            # 🔥 ROC Curve (NEW)
            if hasattr(best_model_obj, "predict_proba"):
                probs = best_model_obj.predict_proba(X_test)[:, 1]
                fpr, tpr, _ = roc_curve(y_test, probs)
                roc_auc = auc(fpr, tpr)
            else:
                fpr, tpr, roc_auc = [], [], 0

            # 🔥 Cross Validation (NEW)
            cv_scores = cross_val_score(best_model_obj, X_scaled, y, cv=5)
            cv_mean = round(cv_scores.mean(), 3)

            # 🔥 Train vs Test Accuracy (NEW)
            train_acc = best_model_obj.score(X_train, y_train)
            test_acc = best_model_obj.score(X_test, y_test)

            # Dataset quality
            if rows < 50:
                dataset_quality = "🔴 LOW"
                quality_score = 30
            elif rows < 300:
                dataset_quality = "🟡 MODERATE"
                quality_score = 70
            else:
                dataset_quality = "🟢 HIGH"
                quality_score = 100

            final_score = round((confidence * 0.6) + (quality_score * 0.4), 2)

            if final_score > 85:
                final_status = "🟢 STRONG MODEL"
            elif final_score > 70:
                final_status = "🟡 MODERATE MODEL"
            else:
                final_status = "🔴 WEAK MODEL"

            result = {
                "final_score": final_score,
                "final_status": final_status,
                "best_model": best_model,
                "confidence": round(confidence, 2),
                "dataset_quality": dataset_quality,
                "dataset_quality_score": quality_score,
                "imbalance_status": imbalance_status,
                "dataset_info": {"rows": rows, "columns": cols, "missing": missing},
                "models": results,
                "feature_importance": importance,
                "confusion_matrix": cm,
                "roc_fpr": fpr.tolist() if len(fpr) else [],
                "roc_tpr": tpr.tolist() if len(tpr) else [],
                "roc_auc": round(roc_auc, 3),
                "cv_score": cv_mean,
                "train_acc": round(train_acc, 3),
                "test_acc": round(test_acc, 3)
            }

        except Exception as e:
            result = {"error": str(e)}

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(debug=True)