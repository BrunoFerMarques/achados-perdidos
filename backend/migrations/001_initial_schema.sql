-- Initial schema, based on docs/diagrama.md.
-- Rules that depend on counting or comparing other rows (RN10, RN12, RN20, RN41...)
-- are enforced by the application; constraints here cover what the database can guarantee alone.

-- ========== Types ==========

CREATE TYPE user_role AS ENUM ('user', 'attendant', 'admin');

CREATE TYPE item_status AS ENUM (
    'registered', 'available', 'in_transit', 'reserved',
    'returned', 'expired', 'disposed', 'cancelled'
);

CREATE TYPE item_disposition AS ENUM ('donated', 'discarded');

CREATE TYPE claim_status AS ENUM (
    'pending', 'approved', 'rejected', 'cancelled', 'completed', 'expired'
);

CREATE TYPE claim_rejection_reason AS ENUM ('low_score', 'attendant', 'returned_to_other');

CREATE TYPE lost_report_status AS ENUM ('active', 'closed', 'expired');

CREATE TYPE notification_type AS ENUM ('match', 'claim');

-- RN42, plus reservation_ended: RESERVADO -> DISPONIVEL also needs an event (RN06)
CREATE TYPE custody_event_type AS ENUM (
    'registered', 'received', 'transfer_out', 'transfer_in', 'reserved',
    'reservation_ended', 'returned', 'expired', 'disposed', 'cancelled'
);

-- ========== Functions ==========

CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

CREATE FUNCTION prevent_modification() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'table % is append-only', TG_TABLE_NAME;
END;
$$;

-- ========== Users and auth ==========

CREATE TABLE users (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    role           user_role NOT NULL DEFAULT 'user',
    blocked_until  TIMESTAMPTZ,  -- RN15/RN16
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_email_lowercase_check CHECK (email = lower(email))
);

