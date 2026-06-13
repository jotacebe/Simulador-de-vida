# Fórmulas: Mortalidad

## 1. Ley de Gompertz-Makeham Adaptativa
La probabilidad de muerte diaria ($P_d$) se calcula utilizando una tasa de riesgo ($\lambda$):
$$\lambda = \left( \frac{\alpha}{365} \right) \cdot e^{\left( \frac{\beta}{365 \cdot L} \right) \cdot A} \cdot (1 + (P \cdot M))$$

Donde:
* **$A$**: Edad en días (`age_days`).
* **$L$**: Gen de Longevidad (`genome.longevity`).
* **$P$**: Presión ambiental.
* **$M$**: Multiplicador de densidad (`density_penalty_multiplier`).
* **$\alpha, \beta$**: Constantes base ($0.0001$ y $0.08$).

## 2. Probabilidad Acumulada
Como el simulador puede ejecutarse con diferentes `delta_days`, usamos la función de distribución acumulada para calcular la probabilidad real de muerte en el periodo:
$$P_{muerte} = 1 - e^{-\lambda \cdot \Delta t}$$

## 3. Impacto de la Inmunidad
Si la entidad está enferma ($is\_sick = True$), el riesgo se escala mediante:
$$R_{final} = \lambda \cdot \max\left(1.1, \frac{2.5}{I}\right)$$
*Donde $I$ es el gen de inmunidad.*