// weatherapi.ts
import axios from "axios";

const WEATHERAPI_KEY = "4bf597a34a5a49549c580552253006"; 

export async function getWeatherChartUrl(city: string): Promise<string | -1> {
  try {
    const today = new Date();
    const labels: string[] = [];
    const temps: (number | null)[] = [];

    for (let daysAgo = 5; daysAgo > 0; daysAgo--) {
      const date = new Date(today);
      date.setDate(today.getDate() - daysAgo);
      const formattedDate = date.toISOString().split("T")[0];

      const url = `http://api.weatherapi.com/v1/history.json?key=${WEATHERAPI_KEY}&q=${encodeURIComponent(
        city
      )}&dt=${formattedDate}`;

      const response = await axios.get(url);
      const data = response.data;

      if ("error" in data) return -1;

      if (
        data.forecast &&
        data.forecast.forecastday &&
        data.forecast.forecastday[0]?.day?.avgtemp_c !== undefined
      ) {
        temps.push(Math.round(data.forecast.forecastday[0].day.avgtemp_c * 100) / 100);
        labels.push(formattedDate);
      } else {
        temps.push(null);
        labels.push(formattedDate);
      }
    }

    return generateChartUrl(labels, temps, city);
  } catch (e) {
    return -1;
  }
}

function generateChartUrl(labels: string[], temps: (number | null)[], city: string): string {
  const safeTemps = temps.map((t) => (t === null ? "null" : t));

  const chartConfig = {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: `Past 5 Days Temperature in ${city}`,
          data: safeTemps,
        },
      ],
    },
    options: {
      title: {
        display: true,
        text: `Temperature in ${city} (°C)`,
      },
    },
  };

  const encoded = encodeURIComponent(JSON.stringify(chartConfig));
  return `https://quickchart.io/chart?c=${encoded}`;
}
