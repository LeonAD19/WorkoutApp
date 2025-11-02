def mifflin_bmr(sex: str, age: float, height_cm: float, weight_kg: float) -> float:
    # sex: "male"/"female"; height in cm, weight in kg
    s = 5 if (sex or "").lower().startswith("m") else -161
    return 10*weight_kg + 6.25*height_cm - 5*age + s

def katch_bmr(weight_kg: float, body_fat_percent: float) -> float:
    # LBM in kg
    lbm = weight_kg * (1 - (body_fat_percent or 0)/100.0)
    return 370 + 21.6 * lbm

def activity_factor(level: str) -> float:
    level = (level or "moderate").lower()
    table = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9
    }
    return table.get(level, 1.55)

def tdee(sex, age, height_cm, weight_kg, activity, body_fat_percent=None):
    if body_fat_percent is not None:
        bmr = katch_bmr(weight_kg, body_fat_percent)
    else:
        bmr = mifflin_bmr(sex, age, height_cm, weight_kg)
    return bmr * activity_factor(activity)

def goal_calories(tdee_kcal: float, goal: str, pace_lbs_per_week: float = 0.0) -> float:
    # 1 lb/week ~ 500 kcal/day; 2 lb/week ~ 1000 kcal/day
    adj = 500.0 * abs(pace_lbs_per_week or 0.0)
    goal = (goal or "maintain").lower()
    if goal.startswith("cut") or goal.startswith("lose"):
        return max(1200, tdee_kcal - adj)  # floor for safety
    if goal.startswith("bulk") or goal.startswith("gain"):
        return tdee_kcal + adj
    return tdee_kcal

def macro_targets(calories: float, weight_kg: float, goal: str, protein_g_per_kg: float = None):
    # default protein targets
    if protein_g_per_kg is None:
        if goal.startswith(("cut","lose")):
            protein_g_per_kg = 2.0   # 1.8–2.4 g/kg; pick middle
        elif goal.startswith(("bulk","gain")):
            protein_g_per_kg = 1.8   # 1.6–2.2 g/kg
        else:
            protein_g_per_kg = 1.8

    protein_g = protein_g_per_kg * weight_kg
    protein_kcal = protein_g * 4

    # fat: 25% calories (safe range 20–30%)
    fat_kcal = calories * 0.25
    fat_g = fat_kcal / 9.0

    # carbs: remainder
    carbs_kcal = max(0.0, calories - protein_kcal - fat_kcal)
    carbs_g = carbs_kcal / 4.0

    return {
        "calories": round(calories),
        "protein_g": round(protein_g),
        "fat_g": round(fat_g),
        "carbs_g": round(carbs_g)
    }
