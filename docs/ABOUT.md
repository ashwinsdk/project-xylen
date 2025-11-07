# About Project Xylen

## Overview

Project Xylen is an automated cryptocurrency trading system that uses ensemble machine learning to make trading decisions on Binance Futures markets. The system combines multiple ML models, sophisticated risk management, and real-time monitoring to execute trades automatically.

## Key Features

### Ensemble Machine Learning

- Multiple independent LightGBM models
- Bayesian weighted aggregation
- Confidence-based decision making
- Continuous learning from trade outcomes

### Risk Management

- Configurable position sizing (fixed fraction, Kelly Criterion)
- Automatic stop loss and take profit placement
- Circuit breakers for consecutive losses
- Daily loss limits (percentage and absolute)
- Emergency shutdown on extreme drawdown

### Real-Time Monitoring

- React dashboard with WebSocket updates
- Model health metrics (CPU, memory, latency, confidence)
- Live trade list with P&L tracking
- Performance charts and statistics
- Telegram alerts for critical events

### Distributed Architecture

- Microservices design with Docker
- Horizontally scalable model servers
- Independent service deployment and updates
- Prometheus metrics and Grafana dashboards

## Technology Stack

### Backend

- Python 3.10
- FastAPI (model servers)
- LightGBM with ONNX optimization
- SQLite for persistence
- Pandas and NumPy for data processing
- ccxt for exchange API abstraction

### Frontend

- React 18
- Vite build tool
- Tailwind CSS
- Lucide icons
- Native WebSocket client

### Infrastructure

- Docker and Docker Compose
- Prometheus for metrics
- Grafana for visualization
- Binance Futures API

## Design Principles

### Safety First

- Always test on testnet before mainnet
- Conservative default settings
- Multiple layers of risk checks
- Circuit breakers to prevent runaway losses
- Comprehensive logging and alerting

### Modularity

- Independent model servers
- Pluggable ensemble methods
- Configurable risk parameters
- Extensible feature engineering

### Performance

- ONNX-optimized model inference (5-15ms)
- Async I/O throughout stack
- Efficient data structures
- Horizontal scaling capability

### Transparency

- Detailed logging of all decisions
- Audit trail of trades
- Real-time metrics and monitoring
- Clear rejection reasons for trades

## Use Cases

### Algorithmic Trading

- Automated 24/7 trading
- Emotion-free decision making
- Backtestable strategies
- Risk-controlled execution

### Machine Learning Research

- Ensemble learning experimentation
- Continuous learning implementation
- Feature engineering exploration
- Performance benchmarking

### System Design Study

- Microservices architecture patterns
- Real-time data processing
- WebSocket communication
- Docker orchestration

## System Requirements

### Minimum

- 4GB RAM
- 2 CPU cores
- 10GB disk space
- Stable internet connection

### Recommended

- 8GB RAM
- 4 CPU cores  
- 50GB SSD
- Low-latency network (<50ms to Binance)

## Performance Characteristics

### Latency

- Model inference: 5-15ms
- Ensemble aggregation: <5ms
- Total decision cycle: 60 seconds (configurable)
- WebSocket updates: 60 seconds

### Throughput

- Handle 4+ model servers concurrently
- Process 29+ technical indicators per cycle
- Support multiple timeframes (5m, 15m, 1h)

### Accuracy

- Model accuracy depends on training data quality
- Ensemble typically improves individual model accuracy by 5-10%
- Continuous learning adapts to market changes

## Known Limitations

### Market Conditions

- Performs best in trending markets
- May struggle in choppy sideways markets
- Relies on technical indicators (no fundamental analysis)

### Technical

- Single trading pair at a time (configurable for multi-symbol)
- Requires stable internet connection
- SQLite not suitable for high-frequency trading (can migrate to PostgreSQL)

### Risk

- Cannot predict black swan events
- Subject to exchange downtime and slippage
- Backtesting performance may differ from live trading

## Development Status

**Current Version**: 2.0.0-alpha

**Status**: Active development

**Recent Updates**:
- Enhanced dashboard with detailed metrics
- Fixed confidence/latency display issues
- Added coordinator CPU/memory monitoring
- Improved WebSocket data structure
- Settings panel functionality

**Planned Features**:
- Multi-symbol trading support
- Advanced regime detection
- Alternative execution algorithms (TWAP, VWAP)
- Mobile dashboard app
- Backtesting framework improvements

## Project History

Project Xylen started as an experiment in ensemble learning for cryptocurrency trading. The system has evolved through multiple iterations:

**Phase 1**: Single model prototyping
**Phase 2**: Distributed model servers and ensemble aggregation  
**Phase 3**: Risk management and safety mechanisms
**Phase 4**: Real-time dashboard and monitoring (current)

## Contributing

This is a private/proprietary project. Contributions are managed internally.

## Support and Contact

For technical issues:
1. Check documentation in `docs/` directory
2. Review logs: `docker logs xylen-coordinator`
3. Verify configuration in `config.yaml`
4. Test on Binance testnet first

## License

Proprietary - All rights reserved

## Disclaimer

**TRADING DISCLAIMER**: Cryptocurrency trading carries substantial risk of loss. This software is provided "as is" without warranty. Users are solely responsible for:
- Understanding the code and system behavior
- Testing thoroughly on testnet before using real funds
- Managing risk appropriate to their situation
- Complying with applicable laws and regulations

Past performance does not guarantee future results. The developers are not liable for any financial losses incurred through use of this software.

## Acknowledgments

- Binance for Futures API and testnet
- LightGBM team for excellent ML library
- FastAPI for modern Python web framework
- React team for powerful UI library
- Docker for containerization platform
