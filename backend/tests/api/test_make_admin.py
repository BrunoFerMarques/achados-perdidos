# no route makes anyone admin on its own, so the first admin comes from make_admin.py
import make_admin

MARIA = {"name": "Maria Silva", "email": "maria@example.com", "password": "senha-forte"}


def test_script_promotes_an_existing_user_to_admin(client, signup, capsys):
    maria = signup(MARIA)

    exit_code = make_admin.main(["MARIA@example.com"])

    assert exit_code == 0
    assert "maria@example.com agora é admin" in capsys.readouterr().out
    # the same token now reaches the admin routes
    assert client.get("/v1/users", headers=maria.headers).status_code == 200


def test_script_fails_for_an_unknown_email(capsys):
    exit_code = make_admin.main(["ninguem@example.com"])

    assert exit_code == 1
    assert "Usuário não encontrado" in capsys.readouterr().err


def test_script_without_an_email_shows_usage(capsys):
    exit_code = make_admin.main([])

    assert exit_code == 2
    assert "Uso: python make_admin.py <email>" in capsys.readouterr().err
