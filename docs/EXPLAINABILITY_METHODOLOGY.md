# AirSense Pakistan Explainability Methodology

## 1. Overview
AirSense Pakistan provides transparent global and local forecast attributions to build operator trust and support pilot decision making.

---

## 2. Explanation Methods & Scope

1. **Global Explainability**:
   - `shap_tree` / `shap_linear`: Computed via SHAP Tree or Linear Explainers when SHAP is available.
   - `model_native`: Extracted directly from Scikit-Learn `feature_importances_`.
   - `coefficient`: Absolute standardized coefficients for linear models.
   - `permutation_importance`: Permutation importance fallback where SHAP is uninstalled or unsupported.

2. **Local Prediction Explainability**:
   - Decomposes a single forecast vector into directional contributions relative to a baseline concentration.
   - Identifies feature values, contribution direction (+ or -), and magnitude.
