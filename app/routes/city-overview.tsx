import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Header } from "~/components/header";
import { fetchCityPulse, listPulseCities, type CityPulseResponse } from "~/lib/city-pulse";
import { fetchIssues } from "~/lib/api";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip } from "recharts";
import styles from "./city-overview.module.css";

const COLORS = ["#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6"];

type TrendPoint = { bucket: string; count: number };

export default function CityOverview() {
  const { t } = useTranslation();
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
            <h1 className={styles.title}>{t('cityPulse.overview')}</h1>
            <p className={styles.subtitle}>
              {t('cityPulse.calmSnapshot')}
            </p>
          </div>

          <div className={styles.controls}>
            <label className={styles.label}>
              {t('cityPulse.cityLabel')}
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
            <h2 className={styles.sectionTitle}>{t('cityPulse.pulseHeader')}</h2>
            {pulse && <div className={styles.meta}>{t('cityPulse.activeReports')}: {pulse.report_count}</div>}
          </div>

          {loading ? (
            <div className={styles.loading}>{t('cityPulse.loadingPulse')}</div>
          ) : error ? (
            <div className={styles.empty}>
              <div>{t('cityPulse.noPulseData')}</div>
              <p className={styles.note}>
                {t('cityPulse.pulseUpdates')}
              </p>
            </div>
          ) : pulse ? (
            <>
              <p className={styles.summary}>{pulse.summary}</p>

              <div className={styles.grid}>
                <div className={styles.panel}>
                  <h3 className={styles.panelTitle}>{t('cityPulse.issueCategories')}</h3>
                  {issueDist.length === 0 ? (
                    <div className={styles.empty}>{t('cityPulse.noActiveIssues')}</div>
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
                  <h3 className={styles.panelTitle}>{t('cityPulse.confidenceBreakdown')}</h3>
                  {confidenceDist.length === 0 ? (
                    <div className={styles.empty}>{t('cityPulse.noData')}</div>
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
                  <h3 className={styles.panelTitle}>{t('cityPulse.affectedLocalities')}</h3>
                  {pulse.affected_localities.length === 0 ? (
                    <div className={styles.empty}>{t('cityPulse.noLocalitiesReported')}</div>
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
                  <h3 className={styles.panelTitle}>{t('cityPulse.last12Hours')}</h3>
                  {trend.length === 0 ? (
                    <div className={styles.empty}>{t('cityPulse.noTrendData')}</div>
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
                  <p className={styles.note}>{t('cityPulse.observationalOnly')}</p>
                </div>
              </div>
            </>
          ) : null}
        </section>

        <section className={styles.whatsappCard}>
          <div className={styles.pulseHeader}>
            <h2 className={styles.sectionTitle}>{t('cityPulse.whatsappSimulated')}</h2>
            <div className={styles.badge}>{t('cityPulse.simulated')}</div>
          </div>
          <p className={styles.note}>
            {t('cityPulse.prototypeMsg')}
          </p>

          <div className={styles.whatsappGrid}>
            <div className={styles.panel}>
              <h3 className={styles.panelTitle}>{t('cityPulse.sampleInbound')}</h3>
              <div className={styles.message}>
                <div className={styles.messageMeta}>{t('cityPulse.whatsappIncoming')}</div>
                <pre className={styles.messageBody}>
{t('cityPulse.sampleInboundContent', { city })}
                </pre>
              </div>
            </div>

            <div className={styles.panel}>
              <h3 className={styles.panelTitle}>{t('cityPulse.sampleOutgoing')}</h3>
              <div className={styles.message}>
                <div className={styles.messageMeta}>{t('cityPulse.whatsappOutgoing')}</div>
                <pre className={styles.messageBody}>
{t('cityPulse.sampleOutgoingContent', { city })}
                </pre>
              </div>
              <div className={styles.disclaimer}>
                {t('cityPulse.disclaimer')}
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

