/**
 * Timeline API functions for frontend.
 */

import { API_BASE_URL } from "./config";

export interface TimelineIssue {
  id: string;
  title: string;
  description: string;
  issue_type: string;
  severity: string;
  confidence: string;
  status: string;
  city?: string;
  locality?: string;
  latitude?: number;
  longitude?: number;
  created_at: string;
  updated_at: string;
  popularity_score: number;
  priority_score?: number;
  confidence_score: string;
  upvotes: number;
  downvotes: number;
  comment_count: number;
  report_count: number;
  media_urls: string[];
  user_vote?: "upvote" | "downvote" | null;
}

export interface IssueAnalytics {
  issue_id: string;
  popularity_score: number;
  confidence_score: string;
  priority_score?: number;
  escalation_flag: boolean;
  issue_type_distribution: Record<string, number>;
  confidence_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  time_series_data: Array<{ date: string; count: number }>;
  location_heatmap: Array<{ latitude: number; longitude: number; intensity: number }>;
  sources: Array<{ source_type: string; count: number; last_updated?: string }>;
  upvotes: number;
  downvotes: number;
  vote_ratio: number;
  comment_count: number;
}

export interface VoteResponse {
  issue_id: string;
  upvotes: number;
  downvotes: number;
  user_vote?: "upvote" | "downvote" | null;
}

export interface Comment {
  id: string;
  issue_id: string;
  text: string;
  user_id?: string;
  user_phone?: string;
  created_at: string;
  likes: number;
}

async function fetchJSON(url: string, options?: RequestInit) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    if (!res.ok) throw new Error(`API error ${res.status}`);
    return res.json();
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Get timeline feed of issues.
 */
export async function getTimelineFeed(city?: string, limit = 50): Promise<TimelineIssue[]> {
  const params = new URLSearchParams();
  if (city) params.append("city", city);
  params.append("limit", limit.toString());
  
  const url = `${API_BASE_URL}/timeline/feed?${params.toString()}`;
  return fetchJSON(url) as Promise<TimelineIssue[]>;
}

/**
 * Get analytics for a specific issue.
 */
export async function getIssueAnalytics(issueId: string): Promise<IssueAnalytics> {
  const url = `${API_BASE_URL}/timeline/issue/${issueId}/analytics`;
  return fetchJSON(url) as Promise<IssueAnalytics>;
}

/**
 * Vote on an issue.
 */
export async function voteOnIssue(
  issueId: string,
  voteType: "upvote" | "downvote",
  userId?: string
): Promise<VoteResponse> {
  const params = new URLSearchParams();
  if (userId) params.append("user_id", userId);
  
  const url = `${API_BASE_URL}/timeline/vote?${params.toString()}`;
  return fetchJSON(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ issue_id: issueId, vote_type: voteType }),
  }) as Promise<VoteResponse>;
}

/**
 * Get votes for an issue.
 */
export async function getIssueVotes(issueId: string, userId?: string): Promise<VoteResponse> {
  const params = new URLSearchParams();
  if (userId) params.append("user_id", userId);
  
  const url = `${API_BASE_URL}/timeline/issue/${issueId}/votes?${params.toString()}`;
  return fetchJSON(url) as Promise<VoteResponse>;
}

/**
 * Add a comment to an issue.
 */
export async function addComment(
  issueId: string,
  text: string,
  userId?: string
): Promise<Comment> {
  const url = `${API_BASE_URL}/timeline/comment`;
  return fetchJSON(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ issue_id: issueId, text, user_id: userId }),
  }) as Promise<Comment>;
}

/**
 * Get comments for an issue.
 */
export async function getIssueComments(issueId: string): Promise<Comment[]> {
  const url = `${API_BASE_URL}/timeline/issue/${issueId}/comments`;
  return fetchJSON(url) as Promise<Comment[]>;
}
