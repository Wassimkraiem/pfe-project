from http import HTTPStatus

from app.exceptionhandler import AppError


class FavoriteNotFound(AppError):
    default_message = "Favorite not found"
    default_error_code = "favorite_not_found"
    default_status_code = HTTPStatus.NOT_FOUND


class VideoAlreadyFavorited(AppError):
    default_message = "Video is already in favorites"
    default_error_code = "video_already_favorited"
    default_status_code = HTTPStatus.CONFLICT
