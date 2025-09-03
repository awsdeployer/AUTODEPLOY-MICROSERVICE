import os
import tempfile
import subprocess
import re
import shutil
import json
import requests
from flask import Flask, request, jsonify, send_from_directory, session
from flask import Blueprint, redirect

# --------------------------
# Config
# --------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

# Frontend folder (deployer_frontend is sibling of deployer)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../deployer_frontend")

# Docker & Kubernetes binaries
DOCKER_BIN = shutil.which("docker") or "/usr/bin/docker"
KUBECTL_BIN = shutil.which("kubectl") or "/usr/bin/kubectl"
KUBECONFIG = os.environ.get("KUBECONFIG", os.path.expanduser("~/.kube/config"))

# --------------------------
# MONITORING URL
# --------------------------
MONITOR_URL = os.environ.get("MONITOR_URL", "http://flask-monitor:6000/monitor/log")

def log_to_monitor(user_id, service, endpoint, action_type, request_data, response_summary):
    try:
        # Mask sensitive info
        if isinstance(request_data, dict):
            for key in ["access_key", "secret_key", "docker_token", "password"]:
                if key in request_data:
                    request_data[key] = "****"
        requests.post(MONITOR_URL, json={
            "user_id": user_id,
            "service": service,
            "endpoint": endpoint,
            "action_type": action_type,
            "request_data": request_data,
            "response_summary": response_summary,
            "ip_address": request.remote_addr if request else "",
            "user_agent": request.headers.get("User-Agent", "") if request else ""
        }, timeout=1)
    except:
        pass

# --------------------------
# Blueprint
# --------------------------
deployer_bp = Blueprint("deployer_bp", __name__, url_prefix="/deployer-api")

# --------------------------
# Docker Login
# --------------------------
@deployer_bp.route("/docker-login", methods=["POST"])
def docker_login():
    data = request.json
    user = data.get("docker_user")
    token = data.get("docker_token")
    masked_data = {"docker_user": user, "docker_token": "****"}

    if not user or not token:
        log_to_monitor(
            user_id=user or "anonymous",
            service="Deployer",
            endpoint="/deployer-api/docker-login",
            action_type="docker-login",
            request_data=masked_data,
            response_summary={"success": False, "error": "Missing username or token"}
        )
        return jsonify({"success": False, "error": "Missing username or token"}), 400

    try:
        cmd = [DOCKER_BIN, "login", "-u", user, "--password-stdin"]
        proc = subprocess.run(cmd, input=token.encode(), capture_output=True)
        success = proc.returncode == 0
        logs = proc.stdout.decode() + proc.stderr.decode()

        log_to_monitor(
            user_id=user,
            service="Deployer",
            endpoint="/deployer-api/docker-login",
            action_type="docker-login",
            request_data=masked_data,
            response_summary={"success": success, "error": None if success else logs[:500]}
        )

        if not success:
            return jsonify({"success": False, "error": logs}), 400

    except Exception as e:
        log_to_monitor(
            user_id=user,
            service="Deployer",
            endpoint="/deployer-api/docker-login",
            action_type="docker-login",
            request_data=masked_data,
            response_summary={"success": False, "error": str(e)}
        )
        return jsonify({"success": False, "error": str(e)}), 500

    session["docker_user"] = user
    session["docker_token"] = token
    return jsonify({"success": True, "message": f"Logged in to Docker Hub as {user}"})


# --------------------------
# Docker Logout
# --------------------------
@deployer_bp.route("/docker-logout", methods=["POST"])
def docker_logout():
    user = session.get("docker_user", "anonymous")
    session.pop("docker_user", None)
    session.pop("docker_token", None)

    log_to_monitor(
        user_id=user,
        service="Deployer",
        endpoint="/deployer-api/docker-logout",
        action_type="docker-logout",
        request_data={},
        response_summary={"success": True}
    )

    return jsonify({"success": True})


# --------------------------
# Validate Flask code
# --------------------------
@deployer_bp.route("/validate", methods=["POST"])
def validate():
    data = request.json
    code = data.get("code", "")
    app_name = data.get("app_name", "flaskapp")

    if not code.strip():
        return jsonify({"success": False, "valid": False, "reason": "No code provided"})

    if "Flask" not in code or "app =" not in code:
        return jsonify({"success": False, "valid": False, "reason": "Code does not look like a Flask app"})

    log_to_monitor(
        user_id=session.get("docker_user", "anonymous"),
        service="Deployer",
        endpoint="/deployer-api/validate",
        action_type="validate-code",
        request_data={"app_name": app_name},
        response_summary={"valid": True}
    )

    return jsonify({"success": True, "valid": True, "app_name": app_name})


