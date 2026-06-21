#!/usr/bin/env python
"""
Single entry point for the Dashboard & Alerts Layer.

Starts the Flask + SocketIO server, initializes the data store,
feature analyzer, alert manager, and health simulator.

Usage:
    python run.py                          # Start with defaults
    python run.py --port 8080             # Custom port
    python run.py --experiment 2          # Use binary experiment (best accuracy)
    python run.py --speed 0.5             # Half-speed simulation
    python run.py --no-alerts             # Disable alert system
"""
import argparse
import sys
import os

# eventlet is optional — falls back to threading mode
try:
    import eventlet
    eventlet.monkey_patch()
except ImportError:
    pass

# Ensure the package root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FLASK_HOST, FLASK_PORT
from dashboard.backend.data_loader import store
from dashboard.backend.feature_analyzer import FeatureAnalyzer
from dashboard.backend.app import create_app, socketio, set_alert_manager, start_simulator
from alerts.alert_manager import AlertManager


def main():
    parser = argparse.ArgumentParser(description="Multimodal Health Dashboard & Alerts")
    parser.add_argument("--port", type=int, default=FLASK_PORT,
                        help=f"Server port (default: {FLASK_PORT})")
    parser.add_argument("--host", type=str, default=FLASK_HOST,
                        help=f"Server host (default: {FLASK_HOST})")
    parser.add_argument("--experiment", type=int, default=1,
                        help="Default experiment ID (1=3-class for alerts, 2=binary best)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Simulation speed multiplier (default: 1.0)")
    parser.add_argument("--no-alerts", action="store_true",
                        help="Disable the alert system")
    parser.add_argument("--debug", action="store_true",
                        help="Enable Flask debug mode")
    args = parser.parse_args()

    print("=" * 60)
    print("  Multimodal Health Monitoring — Dashboard & Alerts Layer")
    print("=" * 60)

    # ---- 1. Load data ----
    print("\n[1/5] Loading Fusion Layer outputs...")
    store.load_all()
    store.set_active_experiment(args.experiment)
    exp = store.get_experiment(args.experiment)
    if exp:
        print(f"      Active experiment: Exp {args.experiment} — {exp.get('config_label', '')}")
        print(f"      Test accuracy: {float(exp.get('test_accuracy', 0)) * 100:.1f}%")

    # ---- 2. Fit feature analyzer ----
    print("\n[2/5] Fitting feature analyzer (PCA)...")
    analyzer = FeatureAnalyzer(store.get_feature_matrix())
    analyzer.fit_pca()
    print(f"      Subjects: {len(store.get_unique_subjects())}")

    # ---- 3. Initialize alerts ----
    alert_manager = None
    if not args.no_alerts:
        print("\n[3/5] Initializing alert system...")
        alert_manager = AlertManager()
        set_alert_manager(alert_manager)
        print("      LED: simulated (console + log)")
        print("      Buzzer: simulated (console + log)")
        print("      Telegram: " + ("configured" if alert_manager._telegram.is_configured() else "DRY-RUN mode"))
    else:
        print("\n[3/5] Alert system DISABLED (--no-alerts)")

    # ---- 4. Create Flask app ----
    print("\n[4/5] Creating Flask + SocketIO application...")
    app = create_app()
    app.config["DEBUG"] = args.debug

    # ---- 5. Start simulator ----
    print("\n[5/5] Starting health data simulator...")
    sim = start_simulator()
    sim.set_speed(args.speed)
    print(f"      Interval: {2.0 / args.speed:.1f}s per sample")

    # ---- Ready ----
    print("\n" + "=" * 60)
    print(f"  Server starting at http://{args.host}:{args.port}")
    print(f"  Dashboard: http://localhost:{args.port}")
    print(f"  API:       http://localhost:{args.port}/api/health_state")
    print("=" * 60)
    print("\nPress Ctrl+C to stop.\n")

    if args.debug:
        socketio.run(app, host=args.host, port=args.port, debug=True)
    else:
        socketio.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
