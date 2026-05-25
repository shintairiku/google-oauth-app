create table if not exists google_oauth_connections (
  id uuid primary key default gen_random_uuid(),
  connection_key text not null,
  google_account_email text,
  scopes text[] not null,
  token_type text,
  access_token_expires_at timestamptz,
  encrypted_refresh_token text,
  status text not null,
  error_reason text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint google_oauth_connections_status_check
    check (status in ('connected', 'reauth_required', 'error'))
);

create unique index if not exists google_oauth_connections_connection_key_key
  on google_oauth_connections (connection_key);

create table if not exists google_oauth_states (
  id uuid primary key default gen_random_uuid(),
  state_hash text not null,
  connection_key text not null,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists google_oauth_states_state_hash_key
  on google_oauth_states (state_hash);

alter table google_oauth_connections enable row level security;
alter table google_oauth_states enable row level security;
