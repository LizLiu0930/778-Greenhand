import pandas as pd
import json
from mlxtend.frequent_patterns import association_rules, apriori
from mlxtend.preprocessing import TransactionEncoder

# 加载rules和其他必要的数据
rules = pd.read_csv('rules.csv')
foodID_groceries = pd.read_csv('foodID_groceries.csv')
df_nutrients = pd.read_excel('NZFOODNutrients.xlsx', sheet_name='FOODFiles-Nutrients')
items_amount = pd.read_excel('top_50_items_amount.xlsx')
nutri_intake = pd.read_excel('Nutrition intake.xlsx')
nutrient_list = nutri_intake['Nutrition']


def parse_frozenset(frozenset_str):
    # 假设 frozenset_str 是 "frozenset({'item1', 'item2'})"
    # 我们需要将其转换为一个真正的 frozenset 对象
    # 首先去除 "frozenset()" 部分
    items_str = frozenset_str.strip("frozenset()")
    # 去除大括号 "{}" 并分割成列表
    items_list = items_str.strip("{}").replace("'", "").split(', ')
    # 返回 frozenset 对象
    return frozenset(items_list)

# 在读取 rules.csv 后立即转换 antecedents 和 consequents 列
rules['antecedents'] = rules['antecedents'].apply(parse_frozenset)
rules['consequents'] = rules['consequents'].apply(parse_frozenset)

def recommend_items(item, top_n=20):
    filtered_rules = rules[rules['antecedents'].apply(lambda x: item in x)]
    sorted_rules = filtered_rules.sort_values(by='lift', ascending=False)
    recommended_items = []
    item_class = items_amount.loc[items_amount['itemDescription'] == item, 'Classification']
    item_class = None if item_class.isna().any() else item_class.iloc[0]
    recommended_items.append((item, item_class))
    
    for _, rule_row in sorted_rules.iterrows():
        if len(recommended_items) >= top_n:
            break
        consequents = set(rule_row['consequents'])
        for consequent in consequents:
            if len(recommended_items) >= top_n:
                break
            if consequent in [item[0] for item in recommended_items]:
                continue
            consequent_class = items_amount.loc[items_amount['itemDescription'] == consequent, 'Classification']
            consequent_class = None if consequent_class.isna().any() else consequent_class.iloc[0]
            if consequent_class is not None and consequent_class in [item[1] for item in recommended_items]:
                continue
            recommended_items.append((consequent, consequent_class))
    
    return [item[0] for item in recommended_items]


def get_average_nutrient(item, nutrient_keyword, amount):
    nutrient_column = find_nutrient_column(nutrient_keyword, df_nutrients)
    if nutrient_column is None:
        return 0
    food_ids = foodID_groceries[foodID_groceries['Item'] == item]['FoodID'].iloc[0].split('/')
    total_nutrient = 0
    count = 0
    for fid in food_ids:
        if fid in df_nutrients['FoodID'].values:
            nutrient_value = df_nutrients[df_nutrients['FoodID'] == fid][nutrient_column].iloc[0]
            if not pd.isna(nutrient_value):
                total_nutrient += nutrient_value
                count += 1
    average_nutrient = total_nutrient / count if count > 0 else 0
    adjusted_nutrient = average_nutrient * (amount / 100)
    return adjusted_nutrient


def find_nutrient_column(nutrient_keyword, df):
    for column in df.columns:
        if nutrient_keyword.lower() in column.lower():
            return column
    return None

def nutrient_per_item(recommended_items, nutrient_keyword):
    nutrients = []
    nutrient_unit = nutri_intake.loc[nutri_intake['Nutrition'] == nutrient_keyword, 'Unit'].values[0]
    for item in recommended_items:
        item_data = items_amount[items_amount['itemDescription'] == item]
        if not item_data.empty:
            amount = item_data['Amount(ml/g)'].iloc[0]
            unit = item_data['Unit'].iloc[0]
            amount_with_unit = f"{amount} {unit}"
            avg_nutrient = get_average_nutrient(item, nutrient_keyword, amount)
            nutrients.append({
                'Item': item,
                'Quantity': amount_with_unit,
                f'{nutrient_keyword.title()}({nutrient_unit})': round(avg_nutrient, 2)  # Rounded to two decimal places
            })
        else:
            print(f"Item {item} not found in items_amount DataFrame.")
    return pd.DataFrame(nutrients)

