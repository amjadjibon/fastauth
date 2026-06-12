import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Counter, Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

const authErrors = new Counter('auth_errors');
const errorRate = new Rate('error_rate');

export const options = {
  scenarios: {
    // Baseline: constant light health-check traffic throughout the run
    health: {
      executor: 'constant-vus',
      vus: 3,
      duration: '1m',
      exec: 'healthCheck',
    },
    // Core: realistic login → /me → refresh user journey, ramping up
    auth: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: 10 },  // ramp up
        { duration: '30s', target: 10 },  // sustain
        { duration: '15s', target: 0 },   // ramp down
      ],
      exec: 'authFlow',
    },
    // Registrations: low-rate constant arrival (rate-limiter is 10/min)
    register: {
      executor: 'constant-arrival-rate',
      rate: 6,
      timeUnit: '1m',
      duration: '1m',
      preAllocatedVUs: 3,
      exec: 'registerUser',
    },
  },
  thresholds: {
    // 95th percentile under 500ms, 99th under 1s
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    // Less than 1% of all requests fail
    error_rate: ['rate<0.01'],
    // Auth flow end-to-end under 2s at p95
    auth_flow_duration_ms: ['p(95)<2000'],
  },
};

// Scenario: GET /livez — tests infrastructure health under steady load.
export function healthCheck() {
  const res = http.get(`${BASE_URL}/livez`);
  check(res, { 'livez 200': (r) => r.status === 200 }) || errorRate.add(1);
  sleep(1);
}

// Scenario: login → GET /me → POST /refresh — full authenticated user journey.
// Each VU creates its own user during init() to avoid rate limiter contention.
export function authFlow() {
  const params = { headers: { 'Content-Type': 'application/json' } };
  const username = `loadtest_${__VU}_${Date.now()}`;
  const password = 'LoadTest123!';

  let accessToken = '';
  let refreshToken = '';

  group('register', () => {
    const res = http.post(
      `${BASE_URL}/auth/register`,
      JSON.stringify({ username, email: `${username}@example.com`, password }),
      params,
    );
    const ok = check(res, { 'register 201': (r) => r.status === 201 });
    if (!ok) {
      authErrors.add(1);
      errorRate.add(1);
      return;
    }
  });

  group('login', () => {
    const res = http.post(
      `${BASE_URL}/auth/login`,
      JSON.stringify({ username, password }),
      params,
    );
    const ok = check(res, {
      'login 200': (r) => r.status === 200,
      'has access_token': (r) => !!r.json('access_token'),
      'has refresh_token': (r) => !!r.json('refresh_token'),
    });
    if (!ok) {
      authErrors.add(1);
      errorRate.add(1);
      return;
    }
    accessToken = res.json('access_token');
    refreshToken = res.json('refresh_token');
  });

  if (!accessToken) return;

  group('/me', () => {
    const res = http.get(`${BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    check(res, {
      '/me 200': (r) => r.status === 200,
      '/me has username': (r) => !!r.json('username'),
    }) || errorRate.add(1);
  });

  group('refresh', () => {
    const res = http.post(
      `${BASE_URL}/auth/refresh`,
      JSON.stringify({ refresh_token: refreshToken }),
      params,
    );
    check(res, {
      'refresh 200': (r) => r.status === 200,
      'refresh has access_token': (r) => !!r.json('access_token'),
    }) || errorRate.add(1);
  });

  sleep(Math.random() * 2 + 0.5);
}

// Scenario: POST /auth/register — tests registration throughput under the rate limiter.
export function registerUser() {
  const n = `u${Math.floor(Math.random() * 1e12)}`;
  const params = { headers: { 'Content-Type': 'application/json' } };
  const res = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify({ username: n, email: `${n}@example.com`, password: 'LoadTest123!' }),
    params,
  );
  check(res, { 'register 201': (r) => r.status === 201 }) || errorRate.add(1);
}
