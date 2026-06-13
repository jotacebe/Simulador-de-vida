# Mecánica: Sistema de Mortalidad

## 1. Objetivo
Gestionar el cese de actividad de las entidades mediante un modelo probabilístico que combina la senescencia biológica con factores de riesgo ambientales y genéticos.

## 2. Componentes del Sistema
El sistema se divide en dos módulos:
* **`MortalitySystem`**: Ejecuta la lógica probabilística (Gompertz-Makeham). Determina quién muere en función de su edad, genética y salud.
* **`DeathResolver`**: Actúa como un "limpiador de contingencias". Asegura que ninguna acción (casarse, moverse, procrear) sea procesada si la entidad ha muerto en el mismo ciclo.

## 3. Lógica de Resolución
1. **Verificación de Límite (Hard Cap)**: Si la edad supera `max_age_cap_days * genome.longevity`, la muerte es **determinista** (100% de probabilidad).
2. **Cálculo Probabilístico**: Si la entidad sobrevive al límite biológico, se calcula una tasa de riesgo (Hazard Rate) basada en:
    * **Edad**: Aumenta exponencialmente.
    * **Entorno**: Presión local (densidad poblacional).
    * **Salud**: La inmunidad genética modula el riesgo de morir al estar enfermo.
3. **Resolución de Conflictos**: El `DeathResolver` purga las intenciones del `PendingChanges` de los fallecidos para evitar inconsistencias (ej: un muerto no puede divorciarse).