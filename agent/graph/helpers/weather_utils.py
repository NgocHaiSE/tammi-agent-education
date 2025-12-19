"""
Weather service utilities for fetching and processing weather data.

Provides:
- WeatherService: Main class for weather API calls
- Time of day calculation (morning, afternoon, evening, night)
- Season calculation (spring, summer, autumn, winter)
- Weather context building
"""

import logging
from typing import Optional, Dict, Any
import datetime

from agent.config.settings import get_settings
from agent.external_clients.http_client import APIGatewayHTTPClient

logger = logging.getLogger(__name__)


def get_time_of_day(hour: int) -> str:
    """
    Determine time of day from hour (0-23).
    
    Returns: "sáng" (morning), "trưa" (afternoon), "chiều" (evening), "tối" (night)
    """
    if 5 <= hour < 11:
        return "sáng"
    elif 11 <= hour < 14:
        return "trưa"
    elif 14 <= hour < 18:
        return "chiều"
    else:
        return "tối"


def get_season(month: int) -> str:
    """
    Determine season from month (1-12).
    
    Returns: "mùa xuân" (spring), "mùa hè" (summer), "mùa thu" (autumn), "mùa đông" (winter)
    """
    if month in [12, 1, 2]:
        return "mùa đông"
    elif month in [3, 4, 5]:
        return "mùa xuân"
    elif month in [6, 7, 8]:
        return "mùa hè"
    else:
        return "mùa thu"


