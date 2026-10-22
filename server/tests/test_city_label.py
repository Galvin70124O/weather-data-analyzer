from app.models import City


def label(name: str, state: str | None, country: str) -> str:
    return City(name=name, state=state, country=country, lat=0, lon=0).label


def test_label_names_the_state_only_when_it_adds_something():
    assert label("London", "England", "GB") == "London, England, GB"
    assert label("Tokyo", None, "JP") == "Tokyo, JP"
    assert label("Cairo", "Cairo", "EG") == "Cairo, EG"
    assert label("New York", "new york", "US") == "New York, US"
