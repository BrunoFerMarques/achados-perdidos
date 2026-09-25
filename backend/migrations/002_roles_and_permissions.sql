-- Replace the fixed users.role column with configurable roles (RBAC).
-- Admins create roles and choose their permissions. Permissions are seeded here
-- and only change through migrations, because each one maps to a check in the code.

CREATE TABLE permissions (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,
    description  TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE roles (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT,
    is_system    BOOLEAN NOT NULL DEFAULT false,  -- cannot be renamed or deleted
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE role_permissions (
    role_id        BIGINT NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    permission_id  BIGINT NOT NULL REFERENCES permissions (id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (role_id, permission_id)
);
CREATE INDEX role_permissions_permission_id_idx ON role_permissions (permission_id);

CREATE TABLE user_roles (
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role_id     BIGINT NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, role_id)
);
CREATE INDEX user_roles_role_id_idx ON user_roles (role_id);

CREATE TRIGGER roles_set_updated_at
    BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE FUNCTION protect_system_role() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'system role % cannot be deleted', OLD.name;
    END IF;
    IF NEW.name <> OLD.name OR NOT NEW.is_system THEN
        RAISE EXCEPTION 'system role % cannot be renamed or unmarked as system', OLD.name;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER roles_protect_system
    BEFORE UPDATE OR DELETE ON roles
    FOR EACH ROW WHEN (OLD.is_system) EXECUTE FUNCTION protect_system_role();

-- ========== Seed (docs/diagrama.md, section 11) ==========

INSERT INTO permissions (code, description) VALUES
    ('items.register',          'Registrar item achado'),
    ('items.register_direct',   'Registrar item direto no ponto de coleta, já disponível'),
    ('items.receive',           'Confirmar recebimento de item'),
    ('items.transfer',          'Transferir item entre pontos de coleta'),
    ('items.dispose',           'Registrar destinação de item expirado'),
    ('claims.create',           'Reivindicar item'),
    ('claims.review',           'Analisar reivindicação'),
    ('pickups.validate',        'Validar retirada'),
    ('lost_reports.create',     'Relatar perda'),
    ('catalog.manage',          'Gerenciar pontos de coleta, locais, categorias e cores'),
    ('users.unblock',           'Desbloquear usuário'),
    ('access.manage',           'Gerenciar cargos, acessos e vínculo de atendentes a pontos'),
    ('collection_points.all',   'Operar itens de qualquer ponto de coleta, sem vínculo');

INSERT INTO roles (name, description, is_system) VALUES
    ('user',      'Usuário cadastrado', true),
    ('attendant', 'Atendente de ponto de coleta', false),
    ('admin',     'Administrador do sistema', true);

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM (VALUES
    ('user',      'items.register'),
    ('user',      'lost_reports.create'),
    ('user',      'claims.create'),
    ('attendant', 'items.register_direct'),
    ('attendant', 'items.receive'),
    ('attendant', 'items.transfer'),
    ('attendant', 'claims.review'),
    ('attendant', 'pickups.validate'),
    ('admin',     'items.register_direct'),
    ('admin',     'items.receive'),
    ('admin',     'items.transfer'),
    ('admin',     'items.dispose'),
    ('admin',     'claims.review'),
    ('admin',     'pickups.validate'),
    ('admin',     'catalog.manage'),
    ('admin',     'users.unblock'),
    ('admin',     'access.manage'),
    ('admin',     'collection_points.all')
) AS grants (role_name, permission_code)
JOIN roles r ON r.name = grants.role_name
JOIN permissions p ON p.code = grants.permission_code;

-- ========== Move existing users to user_roles ==========

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = u.role::text;

ALTER TABLE users DROP COLUMN role;
DROP TYPE user_role;
