"""Camada de abstração de provedores de IA.

O MVP implementa um provedor real (Anthropic, via SDK oficial). Novos provedores implementam
`AIProvider`. Quando nenhum provedor está configurado, `UnavailableProvider` falha com uma
mensagem explícita — o sistema nunca devolve respostas simuladas como se fossem da IA.
"""
from __future__ import annotations

import copy
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Integration
from ..security import decrypt_secret

# Preços por milhão de tokens (USD), entrada/saída. Usados para estimar custo por execução.
PRICING_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-fable-5-1": (10.0, 50.0),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-opus-5": (5.0, 25.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (2.0, 10.0),
    "claude-haiku-5-5": (0.10, 0.50),
}
SUPPORTED_MODELS = list(PRICING_PER_MTOK)
EFFORT_LEVELS = ["low", "medium", "high", "xhigh", "max"]


class AIError(RuntimeError):
    """Falha ao obter resposta do provedor (configuração, rede, recusa, validação)."""


class AINotConfigured(AIError):
    pass


@dataclass
class AIUsage:
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def cost_usd(self) -> float:
        price_in, price_out = PRICING_PER_MTOK.get(self.model, (0.0, 0.0))
        return round(self.input_tokens / 1_000_000 * price_in + self.output_tokens / 1_000_000 * price_out, 6)


@dataclass
class AIResult:
    data: BaseModel
    usage: AIUsage
    raw_text: str


class AIProvider(Protocol):
    name: str
    model: str

    def status(self) -> dict[str, Any]: ...

    def generate_structured(self, *, system: str, prompt: str, schema: type[BaseModel], max_tokens: int | None = None) -> AIResult: ...


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Converte o schema Pydantic para o formato aceito por saídas estruturadas.

    Todos os objetos recebem `additionalProperties: false` e todas as propriedades ficam obrigatórias.
    """
    schema = copy.deepcopy(model.model_json_schema())

    def fix(node: Any) -> None:
        """Percorre apenas nós de schema; mapas de propriedades/definições são tratados à parte,
        para não confundir um campo chamado ``title`` com a palavra-chave ``title``."""
        if isinstance(node, list):
            for value in node:
                fix(value)
            return
        if not isinstance(node, dict):
            return
        node.pop("default", None)
        node.pop("title", None)
        if node.get("type") == "object" or "properties" in node:
            node["additionalProperties"] = False
            if "properties" in node:
                node["required"] = list(node["properties"].keys())
        for key, value in node.items():
            if key in {"properties", "$defs", "definitions"} and isinstance(value, dict):
                for sub in value.values():
                    fix(sub)
            elif isinstance(value, (dict, list)):
                fix(value)

    fix(schema)
    return schema


class UnavailableProvider:
    name = "none"

    def __init__(self, reason: str, model: str = "") -> None:
        self.reason = reason
        self.model = model

    def status(self) -> dict[str, Any]:
        return {"provider": self.name, "configured": False, "model": self.model, "reason": self.reason}

    def generate_structured(self, **_: Any) -> AIResult:
        raise AINotConfigured(self.reason)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, effort: str, key_source: str) -> None:
        self.api_key = api_key
        self.model = model
        self.effort = effort
        self.key_source = key_source

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "configured": True,
            "model": self.model,
            "effort": self.effort,
            "key_source": self.key_source,
            "refusal_fallbacks": settings.ai_refusal_fallbacks,
        }

    def _client(self):
        import anthropic

        return anthropic.Anthropic(api_key=self.api_key, timeout=settings.ai_timeout_seconds, max_retries=2)

    def generate_structured(self, *, system: str, prompt: str, schema: type[BaseModel], max_tokens: int | None = None) -> AIResult:
        import anthropic

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or settings.ai_max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": {
                "effort": self.effort,
                "format": {"type": "json_schema", "schema": strict_json_schema(schema)},
            },
        }
        if settings.ai_refusal_fallbacks:
            # Em caso de recusa pelos classificadores, a API reexecuta a requisição em um modelo
            # de fallback escolhido por categoria (beta server-side-fallback-2026-07-01).
            kwargs["extra_headers"] = {"anthropic-beta": "server-side-fallback-2026-07-01"}
            kwargs["extra_body"] = {"fallbacks": "default"}
        try:
            response = self._client().messages.create(**kwargs)
        except anthropic.AuthenticationError as exc:
            raise AIError("Chave de API da Anthropic inválida") from exc
        except anthropic.PermissionDeniedError as exc:
            raise AIError("A chave de API não tem permissão para este modelo") from exc
        except anthropic.NotFoundError as exc:
            raise AIError(f"Modelo não encontrado: {self.model}") from exc
        except anthropic.RateLimitError as exc:
            raise AIError("Limite de uso do provedor atingido (429)") from exc
        except anthropic.BadRequestError as exc:
            raise AIError(f"Requisição rejeitada pelo provedor: {exc.message}") from exc
        except anthropic.APIStatusError as exc:
            raise AIError(f"Erro do provedor ({exc.status_code})") from exc
        except anthropic.APIConnectionError as exc:
            raise AIError("Falha de conexão com o provedor de IA") from exc

        usage = AIUsage(
            provider=self.name,
            model=getattr(response, "model", None) or self.model,
            input_tokens=int(getattr(response.usage, "input_tokens", 0) or 0),
            output_tokens=int(getattr(response.usage, "output_tokens", 0) or 0),
        )
        if response.stop_reason == "refusal":
            raise AIError("O modelo recusou a solicitação (stop_reason=refusal)")
        if response.stop_reason == "max_tokens":
            raise AIError("Resposta truncada: limite de tokens atingido")
        text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), "")
        try:
            data = schema.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise AIError(f"Resposta da IA não corresponde ao formato esperado: {exc}") from exc
        return AIResult(data=data, usage=usage, raw_text=text)


# Permite que testes injetem um provedor determinístico explicitamente identificado.
_provider_override: Callable[[], AIProvider] | None = None


def set_provider_override(factory: Callable[[], AIProvider] | None) -> None:
    global _provider_override
    _provider_override = factory


def resolve_provider(db: Session, owner_id: str | None) -> AIProvider:
    if _provider_override is not None:
        return _provider_override()
    integration = None
    if owner_id:
        integration = (
            db.query(Integration)
            .filter(Integration.owner_id == owner_id, Integration.name == "anthropic", Integration.enabled.is_(True))
            .one_or_none()
        )
    model = settings.ai_model
    effort = settings.ai_effort
    if integration is not None:
        model = integration.config.get("model") or model
        effort = integration.config.get("effort") or effort
    if settings.ai_provider != "anthropic":
        return UnavailableProvider(f"Provedor '{settings.ai_provider}' não suportado neste MVP", model)
    if integration is not None and integration.secret_ciphertext:
        key = decrypt_secret(integration.secret_ciphertext)
        if key:
            return AnthropicProvider(key, model, effort, "integração (cifrada)")
    import os

    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return AnthropicProvider(env_key, model, effort, "variável de ambiente")
    return UnavailableProvider(
        "Nenhum provedor de IA configurado. Defina ANTHROPIC_API_KEY ou cadastre a chave em Configurações.", model
    )
