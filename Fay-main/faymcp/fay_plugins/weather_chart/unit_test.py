# test_weather_chart.py
import weather_chart

if __name__ == "__main__":
    # Change the location to test other cities
    location = "Tokyo"
    chart_url = weather_chart.run(location)
    print("Generated chart URL:", chart_url)
