export const openApiSpec = {
  openapi: "3.0.3",
  info: {
    title: "Gas Detection API",
    version: "1.0.0",
    description: "API for the smart home gas leak dashboard.",
  },
  servers: [
    {
      url: "http://127.0.0.1:3000",
      description: "Local (127.0.0.1)",
    },
    {
      url: "http://localhost:3000",
      description: "Local (localhost)",
    },
  ],
  tags: [
    { name: "Health" },
    { name: "Dashboard" },
  ],
  paths: {
    "/health": {
      get: {
        tags: ["Health"],
        summary: "Health check",
        responses: {
          "200": {
            description: "OK",
            content: {
              "application/json": {
                schema: { "$ref": "#/components/schemas/HealthStatus" },
              },
            },
          },
        },
      },
    },
    "/api/dashboard/latest": {
      get: {
        tags: ["Dashboard"],
        summary: "Latest reading",
        parameters: [
          {
            name: "device_id",
            in: "query",
            required: false,
            schema: { type: "string" },
            description: "Device ID (optional)",
          },
        ],
        responses: {
          "200": {
            description: "Latest reading",
            content: {
              "application/json": {
                schema: { "$ref": "#/components/schemas/GasReading" },
              },
            },
          },
        },
      },
    },
    "/api/dashboard/history": {
      get: {
        tags: ["Dashboard"],
        summary: "Historical readings",
        parameters: [
          {
            name: "device_id",
            in: "query",
            required: false,
            schema: { type: "string" },
          },
          {
            name: "minutes",
            in: "query",
            required: false,
            schema: { type: "integer", minimum: 1, default: 30 },
          },
          {
            name: "sample_every",
            in: "query",
            required: false,
            schema: { type: "integer", minimum: 1, default: 10 },
          },
        ],
        responses: {
          "200": {
            description: "Historical readings",
            content: {
              "application/json": {
                schema: {
                  type: "array",
                  items: { "$ref": "#/components/schemas/GasReading" },
                },
              },
            },
          },
        },
      },
    },
    "/api/dashboard/overview": {
      get: {
        tags: ["Dashboard"],
        summary: "System overview",
        responses: {
          "200": {
            description: "Pipeline status",
            content: {
              "application/json": {
                schema: { "$ref": "#/components/schemas/SystemOverview" },
              },
            },
          },
        },
      },
    },
    "/api/dashboard/alerts": {
      get: {
        tags: ["Dashboard"],
        summary: "Recent alerts",
        parameters: [
          {
            name: "limit",
            in: "query",
            required: false,
            schema: { type: "integer", minimum: 1, default: 50 },
          },
        ],
        responses: {
          "200": {
            description: "Alert rows",
            content: {
              "application/json": {
                schema: {
                  type: "array",
                  items: { "$ref": "#/components/schemas/AlertRow" },
                },
              },
            },
          },
        },
      },
    },
    "/api/dashboard/actions": {
      get: {
        tags: ["Dashboard"],
        summary: "Recent actions",
        parameters: [
          {
            name: "limit",
            in: "query",
            required: false,
            schema: { type: "integer", minimum: 1, default: 50 },
          },
        ],
        responses: {
          "200": {
            description: "Action rows",
            content: {
              "application/json": {
                schema: {
                  type: "array",
                  items: { "$ref": "#/components/schemas/ActionRow" },
                },
              },
            },
          },
        },
      },
    },
    "/api/dashboard/alerts/stream": {
      get: {
        tags: ["Dashboard"],
        summary: "Alert SSE stream",
        description: "Server-Sent Events stream of alert events.",
        responses: {
          "200": {
            description: "text/event-stream",
            content: {
              "text/event-stream": {
                schema: { type: "string" },
              },
            },
          },
        },
      },
    },
  },
  components: {
    schemas: {
      HealthStatus: {
        type: "object",
        properties: {
          status: { type: "string" },
          service: { type: "string" },
          ts: { type: "string", format: "date-time" },
        },
        required: ["status", "service", "ts"],
      },
      GasReading: {
        type: "object",
        properties: {
          deviceId: { type: "string" },
          gasPpm: { type: "number" },
          temperatureC: { type: "number" },
          humidityPercent: { type: "number" },
          lstmRiskScore: { type: "number" },
          predictedRisk5Min: { type: "number" },
          riskLabel: { type: "string", enum: ["NORMAL", "WARNING", "ALERT"] },
          rlAction: { type: "string", enum: ["NO_OP", "ALERT_USER", "FAN_ON", "CLOSE_VALVE"] },
          rlActionId: { type: "integer" },
          ts: { type: "string", format: "date-time" },
          _source: { type: "string" },
        },
        required: [
          "deviceId",
          "gasPpm",
          "temperatureC",
          "humidityPercent",
          "lstmRiskScore",
          "predictedRisk5Min",
          "riskLabel",
          "rlAction",
          "rlActionId",
          "ts",
        ],
      },
      AlertEvent: {
        type: "object",
        properties: {
          deviceId: { type: "string" },
          gasPpm: { type: "number" },
          predictedRisk5Min: { type: "number" },
          riskLabel: { type: "string" },
          eventTs: { type: "integer", format: "int64" },
          riskScore: { type: "number" },
        },
        required: ["deviceId", "gasPpm", "predictedRisk5Min", "riskLabel", "eventTs", "riskScore"],
      },
      AlertRow: {
        type: "object",
        properties: {
          deviceId: { type: "string" },
          gasPpm: { type: "number" },
          predictedRisk5Min: { type: "number" },
          riskLabel: { type: "string" },
          eventTs: { type: "integer", format: "int64" },
          createdAt: { type: "string", format: "date-time" },
        },
        required: ["deviceId", "gasPpm", "predictedRisk5Min", "riskLabel", "eventTs", "createdAt"],
      },
      ActionRow: {
        type: "object",
        properties: {
          deviceId: { type: "string" },
          action: { type: "string" },
          actionId: { type: "integer" },
          triggerP5: { type: "number" },
          gasPpm: { type: "number" },
          eventTs: { type: "integer", format: "int64" },
          createdAt: { type: "string", format: "date-time" },
        },
        required: ["deviceId", "action", "actionId", "triggerP5", "gasPpm", "eventTs", "createdAt"],
      },
      SystemOverview: {
        type: "object",
        properties: {
          services: { "$ref": "#/components/schemas/ServiceStatus" },
          model: { "$ref": "#/components/schemas/ModelStatus" },
          ts: { type: "string", format: "date-time" },
        },
        required: ["services", "model", "ts"],
      },
      ServiceStatus: {
        type: "object",
        properties: {
          mqtt: { type: "string" },
          kafka: { type: "string" },
          spark: { type: "string" },
          influxdb: { type: "string" },
          postgres: { type: "string" },
        },
        required: ["mqtt", "kafka", "spark", "influxdb", "postgres"],
      },
      ModelStatus: {
        type: "object",
        properties: {
          lstm: { type: "string" },
          forecaster: { type: "string" },
          rl: { type: "string" },
        },
        required: ["lstm", "forecaster", "rl"],
      },
    },
  },
} as const;
