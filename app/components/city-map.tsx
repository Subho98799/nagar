import { useEffect, useRef, useState } from "react";
import type { Issue } from "~/data/mock-issues";
import styles from "./city-map.module.css";
import "leaflet/dist/leaflet.css";

// Mock coordinates for the city center (you can change this to your actual city)
const CITY_CENTER: [number, number] = [28.6139, 77.209]; // Delhi as example

// Generate mock coordinates for each issue based on location name
function getIssueCoordinates(issue: Issue): [number, number] {
  const baseCoords = { lat: CITY_CENTER[0], lng: CITY_CENTER[1] };
  
  // Simple hash function to generate consistent coordinates for each location
  const hash = issue.location.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  
  // Spread issues around the city center (within ~5km radius)
  const offsetLat = ((hash % 100) - 50) * 0.02; // ~2km range
  const offsetLng = ((hash % 73) - 36) * 0.02;
  
  return [baseCoords.lat + offsetLat, baseCoords.lng + offsetLng];
}

// Custom pulsing marker icon
// createPulsingIcon will be created at runtime after Leaflet loads (client-only)

interface CityMapProps {
  issues: Issue[];
  className?: string;
}

// Component to fit bounds to all markers
export function CityMap({ issues, className }: CityMapProps) {
  const mapRef = useRef<any>(null);
  const [leafletReady, setLeafletReady] = useState(false);
  const [Leaflet, setLeaflet] = useState<any>(null);
  const [RL, setRL] = useState<any>(null);

  // Filter active issues only
  const activeIssues = issues.filter((issue) => issue.status === "Active");

  // Client-only import of leaflet + react-leaflet to avoid SSR window errors
  useEffect(() => {
    let mounted = true;
    if (typeof window === "undefined") return;
    Promise.all([import("leaflet"), import("react-leaflet")])
      .then(([leafletModule, reactLeafletModule]) => {
        if (!mounted) return;
        const L = (leafletModule as any).default || leafletModule;
        setLeaflet(L);
        setRL(reactLeafletModule);
        setLeafletReady(true);
      })
      .catch(() => {
        // failed to load leaflet in this environment; keep map hidden
      });
    return () => {
      mounted = false;
    };
  }, []);

  // Render nothing until Leaflet is loaded in browser
  if (!leafletReady || !Leaflet || !RL) {
    return <div className={`${styles.mapWrapper} ${className || ""}`} />;
  }

  // Create pulsing icon using loaded Leaflet
  function createPulsingIcon(severity: Issue["severity"]) {
    return Leaflet.divIcon({
      className: styles.pulsingMarker,
      html: `
        <div class="${styles.markerContainer}" data-severity="${severity.toLowerCase()}">
          <div class="${styles.pulse}"></div>
          <div class="${styles.markerDot}"></div>
        </div>
      `,
      iconSize: [30, 30],
      iconAnchor: [15, 15],
    });
  }

  const { MapContainer, TileLayer, Marker, Popup, useMap } = RL as any;

  // MapBounds must use the dynamically loaded useMap hook
  function MapBoundsInner({ issues }: { issues: Issue[] }) {
    const map = useMap();

    useEffect(() => {
      if (issues.length > 0) {
        const bounds = issues.map((issue) => getIssueCoordinates(issue));
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 13 });
      }
    }, [issues, map]);

    return null;
  }

  return (
    <div className={`${styles.mapWrapper} ${className || ""}`}>
      <MapContainer
        center={CITY_CENTER}
        zoom={12}
        className={styles.map}
        ref={mapRef}
        zoomControl={true}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        <MapBoundsInner issues={activeIssues} />

        {activeIssues.map((issue) => {
          const coords = getIssueCoordinates(issue);
          return (
            <Marker key={issue.id} position={coords} icon={createPulsingIcon(issue.severity)}>
              <Popup className={styles.popup}>
                <div className={styles.popupContent}>
                  <div className={styles.popupHeader}>
                    <span className={`${styles.badge} ${styles[`severity${issue.severity}`]}`}>
                      {issue.severity}
                    </span>
                    <span className={styles.type}>{issue.type}</span>
                  </div>
                  <h3 className={styles.title}>{issue.title}</h3>
                  <p className={styles.location}>{issue.location}</p>
                  <p className={styles.description}>{issue.description}</p>
                  <div className={styles.meta}>
                    <span>{issue.reportCount} reports</span>
                    <span>Confidence: {issue.confidence}</span>
                  </div>
                  <a href={`/issue/${issue.id}`} className={styles.viewLink}>
                    View Details →
                  </a>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
