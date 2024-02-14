from flask import Flask, render_template, request, jsonify
import recommendation_system as rs
from recommendation_system import recommend_items
import pandas as pd
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    number_of_items = int(request.form.get('number_of_items'))
    basic_food = request.form.get('basic_food')
    nutrition = request.form.get('nutrition')
    
    print(f"Received form data: number_of_items={number_of_items}, basic_food={basic_food}, nutrition={nutrition}")
    
    recommended_items_set = rs.recommend_items(basic_food, top_n=20)
    print(f"Recommended items: {recommended_items_set}")
    
    nutrient_table_all = rs.nutrient_per_item(recommended_items_set, nutrition)
    print(f"Nutrient table all: {nutrient_table_all}")
    
    selected_foods = rs.get_selected_foods(nutrition, nutrient_table_all, number_of_items, basic_food)
    print(f"selected_foods: {nutrient_table_all}")
        
    nutrient_table = rs.nutrient_per_item(selected_foods, nutrition)
    print(f"Nutrient table: {nutrient_table}")
        
    total_nutrient_value = rs.total_nutrient_in_recommendations(nutrient_table, nutrition)
    print(f"Total {nutrition} in Recommended Items: {total_nutrient_value}")
    
    total_nutrients = rs.calculate_total_nutrients(selected_foods)
    print(f"{total_nutrients}")
    
    result = nutrient_table.to_json(orient="split")
    parsed = json.loads(result)

    total_nutrients_ordered = [{'Nutrient': key, 'Amount': value} for key, value in total_nutrients.items()]
    
    percent_daily_values = rs.calculate_percent_daily_value(total_nutrients)
    print(f"percent_daily_values {percent_daily_values}")

    percent_daily_values_dict = percent_daily_values.to_dict(orient='records')

    response_data = {
    'table_data': parsed['data'],
    'columns': parsed['columns'],
    'total_nutrient_value': total_nutrient_value,
    'total_nutrients': total_nutrients_ordered,
    'percent_daily_values': percent_daily_values_dict  # Now this is a list of dictionaries
}
    return jsonify(response_data)


@app.route('/show-nutrients-chart')
def show_nutrients_chart():
    img_base64 = rs.plot_percent_daily_values(percent_daily_values)
    return render_template('index.html', img_base64=img_base64)


if __name__ == '__main__':
    app.run(debug=True)