class WeatherService:
    """Service for fetching and processing weather data."""
    
    def __init__(self):
        self.settings = get_settings()
    
    async def get_weather(
        self,
        location: str,
        units: str = "metric",
        lang: str = "vi"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch weather data from API Gateway.
        
        Args:
            location: Location name (e.g., "Hanoi")
            units: "metric" (°C) or "imperial" (°F)
            lang: Language code (e.g., "vi" for Vietnamese)
        
        Returns:
            Weather data dict or None if failed
        """
        try:
            api_client = APIGatewayHTTPClient(
                base_url=self.settings.API_GATEWAY_HTTP_URL,
                timeout=self.settings.EXTERNAL_CLIENT_TIMEOUT,
                max_retries=self.settings.EXTERNAL_CLIENT_MAX_RETRIES,
            )
            
            response = await api_client.get_current_weather(
                location=location,
                units=units,
                lang=lang
            )
            
            await api_client.close()
            
            if response and "data" in response:
                logger.info(f"Weather data fetched for {location}")
                return response["data"]
            else:
                logger.warning(f"No weather data in response for {location}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch weather for {location}: {e}", exc_info=True)
            return None
    
    async def build_weather_context_for_outfit(
        self,
        location: str
    ) -> Dict[str, Any]:
        """
        Build weather context specifically for outfit suggestion.
        
        Returns dict with keys:
        - weather_data: Full weather dict from API
        - context_str: Formatted weather context string
        - temp: Temperature
        - feels_like: Feels-like temperature
        - weather_desc: Weather description
        - humidity: Humidity percentage
        - wind_speed: Wind speed
        - uvi: UV index
        """
        weather_data = await self.get_weather(location)
        
        if not weather_data:
            logger.warning(f"No weather data available for {location}")
            return {
                "weather_data": None,
                "context_str": f"Không thể lấy thông tin thời tiết cho {location}.",
                "temp": None,
                "feels_like": None,
                "weather_desc": None,
                "humidity": None,
                "wind_speed": None,
                "uvi": None,
            }
        
        current = weather_data.get("current", {})
        location_info = weather_data.get("location", {})
        
        temp = current.get("temp", "N/A")
        feels_like = current.get("feels_like", "N/A")
        weather_desc = current.get("weather", {}).get("description", "N/A")
        humidity = current.get("humidity", "N/A")
        wind_speed = current.get("wind", {}).get("speed", "N/A")
        uvi = current.get("uvi", "N/A")
        
        current_time = datetime.datetime.fromtimestamp(current.get("dt", 0))
        time_of_day = get_time_of_day(current_time.hour)
        
        context_str = (
            f"Thời tiết hiện tại tại {location_info.get('name', location)}:\n"
            f"- Thời gian: {time_of_day} ({current_time.strftime('%H:%M')})\n"
            f"- Nhiệt độ: {temp}°C (cảm giác như {feels_like}°C)\n"
            f"- Thời tiết: {weather_desc}\n"
            f"- Độ ẩm: {humidity}%\n"
            f"- Gió: {wind_speed} m/s\n"
            f"- Chỉ số UV: {uvi}\n"
        )
        
        return {
            "weather_data": weather_data,
            "context_str": context_str,
            "temp": temp,
            "feels_like": feels_like,
            "weather_desc": weather_desc,
            "humidity": humidity,
            "wind_speed": wind_speed,
            "uvi": uvi,
        }
    
    async def build_weather_context_for_food(
        self,
        location: str
    ) -> Dict[str, Any]:
        """
        Build weather context specifically for food suggestion.
        
        Returns dict with:
        - weather_data: Full weather dict
        - context_str: Formatted context string
        - time_of_day: sáng/trưa/chiều/tối
        """
        weather_data = await self.get_weather(location)
        
        if not weather_data:
            now = datetime.datetime.now()
            time_of_day = get_time_of_day(now.hour)
            return {
                "weather_data": None,
                "context_str": (
                    f"Thông tin ngữ cảnh:\n"
                    f"- Vị trí: {location}\n"
                    f"- Thời gian: {time_of_day}\n"
                ),
                "time_of_day": time_of_day,
            }
        
        current = weather_data.get("current", {})
        location_info = weather_data.get("location", {})
        
        temp = current.get("temp", "N/A")
        weather_desc = current.get("weather", {}).get("description", "N/A")
        
        current_time = datetime.datetime.fromtimestamp(current.get("dt", 0))
        time_of_day = get_time_of_day(current_time.hour)
        
        context_str = (
            f"Thông tin ngữ cảnh:\n"
            f"- Vị trí: {location_info.get('name', location)}\n"
            f"- Thời gian: {time_of_day} ({current_time.strftime('%H:%M')})\n"
            f"- Thời tiết: {weather_desc}, {temp}°C\n"
        )
        
        return {
            "weather_data": weather_data,
            "context_str": context_str,
            "time_of_day": time_of_day,
        }
    
    async def build_weather_context_for_activity(
        self,
        location: str
    ) -> Dict[str, Any]:
        """
        Build weather context specifically for activity suggestion.
        
        Includes date, weekday, season information for activity planning.
        
        Returns dict with:
        - weather_data: Full weather dict
        - context_str: Formatted context string
        - current_date: YYYY-MM-DD format
        - season: mùa xuân/hè/thu/đông
        """
        weather_data = await self.get_weather(location)
        
        now = datetime.datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_weekday = now.strftime("%A")
        current_weekday_vi = {
            "Monday": "Thứ Hai",
            "Tuesday": "Thứ Ba",
            "Wednesday": "Thứ Tư",
            "Thursday": "Thứ Năm",
            "Friday": "Thứ Sáu",
            "Saturday": "Thứ Bảy",
            "Sunday": "Chủ Nhật"
        }.get(current_weekday, current_weekday)
        
        season = get_season(now.month)
        
        if not weather_data:
            context_str = (
                f"Thông tin ngữ cảnh:\n"
                f"- Ngày hiện tại: {current_weekday_vi}, {current_date}\n"
                f"- Mùa: {season}\n"
                f"- Vị trí: {location}\n"
            )
            return {
                "weather_data": None,
                "context_str": context_str,
                "current_date": current_date,
                "season": season,
            }
        
        current = weather_data.get("current", {})
        location_info = weather_data.get("location", {})
        
        temp = current.get("temp", "N/A")
        weather_desc = current.get("weather", {}).get("description", "N/A")
        
        context_str = (
            f"Thông tin ngữ cảnh:\n"
            f"- Ngày hiện tại: {current_weekday_vi}, {current_date}\n"
            f"- Mùa: {season}\n"
            f"- Vị trí: {location_info.get('name', location)}\n"
            f"- Thời tiết: {weather_desc}, {temp}°C\n"
        )
        
        return {
            "weather_data": weather_data,
            "context_str": context_str,
            "current_date": current_date,
            "season": season,
        }


# Singleton instance
_weather_service: Optional[WeatherService] = None


def get_weather_service() -> WeatherService:
    """Get or create weather service singleton."""
    global _weather_service
    if _weather_service is None:
        _weather_service = WeatherService()
    return _weather_service
