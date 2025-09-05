**Backend**
  - FastAPI REST API + WebSocket broadcast (`/ws`)
  - RSS/News ingestion & scoring
  - Relevance filtering: only private-company deal activity
  - Preference-aware scoring (keywords, firms, sectors, geos)
  
**Frontend**
  - React interface
  - Filter form with **Apply Preferences** button (spinner/disable feedback on click)
  - Live feed display
  - Simple search input (keywords are matched directly on item title + summary)
  - Type Dropdown: filter to only the messages tagged with the chosen tag