# --------------------------
# Deploy
# --------------------------
@deployer_bp.route("/deploy", methods=["POST"])
def deploy():
    user = session.get("docker_user", "anonymous")
    if "docker_user" not in session or "docker_token" not in session:
        return jsonify({"success": False, "error": "Not logged into Docker Hub"}), 401

    data = request.json
    raw_app_name = data.get("app_name", "flaskapp")
    app_name = re.sub(r'[^a-z0-9-]', '-', raw_app_name.lower()).strip('-')
    code = data.get("code", "")
    k8s_kind = data.get("k8s_kind", "Deployment")
    replicas = int(data.get("replicas", 2))
    service_type = data.get("service_type", "NodePort")
    container_port = int(data.get("container_port", 5000))
    namespace = data.get("namespace", "default")
    docker_user = session["docker_user"]
    remote_tag = f"{docker_user}/{app_name}:latest"
    logs = []
    service_url_hint = ""

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            app_path = os.path.join(tmpdir, "app.py")
            dockerfile_path = os.path.join(tmpdir, "Dockerfile")

            with open(app_path, "w") as f:
                f.write(code)

            with open(dockerfile_path, "w") as f:
                f.write(f"""
FROM python:3.10-slim
WORKDIR /app
COPY app.py /app/
RUN pip install flask
ENV FLASK_RUN_PORT={container_port}
CMD ["python", "app.py"]
""")

            # Build image
            cmd = [DOCKER_BIN, "build", "-t", remote_tag, tmpdir]
            proc = subprocess.run(cmd, capture_output=True)
            logs.append(proc.stdout.decode() + proc.stderr.decode())
            if proc.returncode != 0:
                return jsonify({"success": False, "error": "Docker build failed", "logs": logs})

            # Push image
            cmd = [DOCKER_BIN, "push", remote_tag]
            proc = subprocess.run(cmd, capture_output=True)
            logs.append(proc.stdout.decode() + proc.stderr.decode())
            if proc.returncode != 0:
                return jsonify({"success": False, "error": "Docker push failed", "logs": logs})

            # Create K8s manifest
            node_port = 30000 + (hash(app_name) % 1000)
            deployment_yaml = f"""
apiVersion: apps/v1
kind: {k8s_kind}
metadata:
  name: {app_name}
  namespace: {namespace}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_name}
  template:
    metadata:
      labels:
        app: {app_name}
    spec:
      containers:
      - name: {app_name}
        image: {remote_tag}
        ports:
        - containerPort: {container_port}
---
apiVersion: v1
kind: Service
metadata:
  name: {app_name}-svc
  namespace: {namespace}
spec:
  selector:
    app: {app_name}
  ports:
  - port: {container_port}
    targetPort: {container_port}
    protocol: TCP
    {"nodePort: " + str(node_port) if service_type == "NodePort" else ""}
  type: {service_type}
"""

            manifest_file = os.path.join(tmpdir, "manifest.yaml")
            with open(manifest_file, "w") as f:
                f.write(deployment_yaml)

            # Apply manifest
            cmd = [KUBECTL_BIN, "--kubeconfig", KUBECONFIG, "apply", "-f", manifest_file]
            proc = subprocess.run(cmd, capture_output=True)
            logs.append(proc.stdout.decode() + proc.stderr.decode())
            if proc.returncode != 0:
                return jsonify({
                    "success": False,
                    "error": "kubectl apply failed",
                    "logs": logs,
                    "manifest": deployment_yaml
                })

            # Get service info
            svc_info = subprocess.getoutput(f"{KUBECTL_BIN} --kubeconfig {KUBECONFIG} get svc {app_name}-svc -n {namespace} -o json")
            try:
                svc_json = json.loads(svc_info)
                ip = None
                port = container_port

                if service_type == "NodePort":
                    ip = subprocess.getoutput("hostname -I").split()[0]
                    port = svc_json['spec']['ports'][0]['nodePort']
                elif service_type == "LoadBalancer":
                    ingress = svc_json.get('status', {}).get('loadBalancer', {}).get('ingress', [])
                    if ingress:
                        ip = ingress[0].get('ip') or ingress[0].get('hostname')
                    else:
                        ip = svc_json['spec']['clusterIP']
                    port = svc_json['spec']['ports'][0]['port']
                elif service_type == "ClusterIP":
                    ip = svc_json['spec']['clusterIP']
                    port = svc_json['spec']['ports'][0]['port']

                service_url_hint = f"http://{ip}:{port}/" if ip else "(Check service manually)"
            except:
                service_url_hint = "(Check service manually)"

    except Exception as e:
        return jsonify({"success": False, "error": str(e), "logs": logs})

    log_to_monitor(
        user_id=user,
        service="Deployer",
        endpoint="/deployer-api/deploy",
        action_type="deploy-app",
        request_data={"app_name": app_name, "namespace": namespace, "replicas": replicas},
        response_summary={"success": True, "image": remote_tag, "service_url_hint": service_url_hint[:500]}
    )

    return jsonify({
        "success": True,
        "image": remote_tag,
        "logs": logs,
        "manifest": deployment_yaml,
        "service_url_hint": service_url_hint
    })

# --------------------------
# Register blueprint
# --------------------------
app.register_blueprint(deployer_bp)

# --------------------------
# Serve frontend
# --------------------------
@app.route("/deployer/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/deployer/<path:path>")
def serve_frontend(path):
    return send_from_directory(FRONTEND_DIR, path)


@app.route("/")
def root_redirect():
    return redirect("/deployer/")


# --------------------------
# Run
# --------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

