drop index if exists google_oauth_connections_connection_key_key;

create unique index if not exists google_oauth_connections_connection_key_google_account_email_key
  on google_oauth_connections (connection_key, google_account_email);
