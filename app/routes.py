# app/routes.py
from flask import Blueprint, jsonify, request, current_app

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET'])
def home():
    return jsonify({
        "service": "ACEest Fitness & Gym",
        "version": "v1.3",
        "message": "Welcome to ACEest Fitness API"
    }), 200

@bp.route('/healthcheck/live', methods=['GET'])
def liveness():
    # simple liveness: app is running
    return jsonify({"status": "alive"}), 200

@bp.route('/healthcheck/ready', methods=['GET'])
def readiness():
    # readiness: example check for dependencies; here we assume ready
    # Replace with DB/minikube checks later
    return jsonify({"status": "ready"}), 200
