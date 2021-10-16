from dataclasses import dataclass, field
from typing import Callable

from .events.event import Event
from .events.eventHandler import EventHandler
from . import Connection




class GroupNotFoundError(Exception):

    def __init__(self, groupName: str, message: str):
        self.groupName = groupName
        super().__init__(message)

class ClientNotFoundError(Exception):

    def __init__(self, groupName: str, clientName: str, message: str):
        self.groupName = groupName
        self.clientName = clientName
        super().__init__(message)

@dataclass
class ClientConnection:
    name: str
    connection: Connection.RequestSender

@dataclass
class Group:
    name: str
    clients: dict[str, ClientConnection] = field(default_factory=dict)

class Server:

    def __init__(self, eventPort: int, replyPort: int, clientType: type[ClientConnection] = ClientConnection):
        self.eventConnection = Connection.EventSender(eventPort)
        self.requestConnection = Connection.RequestReceiver(replyPort, daemon = False)

        self.clientType = clientType

        self.groups: dict[str, Group] = {}
        self.groups["main"] = Group("main")

        self.eventHandler = EventHandler()

        self.requestConnection.SetCallback(self.eventHandler.handleEvent)

        joinGroupEvent = Event("join group")
        self.eventHandler.addEventListener(joinGroupEvent, self.joinGroup)

    def joinGroup(self, eventData):
        groupName, clientName, clientIp, clientRequestRecievePort = eventData
        group = self.getGroup(groupName)

        connection = Connection.RequestSender(clientIp, clientRequestRecievePort)
        group.clients[clientName] = self.clientType(clientName, connection)

    def SendEvent(self, target: str, data):
        self.eventConnection.SendMessage(target, data)

    def SendRequest(self, groupName: str, clientName: str, requestType: str, data):
        client = self.getClient(groupName, clientName)

        event = Event(requestType)
        reply = client.connection.SendMessage(event, data)

        return reply

    def AddRequestListener(self, name: str, listener: Callable):
        self.eventHandler.addEventListener(Event(name), listener)

    def getGroup(self, groupName: str) -> Group:
        if not groupName in self.groups:
            raise GroupNotFoundError(groupName, f"Could not find group '{groupName}'")

        return self.groups[groupName]

    def getClient(self, groupName: str, clientName: str) -> ClientConnection:
        try:
            group = self.getGroup(groupName)

            if not clientName in group.clients:
                raise ClientNotFoundError(groupName, clientName, f"Could not find client '{clientName}' in group '{groupName}'")

            return group.clients[clientName]

        except GroupNotFoundError:
            raise ClientNotFoundError(groupName, clientName, f"could not find group '{groupName}' while searching for client {clientName}")