import requests
import datetime
import json
import urllib.parse

# ==== INSERT YOUR WeatherAPI KEY HERE ====
WEATHERAPI_KEY = '4bf597a34a5a49549c580552253006'

def get_past_temperatures(city):
    base_url = "http://api.weatherapi.com/v1/history.json"
    today = datetime.date.today()
    temps = []
    labels = []

    for days_ago in range(5, 0, -1):
        date = today - datetime.timedelta(days=days_ago)
        formatted_date = date.strftime("%Y-%m-%d")
        url = f"{base_url}?key={WEATHERAPI_KEY}&q={city}&dt={formatted_date}"

        response = requests.get(url)
        data = response.json()

        # Return failure on any error
        if "error" in data:
            return None, None

        if 'forecast' in data and data['forecast']['forecastday']:
            avg_temp = data['forecast']['forecastday'][0]['day']['avgtemp_c']
            temps.append(round(avg_temp, 2))
            labels.append(formatted_date)
        else:
            temps.append(None)
            labels.append(formatted_date)

    return labels, temps

def generate_chart(labels, temps, city):
    js_safe_temps = ['null' if t is None else t for t in temps]

    chart_config = {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": f"Past 5 Days Temperature in {city}",
                "data": js_safe_temps
            }]
        },
        "options": {
            "title": {
                "display": True,
                "text": f"Temperature in {city} (°C)"
            }
        }
    }

    json_config = json.dumps(chart_config, ensure_ascii=False).replace('"null"', 'null')
    encoded_config = urllib.parse.quote(json_config)
    return f"https://quickchart.io/chart?c={encoded_config}"

# ==== PUBLIC FUNCTION ====
def get_weather_chart_url(city):
    try:
        labels, temps = get_past_temperatures(city)
        if labels is None or temps is None:
            return -1
        return generate_chart(labels, temps, city)
    except Exception:
        return -1

# ==== Standalone test ====
if __name__ == "__main__":
    city = input("Enter city name: ")
    result = get_weather_chart_url(city)
    print(result)


'''
how other files can import this function


from weatherapi import get_weather_chart_url

url_or_error = get_weather_chart_url("London")
if url_or_error == -1:
    xxx
else:
    print("Chart URL:", url_or_error)
'''