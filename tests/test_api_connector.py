"""Test for the ONYX API Connector."""

from unittest.mock import MagicMock, patch

import pytest
from onyx_client.client import OnyxClient
from onyx_client.data.numeric_value import NumericValue
from onyx_client.data.date_information import DateInformation
from onyx_client.data.device_command import DeviceCommand
from onyx_client.data.device_mode import DeviceMode
from onyx_client.device.shutter import Shutter
from onyx_client.enum.action import Action
from onyx_client.enum.device_type import DeviceType
from onyx_client.group.group import Group

from custom_components.hella_onyx import APIConnector
from custom_components.hella_onyx.api_connector import (
    CommandException,
    UnknownStateException,
)


class TestAPIConnector:
    @pytest.fixture
    def client(self):
        yield MockClient()

    @pytest.fixture
    def api(self):
        yield APIConnector(None, 100000000, "finger", "token")

    @pytest.mark.asyncio
    async def test_update(self, api, client):
        with patch.object(api, "_client", new=client.make):
            await api.update()
            assert len(api.data) == 1
            assert len(api.groups) == 1
            assert client.is_called

    @pytest.mark.asyncio
    async def test_get_timezone(self, api, client):
        with patch.object(api, "_client", new=client.make):
            tz = await api.get_timezone()
            assert tz == "Europe/Vienna"
            assert client.is_called

    @pytest.mark.asyncio
    async def test_get_timezone_fallback(self, api):
        client = MockClientNoDate()
        with patch.object(api, "_client", new=client.make):
            tz = await api.get_timezone()
            assert tz == "UTC"
            assert client.called

    def test_device(self, api):
        api.data = {"uuid": "device"}
        assert api.device("uuid") == "device"

    def test_device_not_found(self, api):
        with pytest.raises(UnknownStateException):
            api.device("uuid")

    @pytest.mark.asyncio
    async def test_update_device(self, api, client):
        assert len(api.data) == 0
        with patch.object(api, "_client", new=client.make):
            await api.update_device("id")
            assert len(api.data) == 1
            assert client.is_called

    @pytest.mark.asyncio
    async def test_updated_device(self, api, client):
        api.data = {
            "id": Shutter(
                "id",
                "name",
                DeviceType.RAFFSTORE_90,
                DeviceMode(DeviceType.RAFFSTORE_90),
                list(Action),
                actual_angle=NumericValue(0, 0, 0, False),
                actual_position=NumericValue(0, 0, 0, False),
            )
        }
        assert len(api.data) == 1
        actual_angle = NumericValue(1, 1, 1, False)
        api.updated_device(
            Shutter(
                "id",
                "name",
                DeviceType.RAFFSTORE_90,
                DeviceMode(DeviceType.RAFFSTORE_90),
                list(Action),
                actual_angle=actual_angle,
            )
        )
        assert api.data["id"].actual_angle == actual_angle

    @pytest.mark.asyncio
    async def test_updated_device_new(self, api, client):
        api.data = {
            "id": Shutter(
                "id",
                "name",
                DeviceType.RAFFSTORE_90,
                DeviceMode(DeviceType.RAFFSTORE_90),
                list(Action),
                actual_angle=NumericValue(0, 0, 0, False),
                actual_position=NumericValue(0, 0, 0, False),
            )
        }
        assert len(api.data) == 1
        api.updated_device(
            Shutter(
                "id1",
                "name",
                DeviceType.RAFFSTORE_90,
                DeviceMode(DeviceType.RAFFSTORE_90),
                list(Action),
            )
        )
        assert api.data["id"].actual_angle == NumericValue(0, 0, 0, False)

    @pytest.mark.asyncio
    async def test_send_device_command_action(self, api, client):
        with patch.object(api, "_client", new=client.make):
            await api.send_device_command_action("id", Action.STOP)
            assert client.is_called

    @pytest.mark.asyncio
    async def test_send_device_command_action_failed(self, api, client):
        with patch.object(api, "_client", new=client.make):
            with pytest.raises(CommandException):
                await api.send_device_command_action("id", Action.CLOSE)
            assert client.is_called

    @pytest.mark.asyncio
    async def test_send_device_command_properties(self, api, client):
        with patch.object(api, "_client", new=client.make):
            await api.send_device_command_properties("id", {"action": 0})
            assert client.is_called

    @pytest.mark.asyncio
    async def test_send_device_command_properties_failed(self, api, client):
        with patch.object(api, "_client", new=client.make):
            with pytest.raises(CommandException):
                await api.send_device_command_properties("id", {"fail": 0})
            assert client.is_called

    @pytest.mark.asyncio
    async def test__client(self, api):
        api.hass = MagicMock()
        client = api._client()
        assert client is not None
        assert isinstance(client, OnyxClient)

    # FIXME:
    # @pytest.mark.asyncio
    # async def test_events(self, api, client):
    #     with patch.object(api, "_new_client", new=client.make):
    #         async for device in api.events():
    #             assert device is not None
    #         assert client.is_called
    #         assert not client.is_force_update

    # FIXME:
    # @pytest.mark.asyncio
    # async def test_events_force_update(self, api, client):
    #     with patch.object(api, "_new_client", new=client.make):
    #         async for device in api.events(True):
    #             assert device is not None
    #         assert client.is_called
    #         assert client.is_force_update


class MockClient:
    def __init__(self):
        self.called = False
        self.force_update = False
        self.date = None

    def make(self, *kwargs):
        self.called = False
        self.force_update = False
        self.date = DateInformation(100.0, "Europe/Vienna", 3600)
        return self

    @property
    def is_called(self):
        return self.called

    @property
    def is_force_update(self):
        return self.force_update

    async def devices(self, include_details: bool):
        assert include_details
        self.called = True
        return [
            Shutter(
                "id",
                "name",
                DeviceType.RAFFSTORE_90,
                DeviceMode(DeviceType.RAFFSTORE_90),
                list(Action),
            )
        ]

    async def groups(self):
        self.called = True
        return [Group("group", "group", [])]

    async def device(self, uuid: str):
        self.called = True
        return Shutter(
            "id",
            "other",
            DeviceType.RAFFSTORE_90,
            DeviceMode(DeviceType.RAFFSTORE_90),
            list(Action),
        )

    async def events(self, force_update: bool):
        self.called = True
        self.force_update = force_update
        yield Shutter(
            "id",
            "other",
            DeviceType.RAFFSTORE_90,
            DeviceMode(DeviceType.RAFFSTORE_90),
            list(Action),
        )

    async def send_command(self, uuid: str, command: DeviceCommand):
        self.called = True
        return command.action == Action.STOP or (
            command.properties is not None and "fail" not in command.properties
        )

    async def date_information(self):
        self.called = True
        return self.date


class MockClientNoDate(MockClient):
    async def date_information(self):
        self.called = True
        return None
