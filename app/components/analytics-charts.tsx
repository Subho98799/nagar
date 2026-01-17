import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { IssueAnalytics, TimelineIssue } from "~/lib/timeline-api";
import styles from "./analytics-charts.module.css";

interface AnalyticsChartsProps {
  analytics: IssueAnalytics;
  issue: TimelineIssue;
}

const COLORS = {
  pie: ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#00ff00"],
  bar: "#8884d8",
};

export function AnalyticsCharts({ analytics, issue }: AnalyticsChartsProps) {
  // Prepare pie chart data
  const issueTypeData = Object.entries(analytics.issue_type_distribution).map(([name, value]) => ({
    name,
    value,
  }));

  const confidenceData = Object.entries(analytics.confidence_distribution).map(([name, value]) => ({
    name,
    value,
  }));

  const statusData = Object.entries(analytics.status_distribution).map(([name, value]) => ({
    name,
    value,
  }));

  return (
    <div className={styles.charts}>
      {/* Issue Type Distribution */}
      {issueTypeData.length > 0 && (
        <div className={styles.chartContainer}>
          <h4 className={styles.chartTitle}>Issue Type Distribution</h4>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={issueTypeData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {issueTypeData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS.pie[index % COLORS.pie.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Confidence Distribution */}
      {confidenceData.length > 0 && (
        <div className={styles.chartContainer}>
          <h4 className={styles.chartTitle}>Confidence Distribution</h4>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={confidenceData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {confidenceData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS.pie[index % COLORS.pie.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Status Distribution */}
      {statusData.length > 0 && (
        <div className={styles.chartContainer}>
          <h4 className={styles.chartTitle}>Status Distribution</h4>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={statusData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS.pie[index % COLORS.pie.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Time Series Histogram */}
      {analytics.time_series_data.length > 0 && (
        <div className={styles.chartContainer}>
          <h4 className={styles.chartTitle}>Reports Over Time</h4>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={analytics.time_series_data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill={COLORS.bar} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Location Heatmap Info */}
      {analytics.location_heatmap.length > 0 && (
        <div className={styles.chartContainer}>
          <h4 className={styles.chartTitle}>Location Heatmap</h4>
          <div className={styles.heatmapInfo}>
            <p>Total locations: {analytics.location_heatmap.length}</p>
            {issue.latitude && issue.longitude && (
              <p>
                Primary location: {issue.latitude.toFixed(4)}, {issue.longitude.toFixed(4)}
              </p>
            )}
            <p className={styles.heatmapNote}>
              Heatmap visualization would be integrated with map component
            </p>
          </div>
        </div>
      )}

      {/* Scores Summary */}
      <div className={styles.scoresSummary}>
        <h4 className={styles.chartTitle}>AI Scores</h4>
        <div className={styles.scoresGrid}>
          <div className={styles.scoreItem}>
            <span className={styles.scoreLabel}>Popularity</span>
            <span className={styles.scoreValue}>{Math.round(analytics.popularity_score)}</span>
          </div>
          <div className={styles.scoreItem}>
            <span className={styles.scoreLabel}>Confidence</span>
            <span className={styles.scoreValue}>{analytics.confidence_score}</span>
          </div>
          {analytics.priority_score !== undefined && (
            <div className={styles.scoreItem}>
              <span className={styles.scoreLabel}>Priority</span>
              <span className={styles.scoreValue}>{analytics.priority_score}</span>
            </div>
          )}
          <div className={styles.scoreItem}>
            <span className={styles.scoreLabel}>Vote Ratio</span>
            <span className={styles.scoreValue}>{(analytics.vote_ratio * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
