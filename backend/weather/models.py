from pydantic import BaseModel, Field


class Location(BaseModel):
    name: str
    country: str | None = None
    region: str | None = None
    latitude: float
    longitude: float


class CurrentWeather(BaseModel):
    time: str
    temperature: float
    feels_like: float
    humidity: float
    wind_speed: float
    weather_code: int
    condition: str
    icon: str
    wind_direction: float | None = None
    pressure: float | None = None
    cloud_cover: float | None = None


class ForecastHour(BaseModel):
    time: str
    temperature: float
    humidity: float
    precipitation_probability: float
    precipitation: float
    wind_speed: float
    weather_code: int
    condition: str
    icon: str
    wind_direction: float | None = None
    pressure: float | None = None
    cloud_cover: float | None = None


class WeatherResponse(BaseModel):
    location: Location
    current: CurrentWeather
    forecast: list[ForecastHour]


class DailyForecastDay(BaseModel):
    date: str
    max_temperature: float
    min_temperature: float
    precipitation_sum: float
    precipitation_probability_max: float
    wind_speed_max: float
    weather_code: int
    condition: str
    icon: str


class DailyForecastResponse(BaseModel):
    location: Location
    daily: list[DailyForecastDay]
