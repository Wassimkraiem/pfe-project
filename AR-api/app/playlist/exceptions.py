from http import HTTPStatus

from app.exceptionhandler import AppError


class PlaylistNotFound(AppError):
    default_message = "Playlist not found"
    default_error_code = "playlist_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class PlaylistForbidden(AppError):
    default_message = "You do not have access to this playlist"
    default_error_code = "playlist_forbidden"
    default_status_code = HTTPStatus.FORBIDDEN


class VideoAlreadyInPlaylist(AppError):
    default_message = "Video is already in this playlist"
    default_error_code = "video_already_in_playlist"
    default_status_code = HTTPStatus.CONFLICT
