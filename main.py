"""
API REST de catalogo de livros (FastAPI).

Estrutura em camadas:
  - Rotas (este arquivo): recebem a requisicao, chamam o service, devolvem a resposta
  - Service: regras de negocio
  - Repository (repository.py): guarda e recupera os dados

Extensoes implementadas:
  - Busca por titulo:   GET /livros?titulo=<termo>
  - Filtro por autor:   GET /livros?autor=<termo>
  - Paginacao:          GET /livros?pagina=1&por_pagina=10
  - Validacao de ISBN:  ISBN-10 e ISBN-13 com digito verificador (models.py)

Para rodar:
  pip install fastapi uvicorn
  uvicorn main:app --reload

Documentacao interativa: http://localhost:8000/docs
"""

from fastapi import FastAPI, HTTPException, Query, status

from models import Livro, LivroCriar, LivroAtualizar, ListaLivrosPaginada
from repository import RepositorioEmMemoria, RepositorioLivros


# ----------------------------------------------------------------------
# Camada de servico (regras de negocio)
# ----------------------------------------------------------------------

class ServicoLivros:
    """
    Onde mora a logica de negocio. Recebe um RepositorioLivros pela
    interface --- nao sabe se e em memoria, SQLite ou outra coisa.
    """

    def __init__(self, repositorio: RepositorioLivros) -> None:
        self._repo = repositorio

    def listar(self) -> list[Livro]:
        return self._repo.listar()

    def buscar_por_titulo(self, titulo: str) -> list[Livro]:
        return self._repo.buscar_por_titulo(titulo)

    def filtrar_por_autor(self, autor: str) -> list[Livro]:
        return self._repo.filtrar_por_autor(autor)

    def listar_paginado(self, pagina: int, por_pagina: int) -> ListaLivrosPaginada:
        livros, total = self._repo.listar_paginado(pagina, por_pagina)
        return ListaLivrosPaginada(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            livros=livros,
        )

    def buscar(self, livro_id: int) -> Livro | None:
        return self._repo.buscar_por_id(livro_id)

    def criar(self, dados: LivroCriar) -> Livro:
        return self._repo.adicionar(dados)

    def atualizar(self, livro_id: int, dados: LivroAtualizar) -> Livro | None:
        return self._repo.atualizar(livro_id, dados)

    def remover(self, livro_id: int) -> bool:
        return self._repo.remover(livro_id)


# ----------------------------------------------------------------------
# Montagem da aplicacao
# ----------------------------------------------------------------------

app = FastAPI(title="Catalogo de Livros", version="2.0.0")

servico = ServicoLivros(RepositorioEmMemoria())


# ----------------------------------------------------------------------
# Rotas (camada de API)
# ----------------------------------------------------------------------

@app.get("/livros", response_model=list[Livro])
def listar_livros(
    titulo: str | None = Query(default=None, description="Busca parcial pelo titulo"),
    autor: str | None = Query(default=None, description="Filtra por nome do autor"),
):
    """
    Lista todos os livros.
    - Use ?titulo=<termo> para busca por titulo (parcial, sem diferenciar maiusculas).
    - Use ?autor=<termo> para filtrar por autor (parcial, sem diferenciar maiusculas).
    - Combine os dois filtros para restringir ainda mais.
    """
    resultado = servico.listar()

    if titulo:
        resultado = [l for l in resultado if titulo.lower() in l.titulo.lower()]
    if autor:
        resultado = [l for l in resultado if autor.lower() in l.autor.lower()]

    return resultado


@app.get("/livros/paginado", response_model=ListaLivrosPaginada)
def listar_livros_paginado(
    pagina: int = Query(default=1, ge=1, description="Numero da pagina (começa em 1)"),
    por_pagina: int = Query(default=10, ge=1, le=100, description="Itens por pagina (max 100)"),
):
    """
    Lista livros com paginacao.
    Retorna o total de registros, a pagina atual e os livros da pagina.
    """
    return servico.listar_paginado(pagina, por_pagina)


@app.get("/livros/{livro_id}", response_model=Livro)
def buscar_livro(livro_id: int):
    livro = servico.buscar(livro_id)
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro nao encontrado",
        )
    return livro


@app.post("/livros", response_model=Livro, status_code=status.HTTP_201_CREATED)
def criar_livro(dados: LivroCriar):
    return servico.criar(dados)


@app.put("/livros/{livro_id}", response_model=Livro)
def atualizar_livro(livro_id: int, dados: LivroAtualizar):
    livro = servico.atualizar(livro_id, dados)
    if livro is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro nao encontrado",
        )
    return livro


@app.delete("/livros/{livro_id}", status_code=status.HTTP_200_OK)
def remover_livro(livro_id: int):
    removido = servico.remover(livro_id)
    if not removido:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Livro nao encontrado",
        )
    return {"mensagem": "Livro removido com sucesso"}