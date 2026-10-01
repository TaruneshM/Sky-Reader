from pydantic import BaseModel


class Location(BaseModel):
    name: str
    country: str | None
    region: str | None
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


class WeatherResponse(BaseModel):
    location: Location
    current: CurrentWeather
    forecast: list[ForecastHour]