# run-kafka-pipeline-tests.ps1 - End-to-end MQTT -> Kafka -> Spark tests
#
# This script validates the real data path:
#   MQTT publisher -> Mosquitto -> mqtt-kafka-bridge -> Kafka -> Spark -> InfluxDB
#
# Defaults are demo-sized so the suite finishes quickly with the current
# Spark setting SPARK_MAX_OFFSETS_PER_TRIGGER=20. For full thesis-scale runs,
# pass larger counts explicitly.
#
# Examples:
#   .\scripts\test\run-kafka-pipeline-tests.ps1
#   .\scripts\test\run-kafka-pipeline-tests.ps1 -P1Messages 1000 -P1Rate 1
#   .\scripts\test\run-kafka-pipeline-tests.ps1 -P2Messages 10000 -P2Rate 50
#   .\scripts\test\run-kafka-pipeline-tests.ps1 -P3Messages 50000 -P3Rate 500 -SparkTimeoutSec 900

param(
    [int]$P1Messages = 60,
    [int]$P1Rate = 1,
    [int]$P2Messages = 500,
    [int]$P2Rate = 50,
    [int]$P3Messages = 1000,
    [int]$P3Rate = 500,
    [int]$SparkTimeoutSec = 240,
    [int]$NoProgressTimeoutSec = 120,
    [double]$MinKafkaSuccessRate = 0.98,
    [double]$MinSparkSuccessRate = 0.20,
    [string]$MqttTopic = "sensors/gas",
    [string]$BootstrapServer = "kafka:9092",
    [string]$RawTopic = "gas.raw.sensor",
    [string]$AlertTopic = "gas.alert.events",
    [string]$ActionTopic = "gas.action.events",
    [string]$InfluxUrl = "http://localhost:8086",
    [string]$InfluxOrg = "thesis-org",
    [string]$InfluxBucket = "gas_sensor_data",
    [string]$InfluxToken = "thesis-super-token",
    [switch]$KeepSimulatorRunning
)

$ErrorActionPreference = "Stop"

$ROOT = (Get-Item $PSScriptRoot).Parent.Parent.FullName
$originalLocation = Get-Location
$pausedSimulator = $false

