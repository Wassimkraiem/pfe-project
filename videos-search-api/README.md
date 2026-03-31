# BVIRAL Project

## Overview

BVIRAL is a video management platform with a RESTful API for creating, retrieving, searching, and deleting video documents. It provides a Python SDK for easy integration, so your team can use its features without deep knowledge of the API internals.

---

## Running the Project Locally

### Prerequisites

- Docker & Docker Compose installed
- Python 3.8+ (for SDK usage)

### Start the App

1. Clone the repository:
   ```bash
   git clone <your-repo-url>
   cd BVIRAL
   ```
2. Copy and configure your `.env` file as needed.
3. Start the services:
   ```bash
   docker compose -f docker-compose.local.yml up
   ```
4. The API will be available at `http://http://localhost:5000` by default.

---

## API Usage

### Endpoints

- `POST   /api/videos/` — Create or update a video
- `DELETE /api/videos/` — Delete a video (by JSON body)
- `POST   /api/videos/query` — Search videos (by JSON body)
- `GET    /api/videos/query` — Get all videos

### Example: Create a Video (with curl)

```bash
curl -X POST http://http://localhost:5000/api/videos/ \
     -H 'Content-Type: application/json' \
     -d '{
           "video_id": "test123",
           "service_identifier": "rms",
           "video_data": {"title": "Test Video", "views": 42}
         }'
```

## Python SDK Usage

### Installation

Copy `bviral_sdk.py` into your project or package it as a module.

### Example Usage

```python
from bviral_sdk import BviralSDK

sdk = BviralSDK("http://http://localhost:5000",API_KEY="key1")

# Create a video
data = {
    "video_id": "test123",
    "service_identifier": "rms",
    "video_data": {"title": "Test Video", "views": 42}
}
print(sdk.create_video(data))

# Get a video by ID
print(sdk.get_video("test123"))

# Search for videos
print(sdk.search_videos({"title": "Test Video"}))

# Delete a video
print(sdk.delete_video("test123"))
```

---

## Contributing

Feel free to open issues or submit pull requests for improvements!

---

## License

MIT (or your chosen license)
