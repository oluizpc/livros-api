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

# ISBNs validos usados nos testes
ISBN_VALIDO_13 = "978-85-333-0227-3"   # ISBN-13 valido
ISBN_VALIDO_10 = "0-306-40615-2"       # ISBN-10 valido
ISBN_INVALIDO  = "9788533302279"        # ISBN-13 invalido (digito verificador errado)


def _criar_livro_exemplo(
    titulo="Dom Casmurro",
    autor="Machado de Assis",
    ano=1899,
    isbn=ISBN_VALIDO_13,
):
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
        "isbn": ISBN_VALIDO_13,
    })
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
        "isbn": ISBN_VALIDO_13,
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
        "isbn": ISBN_VALIDO_13,
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
# Busca por titulo
# ----------------------------------------------------------------------

def test_busca_por_titulo_retorna_apenas_correspondentes():
    _criar_livro_exemplo(titulo="A Moreninha")
    _criar_livro_exemplo(titulo="O Cortico")

    resp = client.get("/livros?titulo=Moreninha")
    assert resp.status_code == 200
    titulos = [l["titulo"] for l in resp.json()]
    assert "A Moreninha" in titulos
    assert "O Cortico" not in titulos


def test_busca_por_titulo_case_insensitive():
    _criar_livro_exemplo(titulo="Iracema")

    resp = client.get("/livros?titulo=iracema")
    assert resp.status_code == 200
    titulos = [l["titulo"] for l in resp.json()]
    assert "Iracema" in titulos


def test_busca_por_titulo_sem_resultado_retorna_lista_vazia():
    resp = client.get("/livros?titulo=XYZ_INEXISTENTE_ABC")
    assert resp.status_code == 200
    assert resp.json() == []


def test_busca_por_titulo_parcial():
    _criar_livro_exemplo(titulo="Grande Sertao Veredas")

    resp = client.get("/livros?titulo=Sertao")
    assert resp.status_code == 200
    titulos = [l["titulo"] for l in resp.json()]
    assert "Grande Sertao Veredas" in titulos


# ----------------------------------------------------------------------
# Filtro por autor
# ----------------------------------------------------------------------

def test_filtro_por_autor_retorna_apenas_correspondentes():
    _criar_livro_exemplo(titulo="Livro A", autor="Clarice Lispector")
    _criar_livro_exemplo(titulo="Livro B", autor="Jorge Amado")

    resp = client.get("/livros?autor=Clarice")
    assert resp.status_code == 200
    autores = [l["autor"] for l in resp.json()]
    assert all("Clarice" in a for a in autores)
    assert "Jorge Amado" not in autores


def test_filtro_por_autor_case_insensitive():
    _criar_livro_exemplo(titulo="Livro C", autor="Guimaraes Rosa")

    resp = client.get("/livros?autor=guimaraes")
    assert resp.status_code == 200
    autores = [l["autor"] for l in resp.json()]
    assert any("Guimaraes" in a for a in autores)


def test_filtro_por_titulo_e_autor_combinados():
    _criar_livro_exemplo(titulo="Obra Completa", autor="Drummond")
    _criar_livro_exemplo(titulo="Obra Incompleta", autor="Bandeira")

    resp = client.get("/livros?titulo=Obra&autor=Drummond")
    assert resp.status_code == 200
    resultado = resp.json()
    assert len(resultado) >= 1
    assert all("Drummond" in l["autor"] for l in resultado)


# ----------------------------------------------------------------------
# Paginacao
# ----------------------------------------------------------------------

def test_paginacao_retorna_estrutura_correta():
    # cria pelo menos 3 livros para ter dados suficientes
    for i in range(3):
        _criar_livro_exemplo(titulo=f"Livro Paginacao {i}")

    resp = client.get("/livros/paginado?pagina=1&por_pagina=2")
    assert resp.status_code == 200
    corpo = resp.json()
    assert "total" in corpo
    assert "pagina" in corpo
    assert "por_pagina" in corpo
    assert "livros" in corpo
    assert corpo["pagina"] == 1
    assert corpo["por_pagina"] == 2
    assert len(corpo["livros"]) <= 2


def test_paginacao_segunda_pagina_diferente_da_primeira():
    for i in range(5):
        _criar_livro_exemplo(titulo=f"Livro Pag2 {i}")

    resp1 = client.get("/livros/paginado?pagina=1&por_pagina=2")
    resp2 = client.get("/livros/paginado?pagina=2&por_pagina=2")

    ids_p1 = {l["id"] for l in resp1.json()["livros"]}
    ids_p2 = {l["id"] for l in resp2.json()["livros"]}
    assert ids_p1.isdisjoint(ids_p2), "Paginas diferentes nao devem ter os mesmos livros"


def test_paginacao_pagina_alem_do_limite_retorna_lista_vazia():
    resp = client.get("/livros/paginado?pagina=99999&por_pagina=10")
    assert resp.status_code == 200
    assert resp.json()["livros"] == []


def test_paginacao_parametros_invalidos_retornam_422():
    assert client.get("/livros/paginado?pagina=0").status_code == 422
    assert client.get("/livros/paginado?por_pagina=0").status_code == 422
    assert client.get("/livros/paginado?por_pagina=101").status_code == 422


# ----------------------------------------------------------------------
# Validacao de ISBN
# ----------------------------------------------------------------------

def test_isbn_13_valido_aceito():
    resp = _criar_livro_exemplo(isbn=ISBN_VALIDO_13)
    assert resp.status_code == 201


def test_isbn_10_valido_aceito():
    resp = _criar_livro_exemplo(isbn=ISBN_VALIDO_10)
    assert resp.status_code == 201


def test_isbn_invalido_retorna_422():
    resp = _criar_livro_exemplo(isbn=ISBN_INVALIDO)
    assert resp.status_code == 422


def test_isbn_com_formato_incorreto_retorna_422():
    resp = _criar_livro_exemplo(isbn="nao-e-um-isbn")
    assert resp.status_code == 422


# ----------------------------------------------------------------------
# Fluxo completo (mini teste de integracao)
# ----------------------------------------------------------------------

def test_fluxo_completo_criar_buscar_atualizar_remover():
    # cria
    criado = _criar_livro_exemplo(titulo="Ciclo Completo").json()
    livro_id = criado["id"]

    # busca
    assert client.get(f"/livros/{livro_id}").status_code == 200

    # aparece na busca por titulo
    resp_busca = client.get("/livros?titulo=Ciclo Completo")
    titulos = [l["titulo"] for l in resp_busca.json()]
    assert "Ciclo Completo" in titulos

    # atualiza
    client.put(f"/livros/{livro_id}", json={
        "titulo": "Ciclo Completo v2",
        "autor": "Autor",
        "ano": 2021,
        "isbn": ISBN_VALIDO_13,
    })
    assert client.get(f"/livros/{livro_id}").json()["titulo"] == "Ciclo Completo v2"

    # remove
    client.delete(f"/livros/{livro_id}")
    assert client.get(f"/livros/{livro_id}").status_code == 404