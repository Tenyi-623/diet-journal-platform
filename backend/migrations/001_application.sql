CREATE TABLE app_users (
 id integer PRIMARY KEY CHECK(id BETWEEN 1 AND 50), login_id text UNIQUE NOT NULL,
 password_hash text NOT NULL, enabled boolean NOT NULL DEFAULT true,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app_sessions (
 token_hash text PRIMARY KEY, user_id integer NOT NULL REFERENCES app_users(id),
 csrf text NOT NULL, expires_at timestamptz NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX app_sessions_user ON app_sessions(user_id);
CREATE TABLE app_login_attempts (key text PRIMARY KEY, attempts integer NOT NULL, window_at timestamptz NOT NULL);
CREATE TABLE app_profiles (
 user_id integer PRIMARY KEY REFERENCES app_users(id), version integer NOT NULL DEFAULT 1,
 data jsonb NOT NULL, updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app_bp (
 id bigserial PRIMARY KEY,user_id integer NOT NULL REFERENCES app_users(id),
 systolic integer NOT NULL CHECK(systolic BETWEEN 50 AND 300),
 diastolic integer NOT NULL CHECK(diastolic BETWEEN 30 AND 200),
 measured_at timestamptz NOT NULL, CHECK(systolic>diastolic)
);
CREATE TABLE app_income_policies (
 id text PRIMARY KEY, version text NOT NULL, lower_jpy bigint NOT NULL,
 upper_jpy bigint, daily_budget integer NOT NULL CHECK(daily_budget>0),
 label text NOT NULL, data jsonb NOT NULL
);
CREATE TABLE app_ingredients (
 code text PRIMARY KEY, dataset_id bigint NOT NULL, name jsonb NOT NULL,
 allergens text[] NOT NULL, price_per_100g numeric NOT NULL CHECK(price_per_100g>0),
 data jsonb NOT NULL, FOREIGN KEY(dataset_id,code) REFERENCES foods(dataset_id,code)
);
CREATE TABLE app_recipes (
 id text PRIMARY KEY, version text NOT NULL, meal text NOT NULL CHECK(meal IN ('breakfast','lunch','dinner')),
 name jsonb NOT NULL, ingredients jsonb NOT NULL, data jsonb NOT NULL
);
CREATE TABLE app_chat_sessions (
 id uuid PRIMARY KEY,user_id integer NOT NULL REFERENCES app_users(id),created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app_chat_messages (
 id bigserial PRIMARY KEY, session_id uuid NOT NULL REFERENCES app_chat_sessions(id),
 role text NOT NULL CHECK(role IN ('user','assistant')),content text NOT NULL,
 data jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app_jobs (
 id uuid PRIMARY KEY,user_id integer NOT NULL REFERENCES app_users(id),
 idempotency_key text NOT NULL, kind text NOT NULL CHECK(kind IN ('plan','chat','substitute')),
 status text NOT NULL CHECK(status IN ('queued','running','ready','needs_clarification','out_of_scope','unsupported','infeasible','failed','cancelled')),
 input jsonb NOT NULL,result jsonb, attempts integer NOT NULL DEFAULT 0,
 created_at timestamptz NOT NULL DEFAULT now(),updated_at timestamptz NOT NULL DEFAULT now(),
 lease_until timestamptz, UNIQUE(user_id,idempotency_key)
);
CREATE INDEX app_jobs_queue ON app_jobs(status,created_at);
CREATE TABLE app_recommendations (
 id uuid PRIMARY KEY,user_id integer NOT NULL REFERENCES app_users(id),
 job_id uuid UNIQUE REFERENCES app_jobs(id),data jsonb NOT NULL,
 created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE app_home_cache (
 user_id integer PRIMARY KEY REFERENCES app_users(id),cache_key text NOT NULL,
 result jsonb NOT NULL,updated_at timestamptz NOT NULL DEFAULT now()
);
