import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest, after } from "next/server";
import { readProviderHeaders, PROVIDER_KEY_INPUT_ERROR } from "@/lib/provider-keys";
import { buildRuntimeOptions } from "@/lib/copilotkit-runtime-options";
import { getLaunchTelemetry, observeRunResult, runtimeMethod } from "@/lib/launch-telemetry";

// Per-IP agent-run limiter. Runtime discovery, reconnects, and stop requests
// must remain available even when the user has exhausted their run allowance.
const RATE_LIMIT_ENABLED = process.env.RATE_LIMIT_ENABLED === "true";
const RATE_LIMIT_WINDOW_MS = Number(process.env.RATE_LIMIT_WINDOW_MS) || 60_000;
const RATE_LIMIT_MAX = Number(process.env.RATE_LIMIT_MAX) || 40;
const hits = new Map<string, number[]>();

function isRateLimited(ip: string): boolean {
  if (!RATE_LIMIT_ENABLED) return false;
  const now = Date.now();
  const timestamps = hits.get(ip)?.filter(t => t > now - RATE_LIMIT_WINDOW_MS) ?? [];
  // Rejected retries do not consume allowance or extend the lockout.
  if (timestamps.length >= RATE_LIMIT_MAX) {
    hits.set(ip, timestamps);
    return true;
  }
  timestamps.push(now);
  hits.set(ip, timestamps);
  return false;
}

// Prune stale entries every 5 min to prevent unbounded memory growth.
if (RATE_LIMIT_ENABLED) {
  setInterval(() => {
    const cutoff = Date.now() - RATE_LIMIT_WINDOW_MS;
    hits.forEach((timestamps, ip) => {
      const recent = timestamps.filter(t => t > cutoff);
      if (recent.length === 0) hits.delete(ip);
      else hits.set(ip, recent);
    });
  }, 300_000);
}

export const POST = async (req: NextRequest) => {
  // Read from a clone: the runtime still receives the original request body.
  const method = await runtimeMethod(req);
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  if (method === "agent/run" && isRateLimited(ip)) {
    return new Response("Too many agent runs. Please wait and retry.", {
      status: 429,
      headers: {
        "Retry-After": String(Math.ceil(RATE_LIMIT_WINDOW_MS / 1000)),
        "Cache-Control": "no-store",
      },
    });
  }

  let providerHeaders;
  try {
    providerHeaders = process.env.PROVIDER_KEYS_MODE === "server" ? undefined : readProviderHeaders(req.headers);
  } catch {
    return Response.json({ error: PROVIDER_KEY_INPUT_ERROR }, { status: 400, headers: { "Cache-Control": "no-store" } });
  }
  // Construct the agent per request so one visitor's keys cannot reach another.
  const runtimeOptions = buildRuntimeOptions({
    langgraphUrl: process.env.LANGGRAPH_DEPLOYMENT_URL,
    mcpServerUrl: process.env.MCP_SERVER_URL,
    providerHeaders,
  });

  const telemetry = getLaunchTelemetry();
  const telemetryProperties = telemetry.runtimeProperties();
  const watchRun = !telemetry.activated && method === "agent/run";

  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    endpoint: "/api/copilotkit",
    serviceAdapter: new ExperimentalEmptyAdapter(),
    runtime: new CopilotRuntime(runtimeOptions),
    ...(telemetryProperties && { properties: { _copilotkit: telemetryProperties } }),
  });

  const response = await handleRequest(req);
  after(telemetry.recordOpened());
  if (!watchRun || !response.body) return response;

  const [client, observer] = response.body.tee();
  after(observeRunResult(observer).then((ok) => (ok ? telemetry.recordActivated() : undefined)));
  return new Response(client, { status: response.status, statusText: response.statusText, headers: response.headers });
};
