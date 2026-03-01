# Gas Monitoring System

Smart gas monitoring system with real-time ML predictions and Telegram alerts.

## Overview

This system monitors gas sensors (MQ135, MQ5, R1-R8) and environmental conditions (temperature, humidity) using machine learning for predictive analysis and classification. It provides real-time visualization through Grafana dashboards and sends alerts via Telegram bot.

## Tech Stack

- **Node-RED** (Port 1880) - Data collection and flow control
- **InfluxDB 1.8** (Port 8086) - Time-series database
- **Grafana** (Port 3000) - Visualization dashboard
- **FastAPI** (Port 8000) - ML prediction API
- **Telegram Bot** - Alert notifications
- **Docker** - Container orchestration

## Machine Learning Models

### LSTM Regression Models (3 models)
- **CO prediction**: lstm_co_model.h5 (Window: 20 timesteps, Features: 17)
- **Ethanol prediction**: lstm_eth_model_gen.h5 (Window: 20 timesteps, Features: 17)
- **Temperature prediction**: lstm_ht_model.h5 (Window: 20 timesteps, Features: 9)

### SVM Classification Model
- **File**: svm_ht_model_downsampled_10x.pkl
- **Scaler**: ht_sensor_scaler.pkl
- **Classes**: NORMAL, WARNING, DANGER
- **Features**: 10 features from temperature and humidity sensors

## Alert Logic

| Condition | Level | Action |
|-----------|-------|--------|
| CO > 0.7 OR Temperature > 0.8 OR SVM=DANGER | DANGER | Send Telegram alert |
| CO > 0.5 OR Ethanol > 0.6 OR SVM=WARNING | WARNING | Send Telegram alert |
| All OK AND SVM=NORMAL | NORMAL | No alert |

## Quick Start

### Prerequisites
- Docker Desktop installed
- Python 3.10 or higher
- Minimum 4GB RAM

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/DongQuach1804/gas-dashboard.git
cd gas-dashboard
```

2. Create Python virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3. Start Docker services:
```powershell
docker-compose up -d
```

4. Start ML API server:
```powershell
python ml_predictor_hybrid.py
```

5. Access the services:
- Node-RED: http://localhost:1880
- Grafana: http://localhost:3000 (Username: admin, Password: admin)
- API Documentation: http://localhost:8000/docs

## Configuration

### Node-RED Flow

1. Open Node-RED at http://localhost:1880
2. Import the flow file: nodered-flow-ml-api.json
   - Menu > Import > Select a file to import
3. Configure InfluxDB node:
   - Host: influxdb
   - Port: 8086
   - Database: gasdb
   - Username: admin
   - Password: adminpass
4. Deploy the flow

### Grafana Dashboard

1. Login to Grafana at http://localhost:3000
2. Add InfluxDB data source:
   - Configuration > Data Sources > Add data source
   - Type: InfluxDB
   - Query Language: InfluxQL
   - URL: http://influxdb:8086
   - Database: gasdb
   - User: admin
   - Password: adminpass
3. Import dashboard: grafana-dashboard-enhanced-direct.json
   - Create > Import > Upload JSON file

### Telegram Bot (Optional)

To enable Telegram alerts:

1. Create a new bot:
   - Message @BotFather on Telegram
   - Use /newbot command
   - Save the bot token

2. Get your Chat ID:
   - Message @getidsbot on Telegram
   - Save the chat ID

3. Configure Node-RED:
   - Import nodered-flow-telegram.json
   - Configure Telegram bot node with your token and chat ID
   - Deploy the flow

## API Endpoints

### Health Check
```
GET http://localhost:8000/health
```

### Get Models Info
```
GET http://localhost:8000/models
```

### Make Prediction
```
POST http://localhost:8000/predict
Content-Type: application/json

