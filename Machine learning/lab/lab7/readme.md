### Task 1: Why Leakage Invalidates the Comparison

Data leakage occurs when information from outside the training partition influences data preprocessing. In this experiment:

* **Distorts true generalization**: Calculating imputation values (e.g., median) or scaling parameters ($\mu, \sigma$) across the entire dataset exposes the model to test set distribution parameters during training. The test set stops acting as an independent holdout, artificially inflating performance metrics.
* **Biases model comparison**: Different classification algorithms have different sensitivities to feature scaling and distribution shifts. Leaking test distribution statistics alters the feature space in ways that can arbitrarily favor one algorithm over another, making it impossible to determine which algorithm actually generalizes better to genuine, unseen patient screenings.
* **Violates deployment realities**: In a clinical setting, new patient data arrives individually without knowledge of a future population's mean or variance. Using training-only statistics ensures the evaluation reflects actual clinical inference.

### Task 2: Scratch Model Dynamics & Convergence

* **Perceptron update mechanism**: The perceptron uses a discrete step function and updates weights and bias strictly when a misclassification occurs ($y_i \neq \hat{y}_i$). Because the diabetes dataset is not linearly separable, the algorithm cannot reach zero errors. It oscillates endlessly across epochs rather than settling, stopping only when hitting `max_epochs`.
* **Logistic Regression convergence**: Logistic regression outputs continuous class probabilities via the sigmoid function and minimizes binary cross-entropy loss using batch gradient descent. Because the cross-entropy loss surface is convex, gradient updates steadily reduce loss until the change between successive epochs falls below the tolerance threshold ($10^{-6}$), reaching a stable, unique minimum.

### Task 3: Boundary Differences & Coefficient Discrepancies

* **How boundaries differ**:
* The **Perceptron boundary** is volatile. Because it cannot achieve zero training error on non-separable data, its final boundary is arbitrarily determined by whichever misclassified points triggered updates in the final epoch.
* The **Logistic Regression boundary** is smooth and balanced. It positions the hyperplane ($w_1 x_1 + w_2 x_2 + b = 0$) to optimize the probability distribution across all data points simultaneously, placing the boundary cleanly between the core densities of the two classes.


* **Why exact coefficients differ between scratch and scikit-learn**:
* **L2 Regularization**: Scikit-learn's `LogisticRegression` applies an L2 penalty by default (`C=1.0`), which shrinks weights toward zero to mitigate overfitting. The scratch model optimizes unpenalized loss, leading to larger coefficient magnitudes.
* **Optimizer differences**: The scratch model uses standard first-order batch gradient descent with a constant learning rate. Scikit-learn uses **L-BFGS**, a quasi-Newton solver that approximates second-order curvature (Hessian), adapting step sizes to converge to a tighter numerical optimum.
* **Perceptron sample shuffling**: Scikit-learn's `Perceptron` sets `shuffle=True` by default, reordering training instances each epoch and using early stopping based on validation score plateaus. The scratch version processes samples in static sequence, ending on a different set of boundary weights.



### Task 4: Evaluation, Asymmetric Costs, and Model Selection

* **Clinical cost asymmetry (FN vs. FP)**:
* A **False Negative (FN)** means a diabetic patient is told they are healthy and leaves without treatment, leading to undetected disease progression and severe long-term complications.
* A **False Positive (FP)** means a healthy patient receives a false alarm and undergoes a follow-up confirmatory blood test (such as an HbA1c or oral glucose tolerance test). While inconvenient, the clinical risk is negligible.
* Because missing a positive case carries a much higher clinical cost than a false alarm, the team must prioritize **minimizing False Negatives**, which directly means **maximizing Recall** ($\frac{\text{TP}}{\text{TP} + \text{FN}}$).


* **Why accuracy is misleading**:
* In an imbalanced dataset (~65% negative / ~35% positive), accuracy is dominated by True Negatives. A model can achieve 75%+ accuracy simply by predicting negative most of the time, while simultaneously missing over 40% of positive cases. Accuracy rewards predicting the majority class and actively conceals high, dangerous false-negative rates.


* **Preferable model choice**:
* Between the properly converging models, **the model with the highest Recall and lowest FN count on the held-out test set** is preferred for screening.
* In a clinical pipeline, **Logistic Regression** is the superior architecture because it outputs calibrated probabilities ($\hat{p}$). Instead of sticking to an arbitrary 0.5 decision threshold, clinicians can lower the classification threshold (e.g., to 0.3 or 0.25), directly driving Recall above 85–90% to catch nearly all positive cases while managing the false-alarm rate.### Task 1: Why Leakage Invalidates the Comparison

