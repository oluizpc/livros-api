"""
Modelos Pydantic da API de catalogo de livros.

Separamos o modelo de ENTRADA (LivroCriar / LivroAtualizar) do modelo
de SAIDA (Livro). O id e gerado pelo sistema, entao nao faz parte da
entrada --- o cliente nao escolhe o id.
"""

import re

from pydantic import BaseModel, Field, field_validator


def _validar_isbn(valor: str) -> str:
    """
    Aceita ISBN-10 ou ISBN-13.
    Remove hifens e espacos antes de validar.
    """
    limpo = re.sub(r"[\s\-]", "", valor)
    if len(limpo) == 10:
        if not re.fullmatch(r"\d{9}[\dXx]", limpo):
            raise ValueError("ISBN-10 invalido: deve ter 9 digitos e um digito verificador (0-9 ou X)")
        soma = sum((10 - i) * (10 if c in "Xx" else int(c)) for i, c in enumerate(limpo))
        if soma % 11 != 0:
            raise ValueError("ISBN-10 invalido: digito verificador incorreto")
    elif len(limpo) == 13:
        if not re.fullmatch(r"\d{13}", limpo):
            raise ValueError("ISBN-13 invalido: deve conter apenas digitos")
        soma = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(limpo))
        if soma % 10 != 0:
            raise ValueError("ISBN-13 invalido: digito verificador incorreto")
    else:
        raise ValueError("ISBN invalido: deve ter 10 ou 13 caracteres (sem hifens)")
    return valor


class LivroCriar(BaseModel):
    """Dados que o cliente envia para criar um livro (sem id)."""
    titulo: str = Field(..., min_length=1, description="Titulo do livro")
    autor: str = Field(..., min_length=1, description="Nome do autor")
    ano: int = Field(..., ge=0, le=2100, description="Ano de publicacao")
    isbn: str = Field(..., min_length=1, description="Codigo ISBN-10 ou ISBN-13")

    @field_validator("isbn")
    @classmethod
    def isbn_valido(cls, v: str) -> str:
        return _validar_isbn(v)


class LivroAtualizar(BaseModel):
    """Dados que o cliente envia para atualizar um livro (sem id)."""
    titulo: str = Field(..., min_length=1)
    autor: str = Field(..., min_length=1)
    ano: int = Field(..., ge=0, le=2100)
    isbn: str = Field(..., min_length=1)

    @field_validator("isbn")
    @classmethod
    def isbn_valido(cls, v: str) -> str:
        return _validar_isbn(v)


class Livro(BaseModel):
    """Livro completo, como a API devolve (com id gerado pelo sistema)."""
    id: int
    titulo: str
    autor: str
    ano: int
    isbn: str


class ListaLivrosPaginada(BaseModel):
    """Resposta paginada da listagem de livros."""
    total: int
    pagina: int
    por_pagina: int
    livros: list[Livro]