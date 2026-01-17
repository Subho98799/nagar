/**
 * Timeline API functions.
 */

import { API_BASE_URL } from "./config";
import { getAuthToken, getCurrentUser } from "./auth";

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
  confidence_score: number;
  priority_score?: number;
  upvote_count: number;
  downvote_count: number;
  comment_count: number;
  report_count: number;
  user_vote?: "UPVOTE" | "DOWNVOTE";
  is_bookmarked: boolean;
  sources: Array<{ type: string; count: number; description: string }>;
  media_urls: string[];
}

export interface IssueAnalytics {
  issue_id: string;
  popularity_score: number;
  confidence_score: number;
  priority_score?: number;
  source_breakdown: Record<string, number>;
  reports_over_time: Array<{ date: string; count: number }>;
  confidence_over_time: Array<{ date: string; confidence: number }>;
  votes_over_time: Array<{ date: string; upvotes: number; downvotes: number }>;
  issue_type_distribution: Record<string, number>;
  severity_distribution: Record<string, number>;
  status_distribution: Record<string, number>;
  location_heatmap: Array<{ lat: number; lng: number; intensity: number }>;
  ai_metadata?: Record<string, any>;
  comments: Comment[];
  total_upvotes: number;
  total_downvotes: number;
  total_comments: number;
  total_reports: number;
}

export interface Comment {
  id: string;
  issue_id: string;
  user_id?: string;
  user_phone?: string;
  text: string;
  parent_comment_id?: string;
  created_at: string;
  upvote_count: number;
  downvote_count: number;
  user_vote?: "UPVOTE" | "DOWNVOTE";
}

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const user = getCurrentUser();
  
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  
  if (user?.id) {
    headers["X-User-ID"] = user.id;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `API error ${response.status}`);
  }
  
  return response.json();
}

export async function fetchTimelineFeed(city?: string, limit = 50): Promise<TimelineIssue[]> {
  const params = new URLSearchParams();
  if (city) params.append("city", city);
  params.append("limit", limit.toString());
  
  const url = `${API_BASE_URL}/timeline/feed?${params.toString()}`;
  return fetchWithAuth(url);
}

export async function fetchIssueAnalytics(issueId: string): Promise<IssueAnalytics> {
  const url = `${API_BASE_URL}/timeline/issue/${issueId}/analytics`;
  return fetchWithAuth(url);
}

export async function voteOnIssue(issueId: string, voteType: "UPVOTE" | "DOWNVOTE"): Promise<{
  success: boolean;
  action: string;
  upvote_count: number;
  downvote_count: number;
  popularity_score: number;
  user_vote?: string;
}> {
  const url = `${API_BASE_URL}/timeline/issue/${issueId}/vote?vote_type=${voteType}`;
  return fetchWithAuth(url, { method: "POST" });
}

export async function addComment(issueId: string, text: string, parentCommentId?: string): Promise<Comment> {
  const url = `${API_BASE_URL}/timeline/comment`;
  return fetchWithAuth(url, {
    method: "POST",
    body: JSON.stringify({
      issue_id: issueId,
      text,
      parent_comment_id: parentCommentId,
    }),
  });
}

export async function fetchIssueComments(issueId: string): Promise<Comment[]> {
  const url = `${API_BASE_URL}/timeline/issue/${issueId}/comments`;
  return fetchWithAuth(url);
}
