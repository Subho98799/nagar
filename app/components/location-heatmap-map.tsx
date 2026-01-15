import { useEffect, useState } from "react";

interface LocationHeatmapMapProps {
  points: Array<{ lat: number; lng: number; intensity: number }>;
}

export function LocationHeatmapMap({ points }: LocationHeatmapMapProps) {
  const [isClient, setIsClient] = useState(false);
  const [MapComponents, setMapComponents] = useState<any>(null);

  useEffect(() => {
    // Only load on client side
    setIsClient(true);
    import("react-leaflet").then((leaflet) => {
      setMapComponents({
        MapContainer: leaflet.MapContainer,
        TileLayer: leaflet.TileLayer,
        CircleMarker: leaflet.CircleMarker,
        Popup: leaflet.Popup,
      });
      // Import Leaflet CSS
      import("leaflet/dist/leaflet.css");
    });
  }, []);

  if (!isClient || !MapComponents || points.length === 0) {
    return <div style={{ height: "300px", display: "flex", alignItems: "center", justifyContent: "center" }}>Loading map...</div>;
  }

  const { MapContainer, TileLayer, CircleMarker, Popup } = MapComponents;

  return (
    <MapContainer
      center={[points[0].lat, points[0].lng]}
      zoom={13}
      style={{ height: "300px", width: "100%" }}
    >
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {points.map((point, index) => (
        <CircleMarker
          key={index}
          center={[point.lat, point.lng]}
          radius={Math.sqrt(point.intensity) * 3}
          fillColor="#FF8042"
          fillOpacity={0.6}
          stroke={false}
        >
          <Popup>
            Intensity: {point.intensity}
          </Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
