# Achados e perdidos
Projeto de engenharia de software, aonde iremos implementar um sistema de achados e perdidos

## Ambientes

| Ambiente        | API            | Banco                                      |
| --------------- | -------------- | ------------------------------------------ |
| Produção        | Render         | Neon, branch `main`                        |
| Desenvolvimento | Máquina local  | Neon, branch `dev`                         |
| Testes locais   | pytest         | Neon, branch `test` (ou Postgres local)    |
| CI              | GitHub Actions | Postgres temporário criado a cada execução |

Ninguém usa o banco de produção na própria máquina.

## Rodando localmente

Requisito: Python 3.13.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # Linux/macOS
pip install -r requirements-dev.txt
```

Copie `.env.example` para `.env` na raiz do repositório e preencha as URLs do Neon.

```bash
python migrate.py                # aplica as migrações pendentes no DATABASE_URL
uvicorn api:app --reload         # http://localhost:8000/docs
```

## Testes e lint

```bash
cd backend
pytest                           # aplica as migrações no TEST_DATABASE_URL e roda os testes
ruff check .                     # lint
ruff format .                    # formata o código
```

`TEST_DATABASE_URL` nunca deve apontar para produção: os testes gravam dados. O pytest se recusa a rodar se ela não estiver definida ou for igual a `DATABASE_URL`.

## Arquitetura

O backend é dividido em camadas (`routers` → `services` → `repositories` → `models`, com as regras puras em `domain`) e usa Repository, Unit of Work e injeção de dependência. Antes de criar uma feature, leia [docs/arquitetura.md](docs/arquitetura.md): ele explica onde cada coisa fica, quais padrões estão planejados para as regras do escopo e traz o passo a passo para adicionar uma feature.

## Migrações

As tabelas são definidas como models do SQLAlchemy em `backend/models/`. Cada mudança no banco é uma migração do Alembic em `backend/migrations/versions/`, gerada a partir dos models.

Para criar ou alterar uma tabela:

1. Crie ou edite o model. Um model novo precisa ser importado em `backend/models/__init__.py`, senão o Alembic não o enxerga.
2. Gere a migração. O Alembic compara os models com o banco do `DATABASE_URL`, então esse banco precisa estar com todas as migrações aplicadas:

   ```bash
   cd backend
   python migrate.py                                   # deixa o banco local em dia
   alembic revision --autogenerate -m "create items"   # gera a migração a partir dos models
   python migrate.py                                   # aplica a migração nova
   ```

3. Revise o arquivo gerado antes de commitar. O autogenerate não detecta funções, triggers nem tipos `ENUM` alterados: escreva essas partes à mão com `op.execute(...)`.

O `python migrate.py` (o mesmo que `alembic upgrade head`) aplica só as migrações que ainda não rodaram, cada uma em uma transação, e registra a versão atual na tabela `alembic_version`. Para ver o SQL sem executar: `alembic upgrade head --sql`.

Nunca edite uma migração que já está no `master`: crie uma nova.

## CI/CD

1. Todo PR roda o workflow `CI` no GitHub Actions: `ruff check`, `ruff format --check` e `pytest` contra um Postgres temporário.
2. O `master` é protegido: o merge só acontece com PR aprovado e CI verde.
3. Depois do merge, o CI roda de novo no `master`. Com ele verde, o Render faz o deploy.
4. Ao subir, o Render roda `python migrate.py` no banco de produção e só então inicia a API. Se a migração falhar, o deploy falha e a versão anterior continua no ar.

O Dependabot abre PRs semanais com atualizações das dependências Python e das actions.
