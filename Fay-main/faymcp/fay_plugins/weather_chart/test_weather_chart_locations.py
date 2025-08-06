# test_weather_chart_locations.py
import unit_test
from fay_plugins.weather_chart import weather_chart

class TestWeatherChartLocations(unit_test.TestCase):
    def test_valid_locations(self):
        test_locations = [
            "Tokyo",
            "New York",
            "Paris",
            "Beijing",
            "São Paulo",
            "上海",           # Chinese input
            "München",        # German with umlaut
            "12345",          # Zip code (should work if wttr accepts it)
            "Mount Everest",  # Landmark
            "Mars"            # Should not work but test edge case
        ]

        for loc in test_locations:
            with self.subTest(location=loc):
                try:
                    url = weather_chart.run(loc)
                    self.assertTrue(url.startswith("http"), f"Failed for location: {loc}")
                    print(f"{loc}: ✅ {url}")
                except Exception as e:
                    print(f"{loc}: ❌ Exception occurred: {e}")
                    # You can assert failure or just skip if that's expected
                    if loc == "Mars":
                        self.assertIsInstance(e, Exception)  # Acceptable failure
                    else:
                        self.fail(f"Unexpected failure for location {loc}: {e}")

if __name__ == "__main__":
    unit_test.main()
