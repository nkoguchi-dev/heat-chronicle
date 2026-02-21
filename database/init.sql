CREATE DATABASE heat_db
    LOCALE_PROVIDER = 'ICU'
    ICU_LOCALE = 'ja'
    TEMPLATE = template0;

\connect heat_db;
CREATE ROLE heat_user LOGIN PASSWORD 'heat_user';

CREATE SCHEMA heat AUTHORIZATION heat_user;
GRANT ALL PRIVILEGES ON SCHEMA heat TO heat_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA heat
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO heat_user;

ALTER ROLE heat_user SET search_path = heat, public;
