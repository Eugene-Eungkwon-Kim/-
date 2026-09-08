/**
 * Performance measurement utilities for benchmark testing
 */

export interface PerformanceMetrics {
  min: number;
  max: number;
  avg: number;
  median: number;
  p50: number;
  p95: number;
  p99: number;
  samples: number;
}

export interface LoadTestResult {
  endpoint: string;
  scenario: string;
  concurrency: number;
  totalRequests: number;
  successCount: number;
  failureCount: number;
  errorRate: number;
  latency: PerformanceMetrics;
  duration: number;
  throughput: number; // requests per second
}

export function calculateMetrics(latencies: number[]): PerformanceMetrics {
  if (latencies.length === 0) {
    throw new Error('No latencies provided');
  }

  const sorted = [...latencies].sort((a, b) => a - b);
  const len = sorted.length;

  const min = sorted[0];
  const max = sorted[len - 1];
  const avg = sorted.reduce((a, b) => a + b, 0) / len;

  const medianIdx = Math.floor(len / 2);
  const median = len % 2 === 0 ? (sorted[medianIdx - 1] + sorted[medianIdx]) / 2 : sorted[medianIdx];

  const p50Idx = Math.floor(len * 0.5);
  const p50 = sorted[p50Idx];

  const p95Idx = Math.floor(len * 0.95);
  const p95 = sorted[p95Idx];

  const p99Idx = Math.floor(len * 0.99);
  const p99 = sorted[Math.min(p99Idx, len - 1)];

  return {
    min: Math.round(min * 100) / 100,
    max: Math.round(max * 100) / 100,
    avg: Math.round(avg * 100) / 100,
    median: Math.round(median * 100) / 100,
    p50: Math.round(p50 * 100) / 100,
    p95: Math.round(p95 * 100) / 100,
    p99: Math.round(p99 * 100) / 100,
    samples: len,
  };
}

export interface ConcurrentLoadTestConfig {
  endpoint: string;
  method: string;
  payload?: Record<string, unknown>;
  headers?: Record<string, string>;
  concurrency: number;
  totalRequests: number;
  requestFactory?: (index: number) => {
    method: string;
    url: string;
    payload?: Record<string, unknown>;
    headers?: Record<string, string>;
  };
}

export async function simulateConcurrentLoad(
  requestFn: (config: any) => Promise<{ statusCode: number; latency?: number }>,
  config: ConcurrentLoadTestConfig
): Promise<LoadTestResult> {
  const latencies: number[] = [];
  let successCount = 0;
  let failureCount = 0;

  const startTime = performance.now();

  // Simulate concurrent requests by chunking them
  const chunkSize = config.concurrency;
  const chunks = Math.ceil(config.totalRequests / chunkSize);

  for (let chunkIdx = 0; chunkIdx < chunks; chunkIdx++) {
    const requestsInChunk = Math.min(chunkSize, config.totalRequests - chunkIdx * chunkSize);
    const promises: Promise<void>[] = [];

    for (let i = 0; i < requestsInChunk; i++) {
      const requestIdx = chunkIdx * chunkSize + i;
      const requestConfig = config.requestFactory
        ? config.requestFactory(requestIdx)
        : {
            method: config.method,
            url: config.endpoint,
            payload: config.payload,
            headers: config.headers,
          };

      promises.push(
        (async () => {
          const reqStart = performance.now();
          try {
            const result = await requestFn(requestConfig);
            const latency = performance.now() - reqStart;
            latencies.push(latency);

            if (result.statusCode >= 200 && result.statusCode < 300) {
              successCount++;
            } else {
              failureCount++;
            }
          } catch (error) {
            failureCount++;
            const latency = performance.now() - reqStart;
            latencies.push(latency);
          }
        })()
      );
    }

    // Wait for all requests in this chunk to complete
    await Promise.all(promises);
  }

  const endTime = performance.now();
  const duration = endTime - startTime;

  return {
    endpoint: config.endpoint,
    scenario: `${config.concurrency} concurrent, ${config.totalRequests} total`,
    concurrency: config.concurrency,
    totalRequests: config.totalRequests,
    successCount,
    failureCount,
    errorRate: (failureCount / config.totalRequests) * 100,
    latency: calculateMetrics(latencies),
    duration: Math.round(duration * 100) / 100,
    throughput: Math.round((config.totalRequests / duration) * 1000 * 100) / 100,
  };
}

export function formatMetricsTable(results: LoadTestResult[]): string {
  const header = '| Endpoint | Scenario | p50 (ms) | p95 (ms) | p99 (ms) | Throughput (req/s) | Error Rate |';
  const separator = '|----------|----------|----------|----------|----------|-------------------|-----------|';

  const rows = results
    .map(
      (r) =>
        `| ${r.endpoint.padEnd(25)} | ${r.scenario.padEnd(35)} | ${r.latency.p50.toString().padEnd(6)} | ${r.latency.p95.toString().padEnd(6)} | ${r.latency.p99.toString().padEnd(6)} | ${r.throughput.toString().padEnd(17)} | ${r.errorRate.toFixed(2)}% |`
    )
    .join('\n');

  return `${header}\n${separator}\n${rows}`;
}
