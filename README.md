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

## Migrações

Toda mudança no banco é um arquivo novo em `backend/migrations/`, numerado em ordem (`001_...sql`, `002_...sql`). O `python migrate.py` aplica só os arquivos que ainda não rodaram, cada um em uma transação, e registra o que foi aplicado na tabela `schema_migrations`.

Nunca edite uma migração que já está no `master`: crie uma nova.

## CI/CD

1. Todo PR roda o workflow `CI` no GitHub Actions: `ruff check`, `ruff format --check` e `pytest` contra um Postgres temporário.
2. O `master` é protegido: o merge só acontece com PR aprovado e CI verde.
3. Depois do merge, o CI roda de novo no `master`. Com ele verde, o Render faz o deploy.
4. Ao subir, o Render roda `python migrate.py` no banco de produção e só então inicia a API. Se a migração falhar, o deploy falha e a versão anterior continua no ar.

O Dependabot abre PRs semanais com atualizações das dependências Python e das actions.
