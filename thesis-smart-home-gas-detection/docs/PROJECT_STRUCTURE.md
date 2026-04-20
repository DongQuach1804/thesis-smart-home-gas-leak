# Project Structure (Clean-Slate Thesis)

```text
thesis-smart-home-gas-detection/
├── .github/
│   └── workflows/                     # CI workflows (lint/test/build/deploy)
├── application/                       # Layer 4: Application
│   ├── backend/                       # Node.js + TS + Express API
│   │   ├── src/
│   │   │   ├── config/                # Env and app config modules
│   │   │   ├── controllers/           # API handlers
│   │   │   ├── middlewares/           # Auth, validation, error handlers
│   │   │   ├── repositories/          # DB access abstraction
│   │   │   ├── routes/                # Route definitions
│   │   │   ├── services/              # Business logic
│   │   │   ├── types/                 # Shared TS types/interfaces
│   │   │   └── utils/                 # Utility functions
│   │   ├── tests/                     # Backend unit/integration tests
│   │   ├── package.json               # Backend dependency and scripts
│   │   └── tsconfig.json              # TS compiler setup
│   └── frontend/                      # Express + EJS web dashboard
│       ├── public/                    # CSS/JS/assets static files
│       │   ├── assets/
│       │   ├── css/
│       │   └── js/
│       ├── views/                     # EJS templates
│       ├── package.json               # Frontend runtime deps/scripts
│       └── server.js                  # Frontend Express server
├── communication/                     # Layer 2: Communication
│   ├── bridges/                       # Protocol bridge services
│   │   ├── mqtt_kafka_bridge.py       # MQTT -> Kafka bridge
│   │   └── requirements-bridge.txt    # Bridge dependencies
│   ├── kafka/                         # Kafka topic/docs/config placeholders
│   ├── mqtt/                          # MQTT topic/docs/config placeholders
│   └── schemas/                       # JSON/Avro schema definitions
├── deploy/
│   ├── compose/                       # Optional split compose files
│   └── docker/                        # Dockerfiles by subsystem
│       ├── backend/
│       ├── communication/
│       ├── device/
│       ├── frontend/
│       └── processing/
├── device/                            # Layer 1: Device
│   ├── esp32-firmware/                # ESP32 firmware source
│   │   ├── include/
│   │   └── src/
│   └── simulator/                     # Local device simulator
│       ├── requirements.txt
│       └── sensor_simulator.py
├── docs/                              # Thesis docs and architecture notes
│   ├── DATA_FLOW.md
│   ├── PROJECT_STRUCTURE.md
│   └── TECH_STACK_VERSIONS.md
├── infrastructure/                    # Shared infrastructure config
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── provisioning/
│   ├── influxdb/
│   ├── mosquitto/
│   │   └── mosquitto.conf
│   └── postgresql/
│       └── init/
│           └── 01_schema.sql
├── processing/                        # Layer 3: Processing
│   ├── config/                        # Spark/ML runtime config files
│   ├── ml/
│   │   ├── inference/                 # Inference wrappers
│   │   ├── lstm/                      # Pretrained .h5 files
│   │   └── rl/                        # PPO .zip files
│   ├── spark-streaming/
│   │   ├── jobs/                      # Structured Streaming jobs
│   │   └── utils/
│   ├── tests/                         # Processing tests
│   └── requirements-processing.txt    # Python 3.11 processing deps
├── scripts/                           # Dev/prod/test helper scripts
│   ├── db/
│   ├── dev/
│   ├── prod/
│   └── test/
├── .env.example
├── docker-compose.dev.yml
├── docker-compose.yml
└── README.md
```

## Why this structure is thesis-ready
- Strict 4-layer separation makes bug tracing and demo narrative straightforward.
- Communication and processing are decoupled for clearer experiments and benchmarks.
- ML artifacts are isolated under `processing/ml` for reproducibility and model versioning.
- Infrastructure-as-code via Docker Compose makes setup and grading reproducible.
