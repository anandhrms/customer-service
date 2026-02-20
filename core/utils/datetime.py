from datetime import datetime, timezone

import pytz


def utcnow() -> datetime:
    """
    Returns the current time in UTC but with tzinfo set, as opposed
    to datetime.utcnow which does not.
    """
    return datetime.now(timezone.utc)


def convert_from_utc(datetime_obj, timezone=None):
    if isinstance(datetime_obj, str):
        datetime_obj = datetime.fromisoformat(datetime_obj)

    local_timezone = datetime_obj.astimezone(pytz.timezone(timezone))
    return local_timezone.strftime("%Y-%m-%d %H:%M:%S")


def get_duration_from_current_time(incident_time: datetime, timezone: str):
    timezone_info = pytz.timezone(timezone)

    current_time = datetime.now(timezone_info)
    incident_time_with_timezone = timezone_info.localize(incident_time)

    time_difference = current_time - incident_time_with_timezone

    total_seconds = int(time_difference.total_seconds())

    if total_seconds < 60:
        return "Just now"

    elif total_seconds < 120:
        return "a minute ago"

    elif total_seconds < 3600:
        return f"{total_seconds // 60} minutes ago"

    elif total_seconds < 7200:
        return "an hour ago"

    elif total_seconds < 86400:
        return f"{total_seconds // 3600} hours ago"

    elif time_difference.days < 2:
        return "a day ago"

    elif time_difference.days < 30:
        return f"{time_difference.days} days ago"

    elif time_difference.days < 60:
        return "a month ago"

    elif time_difference.days < 365:
        return f"{time_difference.days // 30} months ago"

    elif time_difference.days < 730:
        return "a year ago"

    return f"{time_difference.days // 365} years ago"
