const WORKFLOW = "schedule-disclosures.yml";
const API = "https://api.github.com";

function corsHeaders(env) {
  return {
    "Access-Control-Allow-Origin": env.ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Content-Type": "application/json; charset=utf-8",
    Vary: "Origin",
  };
}

function json(env, body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: corsHeaders(env) });
}

async function github(env, path, init = {}) {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${env.GITHUB_TOKEN}`,
      "User-Agent": "kabu-daily-update-worker",
      "X-GitHub-Api-Version": "2022-11-28",
      ...init.headers,
    },
  });
  if (!response.ok) {
    console.error("GitHub API error", response.status, await response.text());
    throw new Error(`GitHub API returned ${response.status}`);
  }
  return response;
}

async function findRun(env, requestId) {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const response = await github(env, `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${WORKFLOW}/runs?event=workflow_dispatch&per_page=20`);
    const { workflow_runs: runs } = await response.json();
    const run = runs.find((item) => item.display_title?.includes(requestId));
    if (run) return run;
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error("The dispatched workflow run was not found");
}

async function startUpdate(env) {
  const requestId = crypto.randomUUID();
  await github(env, `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${WORKFLOW}/dispatches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ref: env.GITHUB_REF, inputs: { request_id: requestId } }),
  });
  const run = await findRun(env, requestId);
  return { run_id: run.id, status: run.status };
}

async function getUpdate(env, runId) {
  if (!/^\d+$/.test(runId || "")) return json(env, { error: "run_idが不正です。" }, 400);
  const response = await github(env, `/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs/${runId}`);
  const run = await response.json();
  return json(env, {
    status: run.status,
    conclusion: run.conclusion,
    error: run.status === "completed" && run.conclusion !== "success" ? "GitHub Actionsの更新処理が正常終了しませんでした。" : undefined,
  });
}

export default {
  async fetch(request, env) {
    const headers = corsHeaders(env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (request.headers.get("Origin") !== env.ALLOWED_ORIGIN) return json(env, { error: "許可されていないアクセスです。" }, 403);
    try {
      const url = new URL(request.url);
      if (request.method === "GET" && url.pathname === "/health") {
        return json(env, {
          ok: Boolean(env.GITHUB_TOKEN && env.GITHUB_OWNER && env.GITHUB_REPO && env.GITHUB_REF),
          repository: `${env.GITHUB_OWNER}/${env.GITHUB_REPO}`,
          workflow: WORKFLOW,
        });
      }
      if (request.method === "POST") return json(env, await startUpdate(env), 202);
      if (request.method === "GET") return getUpdate(env, url.searchParams.get("run_id"));
      return json(env, { code: "method_not_allowed", error: "この操作は許可されていません。" }, 405);
    } catch (error) {
      console.error(error);
      return json(env, { error: "更新処理を開始または確認できませんでした。" }, 502);
    }
  },
};
