"""Enable the custom integration when the Home Assistant test harness is installed."""

import pytest

try:
    import pytest_homeassistant_custom_component  # noqa: F401
except ImportError:  # plain protocol tests run without Home Assistant
    pass
else:

    @pytest.fixture(autouse=True)
    def _enable_custom_integrations(request):
        if "hass" in request.fixturenames:
            request.getfixturevalue("enable_custom_integrations")
