type HealthResponse = {
  status: string;
  service: string;
  environment: string;
  version: string;
};

const backendInternalUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function fetchHealth(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(`${backendInternalUrl}/api/health`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const health = await fetchHealth();

  return (
    <main className="page">
      <section className="hero">
        <p className="eyebrow">Web App Standard</p>
        <h1>FastAPI と Next.js の開発基盤</h1>
        <p className="lead">
          このリポジトリは、バックエンドとフロントエンドを分離した Web
          アプリ開発の土台です。必要な実装をここから積み上げていけます。
        </p>
      </section>

      <section className="grid">
        <article className="card">
          <h2>Frontend</h2>
          <p>Next.js App Router の最小ページを配置しています。</p>
          <a href="http://localhost:3000" target="_blank" rel="noreferrer">
            http://localhost:3000
          </a>
        </article>

        <article className="card">
          <h2>Backend</h2>
          <p>FastAPI の最小 API と Swagger UI を配置しています。</p>
          <a href={`${apiBaseUrl}/docs`} target="_blank" rel="noreferrer">
            {apiBaseUrl}/docs
          </a>
        </article>

        <article className="card status">
          <h2>Backend Health</h2>
          {health ? (
            <dl>
              <div>
                <dt>Status</dt>
                <dd>{health.status}</dd>
              </div>
              <div>
                <dt>Service</dt>
                <dd>{health.service}</dd>
              </div>
              <div>
                <dt>Environment</dt>
                <dd>{health.environment}</dd>
              </div>
              <div>
                <dt>Version</dt>
                <dd>{health.version}</dd>
              </div>
            </dl>
          ) : (
            <p>
              バックエンドに接続できませんでした。`docker compose up --build`
              で両方のサービスを起動してください。
            </p>
          )}
        </article>
      </section>
    </main>
  );
}
