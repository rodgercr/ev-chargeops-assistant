"""Saída estruturada Pydantic usada pelos evals da Sprint 3."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ConsultaRecarga(BaseModel):
    """Dados explicitamente informados em uma consulta de recarga EV."""

    veiculo: str | None = Field(default=None, description="Modelo do veículo")
    potencia_kw: float | None = Field(default=None, gt=0, description="Potência em kW")
    conector: str | None = Field(default=None, description="Tipo de conector")
    local: Literal["residencial", "comercial", "publico", "desconhecido"] = (
        "desconhecido"
    )
    duvida: str = Field(min_length=1, description="Dúvida principal do usuário")

    @field_validator("potencia_kw")
    @classmethod
    def validar_potencia(cls, valor: float | None) -> float | None:
        if valor is None:
            return valor
        if valor > 350:
            raise ValueError("A potência deve ser menor ou igual a 350 kW.")
        return round(valor, 2)

    @field_validator("veiculo", "conector", mode="before")
    @classmethod
    def normalizar_texto_opcional(cls, valor: object) -> object:
        if isinstance(valor, str):
            texto = valor.strip()
            return texto or None
        return valor

    @field_validator("duvida")
    @classmethod
    def validar_duvida(cls, valor: str) -> str:
        texto = valor.strip()
        if not texto:
            raise ValueError("A dúvida não pode ficar vazia.")
        return texto