CREATE TABLE refresh_tokens (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash  TEXT NOT NULL UNIQUE,  -- SHA-256; the token itself is never stored
    expires_at  TIMESTAMPTZ NOT NULL,
    revoked_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX refresh_tokens_user_id_idx ON refresh_tokens (user_id);

-- ========== Lookup tables (managed by admin) ==========

CREATE TABLE collection_points (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    description  TEXT,
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RN40: an attendant may serve several collection points
CREATE TABLE collection_point_attendants (
    collection_point_id  BIGINT NOT NULL REFERENCES collection_points (id) ON DELETE CASCADE,
    user_id              BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (collection_point_id, user_id)
);
CREATE INDEX collection_point_attendants_user_id_idx ON collection_point_attendants (user_id);

CREATE TABLE locations (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE categories (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    is_document  BOOLEAN NOT NULL DEFAULT false,  -- RN52: holder name is masked in public listing
    is_active    BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE colors (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ========== Items ==========

CREATE TABLE items (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id           BIGINT NOT NULL REFERENCES categories (id),
    color_id              BIGINT NOT NULL REFERENCES colors (id),
    location_id           BIGINT NOT NULL REFERENCES locations (id),
    description           TEXT NOT NULL,
    document_holder_name  TEXT,  -- RN52: document categories only
    found_on              DATE NOT NULL,
    registered_by         BIGINT NOT NULL REFERENCES users (id),
    collection_point_id   BIGINT NOT NULL REFERENCES collection_points (id),  -- origin while in transit
    destination_point_id  BIGINT REFERENCES collection_points (id),           -- set only while in transit
    status                item_status NOT NULL,
    disposition           item_disposition,
    received_at           TIMESTAMPTZ,  -- RN04: 60-day custody starts here
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),  -- RN03: 7-day delivery window starts here
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT items_destination_point_check
        CHECK ((status = 'in_transit') = (destination_point_id IS NOT NULL)),
    CONSTRAINT items_destination_differs_check
        CHECK (destination_point_id <> collection_point_id),
    CONSTRAINT items_disposition_check
        CHECK ((status = 'disposed') = (disposition IS NOT NULL)),
    CONSTRAINT items_received_at_check
        CHECK ((status IN ('registered', 'cancelled')) = (received_at IS NULL))
);
CREATE INDEX items_status_idx ON items (status);
CREATE INDEX items_category_id_idx ON items (category_id);
CREATE INDEX items_collection_point_id_idx ON items (collection_point_id);
CREATE INDEX items_registered_by_idx ON items (registered_by);

-- RN20: 2 to 5 per item (count checked by the application).
-- Plain text on purpose: attendants must see it (RN22) and matching tolerates typos,
-- so a hash would not work. Never expose it outside claim review (RN23).
CREATE TABLE verification_questions (
    id               BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id          BIGINT NOT NULL REFERENCES items (id),
    sort_order       SMALLINT NOT NULL,
    question         TEXT NOT NULL,
    expected_answer  TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (item_id, sort_order),
    CONSTRAINT verification_questions_sort_order_check CHECK (sort_order BETWEEN 1 AND 5)
);

-- ========== Claims ==========

CREATE TABLE claims (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id              BIGINT NOT NULL REFERENCES items (id),
    claimant_id          BIGINT NOT NULL REFERENCES users (id),
    status               claim_status NOT NULL,
    score                NUMERIC(4, 3) NOT NULL,
    rejection_reason     claim_rejection_reason,  -- RN15: only low_score and attendant count as failures
    reviewed_by          BIGINT REFERENCES users (id),
    reviewed_at          TIMESTAMPTZ,
    pickup_code          TEXT,
    pickup_expires_at    TIMESTAMPTZ,  -- RN44
    id_document_checked  BOOLEAN NOT NULL DEFAULT false,  -- RN46
    closed_at            TIMESTAMPTZ,  -- RN15: 30-day failure window counts from here
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT claims_score_check
        CHECK (score BETWEEN 0 AND 1),
    CONSTRAINT claims_closed_at_check
        CHECK ((status IN ('pending', 'approved')) = (closed_at IS NULL)),
    CONSTRAINT claims_rejection_reason_check
        CHECK ((status = 'rejected') = (rejection_reason IS NOT NULL)),
    CONSTRAINT claims_pickup_code_format_check
        CHECK (pickup_code ~ '^[A-Z0-9]{6}$'),
    CONSTRAINT claims_pickup_expires_at_check
        CHECK ((pickup_code IS NULL) = (pickup_expires_at IS NULL)),
    CONSTRAINT claims_pickup_code_required_check
        CHECK (status NOT IN ('approved', 'completed') OR pickup_code IS NOT NULL),
    CONSTRAINT claims_id_document_checked_check
        CHECK (status <> 'completed' OR id_document_checked)
);
-- RN11: one active claim per user and item
CREATE UNIQUE INDEX claims_active_item_claimant_key
    ON claims (item_id, claimant_id) WHERE status IN ('pending', 'approved');
-- RN13: at most one approved claim per item
CREATE UNIQUE INDEX claims_approved_item_key
    ON claims (item_id) WHERE status = 'approved';
-- RN44: pickup codes must not collide among open reservations
CREATE UNIQUE INDEX claims_approved_pickup_code_key
    ON claims (pickup_code) WHERE status = 'approved';
CREATE INDEX claims_item_id_idx ON claims (item_id);
CREATE INDEX claims_claimant_id_status_idx ON claims (claimant_id, status);

-- RN22: attendant compares given and expected answers
CREATE TABLE claim_answers (
    claim_id     BIGINT NOT NULL REFERENCES claims (id),
    question_id  BIGINT NOT NULL REFERENCES verification_questions (id),
    answer       TEXT NOT NULL,
    is_correct   BOOLEAN NOT NULL,
    PRIMARY KEY (claim_id, question_id)
);

-- ========== Lost reports and notifications ==========

CREATE TABLE lost_reports (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id      BIGINT NOT NULL REFERENCES users (id),
    category_id  BIGINT NOT NULL REFERENCES categories (id),
    color_id     BIGINT NOT NULL REFERENCES colors (id),
    location_id  BIGINT NOT NULL REFERENCES locations (id),
    description  TEXT NOT NULL,
    lost_on      DATE NOT NULL,
    status       lost_report_status NOT NULL DEFAULT 'active',
    closed_at    TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),  -- RN33: expires 60 days from here
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT lost_reports_closed_at_check
        CHECK ((status = 'active') = (closed_at IS NULL))
);
CREATE INDEX lost_reports_status_category_id_idx ON lost_reports (status, category_id);
CREATE INDEX lost_reports_user_id_idx ON lost_reports (user_id);

CREATE TABLE notifications (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    type            notification_type NOT NULL,
    message         TEXT NOT NULL,
    item_id         BIGINT REFERENCES items (id),
    lost_report_id  BIGINT REFERENCES lost_reports (id),
    read_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT notifications_match_refs_check
        CHECK (type <> 'match' OR (item_id IS NOT NULL AND lost_report_id IS NOT NULL))
);
-- RN31: a lost report x item pair never notifies twice
CREATE UNIQUE INDEX notifications_match_key
    ON notifications (lost_report_id, item_id) WHERE type = 'match';
CREATE INDEX notifications_unread_user_id_idx
    ON notifications (user_id) WHERE read_at IS NULL;

-- ========== Custody history ==========

CREATE TABLE custody_events (
    id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    item_id              BIGINT NOT NULL REFERENCES items (id),
    type                 custody_event_type NOT NULL,
    collection_point_id  BIGINT NOT NULL REFERENCES collection_points (id),
    actor_id             BIGINT REFERENCES users (id),  -- NULL when triggered by the deadline job
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX custody_events_item_id_created_at_idx ON custody_events (item_id, created_at);

-- RN43: custody history is immutable
CREATE TRIGGER custody_events_prevent_modification
    BEFORE UPDATE OR DELETE ON custody_events
    FOR EACH ROW EXECUTE FUNCTION prevent_modification();

-- ========== updated_at triggers ==========

CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER collection_points_set_updated_at
    BEFORE UPDATE ON collection_points FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER locations_set_updated_at
    BEFORE UPDATE ON locations FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER categories_set_updated_at
    BEFORE UPDATE ON categories FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER colors_set_updated_at
    BEFORE UPDATE ON colors FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER items_set_updated_at
    BEFORE UPDATE ON items FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER claims_set_updated_at
    BEFORE UPDATE ON claims FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER lost_reports_set_updated_at
    BEFORE UPDATE ON lost_reports FOR EACH ROW EXECUTE FUNCTION set_updated_at();
