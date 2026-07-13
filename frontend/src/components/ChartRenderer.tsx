"use client";

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface ChartData {
  type: string;
  data: { name: string; value: number }[];
  title: string;
  x_column?: string;
  y_column?: string;
}

const COLORS = ["#000000", "#404040", "#737373", "#a3a3a3", "#d4d4d4", "#e5e5e5"];

export function ChartRenderer({ chartData }: { chartData: ChartData }) {
  if (!chartData?.data?.length) return null;

  const commonProps = {
    margin: { top: 5, right: 10, left: -10, bottom: 5 },
  };

  const renderChart = () => {
    switch (chartData.type) {
      case "bar":
        return (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData.data} {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: "#737373" }}
                axisLine={{ stroke: "#e5e5e5" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#737373" }}
                axisLine={{ stroke: "#e5e5e5" }}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#000",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "12px",
                }}
              />
              <Bar dataKey="value" fill="#000000" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );

      case "line":
        return (
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData.data} {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11, fill: "#737373" }}
                axisLine={{ stroke: "#e5e5e5" }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontSize: 11, fill: "#737373" }}
                axisLine={{ stroke: "#e5e5e5" }}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#000",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "12px",
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="#000000"
                strokeWidth={2}
                dot={{ fill: "#000000", r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        );

      case "pie":
        return (
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={chartData.data}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                labelLine={{ stroke: "#a3a3a3" }}
              >
                {chartData.data.map((_, index) => (
                  <Cell key={index} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: "#000",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "12px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        );

      case "scatter":
        return (
          <ResponsiveContainer width="100%" height={250}>
            <ScatterChart {...commonProps}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis
                type="number"
                dataKey="value"
                name={chartData.x_column || "X"}
                tick={{ fontSize: 11, fill: "#737373" }}
                axisLine={{ stroke: "#e5e5e5" }}
                tickLine={false}
              />
              <YAxis
                type="number"
                dataKey="value"
                name={chartData.y_column || "Y"}
                tick={{ fontSize: 11, fill: "#737373" }}
                axisLine={{ stroke: "#e5e5e5" }}
                tickLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: "#000",
                  border: "none",
                  borderRadius: "8px",
                  color: "#fff",
                  fontSize: "12px",
                }}
              />
              <Scatter data={chartData.data} fill="#000000" />
            </ScatterChart>
          </ResponsiveContainer>
        );

      default:
        return null;
    }
  };

  return (
    <div>
      {chartData.title && (
        <p className="text-xs font-medium text-neutral-500 mb-2">{chartData.title}</p>
      )}
      {renderChart()}
    </div>
  );
}
