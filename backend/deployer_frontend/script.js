const usernameSpan = document.getElementById("username");
const logoutBtn = document.getElementById("logout");

const dockerUserEl = document.getElementById("docker-user");
const dockerTokenEl = document.getElementById("docker-token");
const dockerLoginBtn = document.getElementById("docker-login-btn");
const dockerLoginStatus = document.getElementById("docker-login-status");

const deployerUI = document.getElementById("deployer-ui");

const appNameEl = document.getElementById("app-name");
const codeEl = document.getElementById("code");
const validateBtn = document.getElementById("validate");
const validStatus = document.getElementById("valid-status");
const deployBtn = document.getElementById("deploy");
const k8sKindEl = document.getElementById("k8s-kind");
const replicasEl = document.getElementById("replicas");
const serviceTypeEl = document.getElementById("service-type");
const namespaceEl = document.getElementById("namespace");
const resultPre = document.getElementById("result");
const manifestPre = document.getElementById("manifest");
const logsPre = document.getElementById("logs");

// -------------------------
// Docker Logout (top button)
// -------------------------
logoutBtn.onclick = async () => {
  await fetch("/deployer-api/docker-logout", {
    method: "POST",
    credentials: "same-origin"
  });

  deployerUI.style.display = "none";
  document.getElementById("docker-login-panel").style.display = "flex";
  dockerLoginStatus.textContent = "";
  dockerUserEl.value = "";
  dockerTokenEl.value = "";
};

// -------------------------
// Docker login
// -------------------------
dockerLoginBtn.onclick = async () => {
  dockerLoginStatus.textContent = "Logging in...";
  const payload = {
    docker_user: dockerUserEl.value.trim(),
    docker_token: dockerTokenEl.value.trim()
  };

  const res = await fetch("/deployer-api/docker-login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "same-origin"
  });

  const data = await res.json();
  if (data.success) {
    dockerLoginStatus.style.color = "#34d399";
    dockerLoginStatus.textContent = "✅ Docker login successful";
    document.getElementById("docker-login-panel").style.display = "none";
    deployerUI.style.display = "block";
  } else {
    dockerLoginStatus.style.color = "#f87171";
    dockerLoginStatus.textContent = `❌ ${data.error}`;
  }
};

// -------------------------
// Validate code
// -------------------------
validateBtn.onclick = async () => {
  validStatus.textContent = "";
  resultPre.textContent = "";
  manifestPre.textContent = "";
  logsPre.textContent = "";

  const payload = {
    app_name: appNameEl.value || "flaskapp",
    code: codeEl.value || ""
  };

  const res = await fetch("/deployer-api/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "same-origin"
  });

  const data = await res.json();

  if (!data.success) {
    validStatus.style.color = "#f87171";
    validStatus.textContent = data.error || data.reason || "Invalid";
    deployBtn.disabled = true;
    return;
  }

  if (data.valid) {
    validStatus.style.color = "#34d399";
    validStatus.textContent = `Valid ✓ (app: ${data.app_name})`;
    deployBtn.disabled = false;
  } else {
    validStatus.style.color = "#f87171";
    validStatus.textContent = data.reason || "Invalid";
    deployBtn.disabled = true;
  }
};

// -------------------------
// Deploy
// -------------------------
deployBtn.onclick = async () => {
  resultPre.textContent = "Deploying… this will build, push, then kubectl apply.";
  manifestPre.textContent = "";
  logsPre.textContent = "";

  const payload = {
    app_name: appNameEl.value || "flaskapp",
    code: codeEl.value || "",
    k8s_kind: k8sKindEl.value,
    replicas: parseInt(replicasEl.value || "2"),
    service_type: serviceTypeEl.value,
    container_port: 5000,
    namespace: namespaceEl.value || "default"
  };

  const res = await fetch("/deployer-api/deploy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    credentials: "same-origin"
  });

  const data = await res.json();

  if (!data.success) {
    resultPre.textContent = `❌ ${data.error || "Deployment failed"}`;
    if (data.manifest) manifestPre.textContent = data.manifest;
    if (data.logs) logsPre.textContent = Array.isArray(data.logs) ? data.logs.join("\n---\n") : String(data.logs);
    return;
  }

  const url = data.service_url_hint || "(Check: kubectl get svc)";
  resultPre.innerHTML = `
    ✅ Deployed image: ${data.image}<br/>
    🔗 <a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>
  `;

  manifestPre.textContent = data.manifest || "";
  logsPre.textContent = Array.isArray(data.logs) ? data.logs.join("\n---\n") : String(data.logs);
};

