#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON="$VENV_DIR/bin/python"
PID_DIR="$PROJECT_DIR/.pids"

# --- Setup ---
setup() {
    # Create venv if missing
    if [ ! -f "$PYTHON" ]; then
        echo "Creating virtual environment..."
        uv venv "$VENV_DIR" --python 3.11
    fi

    # Sync dependencies
    echo "Syncing dependencies..."
    uv pip install -r "$PROJECT_DIR/requirements.txt" --python "$PYTHON" --quiet

    # Initialize database tables and seed data
    echo "Initializing database..."
    $PYTHON setup_db.py

    mkdir -p "$PID_DIR"
    echo "Setup complete."
}

# --- Launch all services ---
launch() {
    setup

    echo "Launching Burst services..."

    # Aggregator (news ingestion)
    $PYTHON main.py &
    echo $! > "$PID_DIR/aggregator.pid"
    echo "  Aggregator started (PID: $!)"

    # Workflow orchestrator
    $PYTHON main_flow.py &
    echo $! > "$PID_DIR/workflow.pid"
    echo "  Workflow started (PID: $!)"

    # Production director
    $PYTHON main_production.py &
    echo $! > "$PID_DIR/production.pid"
    echo "  Production started (PID: $!)"

    # Dashboard
    $PYTHON -m streamlit run dashboard.py \
        --server.port=8501 \
        --server.address=0.0.0.0 \
        --server.headless=true &
    echo $! > "$PID_DIR/dashboard.pid"
    echo "  Dashboard started (PID: $!) → http://localhost:8501"

    echo ""
    echo "All services running. Use './start.sh stop' to shut down."
}

# --- Stop services ---
stop() {
    echo "Stopping Burst services..."
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile")
        name=$(basename "$pidfile" .pid)
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            echo "  Stopped $name (PID: $pid)"
        fi
        rm -f "$pidfile"
    done
    echo "All services stopped."
}

# --- Status ---
status() {
    echo "Burst services:"
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || { echo "  No services tracked."; return; }
        pid=$(cat "$pidfile")
        name=$(basename "$pidfile" .pid)
        if kill -0 "$pid" 2>/dev/null; then
            echo "  $name: running (PID: $pid)"
        else
            echo "  $name: dead"
            rm -f "$pidfile"
        fi
    done
}

# --- Help ---
usage() {
    echo "Burst.fm — AI-powered news platform"
    echo ""
    echo "Usage: ./start.sh <command>"
    echo ""
    echo "  ./start.sh setup    # Create venv, sync deps, init database"
    echo "  ./start.sh launch   # Setup + launch all 4 services"
    echo "  ./start.sh stop     # Graceful shutdown via PID files"
    echo "  ./start.sh status   # Check which services are alive"
    echo "  ./start.sh restart  # Stop + launch"
}

# --- Main ---
case "${1:-help}" in
    setup)   setup ;;
    launch)  launch ;;
    stop)    stop ;;
    status)  status ;;
    restart) stop; sleep 1; launch ;;
    *)       usage ;;
esac
