# Timeline Feature Implementation

## Overview

Complete Facebook-like timeline feature for civic issues with analytics, interactions, and detailed side panel.

## Features Implemented

### 1. Timeline Feed
- Facebook-like feed showing all issues
- Displays popularity, confidence, and priority scores
- Shows upvote/downvote counts
- Shows comment counts
- Source information (citizens, website scraper)
- Real-time updates

### 2. Issue Post Component
- Clickable posts that open analytics panel
- Upvote/downvote buttons with real-time updates
- Popularity score display
- Confidence score with color coding
- Priority score display
- Comment count
- Source information
- Location display

### 3. Analytics Side Panel
- Comprehensive analytics dashboard
- **Pie Charts**: Source breakdown
- **Bar Charts**: Reports over time
- **Line Charts**: Votes over time, confidence over time
- **Heatmap**: Location-based intensity map
- **Scores Display**: Popularity, confidence, priority
- **AI Metadata**: Category, severity, keywords, summary
- **Comments Section**: Add/view comments with upvote/downvote

### 4. User Interactions
- Upvote/downvote issues
- Add comments
- View analytics
- Real-time vote counts
- User-specific vote tracking

## Backend Implementation

### Files Created

1. **`app/models/timeline.py`**
   - `TimelineIssue` - Issue model for timeline feed
   - `IssueAnalytics` - Comprehensive analytics model
   - `CommentCreate`, `CommentResponse` - Comment models
   - `VoteRequest`, `VoteType` - Vote models
   - `SourceType` - Source enumeration

2. **`app/services/timeline_service.py`**
   - `get_timeline_feed()` - Get timeline feed
   - `get_issue_analytics()` - Get comprehensive analytics
   - `vote_on_issue()` - Handle votes
   - `add_comment()` - Add comments
   - Helper methods for data aggregation

3. **`app/routes/timeline.py`**
   - `GET /timeline/feed` - Get timeline feed
   - `GET /timeline/issue/{issue_id}/analytics` - Get analytics
   - `POST /timeline/issue/{issue_id}/vote` - Vote on issue
   - `POST /timeline/comment` - Add comment
   - `GET /timeline/issue/{issue_id}/comments` - Get comments

### Firestore Collections

1. **`votes`** - User votes on issues
   - `issue_id`, `user_id`, `vote_type`, `created_at`

2. **`comments`** - Comments on issues
   - `issue_id`, `user_id`, `text`, `parent_comment_id`, `created_at`

3. **`comment_votes`** - Votes on comments (for future use)
   - `comment_id`, `user_id`, `vote_type`

## Frontend Implementation

### Files Created

1. **`app/lib/timeline.ts`**
   - API functions for timeline operations
   - TypeScript interfaces
   - Authentication integration

2. **`app/routes/timeline.tsx`**
   - Main timeline page
   - Feed display
   - Analytics panel integration

3. **`app/routes/timeline.module.css`**
   - Timeline page styles

4. **`app/components/timeline-post.tsx`**
   - Individual post component
   - Vote buttons
   - Score displays
   - Click handler

5. **`app/components/timeline-post.module.css`**
   - Post component styles

6. **`app/components/issue-analytics-panel.tsx`**
   - Side panel component
   - Charts integration (Recharts)
   - Map integration (React Leaflet)
   - Comments section

7. **`app/components/issue-analytics-panel.module.css`**
   - Panel styles

8. **`app/components/location-heatmap-map.tsx`**
   - Map component for heatmap
   - Circle markers for intensity

## API Endpoints

### GET /timeline/feed
Get timeline feed of issues.

**Query Parameters:**
- `city` (optional): Filter by city
- `limit` (default: 50): Maximum number of issues

**Headers:**
- `X-User-ID` (optional): User ID for personalized data

**Response:**
```json
[
  {
    "id": "issue_123",
    "title": "Water leakage",
    "description": "...",
    "popularity_score": 15,
    "confidence_score": 0.85,
    "priority_score": 75,
    "upvote_count": 20,
    "downvote_count": 5,
    "comment_count": 8,
    "user_vote": "UPVOTE",
    "sources": [...]
  }
]
```

### GET /timeline/issue/{issue_id}/analytics
Get comprehensive analytics for an issue.

**Response:**
```json
{
  "issue_id": "issue_123",
  "popularity_score": 15,
  "confidence_score": 0.85,
  "priority_score": 75,
  "source_breakdown": {"CITIZEN": 5, "WEBSITE_SCRAPER": 2},
  "reports_over_time": [...],
  "votes_over_time": [...],
  "location_heatmap": [...],
  "comments": [...]
}
```

### POST /timeline/issue/{issue_id}/vote
Vote on an issue.

**Headers:**
- `X-User-ID`: User ID (required)

**Query Parameters:**
- `vote_type`: "UPVOTE" or "DOWNVOTE"

**Response:**
```json
{
  "success": true,
  "action": "created",
  "upvote_count": 21,
  "downvote_count": 5,
  "popularity_score": 16,
  "user_vote": "UPVOTE"
}
```

### POST /timeline/comment
Add a comment to an issue.

**Headers:**
- `X-User-ID`: User ID (required)

**Body:**
```json
{
  "issue_id": "issue_123",
  "text": "This is a comment",
  "parent_comment_id": null
}
```

## Charts and Visualizations

### Pie Chart
- Source breakdown (CITIZEN, WEBSITE_SCRAPER, etc.)

### Bar Chart
- Reports over time

### Line Charts
- Votes over time (upvotes/downvotes)
- Confidence over time

### Heatmap
- Location-based intensity map
- Circle markers with size based on intensity

## User Experience

1. **Timeline View**
   - Scrollable feed of issues
   - Each post shows key metrics
   - Click post to open analytics

2. **Analytics Panel**
   - Slides in from right
   - Comprehensive data visualization
   - Interactive charts
   - Comments section

3. **Interactions**
   - One-click voting
   - Real-time updates
   - Comment threading support

## Integration Points

### Authentication
- Timeline requires authentication
- User-specific vote tracking
- Personalized feed

### Reports Integration
- Timeline pulls from reports collection
- Uses existing report data
- Extends with interaction data

### AI Integration
- Displays AI confidence scores
- Shows AI metadata in analytics
- Uses AI classifications

## Future Enhancements

1. **Real-time Updates**
   - WebSocket integration
   - Live vote/comment updates

2. **Advanced Filtering**
   - Filter by issue type
   - Filter by location
   - Sort by popularity/date

3. **Notifications**
   - Notify on new comments
   - Notify on vote changes

4. **Social Features**
   - Share issues
   - Follow issues
   - Bookmark issues

5. **Advanced Analytics**
   - Trend predictions
   - Comparative analysis
   - Export data

## Testing

### Manual Testing Steps

1. Navigate to `/timeline`
2. Verify feed loads with issues
3. Click on a post
4. Verify analytics panel opens
5. Test upvote/downvote
6. Add a comment
7. Verify charts render
8. Verify map displays

## Conclusion

✅ Timeline feed implemented
✅ Analytics panel with charts
✅ Upvote/downvote functionality
✅ Comments system
✅ Source tracking
✅ AI scores display
✅ Location heatmap
✅ Real-time updates

The timeline feature is fully functional and ready for use!
