"""
Testes da API de catalogo de livros usando o TestClient do FastAPI.

Estes testes fazem requisicoes simuladas (sem subir servidor de verdade)
e verificam status code, corpo da resposta e efeitos colaterais.

Para rodar:
  pip install fastapi uvicorn httpx pytest
  pytest -v

NOTA: como o repositorio e em memoria e compartilhado pela aplicacao,
cada teste cria seus proprios dados e nao assume um estado vazio inicial.
Os testes verificam o comportamento de forma independente da ordem.
"""

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _criar_livro_exemplo(titulo="Dom Casmurro", autor="Machado de Assis",
                         ano=1899, isbn="978-85-000-0001-0"):
    """Helper: cria um livro e devolve a resposta."""
    return client.post("/livros", json={
        "titulo": titulo,
        "autor": autor,
        "ano": ano,
        "isbn": isbn,
    })


# ----------------------------------------------------------------------
# Create
# ----------------------------------------------------------------------

def test_criar_livro_retorna_201_e_id():
    resp = _criar_livro_exemplo()
    assert resp.status_code == 201
    corpo = resp.json()
    assert corpo["titulo"] == "Dom Casmurro"
    assert corpo["autor"] == "Machado de Assis"
    assert "id" in corpo
    assert isinstance(corpo["id"], int)


def test_criar_livro_com_dados_invalidos_retorna_422():
    # ano como texto e titulo vazio --- Pydantic rejeita antes de chegar na logica
    resp = client.post("/livros", json={
        "titulo": "",
        "autor": "Alguem",
        "ano": "mil e novecentos",
        "isbn": "123",
    })
    # FastAPI/Pydantic retorna 422 para corpo que nao valida
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# Read
# ----------------------------------------------------------------------

def test_listar_livros_retorna_200_e_lista():
    _criar_livro_exemplo()
    resp = client.get("/livros")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_buscar_livro_existente_retorna_200():
    criado = _criar_livro_exemplo(titulo="Memorias Postumas").json()
    resp = client.get(f"/livros/{criado['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == criado["id"]
    assert resp.json()["titulo"] == "Memorias Postumas"


def test_buscar_livro_inexistente_retorna_404():
    resp = client.get("/livros/999999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Livro nao encontrado"


# ----------------------------------------------------------------------
# Update
# ----------------------------------------------------------------------

def test_atualizar_livro_existente_retorna_200_e_dados_novos():
    criado = _criar_livro_exemplo(titulo="Titulo Antigo").json()
    resp = client.put(f"/livros/{criado['id']}", json={
        "titulo": "Titulo Novo",
        "autor": "Autor Novo",
        "ano": 2020,
        "isbn": "978-85-000-9999-9",
    })
    assert resp.status_code == 200
    corpo = resp.json()
    assert corpo["id"] == criado["id"]
    assert corpo["titulo"] == "Titulo Novo"
    assert corpo["ano"] == 2020


def test_atualizar_livro_inexistente_retorna_404():
    resp = client.put("/livros/999999", json={
        "titulo": "Qualquer",
        "autor": "Qualquer",
        "ano": 2000,
        "isbn": "000",
    })
    assert resp.status_code == 404


# ----------------------------------------------------------------------
# Delete
# ----------------------------------------------------------------------

def test_remover_livro_existente_retorna_200_e_some_da_busca():
    criado = _criar_livro_exemplo(titulo="Para Remover").json()
    livro_id = criado["id"]

    resp_del = client.delete(f"/livros/{livro_id}")
    assert resp_del.status_code == 200

    # efeito colateral: depois de remover, buscar deve dar 404
    resp_get = client.get(f"/livros/{livro_id}")
    assert resp_get.status_code == 404


def test_remover_livro_inexistente_retorna_404():
    resp = client.delete("/livros/999999")
    assert resp.status_code == 404


# ----------------------------------------------------------------------
# Fluxo completo (mini teste de integracao)
# ----------------------------------------------------------------------

def test_fluxo_completo_criar_buscar_atualizar_remover():
    # cria
    criado = _criar_livro_exemplo(titulo="Ciclo Completo").json()
    livro_id = criado["id"]

    # busca
    assert client.get(f"/livros/{livro_id}").status_code == 200

    # atualiza
    client.put(f"/livros/{livro_id}", json={
        "titulo": "Ciclo Completo v2",
        "autor": "Autor",
        "ano": 2021,
        "isbn": "978-85-000-1234-5",
    })
    assert client.get(f"/livros/{livro_id}").json()["titulo"] == "Ciclo Completo v2"

    # remove
    client.delete(f"/livros/{livro_id}")
    assert client.get(f"/livros/{livro_id}").status_code == 404
