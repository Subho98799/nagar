import { useEffect, useMemo, useState } from "react";
import { Header } from "~/components/header";
import { fetchCityPulse, listPulseCities, type CityPulseResponse } from "~/lib/city-pulse";
import { fetchIssues } from "~/lib/api";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
import styles from "./city-overview.module.css";

const COLORS = ["#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];

type TrendPoint = { bucket: string; count: number };

export default function CityOverview() {
  const [cities, setCities] = useState<string[]>([]);
  const [city, setCity] = useState<string>("Demo City");
  const [pulse, setPulse] = useState<CityPulseResponse | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const data = await listPulseCities();
        if (!mounted) return;
        const list = data.cities?.length ? data.cities : ["Demo City"];
        setCities(list);
        setCity(list[0] || "Demo City");
      } catch (e: any) {
        if (!mounted) return;
        setCities(["Demo City"]);
        setCity("Demo City");
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;
    (async () => {
      setLoading(true);
      setError("");
      try {
        const p = await fetchCityPulse(city);
        if (!mounted) return;
        setPulse(p);
      } catch (e: any) {
        if (!mounted) return;
        setPulse(null);
        setError(e?.message || "Failed to load City Pulse.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [city]);

  useEffect(() => {
    let mounted = true;
    (async () => {
      // Read-only, lightweight trend using existing /map/issues timestamps.
      // This is observational only and does not mutate any data.
      try {
        const issues = await fetchIssues(city);
        if (!mounted) return;
        const now = Date.now();
        const windowHours = 12;
        const bucketMins = 60;
        const buckets: TrendPoint[] = [];
        for (let h = windowHours - 1; h >= 0; h--) {
          const label = `${h}h`;
          buckets.push({ bucket: label, count: 0 });
        }
        for (const i of issues) {
          const ts = Date.parse(i.created_at || "");
          if (!Number.isFinite(ts)) continue;
          const ageHrs = Math.floor((now - ts) / (1000 * 60 * bucketMins));
          if (ageHrs >= 0 && ageHrs < windowHours) {
            buckets[windowHours - 1 - ageHrs].count += 1;
          }
        }
        setTrend(buckets);
      } catch {
        if (mounted) setTrend([]);
      }
    })();
    return () => {
      mounted = false;
    };
  }, [city]);

  const issueDist = useMemo(() => {
    const data = pulse?.active_issues || {};
    return Object.entries(data).map(([name, value]) => ({ name, value }));
  }, [pulse]);

  const confidenceDist = useMemo(() => {
    const data = pulse?.confidence_breakdown || {};
    return Object.entries(data).map(([name, value]) => ({ name, value }));
  }, [pulse]);

  return (
    <div className={styles.page}>
      <Header />
      <main className={styles.container}>
        <header className={styles.top}>
          <div className={styles.titleBlock}>
            <h1 className={styles.title}>City Overview</h1>
            <p className={styles.subtitle}>
              A calm, read-only snapshot of what is currently reported. No voting, no comments, no user interaction signals.
            </p>
          </div>

          <div className={styles.controls}>
            <label className={styles.label}>
              City
              <select className={styles.select} value={city} onChange={(e) => setCity(e.target.value)}>
                {cities.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </label>
          </div>
        </header>

        <section className={styles.pulseCard}>
          <div className={styles.pulseHeader}>
            <h2 className={styles.sectionTitle}>City Pulse</h2>
            {pulse && <div className={styles.meta}>Active reports: {pulse.report_count}</div>}
          </div>

          {loading ? (
            <div className={styles.loading}>Loading City Pulse…</div>
          ) : error ? (
            <div className={styles.empty}>
              <div>No verified city updates available at the moment.</div>
              <p className={styles.note}>
                This view updates automatically when new reports are reviewed.
              </p>
            </div>
          ) : pulse ? (
            <>
              <p className={styles.summary}>{pulse.summary}</p>

              <div className={styles.grid}>
                <div className={styles.panel}>
                  <h3 className={styles.panelTitle}>Issue categories (active)</h3>
                  {issueDist.length === 0 ? (
                    <div className={styles.empty}>No active issues.</div>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <PieChart>
                        <Pie data={issueDist} dataKey="value" nameKey="name" outerRadius={80}>
                          {issueDist.map((_, idx) => (
                            <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  )}
                </div>

                <div className={styles.panel}>
                  <h3 className={styles.panelTitle}>Confidence breakdown</h3>
                  {confidenceDist.length === 0 ? (
                    <div className={styles.empty}>No data.</div>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={confidenceDist}>
                        <XAxis dataKey="name" />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Bar dataKey="value" fill="#0ea5e9" />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>

                <div className={styles.panel}>
                  <h3 className={styles.panelTitle}>Most affected localities</h3>
                  {pulse.affected_localities.length === 0 ? (
                    <div className={styles.empty}>No localities reported.</div>
                  ) : (
                    <ul className={styles.list}>
                      {pulse.affected_localities.slice(0, 10).map((l) => (
                        <li key={l} className={styles.listItem}>
                          {l}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className={styles.panel}>
                  <h3 className={styles.panelTitle}>Last 12 hours (reported items)</h3>
                  {trend.length === 0 ? (
                    <div className={styles.empty}>No trend data.</div>
                  ) : (
                    <ResponsiveContainer width="100%" height={220}>
                      <BarChart data={trend}>
                        <XAxis dataKey="bucket" />
                        <YAxis allowDecimals={false} />
                        <Tooltip />
                        <Bar dataKey="count" fill="#22c55e" />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                  <p className={styles.note}>Observational only. No prediction or recommendation.</p>
                </div>
              </div>
            </>
          ) : null}
        </section>

        <section className={styles.whatsappCard}>
          <div className={styles.pulseHeader}>
            <h2 className={styles.sectionTitle}>WhatsApp-first (SIMULATED)</h2>
            <div className={styles.badge}>SIMULATED • No messages are sent</div>
          </div>
          <p className={styles.note}>
            This prototype shows message formats to demonstrate feasibility. There are no live integrations, credentials, or side effects.
          </p>

          <div className={styles.whatsappGrid}>
            <div className={styles.panel}>
              <h3 className={styles.panelTitle}>Sample inbound report (citizen → system)</h3>
              <div className={styles.message}>
                <div className={styles.messageMeta}>WhatsApp • Incoming</div>
                <pre className={styles.messageBody}>
{`Report: Traffic jam near Main Chowk
City: ${city}
Locality: Main Chowk
Location pin: (shared)
Notes: Heavy congestion, slow moving for ~20 minutes`}
                </pre>
              </div>
            </div>

            <div className={styles.panel}>
              <h3 className={styles.panelTitle}>Sample outgoing alert (system → citizens)</h3>
              <div className={styles.message}>
                <div className={styles.messageMeta}>WhatsApp • Outgoing (preview)</div>
                <pre className={styles.messageBody}>
{`⚠️ Traffic disruption near Main Chowk (${city}).
Avoid NH‑44 between 5–7 PM if possible.
Status: Under review (human governance)
Source: Citizen reports (advisory intelligence)`}
                </pre>
              </div>
              <div className={styles.disclaimer}>
                This is a calm advisory preview. No automated alerts are triggered by this UI.
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