Data leakage occurs when information from outside the training partition influences data preprocessing. In this experiment:

* **Distorts true generalization**: Calculating imputation values (e.g., median) or scaling parameters ($\mu, \sigma$) across the entire dataset exposes the model to test set distribution parameters during training. The test set stops acting as an independent holdout, artificially inflating performance metrics.
* **Biases model comparison**: Different classification algorithms have different sensitivities to feature scaling and distribution shifts. Leaking test distribution statistics alters the feature space in ways that can arbitrarily favor one algorithm over another, making it impossible to determine which algorithm actually generalizes better to genuine, unseen patient screenings.
* **Violates deployment realities**: In a clinical setting, new patient data arrives individually without knowledge of a future population's mean or variance. Using training-only statistics ensures the evaluation reflects actual clinical inference.

### Task 2: Scratch Model Dynamics & Convergence

* **Perceptron update mechanism**: The perceptron uses a discrete step function and updates weights and bias strictly when a misclassification occurs ($y_i \neq \hat{y}_i$). Because the diabetes dataset is not linearly separable, the algorithm cannot reach zero errors. It oscillates endlessly across epochs rather than settling, stopping only when hitting `max_epochs`.
* **Logistic Regression convergence**: Logistic regression outputs continuous class probabilities via the sigmoid function and minimizes binary cross-entropy loss using batch gradient descent. Because the cross-entropy loss surface is convex, gradient updates steadily reduce loss until the change between successive epochs falls below the tolerance threshold ($10^{-6}$), reaching a stable, unique minimum.

### Task 3: Boundary Differences & Coefficient Discrepancies

* **How boundaries differ**:
* The **Perceptron boundary** is volatile. Because it cannot achieve zero training error on non-separable data, its final boundary is arbitrarily determined by whichever misclassified points triggered updates in the final epoch.
* The **Logistic Regression boundary** is smooth and balanced. It positions the hyperplane ($w_1 x_1 + w_2 x_2 + b = 0$) to optimize the probability distribution across all data points simultaneously, placing the boundary cleanly between the core densities of the two classes.


* **Why exact coefficients differ between scratch and scikit-learn**:
* **L2 Regularization**: Scikit-learn's `LogisticRegression` applies an L2 penalty by default (`C=1.0`), which shrinks weights toward zero to mitigate overfitting. The scratch model optimizes unpenalized loss, leading to larger coefficient magnitudes.
* **Optimizer differences**: The scratch model uses standard first-order batch gradient descent with a constant learning rate. Scikit-learn uses **L-BFGS**, a quasi-Newton solver that approximates second-order curvature (Hessian), adapting step sizes to converge to a tighter numerical optimum.
* **Perceptron sample shuffling**: Scikit-learn's `Perceptron` sets `shuffle=True` by default, reordering training instances each epoch and using early stopping based on validation score plateaus. The scratch version processes samples in static sequence, ending on a different set of boundary weights.



### Task 4: Evaluation, Asymmetric Costs, and Model Selection

* **Clinical cost asymmetry (FN vs. FP)**:
* A **False Negative (FN)** means a diabetic patient is told they are healthy and leaves without treatment, leading to undetected disease progression and severe long-term complications.
* A **False Positive (FP)** means a healthy patient receives a false alarm and undergoes a follow-up confirmatory blood test (such as an HbA1c or oral glucose tolerance test). While inconvenient, the clinical risk is negligible.
* Because missing a positive case carries a much higher clinical cost than a false alarm, the team must prioritize **minimizing False Negatives**, which directly means **maximizing Recall** ($\frac{\text{TP}}{\text{TP} + \text{FN}}$).


* **Why accuracy is misleading**:
* In an imbalanced dataset (~65% negative / ~35% positive), accuracy is dominated by True Negatives. A model can achieve 75%+ accuracy simply by predicting negative most of the time, while simultaneously missing over 40% of positive cases. Accuracy rewards predicting the majority class and actively conceals high, dangerous false-negative rates.


* **Preferable model choice**:
* Between the properly converging models, **the model with the highest Recall and lowest FN count on the held-out test set** is preferred for screening.
* In a clinical pipeline, **Logistic Regression** is the superior architecture because it outputs calibrated probabilities ($\hat{p}$). Instead of sticking to an arbitrary 0.5 decision threshold, clinicians can lower the classification threshold (e.g., to 0.3 or 0.25), directly driving Recall above 85–90% to catch nearly all positive cases while managing the false-alarm rate.
