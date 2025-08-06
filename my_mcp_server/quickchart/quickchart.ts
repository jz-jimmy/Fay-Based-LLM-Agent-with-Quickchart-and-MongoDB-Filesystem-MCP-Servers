// // quickchart.ts
// import QuickChart from "quickchart-js";
// import { writeFileSync } from "fs";
// import path from "path";
// import crypto from "crypto";

// export async function generateChartImageFile(
//   title: string,
//   labels: string[],
//   data: number[],
//   chartType: string = "line"
// ): Promise<string | -1> {
//   try {
//     const chart = new QuickChart();

//     chart.setConfig({
//       type: chartType,
//       data: {
//         labels: labels,
//         datasets: [
//           {
//             label: title,
//             data: data,
//           },
//         ],
//       },
//       options: {
//         plugins: {
//           title: {
//             display: true,
//             text: title,
//           },
//         },
//       },
//     });

//     chart.setWidth(500);
//     chart.setHeight(300);
//     chart.setBackgroundColor("white");

//     const imageBuffer = await chart.toBinary(); // image buffer
//     const id = crypto.randomBytes(6).toString("hex");
//     const filename = `chart-${id}.png`;
//     const filepath = path.join("charts", filename);

//     writeFileSync(filepath, imageBuffer); // save locally

//     return `/charts/${filename}`; // return relative URL
//   } catch (err) {
//     return -1;
//   }
// }
// quickchart.ts
import QuickChart from "quickchart-js";

export async function generateChartImageFile(
  title: string,
  labels: string[],
  data: number[],
  chartType: string = "line",
): Promise<string | -1> {
  try {
    const chart = new QuickChart();

    chart.setConfig({
      type: chartType,
      data: {
        labels,
        datasets: [
          {
            label: title,
            data,
          },
        ],
      },
      options: {
        plugins: {
          title: {
            display: true,
            text: title,
          },
        },
      },
    });

    chart.setWidth(500);
    chart.setHeight(300);
    chart.setBackgroundColor("white");

    /* ---------- changed block ---------- */
    const url = chart.getUrl();      // encoded config → https://quickchart.io/chart?... 
    return url;                      // absolute URL, no local file
    /* ----------------------------------- */
  } catch (err) {
    return -1;
  }
}