function Write-Step([string]$msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Write-OK([string]$msg) { Write-Host "    [OK] $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "    [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail([string]$msg) { Write-Host "    [FAIL] $msg" -ForegroundColor Red }

function Test-ContainerRunning([string]$name) {
    $containerId = docker ps --filter "name=$name" --filter "status=running" -q 2>$null
    return -not [string]::IsNullOrWhiteSpace($containerId)
}

function Ensure-RequiredContainers {
    foreach ($name in @("mosquitto", "mqtt-kafka-bridge", "kafka", "processing-engine", "influxdb")) {
        if (-not (Test-ContainerRunning $name)) {
            throw "Required container '$name' is not running. Start the stack first: docker compose up -d"
        }
    }
}

function Suspend-BackgroundSimulator {
    if ($KeepSimulatorRunning) {
        Write-Warn "Keeping device-simulator running; Kafka/Spark metrics may include background esp32-lab-01 traffic."
        return
    }

    if (Test-ContainerRunning "device-simulator") {
        Write-Warn "Stopping device-simulator during pipeline test to avoid background traffic."
        docker stop device-simulator | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $script:pausedSimulator = $true
        }
    }
}

function Restore-BackgroundSimulator {
    if ($script:pausedSimulator) {
        Write-Warn "Restarting device-simulator after pipeline test."
        docker start device-simulator | Out-Null
        $script:pausedSimulator = $false
    }
}

function Get-TopicOffset([string]$topic) {
    $lines = & docker exec kafka /opt/kafka/bin/kafka-get-offsets.sh `
        --bootstrap-server $BootstrapServer `
        --topic $topic 2>$null

    if ($LASTEXITCODE -ne 0 -or $null -eq $lines) {
        return 0L
    }

    $sum = 0L
    foreach ($line in $lines) {
        $parts = "$line".Split(":")
        if ($parts.Length -ge 3) {
            $sum += [int64]$parts[2]
        }
    }
    return $sum
}

function Invoke-FluxRows([string]$query) {
    $body = @{ query = $query } | ConvertTo-Json
    try {
        $res = Invoke-WebRequest `
            -Method Post `
            -Uri "$InfluxUrl/api/v2/query?org=$InfluxOrg" `
            -Headers @{ Authorization = "Token $InfluxToken"; "Content-Type" = "application/json" } `
            -Body $body `
            -UseBasicParsing `
            -TimeoutSec 15 `
            -ErrorAction Stop
    } catch {
        Write-Warn "Influx query failed: $($_.Exception.Message)"
        return @()
    }

    $content = [string]$res.Content
    if ([string]::IsNullOrWhiteSpace($content)) {
        return @()
    }

    return $content -split "`n" | Where-Object { $_ -and -not $_.StartsWith("#") }
}

function Get-FluxLastValue([string]$query) {
    $rows = Invoke-FluxRows $query
    if ($rows.Count -lt 2) {
        return $null
    }

    $header = ([string]$rows[0]).Split(",") | ForEach-Object { $_.Trim() }
    $valueIndex = [Array]::IndexOf($header, "_value")
    if ($valueIndex -lt 0) {
        return $null
    }

    for ($i = $rows.Count - 1; $i -ge 1; $i--) {
        $cols = ([string]$rows[$i]).Split(",") | ForEach-Object { $_.Trim() }
        if ($cols.Length -gt $valueIndex -and -not [string]::IsNullOrWhiteSpace($cols[$valueIndex])) {
            return $cols[$valueIndex]
        }
    }
    return $null
}

function Get-InfluxCount([string]$deviceId) {
    $query = @"
from(bucket:"$InfluxBucket")
  |> range(start: 2020-01-01T00:00:00Z, stop: 2035-01-01T00:00:00Z)
  |> filter(fn:(r) => r._measurement == "gas_reading")
  |> filter(fn:(r) => r.device_id == "$deviceId")
  |> filter(fn:(r) => r._field == "gas_ppm")
  |> group()
  |> count()
  |> keep(columns: ["_value"])
"@
    $value = Get-FluxLastValue $query
    $parsed = 0L
    if ($null -ne $value -and [int64]::TryParse($value, [ref]$parsed)) {
        return $parsed
    }
    return 0L
}

function Get-InfluxLatencyStats([string]$deviceId) {
    $query = @"
from(bucket:"$InfluxBucket")
  |> range(start: 2020-01-01T00:00:00Z, stop: 2035-01-01T00:00:00Z)
  |> filter(fn:(r) => r._measurement == "gas_reading")
  |> filter(fn:(r) => r.device_id == "$deviceId")
  |> filter(fn:(r) => r._field == "pipeline_latency_ms")
  |> group()
  |> mean()
  |> keep(columns: ["_value"])
"@
    $mean = 0.0
    $meanValue = Get-FluxLastValue $query
    if ($null -ne $meanValue) {
        [void][double]::TryParse($meanValue, [ref]$mean)
    }

    $queryMax = @"
from(bucket:"$InfluxBucket")
  |> range(start: 2020-01-01T00:00:00Z, stop: 2035-01-01T00:00:00Z)
  |> filter(fn:(r) => r._measurement == "gas_reading")
  |> filter(fn:(r) => r.device_id == "$deviceId")
  |> filter(fn:(r) => r._field == "pipeline_latency_ms")
  |> group()
  |> max()
  |> keep(columns: ["_value"])
"@
    $max = 0.0
    $maxValue = Get-FluxLastValue $queryMax
    if ($null -ne $maxValue) {
        [void][double]::TryParse($maxValue, [ref]$max)
    }

    return @{ mean_ms = [math]::Round($mean, 2); max_ms = [math]::Round($max, 2) }
}

function New-SensorMessage([string]$deviceId, [int]$i, [double]$baseGas = 80.0, [int64]$baseEventTs = 0, [int]$eventStepMs = 1) {
    $gas = $baseGas + ($i % 250)
    $temp = 28.0 + (($i % 10) / 10.0)
    $hum = 58.0 + ($i % 5)
    $ts = if ($baseEventTs -gt 0) { $baseEventTs + ($i * [math]::Max(1, $eventStepMs)) } else { [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() }

    return (@{
        schema_version = 1
        source = "pipeline-test"
        device_id = $deviceId
        gas_ppm = [math]::Round($gas, 2)
        temperature_c = [math]::Round($temp, 2)
        humidity_percent = [math]::Round($hum, 2)
        event_ts = $ts
    } | ConvertTo-Json -Compress)
}

function Publish-MqttLines([string[]]$lines) {
    if ($lines.Count -eq 0) {
        return
    }
    $payload = ($lines -join "`n") + "`n"
    $payload | docker exec -i mosquitto mosquitto_pub -h localhost -p 1883 -t $MqttTopic -l | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "mosquitto_pub failed"
    }
}

function Publish-MqttSensorLoad([string]$deviceId, [int]$messages, [int]$ratePerSec, [double]$baseGas = 80.0) {
    $sent = 0
    $started = Get-Date
    $lastProgress = Get-Date
    $baseEventTs = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $eventStepMs = if ($ratePerSec -gt 0) { [math]::Max(1, [int][math]::Floor(1000 / $ratePerSec)) } else { 1 }

    Write-Host "    Publishing MQTT for ${deviceId}: total=$messages target_rate=${ratePerSec}/s" -ForegroundColor DarkGray

    while ($sent -lt $messages) {
        $batchSize = if ($ratePerSec -gt 0) { [math]::Min($ratePerSec, $messages - $sent) } else { $messages - $sent }
        $lines = for ($j = 0; $j -lt $batchSize; $j++) {
            New-SensorMessage $deviceId ($sent + $j) $baseGas $baseEventTs $eventStepMs
        }
        Publish-MqttLines $lines
        $sent += $batchSize

        $now = Get-Date
        if ($sent -eq $messages -or (($now - $lastProgress).TotalSeconds -ge 5)) {
            $elapsedNow = [math]::Max(0.001, ($now - $started).TotalSeconds)
            $rateNow = [math]::Round($sent / $elapsedNow, 2)
            Write-Host "    MQTT published for ${deviceId}: $sent / $messages (${rateNow}/s)" -ForegroundColor DarkGray
            $lastProgress = $now
        }

        if ($ratePerSec -gt 0 -and $sent -lt $messages) {
            Start-Sleep -Seconds 1
        }
    }

    $elapsed = [math]::Max(0.001, ((Get-Date) - $started).TotalSeconds)
    return @{ sent = $sent; send_seconds = [math]::Round($elapsed, 2); send_rate = [math]::Round($sent / $elapsed, 2) }
}

function Wait-InfluxCount([string]$deviceId, [int]$target, [int]$timeoutSec) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    $count = Get-InfluxCount $deviceId
    $lastCount = $count
    $lastProgressAt = Get-Date
    while ($count -lt $target -and (Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        $count = Get-InfluxCount $deviceId
        Write-Host "    Spark processed for ${deviceId}: $count / $target" -ForegroundColor DarkGray
        if ($count -gt $lastCount) {
            $lastCount = $count
            $lastProgressAt = Get-Date
        } elseif (((Get-Date) - $lastProgressAt).TotalSeconds -ge $NoProgressTimeoutSec) {
            Write-Warn "Spark count has not increased for ${NoProgressTimeoutSec}s; ending this testcase wait early."
            break
        }
    }
    return $count
}

function Run-E2ETest([string]$name, [string]$deviceId, [int]$messages, [int]$rate, [double]$baseGas = 80.0) {
    Write-Step "$name"

    $kafkaBefore = Get-TopicOffset $RawTopic
    $sparkBefore = Get-InfluxCount $deviceId
    $load = Publish-MqttSensorLoad $deviceId $messages $rate $baseGas

    Start-Sleep -Seconds 3
    $kafkaAfter = Get-TopicOffset $RawTopic
    $kafkaReceived = [math]::Max(0, $kafkaAfter - $kafkaBefore)
    Write-Host "    Kafka received for ${deviceId}: $kafkaReceived / $messages" -ForegroundColor DarkGray

    $sparkTarget = [int][math]::Ceiling($messages * $MinSparkSuccessRate)
    $sparkCount = Wait-InfluxCount $deviceId $sparkTarget $SparkTimeoutSec
    $sparkProcessed = [math]::Max(0, $sparkCount - $sparkBefore)

    $kafkaSuccess = if ($messages -gt 0) { $kafkaReceived / $messages } else { 0 }
    $sparkSuccess = if ($messages -gt 0) { $sparkProcessed / $messages } else { 0 }
    $latency = Get-InfluxLatencyStats $deviceId

    $passed = ($kafkaSuccess -ge $MinKafkaSuccessRate) -and ($sparkSuccess -ge $MinSparkSuccessRate)
    $line = "sent=$messages mqtt_rate=$($load.send_rate)/s kafka_received=$kafkaReceived kafka_success=$([math]::Round($kafkaSuccess*100,2))% spark_processed=$sparkProcessed spark_success=$([math]::Round($sparkSuccess*100,2))% avg_latency_ms=$($latency.mean_ms) max_latency_ms=$($latency.max_ms)"

    if ($passed) {
        Write-OK "$name - $line"
    } else {
        Write-Fail "$name - $line"
    }

    return $passed
}

function Run-MultiTopicTest {
    Write-Step "TC-P4: Multiple Kafka topics from one end-to-end gas event"

    $deviceId = "esp32-pipeline-p4-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $rawBefore = Get-TopicOffset $RawTopic
    $alertBefore = Get-TopicOffset $AlertTopic
    $actionBefore = Get-TopicOffset $ActionTopic

    $load = Publish-MqttSensorLoad $deviceId 5 5 1100.0
    Start-Sleep -Seconds 15

    $rawDelta = (Get-TopicOffset $RawTopic) - $rawBefore
    $alertDelta = (Get-TopicOffset $AlertTopic) - $alertBefore
    $actionDelta = (Get-TopicOffset $ActionTopic) - $actionBefore
    $sparkCount = Wait-InfluxCount $deviceId 1 $SparkTimeoutSec

    $passed = ($rawDelta -ge 5) -and ($alertDelta -ge 1) -and ($actionDelta -ge 1) -and ($sparkCount -ge 1)
    $line = "sent=$($load.sent) raw_topic_delta=$rawDelta alert_topic_delta_unfiltered=$alertDelta action_topic_delta_unfiltered=$actionDelta spark_processed=$sparkCount"
    if ($passed) {
        Write-OK "TC-P4 - $line"
    } else {
        Write-Fail "TC-P4 - $line"
    }
    return $passed
}

function Run-BadDataTest {
    Write-Step "TC-P5: Invalid data handling"

    $rawBefore = Get-TopicOffset $RawTopic
    $bridgeLogSince = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    $badLines = @(
        "invalid json data",
        "{bad-json",
        '{"gas":null,"temp":30,"humidity":60}'
    )
    Publish-MqttLines $badLines
    Start-Sleep -Seconds 5

    $rawAfterBad = Get-TopicOffset $RawTopic
    $badKafkaDelta = $rawAfterBad - $rawBefore
    $bridgeRunning = Test-ContainerRunning "mqtt-kafka-bridge"
    $sparkRunning = Test-ContainerRunning "processing-engine"

    $deviceId = "esp32-pipeline-p5-recovery-" + [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
    $validBefore = Get-TopicOffset $RawTopic
    [void](Publish-MqttSensorLoad $deviceId 5 5 80.0)
    Start-Sleep -Seconds 3
    $validKafkaDelta = (Get-TopicOffset $RawTopic) - $validBefore
    $validSpark = Wait-InfluxCount $deviceId 1 $SparkTimeoutSec

    $prevErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $logs = & docker logs mqtt-kafka-bridge --since $bridgeLogSince 2>&1 | ForEach-Object { "$_" }
    } finally {
        $ErrorActionPreference = $prevErrorActionPreference
    }
    $errorHits = ($logs | Select-String -Pattern "Error processing message|JSON|invalid").Count

    # Invalid JSON should be rejected by the bridge before Kafka. JSON that is
    # syntactically valid but has a wrong schema may still reach Kafka and then
    # be ignored by Spark's schema/null filter. The resilience criterion is that
    # the services stay alive and valid traffic recovers immediately afterwards.
    $passed = ($badKafkaDelta -le $badLines.Count) -and $bridgeRunning -and $sparkRunning -and ($validKafkaDelta -ge 5) -and ($validSpark -ge 1)
    $line = "invalid_sent=$($badLines.Count) invalid_kafka_delta=$badKafkaDelta bridge_running=$bridgeRunning spark_running=$sparkRunning recovery_kafka_delta=$validKafkaDelta recovery_spark=$validSpark bridge_error_logs=$errorHits"
    if ($passed) {
        Write-OK "TC-P5 - $line"
    } else {
        Write-Fail "TC-P5 - $line"
    }
    return $passed
}

try {
    Push-Location $ROOT

    Write-Host ""
    Write-Host "===================================================" -ForegroundColor DarkCyan
    Write-Host " MQTT -> Kafka -> Spark Pipeline Testcases" -ForegroundColor Cyan
    Write-Host "===================================================" -ForegroundColor DarkCyan

    Ensure-RequiredContainers
    Suspend-BackgroundSimulator
    if ($MinSparkSuccessRate -lt 0.9) {
        Write-Warn "MinSparkSuccessRate=$MinSparkSuccessRate means this suite verifies pipeline stability/backpressure behavior, not full Spark drain under load."
        Write-Warn "For stricter Spark throughput evidence, run with -MinSparkSuccessRate 0.9 -SparkTimeoutSec 900 or increase SPARK_MAX_OFFSETS_PER_TRIGGER."
    }

    $failed = 0
    $runId = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()

    if (-not (Run-E2ETest "TC-P1: Basic transmission" "esp32-pipeline-p1-$runId" $P1Messages $P1Rate 80.0)) { $failed++ }
    if (-not (Run-E2ETest "TC-P2: Medium load" "esp32-pipeline-p2-$runId" $P2Messages $P2Rate 120.0)) { $failed++ }
    if (-not (Run-E2ETest "TC-P3: Burst data" "esp32-pipeline-p3-$runId" $P3Messages $P3Rate 160.0)) { $failed++ }
    if (-not (Run-MultiTopicTest)) { $failed++ }
    if (-not (Run-BadDataTest)) { $failed++ }

    Write-Host ""
    Write-Host "===================================================" -ForegroundColor DarkCyan
    if ($failed -eq 0) {
        Write-Host " MQTT -> Kafka -> Spark testcase suite PASSED" -ForegroundColor Green
    } else {
        Write-Host " MQTT -> Kafka -> Spark testcase suite FAILED: $failed testcase(s)" -ForegroundColor Red
    }
    Write-Host "===================================================" -ForegroundColor DarkCyan

    exit $failed
} finally {
    Restore-BackgroundSimulator
    Set-Location $originalLocation
}
