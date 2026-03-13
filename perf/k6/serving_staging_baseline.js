import http from "k6/http";
import { check } from "k6";

const serveUrl = (__ENV.SERVE_URL || "").trim();
const bearerToken = (__ENV.SERVE_BEARER_TOKEN || "").trim();
const sustainedDuration = (__ENV.BASELINE_DURATION || "5m").trim();
const sustainedRate = Number(__ENV.BASELINE_RATE || "1");
const realisticIterations = Number(__ENV.REALISTIC_ITERATIONS || "25");
const payload = JSON.parse(open("./payloads/breast_cancer_clf_prod.json"));
const requestBody = JSON.stringify(payload);

if (!serveUrl) {
  throw new Error("SERVE_URL is required");
}

if (!bearerToken) {
  throw new Error("SERVE_BEARER_TOKEN is required");
}

export const options = {
  scenarios: {
    realistic_predict: {
      executor: "per-vu-iterations",
      exec: "predict",
      vus: 1,
      iterations: realisticIterations,
      maxDuration: "2m",
      tags: {
        scenario: "realistic_predict",
      },
    },
    light_sustained_predict: {
      executor: "constant-arrival-rate",
      exec: "predict",
      startTime: "30s",
      rate: sustainedRate,
      timeUnit: "1s",
      duration: sustainedDuration,
      preAllocatedVUs: 2,
      maxVUs: 4,
      tags: {
        scenario: "light_sustained_predict",
      },
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    checks: ["rate>0.99"],
    "http_req_duration{scenario:realistic_predict}": ["p(95)<1000", "p(99)<1500"],
    "http_req_duration{scenario:light_sustained_predict}": [
      "p(95)<1500",
      "p(99)<2500",
    ],
  },
};

function requestHeaders() {
  return {
    Authorization: `Bearer ${bearerToken}`,
    "Content-Type": "application/json",
  };
}

function predictResponseChecks(response) {
  let body = null;
  try {
    body = response.json();
  } catch (_error) {
    body = null;
  }

  return check(response, {
    "status is 200": (r) => r.status === 200,
    "content-type is json": (r) =>
      String(r.headers["Content-Type"] || "").includes("application/json"),
    "response body is object": () => body !== null && typeof body === "object",
    "response includes one probability": () =>
      body !== null &&
      Array.isArray(body.proba) &&
      body.proba.length === payload.rows.length,
  });
}

function postPredict() {
  return http.post(`${serveUrl}/predict?mode=prod`, requestBody, {
    headers: requestHeaders(),
    tags: {
      endpoint: "/predict",
      mode: "prod",
    },
    timeout: "15s",
  });
}

export function setup() {
  const health = http.get(`${serveUrl}/health`, {
    headers: requestHeaders(),
    tags: {
      endpoint: "/health",
    },
    timeout: "10s",
  });
  check(health, {
    "health is 200": (r) => r.status === 200,
  });

  const metadata = http.get(`${serveUrl}/metadata/model`, {
    headers: requestHeaders(),
    tags: {
      endpoint: "/metadata/model",
    },
    timeout: "10s",
  });
  check(metadata, {
    "metadata is 200": (r) => r.status === 200,
  });

  const warmup = postPredict();
  if (!predictResponseChecks(warmup)) {
    throw new Error(`Warmup predict failed with status=${warmup.status}`);
  }

  return {};
}

export function predict() {
  const response = postPredict();
  predictResponseChecks(response);
}
