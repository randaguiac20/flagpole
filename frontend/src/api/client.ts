// Typed API client. Spec: 002-flagpole-web FR-004, FR-014 (types generated from the 001 contract).
import createClient from "openapi-fetch";
import type { Middleware } from "openapi-fetch";
import type { paths } from "./schema";

export type Flag = paths["/flags"]["get"]["responses"]["200"]["content"]["application/json"][number];
export type EnvState = Flag["environments"]["dev"];
export type Env = keyof Flag["environments"];
export type AuditPage = paths["/audit"]["get"]["responses"]["200"]["content"]["application/json"];
export type AuditEntry = AuditPage["items"][number];

export interface ApiOptions {
  baseUrl?: string;
  getToken: () => string | null;
  onUnauthenticated: () => void;
}

export interface ApiError {
  detail: string;
}

export function createApi({ baseUrl = "/api", getToken, onUnauthenticated }: ApiOptions) {
  const client = createClient<paths>({ baseUrl });

  const auth: Middleware = {
    onRequest({ request }) {
      const token = getToken();
      if (token) request.headers.set("Authorization", `Bearer ${token}`);
      return request;
    },
    onResponse({ response }) {
      if (response.status === 401) onUnauthenticated();
      return response;
    },
  };
  client.use(auth);

  const detail = (error: unknown, fallback: string): string =>
    (error as ApiError | undefined)?.detail ?? fallback;

  return {
    async listFlags(): Promise<Flag[]> {
      const { data, error } = await client.GET("/flags");
      if (error) throw new Error(detail(error, "could not load flags"));
      return data ?? [];
    },
    async createFlag(key: string, description: string): Promise<Flag> {
      const { data, error } = await client.POST("/flags", { body: { key, description } });
      if (error) throw new Error(detail(error, "could not create the flag"));
      return data!;
    },
    async setEnvState(key: string, env: Env, state: EnvState): Promise<Flag> {
      const { data, error } = await client.PUT("/flags/{key}/env/{env}", {
        params: { path: { key, env } },
        body: state,
      });
      if (error) throw new Error(detail(error, "could not save the flag"));
      return data!;
    },
    async listAudit(params: { limit?: number; before?: number; flag_key?: string } = {}): Promise<AuditPage> {
      const { data, error } = await client.GET("/audit", { params: { query: params } });
      if (error) throw new Error(detail(error, "could not load the audit log"));
      return data!;
    },
  };
}

export type Api = ReturnType<typeof createApi>;
