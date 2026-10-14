CREATE TABLE IF NOT EXISTS food_datasets (
 id bigserial PRIMARY KEY, sha256 text NOT NULL UNIQUE, metadata jsonb NOT NULL,
 imported_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS food_nutrients (
 dataset_id bigint REFERENCES food_datasets(id), code text, metadata jsonb NOT NULL,
 PRIMARY KEY(dataset_id,code)
);
CREATE TABLE IF NOT EXISTS foods (
 dataset_id bigint REFERENCES food_datasets(id), code text CHECK(code ~ '^[0-9]{5}$'),
 name_ja text NOT NULL, food_group text NOT NULL, source jsonb NOT NULL,
 PRIMARY KEY(dataset_id,code)
);
CREATE TABLE IF NOT EXISTS food_values (
 dataset_id bigint NOT NULL, food_code text NOT NULL, nutrient_code text NOT NULL,
 value numeric, raw text NOT NULL, status text NOT NULL,
 estimated boolean NOT NULL, footnote text,
 PRIMARY KEY(dataset_id,food_code,nutrient_code),
 FOREIGN KEY(dataset_id,food_code) REFERENCES foods(dataset_id,code),
 FOREIGN KEY(dataset_id,nutrient_code) REFERENCES food_nutrients(dataset_id,code),
 CHECK (status IN ('numeric','trace','blank','not_reported','asterisk_unresolved')),
 CHECK ((status='numeric' AND value IS NOT NULL AND value>=0) OR (status<>'numeric' AND value IS NULL))
);
