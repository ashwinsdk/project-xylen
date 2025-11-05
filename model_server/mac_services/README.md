# macOS LaunchDaemons for Project Xylen Model Server

This directory contains macOS LaunchDaemon configurations for running the model server services as system daemons on macOS.

## Files

- `com.projectxylen.modelserver.plist` - Main model server daemon
- `com.projectxylen.datacollector.plist` - Data collection daemon
- `com.projectxylen.continuoustrainer.plist` - Continuous training daemon
- `install.sh` - Automated installation script

## Quick Installation

```bash
cd model_server/mac_services
sudo ./install.sh
```

The installation script will:
1. Create `/usr/local/opt/trading_model` directory
2. Copy all model server files
3. Set up Python virtual environment
4. Install dependencies
5. Install LaunchDaemons

## Manual Installation

### 1. Prepare Installation Directory

```bash
sudo mkdir -p /usr/local/opt/trading_model
sudo mkdir -p /usr/local/opt/trading_model/logs
sudo mkdir -p /usr/local/opt/trading_model/models
sudo mkdir -p /usr/local/opt/trading_model/training_data
```

### 2. Copy Files

```bash
sudo cp ../server.py /usr/local/opt/trading_model/
sudo cp ../model_loader_optimized.py /usr/local/opt/trading_model/
sudo cp ../retrain_optimized.py /usr/local/opt/trading_model/
sudo cp ../continuous_trainer.py /usr/local/opt/trading_model/
sudo cp ../data_collector.py /usr/local/opt/trading_model/
sudo cp ../requirements.txt /usr/local/opt/trading_model/
sudo cp ../models.env.example /usr/local/opt/trading_model/models.env
```

### 3. Setup Python Environment

```bash
cd /usr/local/opt/trading_model
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
sudo nano /usr/local/opt/trading_model/models.env
```

Update the following variables:
- `MODEL_PATH` - Path to your model file
- `MODEL_TYPE` - Model type (lightgbm, onnx, pytorch)
- Memory and threading settings

### 5. Install LaunchDaemons

```bash
sudo cp com.projectxylen.modelserver.plist /Library/LaunchDaemons/
sudo cp com.projectxylen.datacollector.plist /Library/LaunchDaemons/
sudo cp com.projectxylen.continuoustrainer.plist /Library/LaunchDaemons/

sudo chmod 644 /Library/LaunchDaemons/com.projectxylen.*.plist
```

## Service Management

### Start Services

```bash
# Start model server
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.modelserver.plist

# Start data collector
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.datacollector.plist

# Start continuous trainer
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.continuoustrainer.plist
```

### Stop Services

```bash
# Stop model server
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.modelserver.plist

# Stop data collector
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.datacollector.plist

# Stop continuous trainer
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.continuoustrainer.plist
```

### Check Service Status

```bash
# List all Project Xylen services
sudo launchctl list | grep projectxylen

# Check specific service
sudo launchctl list com.projectxylen.modelserver
```

### Restart Services

```bash
# Restart model server
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.modelserver.plist
```

## Logs

Service logs are located at:
- `/usr/local/opt/trading_model/logs/model_server.log`
- `/usr/local/opt/trading_model/logs/model_server.error.log`
- `/usr/local/opt/trading_model/logs/data_collector.log`
- `/usr/local/opt/trading_model/logs/data_collector.error.log`
- `/usr/local/opt/trading_model/logs/continuous_trainer.log`
- `/usr/local/opt/trading_model/logs/continuous_trainer.error.log`

View logs in real-time:
```bash
tail -f /usr/local/opt/trading_model/logs/model_server.log
```

## Troubleshooting

### Service Won't Start

1. Check permissions:
```bash
ls -la /Library/LaunchDaemons/com.projectxylen.*
```

2. Validate plist file:
```bash
plutil -lint /Library/LaunchDaemons/com.projectxylen.modelserver.plist
```

3. Check error logs:
```bash
cat /usr/local/opt/trading_model/logs/model_server.error.log
```

### Python Environment Issues

```bash
# Recreate virtual environment
cd /usr/local/opt/trading_model
rm -rf venv
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Port Already in Use

Check if port 8000 is in use:
```bash
lsof -i :8000
```

Kill the process using the port:
```bash
kill -9 <PID>
```

## Uninstallation

```bash
# Stop and remove services
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.datacollector.plist
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.continuoustrainer.plist

sudo rm /Library/LaunchDaemons/com.projectxylen.*.plist

# Remove installation directory
sudo rm -rf /usr/local/opt/trading_model
```

## Service Configuration

### Model Server
- Process Type: Interactive
- Nice Value: -5 (higher priority)
- Restart: On failure with 10s delay

### Data Collector
- Process Type: Background
- Nice Value: 5 (lower priority)
- Restart: On failure with 10s delay

### Continuous Trainer
- Process Type: Background
- Nice Value: 10 (lowest priority)
- Restart: On failure with 30s delay

## Security Notes

- Services run with system privileges
- Logs are written to `/usr/local/opt/trading_model/logs`
- PrivateTmp is not available on macOS (Linux-only feature)
- Use file permissions to protect sensitive data

## Performance Tuning

Edit plist files to adjust:
- Nice values for process priority
- ThrottleInterval for restart delays
- SoftResourceLimits for file descriptors

After editing, reload the service:
```bash
sudo launchctl unload /Library/LaunchDaemons/com.projectxylen.modelserver.plist
sudo launchctl load /Library/LaunchDaemons/com.projectxylen.modelserver.plist
```
