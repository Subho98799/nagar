export type IssueType = "Traffic" | "Power" | "Water" | "Roadblock" | "Safety" | "Other";
export type Severity = "Low" | "Medium" | "High";
export type Confidence = "Low" | "Medium" | "High";
export type Status = "Under Review" | "Active" | "Resolved";

export interface TimelineEvent {
  id: string;
  timestamp: string;
  time: string;
  confidence: Confidence;
  description: string;
}

export interface Issue {
  id: string;
  type: IssueType;
  title: string;
  location: string;
  description: string;
  severity: Severity;
  confidence: Confidence;
  status: Status;
  timestamp: string;
  reportCount: number;
  timeline: TimelineEvent[];
  operatorNotes?: string;
}

export const mockIssues: Issue[] = [
  {
    id: "1",
    type: "Traffic",
    title: "Heavy congestion near Main Chowk",
    location: "Main Chowk, Station Road",
    description: "Multiple citizens reporting slow-moving traffic. Possible accident or roadwork.",
    severity: "Medium",
    confidence: "High",
    status: "Active",
    timestamp: "2024-01-15T10:15:00",
    reportCount: 12,
    timeline: [
      {
        id: "t1",
        timestamp: "2024-01-15T10:15:00",
        time: "10:15 AM",
        confidence: "Low",
        description: "First reports received from 2 citizens",
      },
      {
        id: "t2",
        timestamp: "2024-01-15T10:45:00",
        time: "10:45 AM",
        confidence: "Medium",
        description: "Multiple nearby reports (8 total) from different locations",
      },
      {
        id: "t3",
        timestamp: "2024-01-15T11:30:00",
        time: "11:30 AM",
        confidence: "High",
        description: "Pattern confirmed across 12 reports. Situation stabilizing",
      },
    ],
    operatorNotes: "Verified with local traffic police. Roadwork in progress.",
  },
  {
    id: "2",
    type: "Power",
    title: "Power outage in Sector 7",
    location: "Sector 7, Residential Area",
    description: "Residents reporting power cut since morning. Affecting approximately 200 households.",
    severity: "High",
    confidence: "Medium",
    status: "Active",
    timestamp: "2024-01-15T09:30:00",
    reportCount: 18,
    timeline: [
      {
        id: "t4",
        timestamp: "2024-01-15T09:30:00",
        time: "09:30 AM",
        confidence: "Low",
        description: "Initial reports from 3 households",
      },
      {
        id: "t5",
        timestamp: "2024-01-15T10:00:00",
        time: "10:00 AM",
        confidence: "Medium",
        description: "Reports increasing (18 total). Area-wide pattern emerging",
      },
      {
        id: "t6",
        timestamp: "2024-01-15T12:00:00",
        time: "12:00 PM",
        confidence: "Medium",
        description: "No new signals. Situation ongoing",
      },
    ],
  },
  {
    id: "3",
    type: "Water",
    title: "Low water pressure in Gandhi Nagar",
    location: "Gandhi Nagar, Zone B",
    description: "Citizens reporting reduced water supply during morning hours.",
    severity: "Low",
    confidence: "Medium",
    status: "Active",
    timestamp: "2024-01-15T08:00:00",
    reportCount: 6,
    timeline: [
      {
        id: "t7",
        timestamp: "2024-01-15T08:00:00",
        time: "08:00 AM",
        confidence: "Low",
        description: "First reports (4 citizens) about low pressure",
      },
      {
        id: "t8",
        timestamp: "2024-01-15T09:15:00",
        time: "09:15 AM",
        confidence: "Medium",
        description: "Additional reports confirm localized issue",
      },
    ],
  },
  {
    id: "4",
    type: "Roadblock",
    title: "Road closure at Railway Crossing",
    location: "Railway Crossing, NH-44",
    description: "Temporary closure due to maintenance work. Alternate routes available.",
    severity: "Medium",
    confidence: "High",
    status: "Resolved",
    timestamp: "2024-01-14T14:00:00",
    reportCount: 8,
    timeline: [
      {
        id: "t9",
        timestamp: "2024-01-14T14:00:00",
        time: "02:00 PM",
        confidence: "Medium",
        description: "Reports of road closure",
      },
      {
        id: "t10",
        timestamp: "2024-01-14T15:30:00",
        time: "03:30 PM",
        confidence: "High",
        description: "Confirmed by multiple sources",
      },
      {
        id: "t11",
        timestamp: "2024-01-14T18:00:00",
        time: "06:00 PM",
        confidence: "High",
        description: "Reports indicate road reopened. Likely resolved",
      },
    ],
  },
  {
    id: "5",
    type: "Safety",
    title: "Street light outage on Park Street",
    location: "Park Street, near City Park",
    description: "Multiple street lights not functioning. Reduced visibility after dark.",
    severity: "Low",
    confidence: "Low",
    status: "Under Review",
    timestamp: "2024-01-15T07:45:00",
    reportCount: 3,
    timeline: [
      {
        id: "t12",
        timestamp: "2024-01-15T07:45:00",
        time: "07:45 AM",
        confidence: "Low",
        description: "Initial reports from 3 citizens. Awaiting verification",
      },
    ],
  },
  {
    id: "6",
    type: "Other",
    title: "Noise complaint in Market Area",
    location: "Central Market, Shopping District",
    description: "Citizens reporting excessive noise from ongoing construction work during evening hours.",
    severity: "Low",
    confidence: "Medium",
    status: "Active",
    timestamp: "2024-01-15T11:20:00",
    reportCount: 5,
    timeline: [
      {
        id: "t13",
        timestamp: "2024-01-15T11:20:00",
        time: "11:20 AM",
        confidence: "Low",
        description: "Initial reports from nearby residents",
      },
      {
        id: "t14",
        timestamp: "2024-01-15T12:00:00",
        time: "12:00 PM",
        confidence: "Medium",
        description: "Multiple reports (5 total) from same area confirm pattern",
      },
    ],
  },
];

export function getCityPulse(issues: Issue[]): { status: "Calm" | "Moderate" | "Disrupted"; activeCount: number } {
  const activeIssues = issues.filter((i) => i.status === "Active");
  const highSeverityCount = activeIssues.filter((i) => i.severity === "High").length;
  const mediumSeverityCount = activeIssues.filter((i) => i.severity === "Medium").length;

  if (highSeverityCount >= 2 || activeIssues.length >= 5) {
    return { status: "Disrupted", activeCount: activeIssues.length };
  } else if (highSeverityCount >= 1 || mediumSeverityCount >= 2) {
    return { status: "Moderate", activeCount: activeIssues.length };
  } else {
    return { status: "Calm", activeCount: activeIssues.length };
  }
}
