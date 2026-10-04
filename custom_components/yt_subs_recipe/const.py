"""Constants for YT Subs → Recipe."""

DOMAIN = "yt_subs_recipe"

CONF_API_KEY = "api_key"
CONF_MODELS = "models"
CONF_PROXY = "proxy"

DEFAULT_MODELS = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash"

SERVICE_DOWNLOAD_SUBS = "download_subs"
SERVICE_GENERATE_RECIPE = "generate_recipe"
SERVICE_DOWNLOAD_AND_GENERATE = "download_and_generate"

ATTR_URL = "url"
ATTR_JOB_ID = "job_id"
ATTR_TEXT = "text"

STORAGE_KEY = f"{DOMAIN}_jobs"
STORAGE_VERSION = 1