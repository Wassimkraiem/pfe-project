from videosearch_sdk import VideoSearchSDK
import csv
import json
from datetime import datetime


def test_sdk():
    # Initialize the SDK
    sdk = VideoSearchSDK("http://18.206.197.145/", api_key="key1")

    # Recursive function to remove problematic fields
    def remove_problematic_fields(d):
        keys_to_remove = []
        for k, v in d.items():
            if isinstance(v, dict):
                remove_problematic_fields(v)
            else:
                # Remove Minor_Version and other fields that will cause mapping errors
                if k.lower() in ("minor_version", "major_version"):
                    keys_to_remove.append(k)
                # Optionally, skip invalid dates
                elif k.lower() in ("creation_time", "modified_time"):
                    try:
                        # keep only ISO or standard format; else remove
                        if "T" not in str(v) and len(str(v)) != 19:  # crude check
                            keys_to_remove.append(k)
                    except Exception:
                        keys_to_remove.append(k)
        for k in keys_to_remove:
            d.pop(k)
        return d

    # Read CSV and push videos
    with open("videos.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            video_info = json.loads(row["video_info"])
            video_info_without_id = {k: v for k, v in video_info.items() if k != "id"}

            # Remove problematic fields
            video_info_without_id = remove_problematic_fields(video_info_without_id)

            video_data = {
                "video_id": video_info["id"],
                "service_identifier": "rms",
                "video_data": video_info_without_id,
            }

            print("Create Video:", sdk.create_video(video_data))

    # 2. Get the video by ID
    # print("Get Video:", sdk.get_video("test123"))

    # # 3. Search for videos (by title, for example)
    # print("Search Videos:", sdk.search_videos({"title": "Test Video"}))

    # 4. Delete the video
    # print("Delete Video:", sdk.delete_video("test123"))


def push_prod_sdk():
    sdk = VideoSearchSDK("http://18.206.197.145/", api_key="key1")
    # Data to push
    video_data = {
        "video_id": "prod_test_001",
        "service_identifier": "rms",
        "video_data": {
            "title": "Production Test Video",
            "views": 100,
            "status": "active",
        },
    }

    # Push data
    response = sdk.create_video(video_data)
    print("Create response:", response)


test_sdk()
# push_prod_sdk()
