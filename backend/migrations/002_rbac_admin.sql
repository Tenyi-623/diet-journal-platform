-- Preserve existing users and history; allow new accounts beyond the initial 50.
ALTER TABLE app_users DROP CONSTRAINT app_users_id_check;
CREATE SEQUENCE app_user_id_seq OWNED BY app_users.id;
SELECT setval('app_user_id_seq', GREATEST(COALESCE((SELECT max(id) FROM app_users), 0), 50));
ALTER TABLE app_users ALTER COLUMN id SET DEFAULT nextval('app_user_id_seq');
CREATE TABLE app_roles (id text PRIMARY KEY, name text NOT NULL);
CREATE TABLE app_permissions (id text PRIMARY KEY, name text NOT NULL);
CREATE TABLE app_role_permissions (
 role_id text REFERENCES app_roles(id), permission_id text REFERENCES app_permissions(id),
 PRIMARY KEY(role_id, permission_id)
);
CREATE TABLE app_user_roles (
 user_id integer REFERENCES app_users(id) ON DELETE CASCADE,
 role_id text REFERENCES app_roles(id), PRIMARY KEY(user_id, role_id)
);
INSERT INTO app_roles VALUES
 ('user','普通用户'),('admin','管理员'),('user_manager','用户管理员'),
 ('recipe_editor','菜谱管理员'),('knowledge_editor','知识库管理员');
INSERT INTO app_permissions VALUES
 ('users.manage','管理用户'),('roles.manage','分配管理角色'),
 ('recipes.manage','管理菜谱和图片'),('knowledge.manage','管理知识库');
INSERT INTO app_role_permissions SELECT 'admin',id FROM app_permissions;
INSERT INTO app_role_permissions VALUES
 ('user_manager','users.manage'),('recipe_editor','recipes.manage'),('knowledge_editor','knowledge.manage');
INSERT INTO app_user_roles SELECT id,'user' FROM app_users;
CREATE TABLE app_admin_audit (
 id bigserial PRIMARY KEY, actor_id integer REFERENCES app_users(id),
 action text NOT NULL, target text NOT NULL, detail jsonb NOT NULL DEFAULT '{}',
 created_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE app_recipes ADD COLUMN enabled boolean NOT NULL DEFAULT true;
ALTER TABLE kb_documents ADD COLUMN IF NOT EXISTS enabled boolean NOT NULL DEFAULT true;
CREATE TABLE app_kb_uploads (
 id uuid PRIMARY KEY, created_by integer REFERENCES app_users(id),
 metadata jsonb NOT NULL, sha256 text NOT NULL UNIQUE, file_path text NOT NULL,
 status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','processing','ready','failed')),
 document_id bigint REFERENCES kb_documents(id), error text,
 attempts integer NOT NULL DEFAULT 0, lease_until timestamptz,
 created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX app_kb_uploads_queue ON app_kb_uploads(status,created_at);
