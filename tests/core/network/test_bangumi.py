import pytest

from data.plugins.astrbot_plugin_galgame_box.core.network import Bangumi
from data.plugins.astrbot_plugin_galgame_box.core.services import Services
from data.plugins.astrbot_plugin_galgame_box.core.type.inner_models import CommandType


@pytest.fixture(scope="function")
def bangumi(service: Services):
    bangumi = Services.get(Bangumi)

    yield bangumi


@pytest.mark.bangumi
async def test_request_search_game(bangumi):
    res = await bangumi.request_search_game("素晴日")
    assert isinstance(res, list)