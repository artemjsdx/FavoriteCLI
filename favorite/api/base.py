from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResponse:
    content: str
    model: str
    context_kb: float = 0.0
    raw: dict | None = None


class IChatProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def chat(self, messages: list[ChatMessage], model: str | None = None) -> ChatResponse: ...

    @abstractmethod
    def list_models(self) -> list[dict]: ...


class IModelLister(ABC):
    @abstractmethod
    def list_models(self) -> list[dict]: ...


class IBillingInfo(ABC):
    @abstractmethod
    def get_billing_info(self) -> dict: ...