{
  "MQ135": 250.5,
  "MQ5": 150.3,
  "R1": 100.0,
  "R2": 110.5,
  "R3": 105.0,
  "R4": 95.0,
  "R5": 120.0,
  "R6": 98.0,
  "R7": 115.0,
  "R8": 102.0,
  "Temperature": 28.5,
  "Humidity": 65.0
}
```

Response:
```json
{
  "co": 0.42,
  "ethanol": 0.35,
  "temperature": 0.68,
  "svm_classification": {
    "class": "WARNING",
    "confidence": 0.87
  },
  "alert_level": "WARNING",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Data Flow

```
Sensors (MQ135, MQ5, R1-R8, Temp, Humidity)
    |
    v
Node-RED (Data Collection)
    |
    v
InfluxDB (gas_data measurement)
    |
    v
ML API (FastAPI)
    |-- LSTM Models --> Regression Predictions (CO, Ethanol, Temperature)
    |-- SVM Model --> Classification (NORMAL/WARNING/DANGER)
    v
InfluxDB (gas_predictions measurement) + Telegram Alerts
    |
    v
Grafana Dashboard (Visualization)
```

## Project Structure

```
gas-dashboard/
├── ml_predictor_hybrid.py              # FastAPI ML prediction server
├── docker-compose.yml                  # Docker services configuration
├── requirements.txt                    # Python dependencies
│
├── lstm_co_model.h5                    # LSTM model for CO prediction
├── lstm_eth_model_gen.h5               # LSTM model for Ethanol prediction
├── lstm_ht_model.h5                    # LSTM model for Temperature prediction
├── svm_ht_model_downsampled_10x.pkl    # SVM classification model
├── ht_sensor_scaler.pkl                # MinMaxScaler for SVM features
│
├── nodered-flow-ml-api.json            # Main Node-RED flow
├── nodered-flow-telegram.json          # Telegram bot flow
├── grafana-dashboard-enhanced-direct.json  # Grafana dashboard configuration
│
├── SETUP-GUIDE.md                      # Detailed setup instructions
├── DEVELOPER.md                        # Architecture and development guide
├── TROUBLESHOOTING.md                  # Common issues and solutions
│
├── .gitignore                          # Git ignore rules
└── .gitattributes                      # Git attributes for file handling
```

## Important Notes

### Data Folders (Not Included in Repository)

These folders are created automatically when Docker containers start and contain runtime data:

- **nodered_data/** - Node-RED flow data and credentials
- **influxdb_data/** - InfluxDB time-series database files
- **grafana_data/** - Grafana dashboard configurations and database

These folders are excluded from the repository (.gitignore) because they contain:
- Sensitive credentials (Telegram bot tokens, API keys)
- Large database files
- Environment-specific configurations

### Security Considerations

When deploying this system:

1. Change default passwords in docker-compose.yml:
   - InfluxDB admin password
   - Grafana admin password

2. Do not commit sensitive data:
   - Telegram bot tokens
   - API keys
   - Database credentials
   - flows_cred.json file

3. Use environment variables for production deployment

### Model Files

All ML model files are included in the repository:
- LSTM models (.h5 files) - Keras/TensorFlow models
- SVM model (.pkl file) - Scikit-learn model
- Scaler (.pkl file) - Feature preprocessing

These models are pre-trained and ready to use. Training scripts are not included in this repository.

## Development

### Running in Development Mode

```powershell
# Run ML API with auto-reload
uvicorn ml_predictor_hybrid:app --reload --host 0.0.0.0 --port 8000

# View Docker logs
docker logs -f nodered
docker logs -f influxdb
docker logs -f grafana

# Stop all services
docker-compose down

# Restart services
docker-compose restart
```

### Testing the API

Use the FastAPI auto-generated documentation:
- Interactive API docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Troubleshooting

### API Server Not Starting

```powershell
# Reinstall dependencies
pip install -r requirements.txt --upgrade

# Check Python version
python --version  # Should be 3.10+
```

### No Data in Grafana

- Wait 3-4 minutes after starting for data collection to begin
- Verify Node-RED flow is deployed
- Check InfluxDB data:
```powershell
curl "http://localhost:8086/query?db=gasdb&q=SHOW+MEASUREMENTS"
```

### Docker Container Issues

```powershell
# View container status
docker ps -a

# Restart Docker Desktop
# Then restart containers
docker-compose down
docker-compose up -d
```

For more detailed troubleshooting, see TROUBLESHOOTING.md

## Documentation

- **SETUP-GUIDE.md** - Complete installation and configuration guide
- **DEVELOPER.md** - System architecture and API documentation
- **TROUBLESHOOTING.md** - Common problems and solutions

## License

MIT License

## Author

DongQuach1804

## Repository

https://github.com/DongQuach1804/gas-dashboard