def get_selected_foods(nutrient_keyword, nutrient_table, items_number, basic_food):
    nutrient_col = next(col for col in nutrient_table.columns if nutrient_keyword.lower() in col.lower().replace("(mg)", "").replace("(g)", "").replace("(kj)", ""))
    is_beneficial = nutri_intake.loc[nutri_intake['Nutrition'].str.lower() == nutrient_keyword.lower(), 'Beneficial'].iloc[0] == 'Y'
    sorted_nutrient_table = nutrient_table.sort_values(by=nutrient_col, ascending=not is_beneficial)
    top_items = sorted_nutrient_table.head(items_number - 1)['Item'].tolist()
    if basic_food not in top_items:
        top_items.append(basic_food)
    return top_items

def total_nutrient_in_recommendations(nutrient_table, nutrient_keyword):
    nutrient_column = next(col for col in nutrient_table.columns if nutrient_keyword.lower() in col.lower())
    total_nutrient_value = nutrient_table[nutrient_column].sum()
    unit = nutrient_column.split('(')[-1].strip(')')
    return f"{total_nutrient_value} {unit}"

def calculate_total_nutrients(selected_foods):
    total_nutrients = {nutrient: 0 for nutrient in nutrient_list}
    for item in selected_foods:
        item_amount_data = items_amount[items_amount['itemDescription'].str.lower() == item.lower()]
        if item_amount_data.empty:
            continue
        item_amount = item_amount_data['Amount(ml/g)'].iloc[0] / 100  # 转换为基准量（例如，g或ml）
        for nutrient in nutrient_list:
            avg_nutrient = get_average_nutrient(item, nutrient, item_amount)  # 假设基准量为100
            total_nutrients[nutrient] += avg_nutrient * item_amount
    for nutrient, value in total_nutrients.items():
        total_nutrients[nutrient] = round(value, 2)
    return total_nutrients

def calculate_total_nutrients(selected_foods):
    total_nutrients = {}
    for nutrient_keyword in nutrient_list:
        total_nutrient = 0
        for item in selected_foods:
            item_amount_data = items_amount[items_amount['itemDescription'] == item]
            if not item_amount_data.empty:
                item_amount = item_amount_data['Amount(ml/g)'].iloc[0]
                adjusted_nutrient = get_average_nutrient(item, nutrient_keyword, item_amount)
                total_nutrient += adjusted_nutrient
        total_nutrients[nutrient_keyword] = round(total_nutrient, 2)
    return total_nutrients

def calculate_total_nutrients(selected_foods):
    total_nutrients = {}
    for nutrient_keyword in nutrient_list:
        total_nutrient = 0
        for item in selected_foods:
            item_amount_data = items_amount[items_amount['itemDescription'] == item]
            if not item_amount_data.empty:
                item_amount = item_amount_data['Amount(ml/g)'].iloc[0]
                adjusted_nutrient = get_average_nutrient(item, nutrient_keyword, item_amount)
                total_nutrient += adjusted_nutrient
        nutrient_unit = nutri_intake.loc[nutri_intake['Nutrition'] == nutrient_keyword, 'Unit'].values[0]
        total_nutrients[nutrient_keyword] = f"{round(total_nutrient, 2)} {nutrient_unit}"
    if 'Energy' in total_nutrients:
        energy_value = float(total_nutrients['Energy'].split()[0])
        calories_value = energy_value * 0.24  # Convert kJ to kcal
        total_nutrients['Calories'] = f"{round(calories_value, 2)} kcal"
    return total_nutrients

def calculate_percent_daily_value(total_nutrients):
    nutrient_values = []
    for nutrient, value in total_nutrients.items():
        nutrient_value, unit = value.split()
        nutrient_value = float(nutrient_value)
        daily_value_row = nutri_intake[nutri_intake['Nutrition'] == nutrient]
        if not daily_value_row.empty:
            daily_value = daily_value_row['Daily Value'].values[0]
            percent_daily_value = (nutrient_value / daily_value) * 100
            nutrient_values.append({
                'Nutrition': nutrient,
                'Value': value,
                '% Daily Value': f"{round(percent_daily_value, 2)}%"
            })
    return pd.DataFrame(nutrient_values)